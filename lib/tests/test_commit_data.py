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
    QBzrCommitData,
    )


class TestCommitDataBase(TestCase):

    def test_empty(self):
        d = CommitData()
        # CommitData instance has bool value False if there is no data inside
        self.assertFalse(bool(d))
        self.assertEqual(None, d['message'])
        self.assertEqual({}, d.as_dict())
        self.assertEqual([], d.keys())

    def test_set_data_dict(self):
        d = CommitData()
        d.set_data({'message': 'foo bar'})
        # CommitData instance has bool value True if there is some data inside
        self.assertTrue(bool(d))
        self.assertEqual('foo bar', d['message'])
        self.assertEqual({'message': 'foo bar'}, d.as_dict())
        self.assertEqual(['message'], d.keys())

    def test_set_data_kw(self):
        d = CommitData()
        d.set_data(message='foo bar')
        # CommitData instance has bool value True if there is some data inside
        self.assertTrue(bool(d))
        self.assertEqual('foo bar', d['message'])
        self.assertEqual({'message': 'foo bar'}, d.as_dict())
        self.assertEqual(['message'], d.keys())

    def test_set_data_dict_and_kw(self):
        d = CommitData()
        d.set_data({'fixes': 'lp:123456'}, message='foo bar')
        # CommitData instance has bool value True if there is some data inside
        self.assertTrue(bool(d))
        self.assertEqual('foo bar', d['message'])
        self.assertEqual({'message': 'foo bar',
                          'fixes': 'lp:123456',
                         }, d.as_dict())
        self.assertEqual(set(['message', 'fixes']), set(d.keys()))

    def test_init_with_data(self):
        d = CommitData(data={'fixes': 'lp:123456', 'message': 'foo bar'})
        # CommitData instance has bool value True if there is some data inside
        self.assertTrue(bool(d))
        self.assertEqual('foo bar', d['message'])
        self.assertEqual({'message': 'foo bar',
                          'fixes': 'lp:123456',
                         }, d.as_dict())
        self.assertEqual(set(['message', 'fixes']), set(d.keys()))

    def test_compare_data(self):
        this = CommitData(data={'fixes': 'lp:123456', 'message': 'foo bar'})
        self.assertTrue(this.compare_data(
            CommitData(data={'fixes': 'lp:123456',
                             'message': 'foo bar'})))
        self.assertTrue(this.compare_data({'fixes': 'lp:123456',
                                           'message': 'foo bar'}))
        other = CommitData(data={'fixes': 'lp:123456',
                                 'message': 'foo bar',
                                 'old_revid': 'xxx',
                                 'new_revid': 'yyy',
                                 })
        self.assertFalse(this.compare_data(other))
        self.assertTrue(this.compare_data(other, all_keys=False))


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

    def test_set_data_on_uncommit_bugids(self):
        wt = self.make_branch_and_tree('.')
        self.run_bzr('commit --unchanged -m foo --fixes lp:12345 --fixes lp:67890')
        revid1 = wt.last_revision()
        d = CommitData(branch=wt.branch)
        d.set_data_on_uncommit(revid1, None)
        self.assertEqual({'message': 'foo',
                          'bugs': 'lp:12345 lp:67890',
                          'old_revid': revid1,
                          'new_revid': 'null:',
                         }, d.as_dict())

    def test_load_nothing(self):
        wt = self.make_branch_and_tree('.')
        d = CommitData(tree=wt)
        d.load()
        self.assertEqual({}, d.as_dict())

    def test_save_data(self):
        wt = self.make_branch_and_tree('.')
        d = CommitData(tree=wt)
        d.set_data(message='spam', old_revid='foo', new_revid='bar')
        d.save()
        # check branch.conf
        cfg = wt.branch.get_config()
        self.assertEqual({'message': 'spam',
                          'old_revid': 'foo',
                          'new_revid': 'bar',
                          }, cfg.get_user_option('commit_data'))

    def test_save_filter_out_empty_data(self):
        wt = self.make_branch_and_tree('.')
        d = CommitData(tree=wt)
        d.set_data({'message': '', 'foo': 'bar'})
        d.save()
        # check branch.conf
        cfg = wt.branch.get_config()
        self.assertEqual({'foo': 'bar'}, cfg.get_user_option('commit_data'))

    def test_load_saved_data(self):
        wt = self.make_branch_and_tree('.')
        cfg = wt.branch.get_config()
        cfg.set_user_option('commit_data',
            {'message': 'spam',
             'old_revid': 'foo',
             'new_revid': 'bar',
             })
        d = CommitData(tree=wt)
        d.load()
        self.assertEqual({'message': 'spam',
                          'old_revid': 'foo',
                          'new_revid': 'bar',
                          }, d.as_dict())

    def test_wipe_saved_data(self):
        wt = self.make_branch_and_tree('.')
        cfg = wt.branch.get_config()
        cfg.set_user_option('commit_data',
            {'message': 'spam',
             'old_revid': 'foo',
             'new_revid': 'bar',
             })
        d = CommitData(tree=wt)
        d.wipe()
        # check branch.conf
        cfg = wt.branch.get_config()
        self.assertEqual({}, cfg.get_user_option('commit_data'))



class TestQBzrCommitData(TestCaseWithTransport):

    def test_io_old_data_transition(self):
        # we should handle old data (i.e. qbzr_commit_message) gracefully
        wt = self.make_branch_and_tree('.')
        cfg = wt.branch.get_config()
        cfg.set_user_option('qbzr_commit_message', 'spam')
        # load
        d = QBzrCommitData(tree=wt)
        d.load()
        self.assertEqual({'message': 'spam',
                          }, d.as_dict())
        #
        # if here both old and new then prefer new
        cfg.set_user_option('commit_data', {'foo': 'bar'})
        d = QBzrCommitData(tree=wt)
        d.load()
        self.assertEqual({'foo': 'bar',
                          }, d.as_dict())
        #
        # on save we should clear old data
        d = QBzrCommitData(tree=wt)
        d.set_data(message='eggs', old_revid='foo', new_revid='bar')
        d.save()
        # check branch.conf
        cfg = wt.branch.get_config()
        self.assertEqual('', cfg.get_user_option('qbzr_commit_message'))
        self.assertEqual({'message': 'eggs',
                          'old_revid': 'foo',
                          'new_revid': 'bar',
                          }, cfg.get_user_option('commit_data'))
        #
        # on wipe we should clear old data too
        cfg = wt.branch.get_config()
        cfg.set_user_option('qbzr_commit_message', 'spam')
        d = QBzrCommitData(tree=wt)
        d.wipe()
        # check branch.conf
        cfg = wt.branch.get_config()
        self.assertEqual('', cfg.get_user_option('qbzr_commit_message'))
        self.assertEqual({}, cfg.get_user_option('commit_data'))
