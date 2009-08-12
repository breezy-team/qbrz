# -*- coding: utf-8 -*-
#
# QBzr - Qt frontend to Bazaar commands
# Copyright (C) 2009 Alexander Belchenko
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

"""Tests for commit data object and operations."""

from bzrlib.tests import TestCase, TestCaseWithTransport
from bzrlib.plugins.qbzr.lib.commit_data import (
    CommitData,
    )


class TestCommitDataBase(TestCase):

    def test_empty(self):
        d = CommitData()
        self.assertFalse(bool(d))
        self.assertEqual(None, d['message'])
        self.assertEqual({}, d.as_dict())

    def test_set_data(self):
        d = CommitData()
        d.set_data({'message': 'foo bar'})
        self.assertTrue(bool(d))
        self.assertEqual('foo bar', d['message'])
        self.assertEqual({'message': 'foo bar'}, d.as_dict())
        #
        d = CommitData()
        d.set_data(message='foo bar')
        self.assertTrue(bool(d))
        self.assertEqual('foo bar', d['message'])
        self.assertEqual({'message': 'foo bar'}, d.as_dict())
        #
        d = CommitData()
        d.set_data({'fixes': 'lp:123456'}, message='foo bar')
        self.assertTrue(bool(d))
        self.assertEqual('foo bar', d['message'])
        self.assertEqual({'message': 'foo bar',
                          'fixes': 'lp:123456',
                         }, d.as_dict())


class TestCommitDataWithTree(TestCaseWithTransport):

    def test_set_data_on_uncommit(self):
        wt = self.make_branch_and_tree('.')
        revid1 = wt.commit(message='1')
        # imitate uncommit in branch with only one revision
        d = CommitData(branch=wt.branch)
        d.set_data_on_uncommit(revid1, None)
        self.assertEqual({'message': '1',
                          'old_revid': revid1,
                          'new_revid': 'null:',
                         }, d.as_dict())
        #
        revid2 = wt.commit(message='2')
        # imitate uncommit in branch with several revisions
        d = CommitData(branch=wt.branch)
        d.set_data_on_uncommit(revid2, revid1)
        self.assertEqual({'message': '2',
                          'old_revid': revid2,
                          'new_revid': revid1,
                         }, d.as_dict())
