# -*- coding: utf-8 -*-
#
# Copyright (C) 2009 Gary van der Merwe <garyvdm@gmail.com>
#
# This program is free software; you can redistribute it and/or
# modify it under the terms of the GNU General Public License
# as published by the Free Software Foundation; either versio0n 2
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

from bzrlib.tests import TestCase, TestCaseWithTransport
from PyQt4 import QtCore, QtGui
from bzrlib.plugins.qbzr.lib.treewidget import TreeModel
from bzrlib.plugins.qbzr.lib.tests.modeltest import ModelTest
from bzrlib.plugins.qbzr.lib.tests.excepthookwatcher import TestWatchExceptHook

class TestTreeModel(TestWatchExceptHook, TestCaseWithTransport):
    
    def test_model_working_tree(self):

        tree = self.make_branch_and_tree('tree')
        self.build_tree(['tree/b/', "tree/e/"])
        self.build_tree_contents([('tree/a', ''),
                                  ('tree/b/c', ''),
                                  ('tree/d', ''),
                                  ('tree/e/f', '')])
        tree.add(['a'], ['a-id'])
        tree.add(['b'], ['b-id'])
        tree.add(['b/c'], ['c-id'])
        tree.commit('a', rev_id='rev-1',
                     committer="joe@foo.com",
                     timestamp=1166046000.00, timezone=0)

        model = TreeModel(parent=None)
        modeltest = ModelTest(model, None)

        model.set_tree(tree, tree.branch)

    #def test_model_revision_tree(self):
    #
    #    tree = self.make_branch_and_tree('tree')
    #    self.build_tree(['tree/b/'])
    #    self.build_tree_contents([('tree/a', ''),
    #                              ('tree/b/c', '')])
    #    tree.add(['a'], ['a-id'])
    #    tree.add(['b'], ['b-id'])
    #    tree.add(['b/c'], ['c-id'])
    #    tree.commit('a', rev_id='rev-1',
    #                 committer="joe@foo.com",
    #                 timestamp=1166046000.00, timezone=0)
    #
    #    widget = TreeWidget()
    #    model = widget.model
    #    
    #    revtree = branch.repository.revision_tree('rev-1')
    #    widget.set_tree(revtree, branch)
    #    modeltest = ModelTest(model, None)


