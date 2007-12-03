# -*- coding: utf-8 -*-
#
# QBzr - Qt frontend to Bazaar commands
# Copyright (C) 2006 Lukáš Lalinský <lalinsky@gmail.com>
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

"""QBzr - Qt-based front end for Bazaar

Provided commands: qcommit, qdiff, qlog, qannotate, qbrowse
"""

version_info = (0, 8, 0, 'dev', 0)
__version__ = '.'.join(map(str, version_info))

import os.path
import sys

if hasattr(sys, "frozen"):
    # "hack in" our PyQt4 binaries
    sys.path.append(os.path.join(os.path.dirname(__file__), '_lib'))

import bzrlib.plugins.qbzr.resources
from bzrlib import errors
from bzrlib.option import Option
from bzrlib.commands import Command, register_command
from bzrlib.lazy_import import lazy_import
lazy_import(globals(), '''
from PyQt4 import QtGui
from bzrlib import (
    builtins,
)
from bzrlib.branch import Branch
from bzrlib.bzrdir import BzrDir
from bzrlib.plugins.qbzr.annotate import AnnotateWindow
from bzrlib.plugins.qbzr.browse import BrowseWindow
from bzrlib.plugins.qbzr.commit import CommitWindow
from bzrlib.plugins.qbzr.config import QBzrConfigWindow
from bzrlib.plugins.qbzr.diff import DiffWindow
from bzrlib.plugins.qbzr.log import LogWindow
from bzrlib.plugins.qbzr.util import (
    get_branch_config,
    get_qlog_replace,
    get_set_encoding,
    is_valid_encoding,
    )
from bzrlib.workingtree import WorkingTree
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


class cmd_qannotate(Command):
    """Show the origin of each line in a file."""
    takes_args = ['filename']
    takes_options = ['revision',
                     Option('encoding', type=check_encoding,
                     help='Encoding of files content (default: utf-8)'),
                    ]
    aliases = ['qann', 'qblame']

    def run(self, filename=None, revision=None, encoding=None):
        from bzrlib.annotate import _annotate_file
        tree, relpath = WorkingTree.open_containing(filename)
        branch = tree.branch
        branch.lock_read()
        try:
            if revision is None:
                revision_id = branch.last_revision()
            elif len(revision) != 1:
                raise errors.BzrCommandError('bzr qannotate --revision takes exactly 1 argument')
            else:
                revision_id = revision[0].in_history(branch).rev_id
            file_id = tree.path2id(relpath)
            if file_id is None:
                raise errors.NotVersionedError(filename)
            tree = branch.repository.revision_tree(revision_id)
            entry = tree.inventory[file_id]
            if entry.kind != 'file':
                return
            repo = branch.repository
            w = repo.weave_store.get_weave(file_id, repo.get_transaction())
            content = list(w.annotate_iter(entry.revision))
            revision_ids = set(o for o, t in content)
            revision_ids = [o for o in revision_ids if repo.has_revision(o)]
            revisions = branch.repository.get_revisions(revision_ids)
        finally:
            branch.unlock()

        config = get_branch_config(branch)
        encoding = get_set_encoding(encoding, config)

        app = QtGui.QApplication(sys.argv)
        win = AnnotateWindow(filename, content, revisions, encoding=encoding,
                             branch=branch)
        win.show()
        app.exec_()


class cmd_qbrowse(Command):
    """Show inventory."""
    takes_args = ['location?']
    takes_options = ['revision']

    def run(self, revision=None, location=None):
        branch, path = Branch.open_containing(location)
        app = QtGui.QApplication(sys.argv)
        win = BrowseWindow(branch)
        win.show()
        app.exec_()


class cmd_qcommit(Command):
    """GUI for committing revisions."""
    takes_args = ['selected*']
    aliases = ['qci']

    def run(self, selected_list=None):
        tree, selected_list = builtins.tree_files(selected_list)
        if selected_list == ['']:
            selected_list = []
        application = QtGui.QApplication(sys.argv)
        window = CommitWindow(tree, selected_list)
        window.show()
        application.exec_()


class cmd_qdiff(Command):
    """Show differences in working tree in a GUI window."""
    takes_args = ['file*']
    takes_options = [
        'revision',
        Option('complete', help='Show complete files'),
        Option('encoding', type=check_encoding,
               help='Encoding of files content (default: utf-8)'),
        ]
    if 'change' in Option.OPTIONS:
        takes_options.append('change')
    aliases = ['qdi']

    def run(self, revision=None, file_list=None, complete=False,
            encoding=None):
        from bzrlib.builtins import internal_tree_files

        if revision and len(revision) > 2:
            raise errors.BzrCommandError('bzr qdiff --revision takes exactly'
                                         ' one or two revision specifiers')

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
            specific_files=file_list, branch=branch, encoding=encoding)
        window.show()
        application.exec_()


class cmd_qlog(Command):
    """Show log of a branch, file, or directory in a Qt window.

    By default show the log of the branch containing the working directory."""

    takes_args = ['location?']
    takes_options = []

    def run(self, location=None):
        file_id = None
        if location:
            dir, path = BzrDir.open_containing(location)
            branch = dir.open_branch()
            if path:
                try:
                    tree = dir.open_workingtree()
                except (errors.NotBranchError, errors.NotLocalUrl):
                    tree = branch.basis_tree()
                file_id = tree.path2id(path)
        else:
            dir, path = BzrDir.open_containing('.')
            branch = dir.open_branch()

        app = QtGui.QApplication(sys.argv)
        branch.lock_read()
        try:
            window = LogWindow(branch, location, file_id, get_qlog_replace(branch))
            window.show()
            app.exec_()
        finally:
            branch.unlock()


class cmd_qconfig(Command):
    """Configure Bazaar."""

    takes_args = []
    takes_options = []
    aliases = ['qconfigure']

    def run(self):
        app = QtGui.QApplication(sys.argv)
        window = QBzrConfigWindow()
        window.show()
        app.exec_()


register_command(cmd_qannotate)
register_command(cmd_qbrowse)
register_command(cmd_qconfig)
register_command(cmd_qcommit)
register_command(cmd_qdiff)
register_command(cmd_qlog)
