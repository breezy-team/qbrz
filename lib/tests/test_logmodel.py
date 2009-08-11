# -*- coding: utf-8 -*-
#
# Copyright (C) 2008 Lukáš Lalinský <lalinsky@gmail.com>
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
from PyQt4 import QtCore
from bzrlib.plugins.qbzr.lib.logmodel import (
    get_bug_id,
    QVariant_fromList,
    LogModel,
    )
from bzrlib.plugins.qbzr.lib.loggraphprovider import LogGraphProvider

from bzrlib.plugins.qbzr.lib.tests.modeltest import ModelTest
from bzrlib.plugins.qbzr.lib.tests.excepthookwatcher import TestWatchExceptHook

class TestGetBugId(TestCase):

    def test_launchpad(self):
        self.assertEquals('261234', get_bug_id('https://launchpad.net/bugs/261234'))

    def test_trac(self):
        self.assertEquals('3852', get_bug_id('http://bugs.musicbrainz.org/ticket/3852'))

    def test_bugzilla(self):
        self.assertEquals('169104', get_bug_id('http://bugs.kde.org/show_bug.cgi?id=169104'))

    def test_redmine(self):
        self.assertEquals('1832', get_bug_id('http://www.redmine.org/issues/show/1832'))

    def test_fogbugz(self):
        self.assertEquals('1234', get_bug_id('http://test.fogbugz.com/default.asp?1234'))

    def test_roundup(self):
        self.assertEquals('5243', get_bug_id('http://bugs.python.org/issue5243'))


class TestQVariantFromList(TestCase):

    def test_variant_from_list(self):
        lst = [QtCore.QVariant("a"), QtCore.QVariant("b")]
        var = QVariant_fromList(lst)
        lst = var.toList()
        self.assertEquals("a", lst[0].toString())
        self.assertEquals("b", lst[1].toString())

class TestModel(TestWatchExceptHook, TestCaseWithTransport):
    
    def _test(self, wt):
        graph_provider = LogGraphProvider(False)
        log_model = LogModel(graph_provider)
        graph_provider.open_branch(wt.branch, None, wt)
        log_model.load_graph_all_revisions()
        modeltest = ModelTest(log_model, None);
    
    def test_empty_branch(self):
        wt = self.make_branch_and_tree('.')
        self._test(wt)

    # Copied for bzrlib/tests/test_log.py
    def _prepare_tree_with_merges(self, with_tags=False):
        wt = self.make_branch_and_memory_tree('.')
        wt.lock_write()
        self.addCleanup(wt.unlock)
        wt.add('')
        wt.commit('rev-1', rev_id='rev-1',
                  timestamp=1132586655, timezone=36000,
                  committer='Joe Foo <joe@foo.com>')
        wt.commit('rev-merged', rev_id='rev-2a',
                  timestamp=1132586700, timezone=36000,
                  committer='Joe Foo <joe@foo.com>')
        wt.set_parent_ids(['rev-1', 'rev-2a'])
        wt.branch.set_last_revision_info(1, 'rev-1')
        wt.commit('rev-2', rev_id='rev-2b',
                  timestamp=1132586800, timezone=36000,
                  committer='Joe Foo <joe@foo.com>')
        if with_tags:
            branch = wt.branch
            branch.tags.set_tag('v0.2', 'rev-2b')
            wt.commit('rev-3', rev_id='rev-3',
                      timestamp=1132586900, timezone=36000,
                      committer='Jane Foo <jane@foo.com>')
            branch.tags.set_tag('v1.0rc1', 'rev-3')
            branch.tags.set_tag('v1.0', 'rev-3')
        return wt

    def test_merges(self):
        wt = self._prepare_tree_with_merges()
        self._test(wt)


