# -*- coding: utf-8 -*-
#
# QBzr - Qt frontend to Bazaar commands
# Copyright (C) 2010 QBzr Developers
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

from PyQt4 import QtCore
import time
from collections import defaultdict
from functools import wraps

"""Decorators for debugging and maybe main work mode."""

def print_in_out(unbound):
    """Decorator to print input arguments and return value of the function."""
    def _run(*args, **kwargs):
        from bzrlib.trace import mutter
        a = ','.join(repr(i) for i in args)
        b = ','.join('%s=%r' % (i,j) for (i,j) in kwargs.iteritems())
        if a and b:
            a = a + ',' + b
        else:
            a = a or b
        func_name = unbound.func_name
        mutter('Called %s(%s)' % (func_name, a))
        result = unbound(*args, **kwargs)
        mutter('%s returned %r' % (func_name, result))
        return result
    return _run

class LazyCall(object):

    def __init__(self, millisec, func, callback=None):
        self.func = func
        self.millisec = millisec
        self.callback = callback
        self._last_scheduled_at = 0

    def call(self, *args, **kargs):
        self._func = lambda:self.func(*args, **kargs)
        if self._last_scheduled_at == 0:
            QtCore.QTimer.singleShot(self.millisec, self._exec)
        self._last_scheduled_at = time.time()

    def _exec(self):
        elapsed = (time.time() - self._last_scheduled_at) * 1000
        if elapsed < self.millisec:
            # Retry
            QtCore.QTimer.singleShot(self.millisec - elapsed, self._exec)
            return

        last_executed_at = self._last_scheduled_at
        ret = self._func()
        has_next = last_executed_at != self._last_scheduled_at
        if self.callback:
            self.callback(ret, has_next)

        if has_next:
            # One more call if there was another request when executing proc
            QtCore.QTimer.singleShot(self.millisec, self._exec)
            return
        
        self._last_scheduled_at = 0

def lazy_call(millisec, per_instance=False):
    """
    Decorator to delay function call.
    Specified function will called after waiting `millisec`,
    if there are multiple call while waiting, only last one will be done.
    """
    def _lazy_call(function):
        if per_instance:
            _instances = defaultdict(lambda:LazyCall(millisec, function))
            def __lazy_call(*args, **kwargs):
                key = hash(args[0])
                caller = _instances[key]
                if not caller.callback:
                    def cleanup(ret, has_next):
                        if not has_next:
                            del _instances[key]
                    caller.callback = cleanup
                caller.call(*args, **kwargs)
        else:
            caller = LazyCall(millisec, function)
            def __lazy_call(*args, **kwargs):
                caller.call(*args, **kwargs)
        return __lazy_call
    return _lazy_call




