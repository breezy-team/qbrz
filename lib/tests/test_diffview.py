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
from bzrlib.plugins.qbzr.lib.diffview import insert_intraline_changes


class FakeCursor(object):

    def __init__(self):
        self.text = ''

    def insertText(self, text, format):
        self.text += '<%s>%s</%s>' % (format, text, format)


class TestInsertIntralineChanges(TestCase):

    def test_no_change(self):
        cursor1 = FakeCursor()
        cursor2 = FakeCursor()
        insert_intraline_changes(cursor1, cursor2, 'foo', 'foo', 'n', 'ins', 'del')
        self.assertEquals('<n>foo</n>', cursor1.text)
        self.assertEquals('<n>foo</n>', cursor2.text)

    def test_whole_line_changed(self):
        cursor1 = FakeCursor()
        cursor2 = FakeCursor()
        insert_intraline_changes(cursor1, cursor2, 'foo', 'bar', 'n', 'ins', 'del')
        self.assertEquals('<del>foo</del>', cursor1.text)
        self.assertEquals('<ins>bar</ins>', cursor2.text)

    def test_delete_char(self):
        cursor1 = FakeCursor()
        cursor2 = FakeCursor()
        insert_intraline_changes(cursor1, cursor2, 'foo', 'fo', 'n', 'ins', 'del')
        self.assertEquals('<n>fo</n><del>o</del>', cursor1.text)
        self.assertEquals('<n>fo</n>', cursor2.text)

    def test_insert_char(self):
        cursor1 = FakeCursor()
        cursor2 = FakeCursor()
        insert_intraline_changes(cursor1, cursor2, 'fo', 'foo', 'n', 'ins', 'del')
        self.assertEquals('<n>fo</n>', cursor1.text)
        self.assertEquals('<n>fo</n><ins>o</ins>', cursor2.text)

    def test_replace_2_chars(self):
        cursor1 = FakeCursor()
        cursor2 = FakeCursor()
        insert_intraline_changes(cursor1, cursor2, 'foobar', 'foObAr', 'n', 'ins', 'del')
        self.assertEquals('<n>fo</n><del>o</del><n>b</n><del>a</del><n>r</n>', cursor1.text)
        self.assertEquals('<n>fo</n><ins>O</ins><n>b</n><ins>A</ins><n>r</n>', cursor2.text)
