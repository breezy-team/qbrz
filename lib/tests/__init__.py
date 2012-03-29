# -*- coding: utf-8 -*-
#
# QBzr - Qt frontend to Bazaar commands
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

import os
import sys
from bzrlib import (
    tests,
    trace,
    )

try:
    from PyQt4 import QtGui, QtTest
except ImportError:
    pass


def load_tests(basic_tests, module, loader):
    testmod_names = [
        'mock',
        'test_annotate',
        'test_autocomplete',
        'test_bugs',
        'test_cat',
        'test_commit',
        'test_commit_data',
        #'test_diffview', - broken by API changes
        'test_extra_isignored',
        'test_extra_isversioned',
        'test_i18n',
        'test_log',
        'test_loggraphviz',
        'test_logmodel',
        'test_revisionmessagebrowser',
        'test_spellcheck',
        'test_subprocess',
        'test_tree_branch',
        'test_treewidget',
        'test_util',
        'test_decorator',
        'test_guidebar',
        'test_extdiff',
    ]
    for name in testmod_names:
        m = "%s.%s" % (__name__, name)
        try:
            basic_tests.addTests(loader.loadTestsFromModuleName(m))
        except ImportError, e:
            if str(e).endswith('PyQt4'):
                trace.note('QBzr: skip module %s '
                    'because PyQt4 is not installed' % m)
            else:
                raise
    return basic_tests

# The application should be initialized only once pre process, but this should
# be delayed until the first tests is run in a given process, doing it when the
# tests are loaded is too early and failed for selftest --parallel=fork
_qt_app = None

class QTestCase(tests.TestCaseWithTransport):

    def setUp(self):
        super(QTestCase, self).setUp()
        global _qt_app
        if _qt_app is None:
            _qt_app = QtGui.QApplication(sys.argv)
        def excepthook_tests(eclass, evalue, tb):
            def _reraise_on_cleanup():
                raise eclass, evalue, tb
            self.addCleanup(_reraise_on_cleanup)
        self.overrideAttr(sys, "excepthook", excepthook_tests)

    def waitUntil(self, break_condition, timeout, timeout_msg=None):
        erapsed = 0
        while (True):
            if break_condition():
                return
            if timeout < erapsed:
                self.fail(timeout_msg or 'Timeout!')
            QtTest.QTest.qWait(200)
            erapsed += 200

