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

# Updated RJL 2020 - added b(ytes) prefix to strings where needed based
# upon the same usage in breezy/tests/test_annotate.py
# Note that although this was originally copied from the same
# (as per the old comment below) this now differs quite a bit
# and is closest to test_annotate_author_or_committer in breezy commit
# 7513 of 2020-06-11

from breezy.tests import TestCase, TestCaseWithTransport
from PyQt5 import QtCore
from breezy import conflicts
from breezy.plugins.qbrz.lib import tests as qtests
from breezy.plugins.qbrz.lib.annotate import AnnotateWindow


class TestAnnotate(qtests.QTestCase):

    # Copied from breezy/tests/test_annotate.py
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
        self.build_tree_contents([('tree1/a', b'first\n')])
        tree1.add(['a'], [b'a-id'])
        tree1.commit('a', rev_id=b'rev-1', committer="joe@foo.com", timestamp=1166046000.00, timezone=0)

        tree2 = tree1.controldir.sprout('tree2').open_workingtree()

        self.build_tree_contents([('tree1/a', b'first\nsecond\n')])
        tree1.commit('b', rev_id=b'rev-2', committer='joe@foo.com', timestamp=1166046001.00, timezone=0)

        self.build_tree_contents([('tree2/a', b'first\nthird\n')])
        tree2.commit('c', rev_id=b'rev-1_1_1', committer="barry@foo.com", timestamp=1166046002.00, timezone=0)

        num_conflicts = tree1.merge_from_branch(tree2.branch)
        self.assertEqual(1, num_conflicts)

        self.build_tree_contents([('tree1/a', b'first\nsecond\nthird\n')])
        tree1.set_conflicts(conflicts.ConflictList())
        tree1.commit('merge 2', rev_id=b'rev-3', committer='sal@foo.com', timestamp=1166046003.00, timezone=0)
        return tree1, tree2

    def test_just_show_annotate(self):
        tree1, tree2 = self.create_merged_trees()
        win = AnnotateWindow(tree1.branch, tree1, tree1, 'a', b'a-id')
        self.addCleanup(win.close)
        win.show()
        # If you want to see the output, add a sleep after this
        QtCore.QCoreApplication.processEvents()
