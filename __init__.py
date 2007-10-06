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

version_info = (0, 6, 0)
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
from bzrlib.branch import Branch
from bzrlib.bzrdir import BzrDir
from bzrlib.plugins.qbzr.annotate import AnnotateWindow
from bzrlib.plugins.qbzr.browse import BrowseWindow
from bzrlib.plugins.qbzr.commit import CommitWindow
from bzrlib.plugins.qbzr.diff import DiffWindow
from bzrlib.plugins.qbzr.log import LogWindow
from bzrlib.workingtree import WorkingTree
''')


class cmd_qannotate(Command):
    """Show the origin of each line in a file."""
    takes_args = ['filename']
    takes_options = ['revision']
    aliases = ['qann', 'qblame']

    def run(self, filename=None, revision=None):
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
            if tree.inventory[file_id].kind != 'file':
                return

            w = branch.repository.weave_store.get_weave(
                file_id, branch.repository.get_transaction())

            revisions = branch.repository.get_revisions(w.versions())
            content = list(w.annotate_iter(tree.inventory[file_id].revision))
        finally:
            branch.unlock()

        app = QtGui.QApplication(sys.argv)
        win = AnnotateWindow(filename, content, revisions)
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
    takes_args = ['filename?']
    aliases = ['qci']

    def run(self, filename=None):
        tree, filename = WorkingTree.open_containing(filename)
        application = QtGui.QApplication(sys.argv)
        window = CommitWindow(tree, filename)
        window.show()
        application.exec_()


class cmd_qdiff(Command):
    """Show differences in working tree in a GUI window."""
    takes_args = ['file*']
    takes_options = [
        'revision', 'change',
        Option('inline', help='Show inline diff'),
        Option('complete', help='Show complete files'),
        ]
    aliases = ['qdi']

    def run(self, revision=None, file_list=None, inline=False, complete=False):
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
        window = DiffWindow(tree2, tree1, inline=inline, complete=complete, specific_files=file_list, branch=branch)
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

        config = branch.get_config()
        replace = config.get_user_option("qlog_replace")
        if replace:
            replace = replace.split("\n")
            replace = [tuple(replace[2*i:2*i+2])
                       for i in range(len(replace) // 2)]

        app = QtGui.QApplication(sys.argv)
        window = LogWindow(branch, location, file_id, replace)
        window.show()
        app.exec_()


register_command(cmd_qannotate)
register_command(cmd_qbrowse)
register_command(cmd_qcommit)
register_command(cmd_qdiff)
register_command(cmd_qlog)
