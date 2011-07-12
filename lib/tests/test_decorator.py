# -*- coding: utf-8 -*-
#
# QBzr - Qt frontend to Bazaar commands
# Copyright (C) 2011 QBzr Developers
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

import time
from PyQt4 import QtCore, QtGui
from bzrlib.plugins.qbzr.lib.decorators import lazy_call
from bzrlib.tests import TestCase, TestCaseWithTransport
from bzrlib.plugins.qbzr.lib import tests as qtests


test_value = 0
test2_value = 0

@lazy_call(50)
def method_test(arg):
    global test_value
    test_value += arg

@lazy_call(50)
def method_test2(arg):
    global test2_value
    test2_value += arg

class ClassTest(object):
    def __init__(self):
        self.value = 0
        self.value2 = 0

    @lazy_call(50, per_instance=True)
    def test(self, value):
        self.value += value
    
    @lazy_call(50)
    def test2(self, value):
        self.value2 += value


class TestLazyCall(qtests.QTestCase):

    def setUp(self):
        qtests.QTestCase.setUp(self)
        global test_value
        global test2_value
        test_value = test2_value = 0

    def test_single(self):
        method_test(1)
        time.sleep(0.01)
        QtCore.QCoreApplication.processEvents()
        method_test(2)
        time.sleep(0.01)
        QtCore.QCoreApplication.processEvents()
        method_test(4)
        time.sleep(0.1)
        QtCore.QCoreApplication.processEvents()
        # Execute only last one call.
        self.assertEqual(test_value, 4)

    def test_twice(self):
        method_test(1)
        time.sleep(0.01)
        QtCore.QCoreApplication.processEvents()
        method_test(2)
        time.sleep(0.1)
        QtCore.QCoreApplication.processEvents()
        method_test(4)
        time.sleep(0.1)
        QtCore.QCoreApplication.processEvents()
        # Execute 2nd and 3rd calls.
        self.assertEqual(test_value, 6)

    def test_count_millisec_from_last_call(self):
        for i in xrange(5):
            method_test(1)
            time.sleep(0.01)
            QtCore.QCoreApplication.processEvents()
        # No call is executed
        self.assertEqual(test_value, 0)
        time.sleep(0.1)
        QtCore.QCoreApplication.processEvents()
        # Execute only last one call.
        self.assertEqual(test_value, 1)

    def test_2_methods(self):
        method_test(1)
        method_test2(2)
        time.sleep(0.01)
        QtCore.QCoreApplication.processEvents()

        method_test(2)
        method_test2(4)
        time.sleep(0.1)
        QtCore.QCoreApplication.processEvents()

        self.assertEqual(test_value, 2)
        self.assertEqual(test2_value, 4)

    def test_instance_method(self):
        a = ClassTest()
        b = ClassTest()
        a.test(1)
        b.test(10)
        time.sleep(0.1)
        QtCore.QCoreApplication.processEvents()
        self.assertEqual(a.value, 1)
        self.assertEqual(b.value, 10)

        a.test(2)
        b.test(20)
        time.sleep(0.01)
        QtCore.QCoreApplication.processEvents()

        a.test(3)
        b.test(30)
        time.sleep(0.1)
        QtCore.QCoreApplication.processEvents()
        self.assertEqual(a.value, 4)
        self.assertEqual(b.value, 40)

    def test_without_instance_method_flag(self):
        a = ClassTest()
        b = ClassTest()
        a.test2(1)
        b.test2(10)
        time.sleep(0.1)
        QtCore.QCoreApplication.processEvents()
        # a.test2 does not called.
        self.assertEqual(a.value2, 0)
        self.assertEqual(b.value2, 10)

