# -*- coding: utf-8 -*-
#
# Copyright (C) 2010 Alexander Belchenko <bialix@ukr.net>
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
from bzrlib.plugins.qbzr.lib.commit import CommitWindow


class TestCommit(TestWatchExceptHook, TestCaseWithTransport):
    
    def setUp(self):
        super(TestCommit, self).setUp()
        replace_report_exception(self)
    
    def test_bug_526011(self):
        tree = self.make_branch_and_tree('branch')
        self.build_tree(['branch/a/'])
        tree.add('a')
        tree.commit(message='1')
        win = CommitWindow(tree=tree, selected_list=['a'])
        self.addCleanup(win.close)
        win.show()
        QtCore.QCoreApplication.processEvents()
        QtCore.QCoreApplication.processEvents()
