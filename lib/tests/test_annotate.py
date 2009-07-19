# -*- coding: utf-8 -*-
#
# Copyright (C) 2009 Gary van der Merwe <garyvdm@gmail.com>
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

from bzrlib.tests import TestCase, TestCaseWithTransport
from PyQt4 import QtCore, QtGui
from bzrlib.plugins.qbzr.lib.annotate import AnnotateModel
from bzrlib.plugins.qbzr.lib.tests.modeltest import ModelTest
from bzrlib.plugins.qbzr.lib.tests.excepthookwatcher import TestWatchExceptHook
from bzrlib import conflicts

class TestAnnotateModel(TestWatchExceptHook, TestCaseWithTransport):
    
    # Coppied from bzrlib/tests/test_annotate.py
    def create_merged_trees(self):
        """create 2 trees with merges between them.

        rev-1 --+
         |      |
        rev-2  rev-1_1_1
         |      |
         +------+
         |
        rev-3
        """

        tree1 = self.make_branch_and_tree('tree1')
        self.build_tree_contents([('tree1/a', 'first\n')])
        tree1.add(['a'], ['a-id'])
        tree1.commit('a', rev_id='rev-1',
                     committer="joe@foo.com",
                     timestamp=1166046000.00, timezone=0)

        tree2 = tree1.bzrdir.sprout('tree2').open_workingtree()

        self.build_tree_contents([('tree1/a', 'first\nsecond\n')])
        tree1.commit('b', rev_id='rev-2',
                     committer='joe@foo.com',
                     timestamp=1166046001.00, timezone=0)

        self.build_tree_contents([('tree2/a', 'first\nthird\n')])
        tree2.commit('c', rev_id='rev-1_1_1',
                     committer="barry@foo.com",
                     timestamp=1166046002.00, timezone=0)

        num_conflicts = tree1.merge_from_branch(tree2.branch)
        self.assertEqual(1, num_conflicts)

        self.build_tree_contents([('tree1/a',
                                 'first\nsecond\nthird\n')])
        tree1.set_conflicts(conflicts.ConflictList())
        tree1.commit('merge 2', rev_id='rev-3',
                     committer='sal@foo.com',
                     timestamp=1166046003.00, timezone=0)
        tree1.lock_read()
        self.addCleanup(tree1.unlock)
        return tree1, tree2

    def test_model(self):
        model = AnnotateModel(lambda revid: "", QtGui.QFont())
        modeltest = ModelTest(model, None);
        
        tree, tree2 = self.create_merged_trees()
        
        annotate = [(revid, text, True)
                    for revid, text in tree.annotate_iter("a-id")]
        model.set_annotate(annotate, {}, tree.branch)