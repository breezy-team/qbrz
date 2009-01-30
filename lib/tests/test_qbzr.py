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

"""Tests for QBzr plugin."""

from bzrlib.tests import TestCase
from bzrlib.plugins.qbzr import LazyCommandProxy


class FakeCommand(object):
    hidden = True


class TestLazyCommandProxy(TestCase):

    def test_proxy_attrs(self):
        """Test that the class proxies attributes."""
        cmd = LazyCommandProxy('bzrlib.plugins.qbzr.lib.tests.test_qbzr', 'FakeCommand', [])
        self.assertEquals(cmd.hidden, True)

    def test_direct_aliases(self):
        """Test that the class accesses aliases directly."""
        cmd = LazyCommandProxy('bzrlib.plugins.qbzr.lib.tests.test_qbzr_doesnt_exist', 'FakeCommand', ['foo'])
        self.assertEquals(cmd.aliases, ['foo'])
