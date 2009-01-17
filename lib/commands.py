# -*- coding: utf-8 -*-
#
# QBzr - Qt frontend to Bazaar commands
# Copyright (C) 2006 Lukáš Lalinský <lalinsky@gmail.com>
# Copyright (C) 2008, 2009 Alexander Belchenko
#
# This program is free software; you can redistribute it and/or
# modify it under the terms of the GNU General Public License
# as published by the Free Software Foundation; either version 2
# of the License, or (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program; if not, write to the Free Software
# Foundation, Inc., 51 Franklin Street, Fifth Floor, Boston, MA 02110-1301, USA.

import os
import sys
from bzrlib import errors, ui
from bzrlib.option import Option
from bzrlib.commands import Command, register_command, get_cmd_object
import bzrlib.builtins
import bzrlib.ui.text # make sure ui.text is available

from bzrlib.lazy_import import lazy_import
lazy_import(globals(), '''
import signal, shlex, thread

from PyQt4 import QtGui, QtCore

from bzrlib import (
    builtins,
    commands,
    osutils,
    progress,
    )
from bzrlib.util import bencode
from bzrlib.branch import Branch
from bzrlib.bzrdir import BzrDir
from bzrlib.workingtree import WorkingTree

from bzrlib.plugins.qbzr.lib import i18n
from bzrlib.plugins.qbzr.lib.add import AddWindow
from bzrlib.plugins.qbzr.lib.annotate import AnnotateWindow
from bzrlib.plugins.qbzr.lib.browse import BrowseWindow
from bzrlib.plugins.qbzr.lib.cat import QBzrCatWindow, cat_to_native_app
from bzrlib.plugins.qbzr.lib.commit import CommitWindow
from bzrlib.plugins.qbzr.lib.config import QBzrConfigWindow
from bzrlib.plugins.qbzr.lib.diff import DiffWindow
from bzrlib.plugins.qbzr.lib.getupdates import UpdateBranchWindow, UpdateCheckoutWindow
from bzrlib.plugins.qbzr.lib.getnew import GetNewWorkingTreeWindow
from bzrlib.plugins.qbzr.lib.help import show_help
from bzrlib.plugins.qbzr.lib.log import LogWindow
from bzrlib.plugins.qbzr.lib.info import QBzrInfoWindow
from bzrlib.plugins.qbzr.lib.init import QBzrInitWindow
from bzrlib.plugins.qbzr.lib.main import QBzrMainWindow
from bzrlib.plugins.qbzr.lib.pull import (
    QBzrPullWindow,
    QBzrPushWindow,
    QBzrBranchWindow,
    QBzrMergeWindow,
    )
from bzrlib.plugins.qbzr.lib.revert import RevertWindow
from bzrlib.plugins.qbzr.lib.subprocess import SubprocessProgress
from bzrlib.plugins.qbzr.lib.tag import TagWindow
from bzrlib.plugins.qbzr.lib.util import (
    FilterOptions,
    get_set_encoding,
    is_valid_encoding,
    )
''')

from bzrlib.plugins.qbzr.lib import MS_WINDOWS


class InvalidEncodingOption(errors.BzrError):

    _fmt = ('Invalid encoding: %(encoding)s\n'
            'Valid encodings are:\n%(valid)s')

    def __init__(self, encoding):
        errors.BzrError.__init__(self)
        self.encoding = encoding
        import encodings
        self.valid = ', '.join(sorted(list(
            set(encodings.aliases.aliases.values())))).replace('_','-')


def check_encoding(encoding):
    if is_valid_encoding(encoding):
        return encoding
    raise InvalidEncodingOption(encoding)


class PyQt4NotInstalled(errors.BzrError):

    _fmt = ('QBzr require at least PyQt 4.1 and '
            'Qt 4.2 to run. Please check your install')


def report_missing_pyqt(unbound):
    """Decorator for q-commands run method to catch ImportError PyQt4
    and show explanation to user instead of scary traceback.
    See bugs: #240123, #163728
    """
    def run(self, *args, **kwargs):
        try:
            return unbound(self, *args, **kwargs)
        except ImportError, e:
            if str(e).endswith('PyQt4'):
                raise PyQt4NotInstalled
            raise
    return run


def install_gettext(unbound):
    """Decorator for q-commands run method to enable gettext translations."""
    def run(self, *args, **kwargs):
        i18n.install()
        try:
            return unbound(self, *args, **kwargs)
        finally:
            i18n.uninstall()
    return run


class QBzrCommand(Command):
    """Base class for all q-commands.
    NOTE: q-command should define method '_qbzr_run' instead of 'run' (as in
    bzrlib).
    """
    
    @install_gettext
    @report_missing_pyqt
    def run(self, *args, **kwargs):
        return self._qbzr_run(*args, **kwargs)

ui_mode_option = Option("ui-mode", help="Causes dialogs to wait after the operation is complete.")

# A special option so 'revision' can be passed as a simple string, when we do
# *not* wan't bzrlib's feature of parsing the revision string before passing it.
# This is used when we just want a plain string to pass to our dialog for it to
# display in the UI, and we will later pass it to bzr for parsing. If you want
# bzrlib to parse and pass a revisionspec object, just pass the string
# 'revision' as normal.
simple_revision_option = Option("revision",
                             short_name='r',
                             type=unicode,
                             help='See "help revisionspec" for details.')


def bzr_option(cmd_name, opt_name):
    """Helper so we can 'borrow' options from bzr itself without needing to
    duplicate the help text etc.  Pass the builtin bzr command name and an
    option name.

    eg:
      takes_options = [bzr_option("push", "create-prefix")]

    would give a command the exact same '--create-prefix' option as bzr's
    push command has, including help text, parsing, etc.
    """
    from bzrlib.commands import get_cmd_object
    cmd=get_cmd_object(cmd_name, False)
    return cmd.options()[opt_name]


class cmd_qannotate(QBzrCommand):
    """Show the origin of each line in a file."""
    takes_args = ['filename']
    takes_options = ['revision',
                     Option('encoding', type=check_encoding,
                     help='Encoding of files content (default: utf-8).'),
                     ui_mode_option,
                    ]
    aliases = ['qann', 'qblame']

    def _load_branch(self, filename, revision):
        """To assist in getting a UI up as soon as possible, the UI calls
        back to this function to process the command-line args and convert
        them into the branch and tree etc needed by the UI.
        """
        wt, branch, relpath = \
            BzrDir.open_containing_tree_or_branch(filename)
        if wt is not None:
            wt.lock_read()
        else:
            branch.lock_read()
        try:
            if revision is None:
                revision_id = branch.last_revision()
            elif len(revision) != 1:
                raise errors.BzrCommandError('bzr qannotate --revision takes exactly 1 argument')
            else:
                revision_id = revision[0].in_history(branch).rev_id
            tree = branch.repository.revision_tree(revision_id)
            if wt is not None:
                file_id = wt.path2id(relpath)
            else:
                file_id = tree.path2id(relpath)
            if file_id is None:
                raise errors.NotVersionedError(filename)
            entry = tree.inventory[file_id]
            if entry.kind != 'file':
                raise errors.BzrCommandError(
                        'bzr qannotate only works for files (got %r)' % entry.kind)
            #repo = branch.repository
            #w = repo.weave_store.get_weave(file_id, repo.get_transaction())
            #content = list(w.annotate_iter(entry.revision))
            #revision_ids = set(o for o, t in content)
            #revision_ids = [o for o in revision_ids if repo.has_revision(o)]
            #revisions = branch.repository.get_revisions(revision_ids)
        finally:
            if wt is not None:
                wt.unlock()
            else:
                branch.unlock()

        return branch, tree, relpath, file_id

    def _qbzr_run(self, filename=None, revision=None, encoding=None,
                  ui_mode=False):
        app = QtGui.QApplication(sys.argv)
        win = AnnotateWindow(None, None, None, None,
                             encoding=encoding, ui_mode=ui_mode,
                             loader=self._load_branch,
                             loader_args=(filename, revision))
        win.show()
        app.exec_()


class cmd_qadd(QBzrCommand):
    """GUI for adding files or directories."""
    takes_args = ['selected*']
    takes_options = [ui_mode_option]
    
    def _qbzr_run(self, selected_list=None, ui_mode=False):
        tree, selected_list = builtins.tree_files(selected_list)
        if selected_list == ['']:
            selected_list = []
        application = QtGui.QApplication(sys.argv)
        window = AddWindow(tree, selected_list, dialog=False, ui_mode=ui_mode)
        window.show()
        application.exec_()


class cmd_qrevert(QBzrCommand):
    """Revert changes files."""
    takes_args = ['selected*']
    takes_options = [ui_mode_option]

    def _qbzr_run(self, selected_list=None, ui_mode=False):
        tree, selected_list = builtins.tree_files(selected_list)
        if selected_list == ['']:
            selected_list = []
        application = QtGui.QApplication(sys.argv)
        window = RevertWindow(tree, selected_list, dialog=False, ui_mode=ui_mode)
        window.show()
        application.exec_()


class cmd_qbrowse(QBzrCommand):
    """Show inventory."""
    takes_args = ['location?']
    takes_options = ['revision']
    aliases = ['qbw']

    def _qbzr_run(self, revision=None, location=None):
        app = QtGui.QApplication(sys.argv)
        if revision is None:
            win = BrowseWindow(location = location)
        else:
            win = BrowseWindow(location = location, revision = revision[0])
        win.show()
        app.exec_()


class cmd_qcommit(QBzrCommand):
    """GUI for committing revisions."""
    takes_args = ['selected*']
    takes_options = [
            bzr_option('commit', 'message'),
            bzr_option('commit', 'local'),
            ui_mode_option,
            ]
    aliases = ['qci']

    def _qbzr_run(self, selected_list=None, message=None, local=False, ui_mode=False):
        tree, selected_list = builtins.tree_files(selected_list)
        if selected_list == ['']:
            selected_list = []
        application = QtGui.QApplication(sys.argv)
        window = CommitWindow(tree, selected_list, dialog=False,
            message=message, local=local, ui_mode=ui_mode)
        window.show()
        application.exec_()


class cmd_qdiff(QBzrCommand):
    """Show differences in working tree in a GUI window."""
    takes_args = ['file*']
    takes_options = [
        'revision',
        Option('complete', help='Show complete files.'),
        Option('encoding', type=check_encoding,
               help='Encoding of files content (default: utf-8).'),
        Option('added', short_name='A', help='Show diff for added files.'),
        Option('deleted', short_name='K', help='Show diff for deleted files.'),
        Option('modified', short_name='M',
               help='Show diff for modified files.'),
        Option('renamed', short_name='R', help='Show diff for renamed files.'),
        bzr_option('diff', 'old'),
        bzr_option('diff', 'new'),
        ]
    if 'change' in Option.OPTIONS:
        takes_options.append('change')
    aliases = ['qdi']

    def _load_branches(self, revision, file_list, old, new):
        """To assist in getting a UI up as soon as possible, the UI calls
        back to this function to process the command-line args and convert
        them into the branches and trees needed by the UI.

        NOTE: called by a non-UI thread (but its still OK to raise exceptions)
        """
        from bzrlib.builtins import internal_tree_files
        from bzrlib.diff import _get_trees_to_diff

        old_tree, new_tree, specific_files, extra_trees = \
                _get_trees_to_diff(file_list, revision, old, new)
        QtCore.QCoreApplication.processEvents()
        
        if file_list:
            default_location = file_list[0]
        else:
            # If no path is given, the current working tree is used
            default_location = u'.'
        
        if old is None:
            old = default_location
        wt, old_branch, rp = \
            BzrDir.open_containing_tree_or_branch(old)
        QtCore.QCoreApplication.processEvents()
        if new is None:
            new = default_location
        if new != old :
            wt, new_branch, rp = \
                BzrDir.open_containing_tree_or_branch(new)
        else:
            new_branch = old_branch
        QtCore.QCoreApplication.processEvents()
        return old_tree, new_tree, old_branch, new_branch, specific_files

    def _qbzr_run(self, revision=None, file_list=None, complete=False,
            encoding=None,
            added=None, deleted=None, modified=None, renamed=None,
            old=None, new=None, ui_mode=False):

        if revision and len(revision) > 2:
            raise errors.BzrCommandError('bzr qdiff --revision takes exactly'
                                         ' one or two revision specifiers')
        # changes filter
        filter_options = FilterOptions(added=added, deleted=deleted,
            modified=modified, renamed=renamed)
        if not (added or deleted or modified or renamed):
            # if no filter option used then turn all on
            filter_options.all_enable()

        app = QtGui.QApplication(sys.argv)
        window = DiffWindow(loader=self._load_branches,
                            loader_args=(revision, file_list, old, new),
                            complete=complete,
                            encoding=encoding,
                            filter_options=filter_options,
                            ui_mode=ui_mode)
        window.show()
        app.exec_()


class cmd_qlog(QBzrCommand):
    """Show log of a repository, branch, file, or directory in a Qt window.

    By default show the log of the branch containing the working directory.
    
    If multiple files are speciffied, they must be from the same branch.
    Only one repository may be speciffied.
    If multiple branches are speciffied, they must be from the same repository.

    :Examples:
        Log the current branch::

            bzr qlog

        Log of files::

            bzr qlog foo.c bar.c

        Log from different branches::

            bzr qlog ~/repo/branch1 ~/repo/branch2
    """

    takes_args = ['locations*']
    takes_options = [ui_mode_option]

    def _qbzr_run(self, locations_list, ui_mode=False):
        app = QtGui.QApplication(sys.argv)
        window = LogWindow(locations_list, None, None, ui_mode=ui_mode)
        window.show()
        app.exec_()


class cmd_qconfig(QBzrCommand):
    """Configure Bazaar."""

    takes_args = []
    takes_options = []
    aliases = ['qconfigure']

    def _qbzr_run(self):
        app = QtGui.QApplication(sys.argv)
        window = QBzrConfigWindow()
        window.show()
        app.exec_()


class cmd_qcat(QBzrCommand):
    """View the contents of a file as of a given revision.

    If no revision is nominated, the last revision is used.
    """

    takes_options = [
        'revision',
        Option('encoding', type=check_encoding,
               help='Encoding of files content (default: utf-8).'),
        Option('native',
               help='Show file with native application.'),
        ]
    takes_args = ['filename']

    def _qbzr_run(self, filename, revision=None, encoding=None, native=None):
        if revision is not None and len(revision) != 1:
            raise errors.BzrCommandError("bzr qcat --revision takes exactly"
                                         " one revision specifier")

        if native:
            branch, relpath = Branch.open_containing(filename)
            if revision is None:
                tree = branch.basis_tree()
            else:
                revision_id = revision[0].in_branch(branch).rev_id
                tree = branch.repository.revision_tree(revision_id)
            result = cat_to_native_app(tree, relpath)
            return int(not result)


        app = QtGui.QApplication(sys.argv)
        window = QBzrCatWindow(filename = filename, revision = revision,
                               encoding = encoding)
        window.show()
        app.exec_()


class cmd_qpull(QBzrCommand):
    """Turn this branch into a mirror of another branch."""

    takes_options = [
        'remember', 'overwrite',
        simple_revision_option,
        bzr_option('pull', 'directory'),
        ui_mode_option,
        ]
    takes_args = ['location?']

    def _qbzr_run(self, location=None, directory=None,
                  remember=None, overwrite=None, revision=None, ui_mode=False):
        if directory is None:
            directory = u'.'
        try:
            tree_to = WorkingTree.open_containing(directory)[0]
            branch_to = tree_to.branch
        except errors.NoWorkingTree:
            tree_to = None
            branch_to = Branch.open_containing(directory)[0]
        app = QtGui.QApplication(sys.argv)
        window = QBzrPullWindow(branch_to, tree_to, location,
                                remember=remember,
                                overwrite=overwrite,
                                revision=revision,
                                ui_mode=ui_mode)
        window.show()
        app.exec_()


class cmd_qmerge(QBzrCommand):
    """Perform a three-way merge."""

    takes_options = [ui_mode_option,
                     simple_revision_option,
                     bzr_option('merge', 'directory'),
                     'remember']
    takes_args = ['location?']

    def _qbzr_run(self, location=None, directory=None, revision=None,
                  remember=None, ui_mode=False):
        if directory is None:
            directory = u'.'
        try:
            tree_to = WorkingTree.open_containing(directory)[0]
            branch_to = tree_to.branch
        except errors.NoWorkingTree:
            tree_to = None
            branch_to = Branch.open_containing(directory)[0]
        app = QtGui.QApplication(sys.argv)
        window = QBzrMergeWindow(branch_to, tree_to, location, revision=revision,
                                 remember=remember, ui_mode=ui_mode)
        window.show()
        app.exec_()


class cmd_qpush(QBzrCommand):
    """Update a mirror of this branch."""

    takes_options = ['remember', 'overwrite',
                     bzr_option("push", "create-prefix"),
                     bzr_option("push", "use-existing-dir"),
                     bzr_option("push", "directory"),
                     ui_mode_option]
    takes_args = ['location?']

    def _qbzr_run(self, location=None, directory=None,
                  remember=None, overwrite=None,
                  create_prefix=None, use_existing_dir=None,
                  ui_mode=False):

        if directory is None:
            directory = u'.'
        
        branch, relpath = Branch.open_containing(directory)
        app = QtGui.QApplication(sys.argv)
        window = QBzrPushWindow(branch, location,
                                create_prefix=create_prefix,
                                use_existing_dir=use_existing_dir,
                                remember=remember,
                                overwrite=overwrite,
                                ui_mode=ui_mode)
        window.show()
        app.exec_()


class cmd_qbranch(QBzrCommand):
    """Create a new copy of a branch."""

    takes_options = [simple_revision_option,
                     ui_mode_option]
    takes_args = ['from_location?', 'to_location?']

    def _qbzr_run(self, from_location=None, to_location=None,
                  revision=None, ui_mode=False):
        app = QtGui.QApplication(sys.argv)
        window = QBzrBranchWindow(from_location, to_location,
                                  revision=revision, ui_mode=ui_mode)
        window.show()
        app.exec_()


class cmd_qinfo(QBzrCommand):

    takes_options = []
    takes_args = []

    def _qbzr_run(self):
        tree, relpath = WorkingTree.open_containing('.')
        app = QtGui.QApplication(sys.argv)
        window = QBzrInfoWindow(tree)
        window.show()
        app.exec_()


class cmd_qinit(QBzrCommand):
    """Initializes a new (possibly shared) repository."""

    takes_options = [ui_mode_option]
    takes_args = ['location?']

    def _qbzr_run(self, location='.', ui_mode=False):
        app = QtGui.QApplication(sys.argv)
        window = QBzrInitWindow(location, ui_mode=ui_mode)
        window.show()
        app.exec_()


class cmd_merge(bzrlib.builtins.cmd_merge):
    __doc__ = bzrlib.builtins.cmd_merge.__doc__

    takes_options = bzrlib.builtins.cmd_merge.takes_options + [
            Option('qpreview', help='Instead of merging, '
                'show a diff of the merge in a GUI window.'),
            Option('encoding', type=check_encoding,
                   help='Encoding of files content, used with --qpreview '
                        '(default: utf-8).'),
            ]

    def run(self, *args, **kw):
        self.qpreview = ('qpreview' in kw)
        if self.qpreview:
            kw['preview'] = kw['qpreview']
            del kw['qpreview']
        self._encoding = kw.get('encoding')
        if self._encoding:
            del kw['encoding']
        return bzrlib.builtins.cmd_merge.run(self, *args, **kw)

    @install_gettext
    @report_missing_pyqt
    def _do_qpreview(self, merger):
        from bzrlib.diff import show_diff_trees
        tree_merger = merger.make_merger()
        tt = tree_merger.make_preview_transform()
        try:
            result_tree = tt.get_preview_tree()
            
            application = QtGui.QApplication(sys.argv)
            window = DiffWindow(merger.this_tree, result_tree,
                encoding=self._encoding)
            window.show()
            application.exec_()
        finally:
            tt.finalize()

    def _do_preview(self, merger):
        if self.qpreview:
            self._do_qpreview(merger)
        else:
            bzrlib.builtins.cmd_merge._do_preview(self, merger)


class cmd_qbzr(QBzrCommand):
    """The QBzr application.

    Not finished -- DON'T USE
    """

    takes_options = []
    takes_args = []
    hidden = True

    def _qbzr_run(self):
        # Remove svn checkout support
        try:
            from bzrlib.plugins.svn.format import SvnWorkingTreeDirFormat
        except ImportError:
            pass
        else:
            from bzrlib.bzrdir import BzrDirFormat, format_registry
            BzrDirFormat.unregister_control_format(SvnWorkingTreeDirFormat)
            format_registry.remove('subversion-wc')
        # Start QBzr
        app = QtGui.QApplication(sys.argv)
        window = QBzrMainWindow()
        window.setDirectory(osutils.realpath(u'.'))
        window.show()
        app.exec_()


class SubprocessGUIFactory(bzrlib.ui.text.TextUIFactory):

    def __init__(self):
        super(SubprocessGUIFactory, self).__init__(SubprocessProgress)

    def get_password(self, prompt='', **kwargs):
        from bzrlib.util import bencode
        prompt = prompt % kwargs
        self.stdout.write('qbzr:GETPASS:' + bencode.bencode(prompt.encode('utf-8')) + '\n')
        self.stdout.flush()
        line = self.stdin.readline()
        if line.startswith('qbzr:GETPASS:'):
            passwd, accepted = bencode.bdecode(line[13:].rstrip('\r\n'))
            if accepted:
                return passwd
        return ''


class cmd_qsubprocess(Command):

    takes_args = ['cmd']
    hidden = True

    if MS_WINDOWS:
        def __win32_ctrl_c(self):
            import win32event
            from bzrlib.plugins.qbzr.lib.subprocess import get_event_name
            ev = win32event.CreateEvent(None, 0, 0, get_event_name(os.getpid()))
            try:
                win32event.WaitForSingleObject(ev, win32event.INFINITE)
            finally:
                ev.Close()
            thread.interrupt_main()

    def run(self, cmd):
        if MS_WINDOWS:
            thread.start_new_thread(self.__win32_ctrl_c, ())
        else:
            signal.signal(signal.SIGINT, sigabrt_handler)
        ui.ui_factory = SubprocessGUIFactory()
        if cmd.startswith('@'):
            fname = cmd[1:]
            f = open(fname, 'rb')
            try:
                cmd = f.read()
            finally:
                f.close()
        argv = [p.decode('utf8') for p in shlex.split(cmd.encode('utf8'))]
        commands.run_bzr(argv)


def sigabrt_handler(signum, frame):
    raise KeyboardInterrupt()


class cmd_qgetupdates(QBzrCommand):
    """Fetches external changes into the working tree"""

    takes_args = ['location?']
    takes_options = [ui_mode_option]
    aliases = ['qgetu']

    def _qbzr_run(self, location=".", ui_mode=False):
        branch, relpath = Branch.open_containing(location)
        app = QtGui.QApplication(sys.argv)
        if branch.get_bound_location():
            window = UpdateCheckoutWindow(branch, ui_mode=ui_mode)
        else:
            window = UpdateBranchWindow(branch, ui_mode=ui_mode)

        window.show()
        app.exec_()


class cmd_qgetnew(QBzrCommand):
    """Creates a new working tree (either a checkout or full branch)"""

    takes_args = ['location?']
    takes_options = [ui_mode_option]
    aliases = ['qgetn']

    def _qbzr_run(self, location=".", ui_mode=False):
        app = QtGui.QApplication(sys.argv)
        window = GetNewWorkingTreeWindow(location, ui_mode=ui_mode)
        window.show()
        app.exec_()


class cmd_qhelp(QBzrCommand):
    """Shows a help window"""

    takes_args = ['topic']

    # until we get links and better HTML out of 'topics', this is hidden.
    hidden = True

    def _qbzr_run(self, topic):
        app = QtGui.QApplication(sys.argv)
        window = show_help(topic)
        app.exec_()


class cmd_qtag(QBzrCommand):
    """Edit tags."""

    takes_args = ['tag_name?']
    takes_options = [
        ui_mode_option,
        bzr_option('tag', 'delete'),
        bzr_option('tag', 'directory'),
        bzr_option('tag', 'force'),
        'revision',
        ]

    def _qbzr_run(self, tag_name=None, delete=None, directory='.',
        force=None, revision=None, ui_mode=False):
        branch = Branch.open_containing(directory)[0]
        if not branch.tags.supports_tags():
            raise errors.BzrError('This branch does not support tags')
        # determine action based on given options
        action = TagWindow.action_from_options(force=force, delete=delete)
        app = QtGui.QApplication(sys.argv)
        window = TagWindow(branch, tag_name=tag_name, action=action,
            revision=revision, ui_mode=ui_mode)
        window.show()
        app.exec_()
