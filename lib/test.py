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

"""Tests for QBzr plugin."""

from bzrlib.tests import TestCase

from bzrlib.plugins.qbzr.lib import util


class TestUtilFuncs(TestCase):

    def test_file_extension(self):
        self.assertEquals('', util.file_extension(''))
        self.assertEquals('', util.file_extension('/foo/bar.x/'))
        self.assertEquals('', util.file_extension('C:/foo/bar.x/'))
        self.assertEquals('', util.file_extension('.bzrignore'))
        self.assertEquals('', util.file_extension('/foo/bar.x/.bzrignore'))
        self.assertEquals('.txt', util.file_extension('foo.txt'))
        self.assertEquals('.txt', util.file_extension('/foo/bar.x/foo.txt'))
