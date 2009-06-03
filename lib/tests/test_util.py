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

import sys
from bzrlib.tests import TestCase
from bzrlib.plugins.qbzr.lib import util


class TestUtil(TestCase):

    def test_file_extension(self):
        self.assertEquals('', util.file_extension(''))
        self.assertEquals('', util.file_extension('/foo/bar.x/'))
        self.assertEquals('', util.file_extension('C:/foo/bar.x/'))
        self.assertEquals('', util.file_extension('.bzrignore'))
        self.assertEquals('', util.file_extension('/foo/bar.x/.bzrignore'))
        self.assertEquals('.txt', util.file_extension('foo.txt'))
        self.assertEquals('.txt', util.file_extension('/foo/bar.x/foo.txt'))

    def test_filter_options(self):
        fo = util.FilterOptions()
        self.assertEquals(False, bool(fo))
        self.assertEquals(False, fo.is_all_enable())
        self.assertEquals('', fo.to_str())
        self.assertEquals(False, fo.check('added'))
        self.assertEquals(False, fo.check('removed'))
        self.assertEquals(False, fo.check('deleted'))
        self.assertEquals(False, fo.check('renamed'))
        self.assertEquals(False, fo.check('modified'))
        self.assertEquals(False, fo.check('renamed and modified'))
        self.assertRaises(ValueError, fo.check, 'spam')

        fo = util.FilterOptions(deleted=True)
        self.assertEquals(True, bool(fo))
        self.assertEquals(False, fo.is_all_enable())
        self.assertEquals('deleted files', fo.to_str())
        self.assertEquals(False, fo.check('added'))
        self.assertEquals(True, fo.check('removed'))
        self.assertEquals(True, fo.check('deleted'))
        self.assertEquals(False, fo.check('renamed'))
        self.assertEquals(False, fo.check('modified'))
        self.assertEquals(False, fo.check('renamed and modified'))

        fo = util.FilterOptions(added=True)
        self.assertEquals(True, bool(fo))
        self.assertEquals(False, fo.is_all_enable())
        self.assertEquals('added files', fo.to_str())
        self.assertEquals(True, fo.check('added'))
        self.assertEquals(False, fo.check('removed'))
        self.assertEquals(False, fo.check('deleted'))
        self.assertEquals(False, fo.check('renamed'))
        self.assertEquals(False, fo.check('modified'))
        self.assertEquals(False, fo.check('renamed and modified'))

        fo = util.FilterOptions(renamed=True)
        self.assertEquals(True, bool(fo))
        self.assertEquals(False, fo.is_all_enable())
        self.assertEquals('renamed files', fo.to_str())
        self.assertEquals(False, fo.check('added'))
        self.assertEquals(False, fo.check('removed'))
        self.assertEquals(False, fo.check('deleted'))
        self.assertEquals(True, fo.check('renamed'))
        self.assertEquals(False, fo.check('modified'))
        self.assertEquals(True, fo.check('renamed and modified'))

        fo = util.FilterOptions(modified=True)
        self.assertEquals(True, bool(fo))
        self.assertEquals(False, fo.is_all_enable())
        self.assertEquals('modified files', fo.to_str())
        self.assertEquals(False, fo.check('added'))
        self.assertEquals(False, fo.check('removed'))
        self.assertEquals(False, fo.check('deleted'))
        self.assertEquals(False, fo.check('renamed'))
        self.assertEquals(True, fo.check('modified'))
        self.assertEquals(True, fo.check('renamed and modified'))

        fo = util.FilterOptions(added=True, deleted=True, modified=True,
                renamed=True)
        self.assertEquals(True, bool(fo))
        self.assertEquals(True, fo.is_all_enable())
        self.assertEquals('deleted files, added files, '
            'renamed files, modified files', fo.to_str())
        self.assertEquals(True, fo.check('added'))
        self.assertEquals(True, fo.check('removed'))
        self.assertEquals(True, fo.check('deleted'))
        self.assertEquals(True, fo.check('renamed'))
        self.assertEquals(True, fo.check('modified'))
        self.assertEquals(True, fo.check('renamed and modified'))

        fo = util.FilterOptions(all_enable=True)
        self.assertEquals(True, bool(fo))
        self.assertEquals(True, fo.is_all_enable())

        fo = util.FilterOptions()
        fo.all_enable()
        self.assertEquals(True, bool(fo))
        self.assertEquals(True, fo.is_all_enable())

    def test_url_for_display(self):
        self.assertEquals(None, util.url_for_display(None))
        self.assertEquals('', util.url_for_display(''))
        self.assertEquals('http://bazaar.launchpad.net/~qbzr-dev/qbzr/trunk',
            util.url_for_display('http://bazaar.launchpad.net/%7Eqbzr-dev/qbzr/trunk'))
        if sys.platform == 'win32':
            self.assertEquals('C:/work/qbzr/',
                util.url_for_display('file:///C:/work/qbzr/'))
        else:
            self.assertEquals('/home/work/qbzr/',
                util.url_for_display('file:///home/work/qbzr/'))

    def test_htmlencode(self):
        self.assertEquals('&quot;&amp;&lt;&gt;', util.htmlencode('"&<>'))

    def test_is_binary_content(self):
        self.assertEquals(False, util.is_binary_content([]))
        self.assertEquals(False, util.is_binary_content(['foo\n', 'bar\r\n', 'spam\r']))
        self.assertEquals(True, util.is_binary_content(['\x00']))
        self.assertEquals(True, util.is_binary_content(['a'*2048 + '\x00']))

    def test_get_summary(self):
        import bzrlib.revision
        
        r = bzrlib.revision.Revision('1')

        r.message = None
        self.assertEquals('(no message)', util.get_summary(r))

        r.message = ''
        self.assertEquals('(no message)', util.get_summary(r))

