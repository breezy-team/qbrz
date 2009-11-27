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
from bzrlib.plugins.qbzr.lib.tests import replace_report_exception
from bzrlib.plugins.qbzr.lib.tests.excepthookwatcher import TestWatchExceptHook
from bzrlib.plugins.qbzr.lib.log import LogWindow

class TestLog(TestWatchExceptHook, TestCaseWithTransport):
    
    def test_just_show_log_blank_branch(self):
        tree1 = self.make_branch_and_tree('tree1')

        win = LogWindow(['tree1'], None)
        self.addCleanup(win.close)
        win.show()
        QtCore.QCoreApplication.processEvents()

    def setUp(self):
        super(TestLog, self).setUp()
        replace_report_exception(self)

    def test_just_show_log_simple_commit(self):
        wt = self.make_branch_and_tree('.')
        wt.commit('empty commit')
        self.build_tree(['hello'])
        wt.add('hello')
        wt.commit('add one file',
                  committer=u'\u013d\xf3r\xe9m \xcdp\u0161\xfam '
                            u'<test@example.com>')

        win = LogWindow(['.'], None)
        self.addCleanup(win.close)
        win.show()
        QtCore.QCoreApplication.processEvents()
