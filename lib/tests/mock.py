# -*- coding: utf-8 -*-
#
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

"""Simple mock objects."""

from bzrlib.tests import TestCase


class MockFunction(object):
    """Mock function object that remember how many times it called
    and which arguments were used.
    """

    def __init__(self, func=None, ret=None):
        self.count = 0
        self.args = []
        self._func = func
        self.ret = ret

    def __call__(self, *args, **kw):
        self.count += 1
        self.args.append((args, kw))
        if self._func is not None:
            return self._func(*args, **kw)
        else:
            return self.ret

class TestMockFunction(TestCase):

    def test_call(self):
        mf = MockFunction()
        self.assertEquals(0, mf.count)
        self.assertEquals([], mf.args)
        # 1st call
        mf(None, 1, 'foo')
        self.assertEquals(1, mf.count)
        self.assertEquals([((None, 1, 'foo'), {})], mf.args)
        # 2nd call
        mf('bar', baz='spam')
        self.assertEquals(2, mf.count)
        self.assertEquals([
            ((None, 1, 'foo'), {}),
            (('bar',), {'baz': 'spam'}),
            ], mf.args)
