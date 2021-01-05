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

from breezy.tests import TestCase, TestCaseWithTransport
from PyQt5 import QtCore

from breezy.plugins.qbrz.lib import tests as qtests
from breezy.plugins.qbrz.lib.logmodel import (LogModel, GraphVizLoader)
from breezy.plugins.qbrz.lib.loggraphviz import BranchInfo
from breezy.plugins.qbrz.lib.util import ThrobberWidget

from breezy.plugins.qbrz.lib.tests.modeltest import ModelTest


class TestModel(qtests.QTestCase):

    def _test(self, wt):
        def processEvents():
            pass
        throbber = ThrobberWidget(None)
        log_model = LogModel(processEvents, throbber)
        modeltest = ModelTest(log_model, None)
        bi = BranchInfo('', wt, wt.branch)
        log_model.load((bi,), bi, None, False, GraphVizLoader)

    def test_empty_branch(self):
        wt = self.make_branch_and_tree('.')
        self._test(wt)

    # Copied for breezy/tests/test_log.py
    def _prepare_tree_with_merges(self, with_tags=False):
        wt = self.make_branch_and_memory_tree('.')
        wt.lock_write()
        self.addCleanup(wt.unlock)
        wt.add('')
        wt.commit('rev-1', rev_id=b'rev-1', timestamp=1132586655, timezone=36000, committer='Joe Foo <joe@foo5.com>')
        wt.commit('rev-merged', rev_id=b'rev-2a', timestamp=1132586700, timezone=36000, committer='Joe Foo <joe@foo5.com>')
        wt.set_parent_ids([b'rev-1', b'rev-2a'])
        wt.branch.set_last_revision_info(1, b'rev-1')
        wt.commit('rev-2', rev_id=b'rev-2b', timestamp=1132586800, timezone=36000, committer='Joe Foo <joe@foo5.com>')
        if with_tags:
            branch = wt.branch
            branch.tags.set_tag('v0.2', b'rev-2b')
            wt.commit('rev-3', rev_id=b'rev-3', imestamp=1132586900, timezone=36000, committer='Jane Foo <jane@foo5.com>')
            branch.tags.set_tag('v1.0rc1', b'rev-3')
            branch.tags.set_tag('v1.0', b'rev-3')
        return wt

    def test_merges(self):
        wt = self._prepare_tree_with_merges()
        self._test(wt)
