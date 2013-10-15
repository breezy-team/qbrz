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

import signal

from bzrlib import errors
from bzrlib.commands import Command
from bzrlib.option import Option
import bzrlib.builtins

from bzrlib.lazy_import import lazy_import
lazy_import(globals(), '''
import sys

from PyQt4 import QtCore, QtGui

from bzrlib import (
    builtins,
    osutils,
    ui,
    gpg,
    )
from bzrlib.branch import Branch
from bzrlib.bzrdir import BzrDir
from bzrlib.workingtree import WorkingTree

from bzrlib.plugins.qbzr.lib import i18n
from bzrlib.plugins.qbzr.lib.add import AddWindow
from bzrlib.plugins.qbzr.lib.annotate import AnnotateWindow
from bzrlib.plugins.qbzr.lib.branch import QBzrBranchWindow
from bzrlib.plugins.qbzr.lib.browse import BrowseWindow
from bzrlib.plugins.qbzr.lib.cat import (
    QBzrCatWindow,
    QBzrViewWindow,
    cat_to_native_app,
    )
from bzrlib.plugins.qbzr.lib.commit import CommitWindow
from bzrlib.plugins.qbzr.lib.config import QBzrConfigWindow
from bzrlib.plugins.qbzr.lib.diffwindow import DiffWindow
from bzrlib.plugins.qbzr.lib.getupdates import UpdateBranchWindow, UpdateCheckoutWindow
from bzrlib.plugins.qbzr.lib.help import show_help
from bzrlib.plugins.qbzr.lib.log import LogWindow
from bzrlib.plugins.qbzr.lib.info import QBzrInfoWindow
from bzrlib.plugins.qbzr.lib.init import QBzrInitWindow
from bzrlib.plugins.qbzr.lib.main import QBzrMainWindow
from bzrlib.plugins.qbzr.lib.verify_signatures import \
QBzrVerifySignaturesWindow
from bzrlib.plugins.qbzr.lib.pull import (
    QBzrPullWindow,
    QBzrPushWindow,
    QBzrMergeWindow,
    )
from bzrlib.plugins.qbzr.lib.revert import RevertWindow
from bzrlib.plugins.qbzr.lib.tag import TagWindow
from bzrlib.plugins.qbzr.lib.tree_branch import TreeBranch
from bzrlib.plugins.qbzr.lib.uncommit import QBzrUncommitWindow
from bzrlib.plugins.qbzr.lib.update import QBzrUpdateWindow
from bzrlib.plugins.qbzr.lib.util import (
    FilterOptions,
    is_valid_encoding,
    open_tree,
    )
from bzrlib.plugins.qbzr.lib.uifactory import QUIFactory
from bzrlib.plugins.qbzr.lib.send import SendWindow
from bzrlib.plugins.qbzr.lib.shelvewindow import ShelveWindow
from bzrlib.plugins.qbzr.lib.widgets.shelvelist import ShelveListWindow
''')

from bzrlib.plugins.qbzr.lib.diff_arg import DiffArgProvider

CUR_DIR=u'.'

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

    _fmt = ('QBzr require at least PyQt 4.4 and '
            'Qt 4.4 to run. Please check your install')


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

    NOTES:
    1) q-command should define method '_qbzr_run' instead of 'run' (as in
       bzrlib).
    2) The _qbzr_run method should return 0 for successfull exit
       and 1 if operation was cancelled by user.
    3) The _qbzr_run method can return None, in this case return code will be
       asked from self.main_window instance (if there is one).
       self.main_window should be instance of QBzrWindow or QBzrDialog
       with attribute "return_code" set to 0 or 1.
    """

    @install_gettext
    @report_missing_pyqt
    def run(self, *args, **kwargs):
        # We must create the QApplication before we install the QUIFactory.
        # This is because once the factory is installed, it is possible that
        # opening a branch, etc will go to the ui_factory to request a
        # password, and the app must exist before the dialog can be created.
        self._application = QtGui.QApplication(sys.argv)
        std_ui_factory = ui.ui_factory
        try:
            ui.ui_factory = QUIFactory()
            
            # Handle interupt signal correctly.
            signal.signal(signal.SIGINT, signal.SIG_DFL)
            
            # Set up global exception handling.
            from bzrlib.plugins.qbzr.lib.trace import excepthook
            sys.excepthook = excepthook

            try:
                try:
                    ret_code = self._qbzr_run(*args, **kwargs)
                finally:
                    # ensure we flush clipboard data (see bug #503401)
                    clipboard = self._application.clipboard()
                    clipEvent = QtCore.QEvent(QtCore.QEvent.Clipboard)
                    self._application.sendEvent(clipboard, clipEvent)
                if ret_code is None:
                    main_window = getattr(self, "main_window", None)
                    if main_window is not None:
                        # 0.20 special: We check hasattr() first to work around
                        # <http://bugs.python.org/issue4230>
                        if hasattr(main_window, "return_code"):
                            ret_code = main_window.return_code
                return ret_code
            except Exception:
                ui_mode = kwargs.get("ui_mode", False)
                from bzrlib.plugins.qbzr.lib.trace import report_exception
                return report_exception(ui_mode=ui_mode)
        finally:
            ui.ui_factory = std_ui_factory


ui_mode_option = Option("ui-mode",
    help="Causes dialogs to wait after the operation is complete.")
execute_option = Option("execute", short_name='e',
    help="Causes dialogs to start the underlying action immediately without "
         "waiting for user input.")

# A special option so 'revision' can be passed as a simple string, when we do
# *not* want bzrlib's feature of parsing the revision string before passing it.
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
                     Option('no-graph', help="Shows the log with no graph."),
                     Option('line', short_name='L', type=int, argname='N',
                        param_name='activate_line',
                        help='Activate line N on start.'),
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
                if wt is not None:
                    tree = wt
                else:
                    tree = branch.repository.revision_tree(
                                                    branch.last_revision())
            elif len(revision) != 1:
                raise errors.BzrCommandError(
                    'bzr qannotate --revision takes exactly 1 argument')
            else:
                tree = branch.repository.revision_tree(
                        revision_id = revision[0].in_history(branch).rev_id)

            file_id = tree.path2id(relpath)
            if file_id is None:
                raise errors.NotVersionedError(filename)
            [(path, entry)] = list(tree.iter_entries_by_dir(
                specific_file_ids=[file_id]))
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

        return branch, tree, wt, relpath, file_id

    def _qbzr_run(self, filename=None, revision=None, encoding=None,
                  ui_mode=False, no_graph=False, activate_line=None):
        win = AnnotateWindow(None, None, None, None, None,
                             encoding=encoding, ui_mode=ui_mode,
                             loader=self._load_branch,
                             loader_args=(filename, revision),
                             no_graph=no_graph, activate_line=activate_line)
        win.show()
        self._application.exec_()


class cmd_qadd(QBzrCommand):
    """GUI for adding files or directories."""
    takes_args = ['selected*']
    takes_options = [ui_mode_option]

    def _qbzr_run(self, selected_list=None, ui_mode=False):
        tree, selected_list = WorkingTree.open_containing_paths(selected_list)
        if selected_list == ['']:
            selected_list = None
        self.main_window = AddWindow(tree, selected_list, dialog=False, ui_mode=ui_mode)
        self.main_window.show()
        self._application.exec_()


class cmd_qrevert(QBzrCommand):
    """Revert changes files."""
    takes_args = ['selected*']
    takes_options = [ui_mode_option, bzr_option('revert', 'no-backup')]

    def _qbzr_run(self, selected_list=None, ui_mode=False, no_backup=False):
        tree, selected_list = WorkingTree.open_containing_paths(selected_list)
        if selected_list == ['']:
            selected_list = None
        self.main_window = RevertWindow(tree, selected_list, dialog=False,
            ui_mode=ui_mode,
            backup=not no_backup)
        self.main_window.show()
        self._application.exec_()


class cmd_qconflicts(QBzrCommand):
    """Show conflicts."""
    takes_args = []
    takes_options = []
    aliases = ['qresolve']

    def _qbzr_run(self):
        from bzrlib.plugins.qbzr.lib.conflicts import ConflictsWindow
        self.main_window = ConflictsWindow(CUR_DIR)
        self.main_window.show()
        self._application.exec_()


class cmd_qbrowse(QBzrCommand):
    """Show inventory or working tree."""
    takes_args = ['location?']
    takes_options = ['revision']
    aliases = ['qbw']

    def _qbzr_run(self, revision=None, location=None):
        Branch.open_containing(location or u'.')  # if there is no branch we want NotBranchError raised
        if revision is None:
            win = BrowseWindow(location = location)
        else:
            win = BrowseWindow(location = location, revision = revision[0])
        win.show()
        self._application.exec_()


class cmd_qcommit(QBzrCommand):
    """GUI for committing revisions."""
    takes_args = ['selected*']
    takes_options = [
            bzr_option('commit', 'message'),
            bzr_option('commit', 'local'),
            bzr_option('commit', 'file'),
            Option('file-encoding', type=check_encoding,
               help='Encoding of commit message file content.'),
            ui_mode_option,
            ]
    aliases = ['qci']

    def _qbzr_run(self, selected_list=None, message=None, file=None,
                  local=False, ui_mode=False, file_encoding=None):
        if message is not None and file:
            raise errors.BzrCommandError("please specify either --message or --file")
        if file:
            f = open(file)
            try:
                message = f.read().decode(file_encoding or osutils.get_user_encoding())
            finally:
                f.close()
        tree, selected_list = WorkingTree.open_containing_paths(selected_list)
        if selected_list == ['']:
            selected_list = None
        self.main_window = CommitWindow(tree, selected_list, dialog=False,
            message=message, local=local, ui_mode=ui_mode)
        self.main_window.show()
        self._application.exec_()


class cmd_qdiff(QBzrCommand, DiffArgProvider):
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
        Option('ignore-whitespace', short_name='w',
               help="Ignore whitespace when finding differences"),
        bzr_option('diff', 'old'),
        bzr_option('diff', 'new'),
        ]
    if 'change' in Option.OPTIONS:
        takes_options.append('change')
    aliases = ['qdi']

    def get_diff_window_args(self, processEvents, add_cleanup):
        args = {}
        try:
            from bzrlib.diff import get_trees_and_branches_to_diff_locked
        except ImportError:
            from bzrlib.diff import get_trees_and_branches_to_diff
            (args["old_tree"], args["new_tree"],
             args["old_branch"], args["new_branch"],
             args["specific_files"], _) = \
                get_trees_and_branches_to_diff(
                    self.file_list, self.revision, self.old, self.new)
        else:
            (args["old_tree"], args["new_tree"],
             args["old_branch"], args["new_branch"],
             args["specific_files"], _) = \
                get_trees_and_branches_to_diff_locked(
                    self.file_list, self.revision, self.old, self.new,
                    add_cleanup)
        args["ignore_whitespace"] = self.ignore_whitespace
        return args

    def get_ext_diff_args(self, processEvents):
        args = []
        if self.revision and len(self.revision) == 1:
            args.append("-r%s" % (self.revision[0].user_spec,))
        elif self.revision and  len(self.revision) == 2:
            args.append("-r%s..%s" % (self.revision[0].user_spec,
                                       self.revision[1].user_spec))

        if self.new and not self.new == CUR_DIR:
            args.append("--new=%s" % self.new)
        if self.old and not self.old == CUR_DIR:
            args.append("--old=%s" % self.old)

        if self.file_list:
            args.extend(self.file_list)

        return None, args

    def _qbzr_run(self, revision=None, file_list=None, complete=False,
            encoding=None, ignore_whitespace=False,
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

        self.revision = revision
        self.file_list = file_list
        self.old = old
        self.new = new
        self.ignore_whitespace = ignore_whitespace

        window = DiffWindow(self,
                            complete=complete,
                            encoding=encoding,
                            filter_options=filter_options,
                            ui_mode=ui_mode)
        window.show()
        self._application.exec_()


class cmd_qlog(QBzrCommand):
    """Show log of a repository, branch, file, or directory in a Qt window.

    By default show the log of the branch containing the working directory.

    If multiple files are speciffied, they must be from the same branch.

    :Examples:
        Log the current branch::

            bzr qlog

        Log of files::

            bzr qlog foo.c bar.c

        Log from different branches::

            bzr qlog ~/branch1 ~/branch2
    """

    takes_args = ['locations*']
    takes_options = [
        ui_mode_option,
        Option('no-graph', help="Shows the log with no graph."),
        Option('show-trees', help="Show working trees that have changes "
                                  "as nodes in the graph"),
        ]

    def _qbzr_run(self, locations_list=None, ui_mode=False, no_graph=False,
                  show_trees=False):
        window = LogWindow(locations_list, None, None, ui_mode=ui_mode,
                           no_graph=no_graph, show_trees=show_trees)
        window.show()
        self._application.exec_()


class cmd_qconfig(QBzrCommand):
    """Configure Bazaar and QBzr."""

    takes_args = []
    takes_options = []
    aliases = ['qconfigure']

    def _qbzr_run(self):
        window = QBzrConfigWindow()
        window.show()
        self._application.exec_()


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


        window = QBzrCatWindow(filename = filename, revision = revision,
                               encoding = encoding)
        window.show()
        self._application.exec_()


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
            directory = CUR_DIR
        try:
            tree_to = WorkingTree.open_containing(directory)[0]
            branch_to = tree_to.branch
        except errors.NoWorkingTree:
            tree_to = None
            branch_to = Branch.open_containing(directory)[0]
        self.main_window = QBzrPullWindow(branch_to, tree_to, location,
                                remember=remember,
                                overwrite=overwrite,
                                revision=revision,
                                ui_mode=ui_mode)
        self.main_window.show()
        self._application.exec_()


class cmd_qmerge(QBzrCommand):
    """Perform a three-way merge."""

    takes_options = [ui_mode_option,
                     simple_revision_option,
                     bzr_option('merge', 'directory'),
                     bzr_option('merge', 'force'),
                     bzr_option('merge', 'uncommitted'),
                     'remember']
    takes_args = ['location?']

    def _qbzr_run(self, location=None, directory=None, revision=None,
                  remember=None, force=None, uncommitted=None, ui_mode=False):
        if directory is None:
            directory = CUR_DIR
        try:
            tree_to = WorkingTree.open_containing(directory)[0]
            branch_to = tree_to.branch
        except errors.NoWorkingTree:
            tree_to = None
            branch_to = Branch.open_containing(directory)[0]
        self.main_window = QBzrMergeWindow(branch_to, tree_to, location,
            revision=revision, remember=remember, force=force,
            uncommitted=uncommitted, ui_mode=ui_mode)
        self.main_window.show()
        self._application.exec_()


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
            directory = CUR_DIR

        try:
            tree_to = WorkingTree.open_containing(directory)[0]
            branch_to = tree_to.branch
        except errors.NoWorkingTree:
            tree_to = None
            branch_to = Branch.open_containing(directory)[0]
        self.main_window = QBzrPushWindow(branch_to, tree_to,
                                location=location,
                                create_prefix=create_prefix,
                                use_existing_dir=use_existing_dir,
                                remember=remember,
                                overwrite=overwrite,
                                ui_mode=ui_mode)
        self.main_window.show()
        self._application.exec_()


class cmd_qbranch(QBzrCommand):
    """Create a new copy of a branch."""

    takes_options = [simple_revision_option,
                     ui_mode_option]
    try:
        takes_options.append(bzr_option("branch", "bind"))
    except KeyError:
        # older version of bzr that doesn't support the option
        pass
    takes_args = ['from_location?', 'to_location?']

    def _qbzr_run(self, from_location=None, to_location=None,
                  revision=None, bind=False, ui_mode=False):
        self.main_window = QBzrBranchWindow(from_location, to_location,
            revision=revision, bind=bind, ui_mode=ui_mode)
        self.main_window.show()
        self._application.exec_()


class cmd_qinfo(QBzrCommand):
    """Shows information about the current location."""

    takes_options = []
    takes_args = ['location?']

    def _qbzr_run(self, location=CUR_DIR):
        window = QBzrInfoWindow(location)
        window.show()
        self._application.exec_()


class cmd_qverify_signatures(QBzrCommand):
    """Shows digital signature statuses for branch commits"""

    takes_options = [
            Option('acceptable-keys',
                   help='Comma separated list of GPG key patterns which are'
                        ' acceptable for verification.',
                   short_name='k',
                   type=str,),
            'revision', 
          ]
    takes_args = ['location?']

    def _qbzr_run(self, acceptable_keys=None, revision=None, location=CUR_DIR):
        if gpg.GPGStrategy.verify_signatures_available():
            window = QBzrVerifySignaturesWindow(acceptable_keys, revision,
                                                                    location)
            window.show()
            self._application.exec_()
        else:
            raise errors.DependencyNotPresent("python-gpgme", 
                                        "python-gpgme not installed")

class cmd_qinit(QBzrCommand):
    """Initializes a new branch or shared repository."""

    takes_options = [ui_mode_option]
    takes_args = ['location?']

    def _qbzr_run(self, location=CUR_DIR, ui_mode=False):
        self.main_window = QBzrInitWindow(location, ui_mode=ui_mode)
        self.main_window.show()
        self._application.exec_()


class cmd_merge(bzrlib.builtins.cmd_merge, DiffArgProvider):
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

    def get_diff_window_args(self, processEvents, add_cleanup):
        tree_merger = self.merger.make_merger()
        self.tt = tree_merger.make_preview_transform()
        result_tree = self.tt.get_preview_tree()
        return {"old_tree": self.merger.this_tree, "new_tree": result_tree}

    @install_gettext
    @report_missing_pyqt
    def _do_qpreview(self, merger):
        # Set up global execption handeling.
        from bzrlib.plugins.qbzr.lib.trace import excepthook
        sys.excepthook = excepthook

        self.merger = merger
        try:
            window = DiffWindow(self, encoding=self._encoding)
            window.show()
            self._application.exec_()
        finally:
            if self.tt:
                self.tt.finalize()

    def _do_preview(self, merger, *args, **kw):
        if self.qpreview:
            self._do_qpreview(merger)
        else:
            bzrlib.builtins.cmd_merge._do_preview(self, merger, *args, **kw)


class cmd_qmain(QBzrCommand):
    """The QBzr main application.

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
        window = QBzrMainWindow()
        window.setDirectory(osutils.realpath(CUR_DIR))
        window.show()
        self._application.exec_()


# [bialix 2010/02/04] body of cmd_qsubprocess has moved to subprocess.py
# to see annotation of cmd_qsubprocess before move use:
#     bzr qannotate commands.py -r1117

class cmd_qsubprocess(Command):
    """Run some bzr command as subprocess.
    Used with most of subprocess-based dialogs of QBzr.

    If CMD argument starts with @ characters then it used as name of file with
    actual cmd string (in utf-8).

    With --bencode option cmd string interpreted as bencoded list of utf-8
    strings. This is the recommended way to launch qsubprocess.
    """
    takes_args = ['cmd']
    takes_options = [Option("bencoded", help="Pass command as bencoded string.")]
    hidden = True

    def run(self, cmd, bencoded=False):
        from bzrlib.plugins.qbzr.lib.subprocess import run_subprocess_command
        return run_subprocess_command(cmd, bencoded)


class cmd_qgetupdates(QBzrCommand):
    """Fetches external changes into the working tree."""

    takes_args = ['location?']
    takes_options = [ui_mode_option, execute_option]
    aliases = ['qgetu', 'qgetup']

    def _qbzr_run(self, location=CUR_DIR, ui_mode=False, execute=False):
        branch, relpath = Branch.open_containing(location)
        tb = TreeBranch.open_containing(location, ui_mode=ui_mode)
        if tb is None:
            return errors.EXIT_ERROR
        if tb.is_light_co():
            window = QBzrUpdateWindow(tb.tree, ui_mode, immediate=execute)
        elif tb.is_bound():
            window = UpdateCheckoutWindow(tb.branch, ui_mode=ui_mode)
        else:
            window = UpdateBranchWindow(tb.branch, ui_mode=ui_mode)
        self.main_window = window
        self.main_window.show()
        self._application.exec_()


class cmd_qgetnew(QBzrCommand):
    """Creates a new working tree (either a checkout or full branch)."""

    takes_args = ['location?']
    takes_options = [ui_mode_option]
    aliases = ['qgetn']

    def _qbzr_run(self, location=None, ui_mode=False):
        from bzrlib.plugins.qbzr.lib.getnew import GetNewWorkingTreeWindow
        self.main_window = GetNewWorkingTreeWindow(location, ui_mode=ui_mode)
        self.main_window.show()
        self._application.exec_()


class cmd_qhelp(QBzrCommand):
    """Shows a help window"""

    takes_args = ['topic']

    # until we get links and better HTML out of 'topics', this is hidden.
    hidden = True

    def _qbzr_run(self, topic):
        show_help(topic)
        self._application.exec_()


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

    def _qbzr_run(self, tag_name=None, delete=None, directory=CUR_DIR,
        force=None, revision=None, ui_mode=False):
        branch = Branch.open_containing(directory)[0]
        # determine action based on given options
        action = TagWindow.action_from_options(force=force, delete=delete)
        self.main_window = TagWindow(branch, tag_name=tag_name, action=action,
            revision=revision, ui_mode=ui_mode)
        self.main_window.show()
        self._application.exec_()


class cmd_quncommit(QBzrCommand):
    """Move the tip of a branch to an earlier revision."""

    takes_options = [
        ui_mode_option,
        ]
    takes_args = ["location?"]

    def _qbzr_run(self, location=CUR_DIR, ui_mode=False):
        window = QBzrUncommitWindow(location, ui_mode=ui_mode)
        window.show()
        self._application.exec_()


class cmd_qviewer(QBzrCommand):
    """Simple file viewer."""
    aliases = []
    takes_args = ['filename']
    takes_options = [
        Option('encoding', type=check_encoding,
               help='Encoding of file content (default: utf-8).'),
        ]
    _see_also = ['qcat']

    def _qbzr_run(self, filename, encoding=None):
        window = QBzrViewWindow(filename=filename, encoding=encoding)
        window.show()
        self._application.exec_()


class cmd_qversion(QBzrCommand):
    """Show version/system information."""
    takes_args = []
    takes_options = []
    aliases = []

    def _qbzr_run(self):
        from bzrlib.plugins.qbzr.lib.sysinfo import QBzrSysInfoWindow
        window = QBzrSysInfoWindow()
        window.show()
        self._application.exec_()


class cmd_qplugins(QBzrCommand):
    """Show information about installed plugins."""

    takes_args = []
    takes_options = []
    aliases = []

    def _qbzr_run(self):
        from bzrlib.plugins.qbzr.lib.plugins import QBzrPluginsWindow
        window = QBzrPluginsWindow()
        window.show()
        self._application.exec_()


class cmd_qupdate(QBzrCommand):
    """Update working tree with latest changes in the branch."""
    aliases = ['qup']
    takes_args = ['directory?']
    takes_options = [ui_mode_option, execute_option]

    def _qbzr_run(self, directory=None, ui_mode=False, execute=False):
        tree = open_tree(directory, ui_mode)
        if tree is None:
            return
        self.main_window = QBzrUpdateWindow(tree, ui_mode, execute)
        self.main_window.show()
        self._application.exec_()


class cmd_qsend(QBzrCommand):
    """Mail or create a merge-directive for submitting changes."""

    takes_args = ['submit_branch?', 'public_branch?']
    takes_options = [ui_mode_option]

    def _qbzr_run(self, submit_branch=CUR_DIR, public_branch=None, ui_mode=False):
        branch = Branch.open_containing(submit_branch)[0]
        window = SendWindow(branch, ui_mode)
        window.show()
        self._application.exec_()


class cmd_qswitch(QBzrCommand):
    """Set the branch of a checkout and update."""

    takes_args = ['location?']
    takes_options = [ui_mode_option]

    def _qbzr_run(self, location=None, ui_mode=False):
        from bzrlib.plugins.qbzr.lib.switch import QBzrSwitchWindow

        branch = Branch.open_containing(CUR_DIR)[0]
        bzrdir = BzrDir.open_containing(CUR_DIR)[0]
        self.main_window = QBzrSwitchWindow(branch, bzrdir, location, ui_mode)
        self.main_window.show()
        self._application.exec_()


class cmd_qunbind(QBzrCommand):
    """Convert the current checkout into a regular branch."""
    takes_options = [ui_mode_option, execute_option]

    def _qbzr_run(self, ui_mode=False, execute=False):
        from bzrlib.plugins.qbzr.lib.unbind import QBzrUnbindDialog

        branch = Branch.open_containing(CUR_DIR)[0]
        if branch.get_bound_location() == None:
            raise errors.BzrCommandError("This branch is not bound.")

        self.main_window = QBzrUnbindDialog(branch, ui_mode, execute)
        self.main_window.show()
        self._application.exec_()


class cmd_qexport(QBzrCommand):
    """Export current or past revision to a destination directory or archive.

      DEST is the destination file or dir where the branch will be exported.
      If BRANCH_OR_SUBDIR is omitted then the branch containing the current working
      directory will be used.
    """

    takes_args = ['dest?','branch_or_subdir?']
    takes_options = [ui_mode_option]

    def _qbzr_run(self, dest=None, branch_or_subdir=None, ui_mode=False):
        from bzrlib.plugins.qbzr.lib.export import QBzrExportDialog

        if branch_or_subdir == None:
            branch = Branch.open_containing(CUR_DIR)[0]
        else:
            branch = Branch.open_containing(branch_or_subdir)[0]

        window = QBzrExportDialog(dest, branch, ui_mode)
        window.show()
        self._application.exec_()


class cmd_qbind(QBzrCommand):
    """Convert the current branch into a checkout of the supplied branch.

    LOCATION is the branch where you want to bind your current branch.
    """

    takes_args = ['location?']
    takes_options = [ui_mode_option]

    def _qbzr_run(self, location=None, ui_mode=False):
        from bzrlib.plugins.qbzr.lib.bind import QBzrBindDialog

        branch = Branch.open_containing(CUR_DIR)[0]

        self.main_window = QBzrBindDialog(branch, location, ui_mode)
        self.main_window.show()
        self._application.exec_()


class cmd_qrun(QBzrCommand):
    """Run arbitrary bzr command.

    If you wish to pass options to COMMAND, use ``--`` beforehand
    so that the options aren't treated as options to the qrun
    command itself. For example::

      bzr qrun shelve -- --list

    NOTE: you should use only canonical name of the COMMAND, not the alias.
    """
    takes_args = ['command?', 'parameters*']
    takes_options = [ui_mode_option,
        Option('directory',
            help='Working directory.',
            short_name='d',
            type=unicode,
            ),
        Option('category',
            help='Initial category selection.',
            type=unicode,
            ),
        execute_option,
        ]
    aliases = ['qcmd']

    def _qbzr_run(self, command=None, parameters_list=None, ui_mode=False,
        directory=None, category=None, execute=False):
        from bzrlib.plugins.qbzr.lib.run import QBzrRunDialog
        if parameters_list:
            def quote_spaces(s):
                if " " in s:
                    s = '"%s"' % s
                return s
            parameters = " ".join([quote_spaces(i) for i in parameters_list])
        else:
            parameters = None
        if not command:
            execute = False
        window = QBzrRunDialog(command=command, parameters=parameters,
            workdir=directory, category=category, ui_mode=ui_mode,
            execute=execute)
        window.show()
        self._application.exec_()
        
class cmd_qshelve(QBzrCommand):
    """Shelve selected changes away."""
    takes_args = ['file*']
    takes_options = [
        ui_mode_option,
        bzr_option('shelve', 'list'),
        bzr_option('shelve', 'directory'),
        bzr_option('shelve', 'message'),
        Option('all', help='Select all changes.'),
        Option('complete', help='Show complete files.'),
        Option('ignore-whitespace', short_name='w',
               help="Ignore whitespace when finding differences.(Only work when --list specified)"),
        Option('encoding', type=check_encoding,
               help='Encoding of files content (default: utf-8).'),
        ]

    def _qbzr_run(self, file_list=None, list=False, directory=None, ui_mode=False, 
                            complete=False, ignore_whitespace=False, encoding=None,
                            all=False, message=None):
        if list:
            initial_tab = 1
        else:
            initial_tab = 0
        self.main_window = ShelveWindow(file_list=file_list, directory=directory, ui_mode=ui_mode,
                                initial_tab=initial_tab, complete=complete, 
                                ignore_whitespace=ignore_whitespace, encoding=encoding,
                                select_all=all, message=message)
        self.main_window.show()
        self._application.exec_()

class cmd_qunshelve(QBzrCommand):
    """Restore shalved changes."""
    takes_options = [
        ui_mode_option,
        bzr_option('unshelve', 'directory'),
        Option('complete', help='Show complete files.'),
        Option('ignore-whitespace', short_name='w',
               help="Ignore whitespace when finding differences.(Only work when --list specified)"),
        Option('encoding', type=check_encoding,
               help='Encoding of files content (default: utf-8).'),
        ]

    def _qbzr_run(self, directory=None, ui_mode=False, 
                        complete=False, ignore_whitespace=False, encoding=None):
        self.main_window = ShelveWindow(directory=directory, ui_mode=ui_mode,
                                initial_tab=1, complete=complete, 
                                ignore_whitespace=ignore_whitespace, encoding=encoding)
        self.main_window.show()
        self._application.exec_()


class cmd_qignore(QBzrCommand):
    """Ignore files or patterns."""
    takes_args = []
    takes_options = [
        ui_mode_option,
        bzr_option('ignore', 'directory'),
        ]
    aliases = []

    def _qbzr_run(self, directory=None, ui_mode=False):
        from bzrlib.plugins.qbzr.lib.ignore import IgnoreWindow
        wt = WorkingTree.open_containing(directory)[0]
        self.main_window = IgnoreWindow(tree=wt, ui_mode=ui_mode)
        self.main_window.show()
        self._application.exec_()
