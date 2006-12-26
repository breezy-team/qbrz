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

import bzrlib.plugins.qbzr.resources
from bzrlib.plugins.qbzr.browse import *
from bzrlib.plugins.qbzr.log import *
from bzrlib.option import Option

from bzrlib.lazy_import import lazy_import
lazy_import(globals(), '''
from PyQt4 import QtGui
from bzrlib.plugins.qbzr.annotate import AnnotateWindow
from bzrlib.plugins.qbzr.commit import CommitWindow
from bzrlib.plugins.qbzr.diff import DiffWindow
from bzrlib.workingtree import WorkingTree
''')

    
class cmd_qannotate(Command):
    """Show the origin of each line in a file."""
    takes_args = ['filename?']
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
            file_id = tree.inventory.path2id(relpath)
            tree = branch.repository.revision_tree(revision_id)
            file_version = tree.inventory[file_id].revision
            lines = list(_annotate_file(branch, file_version, file_id))
        finally:
            branch.unlock()

        app = QtGui.QApplication(sys.argv)
        win = AnnotateWindow(filename, lines)
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
    takes_args = ['filename?']
    takes_options = [
        'revision',
        Option('inline', help='Show inline diff'),
        Option('complete', help='Show complete files'),
        ]
    aliases = ['qdi']

    def run(self, revision=None, filename=None, inline=False, complete=False):
        wt, filename = WorkingTree.open_containing(filename)
        branch = wt.branch
        if revision is not None:
            if len(revision) == 1:
                tree1 = wt
                revision_id = revision[0].in_history(branch).rev_id
                tree2 = branch.repository.revision_tree(revision_id)
            elif len(revision) == 2:
                revision_id_0 = revision[0].in_history(branch).rev_id
                tree2 = branch.repository.revision_tree(revision_id_0)
                revision_id_1 = revision[1].in_history(branch).rev_id
                tree1 = branch.repository.revision_tree(revision_id_1)
        else:
            tree1 = wt
            tree2 = tree1.basis_tree()
        specific_files = None
        if filename:
            specific_files = (filename,)
        application = QtGui.QApplication(sys.argv)
        window = DiffWindow(tree2, tree1, inline=inline, complete=complete,
                            specific_files=specific_files)
        window.show()
        application.exec_()


register_command(cmd_qannotate)
register_command(cmd_qcommit)
register_command(cmd_qdiff)
