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

from breezy import (
    config,
    errors,
    tests,
    )
from breezy.transport import memory

from breezy.plugins.qbrz.lib import (
    tests as qbrz_tests,
    util,
    )
from breezy.plugins.qbrz.lib.fake_branch import FakeBranch
from breezy.plugins.qbrz.lib.tests import mock


class TestUtil(qbrz_tests.QTestCase):

    def test_file_extension(self):
        self.assertEqual('', util.file_extension(''))
        self.assertEqual('', util.file_extension('/foo/bar.x/'))
        self.assertEqual('', util.file_extension('C:/foo/bar.x/'))
        self.assertEqual('', util.file_extension('.bzrignore'))
        self.assertEqual('', util.file_extension('/foo/bar.x/.bzrignore'))
        self.assertEqual('.txt', util.file_extension('foo.txt'))
        self.assertEqual('.txt', util.file_extension('/foo/bar.x/foo.txt'))

    def test_filter_options(self):
        fo = util.FilterOptions()
        self.assertEqual(False, bool(fo))
        self.assertEqual(False, fo.is_all_enable())
        self.assertEqual('', fo.to_str())
        self.assertEqual(False, fo.check('added'))
        self.assertEqual(False, fo.check('removed'))
        self.assertEqual(False, fo.check('deleted'))
        self.assertEqual(False, fo.check('renamed'))
        self.assertEqual(False, fo.check('modified'))
        self.assertEqual(False, fo.check('renamed and modified'))
        self.assertRaises(ValueError, fo.check, 'spam')

        fo = util.FilterOptions(deleted=True)
        self.assertEqual(True, bool(fo))
        self.assertEqual(False, fo.is_all_enable())
        self.assertEqual('deleted files', fo.to_str())
        self.assertEqual(False, fo.check('added'))
        self.assertEqual(True, fo.check('removed'))
        self.assertEqual(True, fo.check('deleted'))
        self.assertEqual(False, fo.check('renamed'))
        self.assertEqual(False, fo.check('modified'))
        self.assertEqual(False, fo.check('renamed and modified'))

        fo = util.FilterOptions(added=True)
        self.assertEqual(True, bool(fo))
        self.assertEqual(False, fo.is_all_enable())
        self.assertEqual('added files', fo.to_str())
        self.assertEqual(True, fo.check('added'))
        self.assertEqual(False, fo.check('removed'))
        self.assertEqual(False, fo.check('deleted'))
        self.assertEqual(False, fo.check('renamed'))
        self.assertEqual(False, fo.check('modified'))
        self.assertEqual(False, fo.check('renamed and modified'))

        fo = util.FilterOptions(renamed=True)
        self.assertEqual(True, bool(fo))
        self.assertEqual(False, fo.is_all_enable())
        self.assertEqual('renamed files', fo.to_str())
        self.assertEqual(False, fo.check('added'))
        self.assertEqual(False, fo.check('removed'))
        self.assertEqual(False, fo.check('deleted'))
        self.assertEqual(True, fo.check('renamed'))
        self.assertEqual(False, fo.check('modified'))
        self.assertEqual(True, fo.check('renamed and modified'))

        fo = util.FilterOptions(modified=True)
        self.assertEqual(True, bool(fo))
        self.assertEqual(False, fo.is_all_enable())
        self.assertEqual('modified files', fo.to_str())
        self.assertEqual(False, fo.check('added'))
        self.assertEqual(False, fo.check('removed'))
        self.assertEqual(False, fo.check('deleted'))
        self.assertEqual(False, fo.check('renamed'))
        self.assertEqual(True, fo.check('modified'))
        self.assertEqual(True, fo.check('renamed and modified'))

        fo = util.FilterOptions(added=True, deleted=True, modified=True,
                renamed=True)
        self.assertEqual(True, bool(fo))
        self.assertEqual(True, fo.is_all_enable())
        self.assertEqual('deleted files, added files, '
            'renamed files, modified files', fo.to_str())
        self.assertEqual(True, fo.check('added'))
        self.assertEqual(True, fo.check('removed'))
        self.assertEqual(True, fo.check('deleted'))
        self.assertEqual(True, fo.check('renamed'))
        self.assertEqual(True, fo.check('modified'))
        self.assertEqual(True, fo.check('renamed and modified'))

        fo = util.FilterOptions(all_enable=True)
        self.assertEqual(True, bool(fo))
        self.assertEqual(True, fo.is_all_enable())

        fo = util.FilterOptions()
        fo.all_enable()
        self.assertEqual(True, bool(fo))
        self.assertEqual(True, fo.is_all_enable())

    def test_url_for_display(self):
        self.assertEqual(None, util.url_for_display(None))
        self.assertEqual('', util.url_for_display(''))
        self.assertEqual('http://bazaar.launchpad.net/~qbrz-dev/qbrz/trunk',
            util.url_for_display('http://bazaar.launchpad.net/%7Eqbrz-dev/qbrz/trunk'))
        if sys.platform == 'win32':
            self.assertEqual('C:/work/qbrz/',
                util.url_for_display('file:///C:/work/qbrz/'))
        else:
            self.assertEqual('/home/work/qbrz/',
                util.url_for_display('file:///home/work/qbrz/'))

    def test_has_any_binary_content(self):
        self.assertEqual(False, util.has_any_binary_content([]))
        self.assertEqual(False, util.has_any_binary_content(['foo\n', 'bar\r\n', 'spam\r']))
        self.assertEqual(True, util.has_any_binary_content([b'\x00']))
        self.assertEqual(True, util.has_any_binary_content([b'a'*2048 + b'\x00']))

    def test_get_summary(self):
        import breezy.revision

        r = breezy.revision.Revision('1')

        r.message = None
        self.assertEqual('(no message)', util.get_summary(r))

        r.message = ''
        self.assertEqual('(no message)', util.get_summary(r))

        r.message = 'message'
        self.assertEqual('message', util.get_summary(r))

    def test_get_message(self):
        import breezy.revision

        r = breezy.revision.Revision('1')

        r.message = None
        self.assertEqual('(no message)', util.get_message(r))

        r.message = 'message'
        self.assertEqual('message', util.get_message(r))

    def test_ensure_unicode(self):
        self.assertEqual('foo', util.ensure_unicode('foo'))
        self.assertEqual('foo', util.ensure_unicode('foo'))
        self.assertEqual('\u1234', util.ensure_unicode('\u1234'))
        self.assertEqual(1, util.ensure_unicode(1))

    def test__shlex_split_unicode_linux(self):
        self.assertEqual(['foo/bar', '\u1234'], util._shlex_split_unicode_linux("foo/bar \u1234"))

    def test__shlex_split_unicode_windows(self):
        self.assertEqual(['C:\\foo\\bar', '\u1234'], util._shlex_split_unicode_windows("C:\\foo\\bar \u1234"))

    # def test_launchpad_project_from_url(self):
    #     fut = util.launchpad_project_from_url  # fut = function under test
    #     # classic
    #     self.assertEqual('qbrz', fut('bzr+ssh://bazaar.launchpad.net/~qbrz-dev/qbrz/trunk'))
    #     # lp:qbrz
    #     self.assertEqual('qbrz', fut('bzr+ssh://bazaar.launchpad.net/+branch/qbrz'))
    #     self.assertEqual('qbrz', fut('bzr+ssh://bazaar.launchpad.net/%2Bbranch/qbrz'))
    #     # lp:qbrz/0.20
    #     self.assertEqual('qbrz', fut('bzr+ssh://bazaar.launchpad.net/%2Bbranch/qbrz/0.20'))
    #     # lp:ubuntu/qbrz
    #     self.assertEqual('qbrz', fut('bzr+ssh://bazaar.launchpad.net/%2Bbranch/ubuntu/qbrz'))
    #     # lp:ubuntu/natty/qbrz
    #     self.assertEqual('qbrz', fut('bzr+ssh://bazaar.launchpad.net/%2Bbranch/ubuntu/natty/qbrz'))
    #     # lp:ubuntu/natty-proposed/qbrz
    #     self.assertEqual('qbrz', fut('bzr+ssh://bazaar.launchpad.net/%2Bbranch/ubuntu/natty-proposed/qbrz'))
    #     # lp:~someone/ubuntu/maverick/qbrz/sru
    #     self.assertEqual('qbrz', fut('bzr+ssh://bazaar.launchpad.net/~someone/ubuntu/maverick/qbrz/sru'))


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
        self.assertEqual('utf-8', enc)

    def test_get_set_encoding_set(self):
        br = FakeBranch()
        util.get_set_encoding('ascii', br)
        # check that we don't overwrite encoding vaslue in bazaar.conf
        self.assertEqual('utf-8', util.get_set_encoding(None,None))

    def test_get_set_tab_width_chars(self):
        br = FakeBranch()
        w = util.get_set_tab_width_chars(br)
        self.assertEqual(8, w)
