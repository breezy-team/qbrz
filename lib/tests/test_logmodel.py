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

from bzrlib.tests import TestCase
from PyQt4 import QtCore
from bzrlib.plugins.qbzr.lib.logmodel import get_bug_id, QVariant_fromList


class TestGetBugId(TestCase):

    def test_launchpad(self):
        self.assertEquals('261234', get_bug_id('https://launchpad.net/bugs/261234'))

    def test_trac(self):
        self.assertEquals('3852', get_bug_id('http://bugs.musicbrainz.org/ticket/3852'))

    def test_bugzilla(self):
        self.assertEquals('169104', get_bug_id('http://bugs.kde.org/show_bug.cgi?id=169104'))

    def test_redmine(self):
        self.assertEquals('1832', get_bug_id('http://www.redmine.org/issues/show/1832'))

    def test_fogbugz(self):
        self.assertEquals('1234', get_bug_id('http://test.fogbugz.com/default.asp?1234'))


class TestQVariantFromList(TestCase):

    def test_variant_from_list(self):
        lst = [QtCore.QVariant("a"), QtCore.QVariant("b")]
        var = QVariant_fromList(lst)
        lst = var.toList()
        self.assertEquals("a", lst[0].toString())
        self.assertEquals("b", lst[1].toString())
