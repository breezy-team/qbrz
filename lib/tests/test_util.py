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

from bzrlib import (
    config,
    errors,
    tests,
    )
from bzrlib.transport import memory

from bzrlib.plugins.qbzr.lib import (
    tests as qbzr_tests,
    util,
    )
from bzrlib.plugins.qbzr.lib.fake_branch import FakeBranch
from bzrlib.plugins.qbzr.lib.tests import mock


class TestUtil(qbzr_tests.QTestCase):

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

        r.message = 'message'
        self.assertEquals('message', util.get_summary(r))

    def test_get_message(self):
        import bzrlib.revision
        
        r = bzrlib.revision.Revision('1')

        r.message = None
        self.assertEquals('(no message)', util.get_message(r))

        r.message = 'message'
        self.assertEquals('message', util.get_message(r))

    def test_ensure_unicode(self):
        self.assertEqual(u'foo', util.ensure_unicode('foo'))
        self.assertEqual(u'foo', util.ensure_unicode(u'foo'))
        self.assertEqual(u'\u1234', util.ensure_unicode(u'\u1234'))
        self.assertEqual(1, util.ensure_unicode(1))

    def test__shlex_split_unicode_linux(self):
        self.assertEquals([u'foo/bar', u'\u1234'],
            util._shlex_split_unicode_linux(u"foo/bar \u1234"))

    def test__shlex_split_unicode_windows(self):
        self.assertEquals([u'C:\\foo\\bar', u'\u1234'],
            util._shlex_split_unicode_windows(u"C:\\foo\\bar \u1234"))

    def test_launchpad_project_from_url(self):
        fut = util.launchpad_project_from_url  # fut = function under test
        # classic
        self.assertEquals('qbzr', fut('bzr+ssh://bazaar.launchpad.net/~qbzr-dev/qbzr/trunk'))
        # lp:qbzr
        self.assertEquals('qbzr', fut('bzr+ssh://bazaar.launchpad.net/+branch/qbzr'))
        self.assertEquals('qbzr', fut('bzr+ssh://bazaar.launchpad.net/%2Bbranch/qbzr'))
        # lp:qbzr/0.20
        self.assertEquals('qbzr', fut('bzr+ssh://bazaar.launchpad.net/%2Bbranch/qbzr/0.20'))
        # lp:ubuntu/qbzr
        self.assertEquals('qbzr', fut('bzr+ssh://bazaar.launchpad.net/%2Bbranch/ubuntu/qbzr'))
        # lp:ubuntu/natty/qbzr
        self.assertEquals('qbzr', fut('bzr+ssh://bazaar.launchpad.net/%2Bbranch/ubuntu/natty/qbzr'))
        # lp:ubuntu/natty-proposed/qbzr
        self.assertEquals('qbzr', fut('bzr+ssh://bazaar.launchpad.net/%2Bbranch/ubuntu/natty-proposed/qbzr'))
        # lp:~someone/ubuntu/maverick/qbzr/sru
        self.assertEquals('qbzr', fut('bzr+ssh://bazaar.launchpad.net/~someone/ubuntu/maverick/qbzr/sru'))


class TestOpenTree(tests.TestCaseWithTransport):

    def test_no_ui_mode_no_branch(self):
        self.vfs_transport_factory = memory.MemoryServer
        mf = mock.MockFunction()
        self.assertRaises(errors.NotBranchError,
                          util.open_tree, self.get_url('non/existent/path'),
                          ui_mode=False, _critical_dialog=mf)
        self.assertEqual(0, mf.count)

    def test_no_ui_mode(self):
        mf = mock.MockFunction()
        self.make_branch('a')
        self.assertRaises(errors.NoWorkingTree,
            util.open_tree, 'a', ui_mode=False, _critical_dialog=mf)
        self.assertEqual(0, mf.count)
        #
        self.make_branch_and_tree('b')
        tree = util.open_tree('b', ui_mode=False, _critical_dialog=mf)
        self.assertNotEqual(None, tree)
        self.assertEqual(0, mf.count)

    def test_ui_mode_no_branch(self):
        self.vfs_transport_factory = memory.MemoryServer
        mf = mock.MockFunction()
        tree = util.open_tree(self.get_url('/non/existent/path'),
                              ui_mode=True, _critical_dialog=mf)
        self.assertEqual(None, tree)
        self.assertEqual(1, mf.count)

    def test_ui_mode(self):
        mf = mock.MockFunction()
        self.make_branch('a')
        mf = mock.MockFunction()
        tree = util.open_tree('a', ui_mode=True, _critical_dialog=mf)
        self.assertEqual(None, tree)
        self.assertEqual(1, mf.count)
        #
        self.make_branch_and_tree('b')
        mf = mock.MockFunction()
        tree = util.open_tree('b', ui_mode=False, _critical_dialog=mf)
        self.assertNotEqual(None, tree)
        self.assertEqual(0, mf.count)


class TestFakeBranch(tests.TestCaseInTempDir):

    def test_get_branch_config(self):
        br = FakeBranch()
        br_cfg = util.get_branch_config(br)
        self.assertTrue(isinstance(br_cfg, config.GlobalConfig))

    def test_get_set_encoding_get(self):
        br = FakeBranch()
        enc = util.get_set_encoding(None, br)
        self.assertEquals('utf-8', enc)

    def test_get_set_encoding_set(self):
        br = FakeBranch()
        util.get_set_encoding('ascii', br)
        # check that we don't overwrite encoding vaslue in bazaar.conf
        self.assertEquals('utf-8', util.get_set_encoding(None,None))

    def test_get_set_tab_width_chars(self):
        br = FakeBranch()
        w = util.get_set_tab_width_chars(br)
        self.assertEquals(8, w)
