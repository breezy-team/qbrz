# -*- coding: utf-8 -*-
#
# QBzr - Qt frontend to Bazaar commands
# Copyright (C) 2006 Lukáš Lalinský <lalinsky@gmail.com>
# Copyright (C) 2008 Alexander Belchenko
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

import os.path
import sys

if hasattr(sys, "frozen"):
    # "hack in" our PyQt4 binaries
    sys.path.append(os.path.normpath(os.path.join(os.path.dirname(__file__), '..', '_lib')))

from bzrlib import errors
from bzrlib.option import Option
from bzrlib.commands import Command, register_command, get_cmd_object
import bzrlib.builtins

from bzrlib.lazy_import import lazy_import
lazy_import(globals(), '''
from PyQt4 import QtGui
import shlex
from bzrlib import (
    builtins,
    commands,
    osutils,
    progress,
    ui,
    ui.text,
    urlutils,
    )
from bzrlib.util import bencode
from bzrlib.branch import Branch
from bzrlib.bzrdir import BzrDir
from bzrlib.workingtree import WorkingTree

from bzrlib.plugins.qbzr.lib import i18n
from bzrlib.plugins.qbzr.lib.add import AddWindow
from bzrlib.plugins.qbzr.lib.annotate import AnnotateWindow
from bzrlib.plugins.qbzr.lib.browse import BrowseWindow
from bzrlib.plugins.qbzr.lib.cat import QBzrCatWindow
from bzrlib.plugins.qbzr.lib.commit import CommitWindow
from bzrlib.plugins.qbzr.lib.config import QBzrConfigWindow
from bzrlib.plugins.qbzr.lib.diff import DiffWindow
from bzrlib.plugins.qbzr.lib.log import LogWindow
from bzrlib.plugins.qbzr.lib.main import QBzrMainWindow
from bzrlib.plugins.qbzr.lib.info import QBzrInfoWindow
from bzrlib.plugins.qbzr.lib.revert import RevertWindow
from bzrlib.plugins.qbzr.lib.subprocess import SubprocessProgress
from bzrlib.plugins.qbzr.lib.pull import (
    QBzrPullWindow,
    QBzrPushWindow,
    QBzrBranchWindow,
    QBzrMergeWindow,
    )
from bzrlib.plugins.qbzr.lib.util import (
    FilterOptions,
    get_branch_config,
    get_set_encoding,
    is_valid_encoding,
    )
''')


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


class cmd_qannotate(QBzrCommand):
    """Show the origin of each line in a file."""
    takes_args = ['filename']
    takes_options = ['revision',
                     Option('encoding', type=check_encoding,
                     help='Encoding of files content (default: utf-8)'),
                    ]
    aliases = ['qann', 'qblame']

    def _qbzr_run(self, filename=None, revision=None, encoding=None):
        from bzrlib.annotate import _annotate_file
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
                return
            #repo = branch.repository
            #w = repo.weave_store.get_weave(file_id, repo.get_transaction())
            #content = list(w.annotate_iter(entry.revision))
            #revision_ids = set(o for o, t in content)
            #revision_ids = [o for o in revision_ids if repo.has_revision(o)]
            #revisions = branch.repository.get_revisions(revision_ids)
        finally:
            branch.unlock()

        config = get_branch_config(branch)
        encoding = get_set_encoding(encoding, config)

        app = QtGui.QApplication(sys.argv)
        win = AnnotateWindow(branch, tree, relpath, file_id, encoding)
        win.show()
        app.exec_()


class cmd_qadd(QBzrCommand):
    """GUI for adding files or directories."""
    takes_args = ['selected*']

    def _qbzr_run(self, selected_list=None):
        tree, selected_list = builtins.tree_files(selected_list)
        if selected_list == ['']:
            selected_list = []
        application = QtGui.QApplication(sys.argv)
        window = AddWindow(tree, selected_list, dialog=False)
        window.show()
        application.exec_()


class cmd_qrevert(QBzrCommand):
    """Revert changes files."""
    takes_args = ['selected*']

    def _qbzr_run(self, selected_list=None):
        tree, selected_list = builtins.tree_files(selected_list)
        if selected_list == ['']:
            selected_list = []
        application = QtGui.QApplication(sys.argv)
        window = RevertWindow(tree, selected_list, dialog=False)
        window.show()
        application.exec_()


class cmd_qbrowse(QBzrCommand):
    """Show inventory."""
    takes_args = ['location?']
    takes_options = ['revision']
    aliases = ['qbw']

    def _qbzr_run(self, revision=None, location=None):
        branch, path = Branch.open_containing(location)
        app = QtGui.QApplication(sys.argv)
        if revision is None:
            win = BrowseWindow(branch)
        else:
            win = BrowseWindow(branch, revision[0])
        win.show()
        app.exec_()


class cmd_qcommit(QBzrCommand):
    """GUI for committing revisions."""
    takes_args = ['selected*']
    takes_options = [
            Option('message', type=unicode,
                   short_name='m',
                   help="Description of the new revision."),
            Option('local',
                   help="Perform a local commit in a bound "
                        "branch.  Local commits are not pushed to "
                        "the master branch until a normal commit "
                        "is performed."),
            ]
    aliases = ['qci']

    def _qbzr_run(self, selected_list=None, message=None, local=False):
        tree, selected_list = builtins.tree_files(selected_list)
        if selected_list == ['']:
            selected_list = []
        application = QtGui.QApplication(sys.argv)
        window = CommitWindow(tree, selected_list, dialog=False,
            message=message, local=local)
        window.show()
        application.exec_()


class cmd_qdiff(QBzrCommand):
    """Show differences in working tree in a GUI window."""
    takes_args = ['file*']
    takes_options = [
        'revision',
        Option('complete', help='Show complete files'),
        Option('encoding', type=check_encoding,
               help='Encoding of files content (default: utf-8)'),
        Option('added', short_name='A', help='Show diff for added files'),
        Option('deleted', short_name='D', help='Show diff for deleted files'),
        Option('modified', short_name='M',
               help='Show diff for modified files'),
        Option('renamed', short_name='R', help='Show diff for renamed files'),
        ]
    if 'change' in Option.OPTIONS:
        takes_options.append('change')
    aliases = ['qdi']

    def _qbzr_run(self, revision=None, file_list=None, complete=False,
            encoding=None,
            added=None, deleted=None, modified=None, renamed=None):
        from bzrlib.builtins import internal_tree_files

        if revision and len(revision) > 2:
            raise errors.BzrCommandError('bzr qdiff --revision takes exactly'
                                         ' one or two revision specifiers')
        # changes filter
        filter_options = FilterOptions(added=added, deleted=deleted,
            modified=modified, renamed=renamed)
        if not (added or deleted or modified or renamed):
            # if no filter option used then turn all on
            filter_options.all_enable()

        try:
            tree1, file_list = internal_tree_files(file_list)
            tree2 = None
        except errors.FileInWrongBranch:
            if len(file_list) != 2:
                raise errors.BzrCommandError("Can diff only two branches")

            tree1, file1 = WorkingTree.open_containing(file_list[1])
            tree2, file2 = WorkingTree.open_containing(file_list[0])
            if file1 != "" or file2 != "":
                raise errors.BzrCommandError("Files are in different branches")
            file_list = None

        branch = None
        if tree2 is not None:
            if revision is not None:
                raise errors.BzrCommandError(
                        "Sorry, diffing arbitrary revisions across branches "
                        "is not implemented yet")
        else:
            branch = tree1.branch
            if revision is not None:
                if len(revision) == 1:
                    revision_id = revision[0].in_history(branch).rev_id
                    tree2 = branch.repository.revision_tree(revision_id)
                elif len(revision) == 2:
                    revision_id_0 = revision[0].in_history(branch).rev_id
                    tree2 = branch.repository.revision_tree(revision_id_0)
                    revision_id_1 = revision[1].in_history(branch).rev_id
                    tree1 = branch.repository.revision_tree(revision_id_1)
            else:
                tree2 = tree1.basis_tree()

        application = QtGui.QApplication(sys.argv)
        window = DiffWindow(tree2, tree1, complete=complete,
            specific_files=file_list, branch=branch, encoding=encoding,
            filter_options=filter_options)
        window.show()
        application.exec_()


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
    takes_options = []

    def _qbzr_run(self, locations_list):
        app = QtGui.QApplication(sys.argv)
        window = LogWindow(locations_list, None, None)
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
               help='Encoding of files content (default: utf-8)'),
        ]
    takes_args = ['filename']

    def _qbzr_run(self, filename, revision=None, encoding=None):
        if revision is not None and len(revision) != 1:
            raise errors.BzrCommandError("bzr qcat --revision takes exactly"
                                         " one revision specifier")

        branch, relpath = Branch.open_containing(filename)
        if revision is None:
            tree = branch.basis_tree()
        else:
            revision_id = revision[0].in_branch(branch).rev_id
            tree = branch.repository.revision_tree(revision_id)

        app = QtGui.QApplication(sys.argv)
        tree.lock_read()
        try:
            window = QBzrCatWindow.from_tree_and_path(tree, relpath, encoding)
        finally:
            tree.unlock()
        if window is not None:
            window.show()
            app.exec_()


class cmd_qpull(QBzrCommand):
    """Turn this branch into a mirror of another branch."""

    takes_options = []
    takes_args = []

    def _qbzr_run(self):
        branch, relpath = Branch.open_containing('.')
        app = QtGui.QApplication(sys.argv)
        window = QBzrPullWindow(branch)
        window.show()
        app.exec_()



class cmd_qmerge(QBzrCommand):
    """Perform a three-way merge."""

    takes_options = []
    takes_args = []

    def _qbzr_run(self):
        branch, relpath = Branch.open_containing('.')
        app = QtGui.QApplication(sys.argv)
        window = QBzrMergeWindow(branch)
        window.show()
        app.exec_()



class cmd_qpush(QBzrCommand):
    """Update a mirror of this branch."""

    takes_options = []
    takes_args = []

    def _qbzr_run(self):
        branch, relpath = Branch.open_containing('.')
        app = QtGui.QApplication(sys.argv)
        window = QBzrPushWindow(branch)
        window.show()
        app.exec_()


class cmd_qbranch(QBzrCommand):
    """Create a new copy of a branch."""

    takes_options = []
    takes_args = []

    def _qbzr_run(self):
        app = QtGui.QApplication(sys.argv)
        window = QBzrBranchWindow(None)
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


class cmd_merge(bzrlib.builtins.cmd_merge):
    __doc__ = bzrlib.builtins.cmd_merge.__doc__

    takes_options = bzrlib.builtins.cmd_merge.takes_options + [
            Option('qpreview', help='Instead of merging, '
                'show a diff of the merge in a GUI window.'),
            Option('encoding', type=check_encoding,
                   help='Encoding of files content, used with --qpreview '
                        '(default: utf-8)'),
            ]

    def run(self, *args, **kw):
        self.qpreview = ('qpreview' in kw)
        if self.qpreview:
            kw['preview'] = kw['qpreview']
            del kw['qpreview']
        self._encoding = kw.get('encoding')
        if self._encoding:
            del kw['encoding']
        bzrlib.builtins.cmd_merge.run(self, *args, **kw)

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

class cmd_qsubprocess(Command):

    takes_args = ['cmd']
    hidden = True

    def run(self, cmd):
        ui.ui_factory = ui.text.TextUIFactory(SubprocessProgress)
        argv = [p.decode('utf8') for p in shlex.split(cmd.encode('utf8'))]
        commands.run_bzr(argv)
