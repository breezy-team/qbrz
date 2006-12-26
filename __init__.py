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
from bzrlib.plugins.qbzr.annotate import *
from bzrlib.plugins.qbzr.browse import *
from bzrlib.plugins.qbzr.log import *

from bzrlib.lazy_import import lazy_import
lazy_import(globals(), '''
from PyQt4 import QtGui
from bzrlib.plugins.qbzr.commit import CommitWindow
from bzrlib.plugins.qbzr.diff import DiffWindow
''')


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
    takes_options = ['revision']
    aliases = ['qdi']

    def run(self, revision=None, filename=None):
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
        window = DiffWindow(tree2, tree1, specific_files=specific_files)
        window.show()
        application.exec_()


register_command(cmd_qcommit)
register_command(cmd_qdiff)
