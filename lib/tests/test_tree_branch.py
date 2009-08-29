# -*- coding: utf-8 -*-
#
# QBzr - Qt frontend to Bazaar commands
#
# Contributor:
#   Alexander Belchenko, 2009
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

"""Tests for TreeBranch wrapper object."""

from bzrlib import errors
from bzrlib.tests import TestCase, TestCaseWithTransport

from bzrlib.plugins.qbzr.lib import tree_branch
from bzrlib.plugins.qbzr.lib.tests import mock


class TestTreeBranch(TestCaseWithTransport):

    def test_errors_no_ui_mode(self):
        # no branch
        mf = mock.MockFunction()
        self.assertRaises(errors.NotBranchError,
            tree_branch.TreeBranch.open_containing, '/non/existent/path',
            ui_mode=False, _critical_dialog=mf)
        self.assertEqual(0, mf.count)
        # no tree
        self.make_branch('a')
        self.assertRaises(errors.NoWorkingTree,
            tree_branch.TreeBranch.open_containing, 'a', require_tree=True,
            ui_mode=False, _critical_dialog=mf)
        self.assertEqual(0, mf.count)

    def test_errors_ui_mode(self):
        mf = mock.MockFunction()
        tb = tree_branch.TreeBranch.open_containing('/non/existent/path',
            ui_mode=True, _critical_dialog=mf)
        self.assertEqual(None, tb)
        self.assertEqual(1, mf.count)
        #
        self.make_branch('a')
        mf = mock.MockFunction()
        tb = tree_branch.TreeBranch.open_containing('a',
            require_tree=True, ui_mode=True, _critical_dialog=mf)
        self.assertEqual(None, tb)
        self.assertEqual(1, mf.count)

    def test_open(self):
        self.make_branch('a')
        mf = mock.MockFunction()
        tb = tree_branch.TreeBranch.open_containing('a',
            require_tree=False, ui_mode=False, _critical_dialog=mf)
        self.assertNotEqual(None, tb)
        self.assertEqual('a', tb.location)
        self.assertNotEqual(None, tb.branch)
        self.assertEqual(None, tb.tree)
        self.assertEqual('', tb.relpath)
        self.assertEqual(0, mf.count)
        #
        self.make_branch_and_tree('b')
        tb = tree_branch.TreeBranch.open_containing('b',
            require_tree=True, ui_mode=False, _critical_dialog=mf)
        self.assertNotEqual(None, tb)
        self.assertEqual('b', tb.location)
        self.assertNotEqual(None, tb.branch)
        self.assertNotEqual(None, tb.tree)
        self.assertEqual('', tb.relpath)
        self.assertEqual(0, mf.count)
        #
        self.build_tree(['b/dir/'])
        tb = tree_branch.TreeBranch.open_containing('b/dir',
            require_tree=True, ui_mode=False, _critical_dialog=mf)
        self.assertNotEqual(None, tb)
        self.assertEqual('b/dir', tb.location)
        self.assertNotEqual(None, tb.branch)
        self.assertNotEqual(None, tb.tree)
        self.assertEqual('dir', tb.relpath)
        self.assertEqual(0, mf.count)
