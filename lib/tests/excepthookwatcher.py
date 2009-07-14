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

import sys

class TestWatchExceptHook(object):
    """Test class that watches for exceptions with an excepthook.
    
    To use, inherit from this class, and a relevent TestCase. e.g.:
    
        class TestMyCode(TestWatchExceptHook, TestCase)
    """

    def find_base(self):
        self_type = type(self)
        for base_type in self_type.__mro__:
            if (not base_type == self_type and
                not base_type == TestWatchExceptHook):
                return base_type
    
    def run(self, result = None):
        global current_result, current_test
        
        if result is None: result = self.defaultTestResult()
        current_result = result
        current_test = self
        
        old_excepthook = sys.excepthook
        sys.excepthook = excepthook
        try:
            self.find_base().run(self, result)
        finally:
            current_result = None
            current_test = None
            sys.excepthook = old_excepthook

current_result = None
current_test = None

def excepthook(type, value, traceback):
    exc_info = (type, value, traceback)
    if type == AssertionError:
        current_result.addFailure(current_test, exc_info)
    else:
        current_result.addError(current_test, exc_info)