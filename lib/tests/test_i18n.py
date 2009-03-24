# -*- coding: utf-8 -*-
#
# Copyright (C) 2008 Alexander Belchenko
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

"""Tests for i18n module"""

from bzrlib.tests import TestCase
from bzrlib.plugins.qbzr.lib import i18n


class TestI18n(TestCase):

    def setUp(self):
        TestCase.setUp(self)
        i18n.uninstall()

    def tearDown(self):
        i18n.uninstall()
        TestCase.tearDown(self)

    def test_gettext(self):
        # simple pass-through
        self.assertEquals('file', i18n.gettext('file'))

    def test_ngettext(self):
        self.assertEquals('singular', i18n.ngettext('singular', 'plural', 1))
        self.assertEquals('plural', i18n.ngettext('singular', 'plural', 2))
        self.assertEquals('plural', i18n.ngettext('singular', 'plural', 0))
