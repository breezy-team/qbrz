# -*- coding: utf-8 -*-
#
# QBzr - Qt frontend to Bazaar commands
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

from bzrlib import config
from bzrlib.tests import TestCase, TestCaseWithTransport

from bzrlib.plugins.qbzr.lib.bugs import (
    bug_urls_to_ids,
    get_branch_bug_tags,
    get_bug_id,
    get_global_bug_tags,
    get_unique_bug_tags,
    get_user_bug_trackers_tags,
    )


class TestGetBugId(TestCase):

    def test_launchpad(self):
        self.assertEquals('261234', get_bug_id('https://launchpad.net/bugs/261234'))

    def test_trac(self):
        self.assertEquals('3852', get_bug_id('http://bugs.musicbrainz.org/ticket/3852'))

    def test_bugzilla(self):
        self.assertEquals('169104', get_bug_id('http://bugs.kde.org/show_bug.cgi?id=169104'))

    def test_redmine(self):
        self.assertEquals('1832', get_bug_id('http://www.redmine.org/issues/show/1832'))
        self.assertEquals('6', get_bug_id('https://rm.ftrahan.com/issues/6'))

    def test_fogbugz(self):
        self.assertEquals('1234', get_bug_id('http://test.fogbugz.com/default.asp?1234'))

    def test_roundup(self):
        self.assertEquals('5243', get_bug_id('http://bugs.python.org/issue5243'))

    def test_mantis(self):
        self.assertEquals('7721', get_bug_id('http://www.mantisbt.org/bugs/view.php?id=7721'))
        self.assertEquals('123', get_bug_id('http://localhost/view.php?id=123'))

    def test_fusionforge(self):
        self.assertEquals('292', get_bug_id('https://fusionforge.org/tracker/index.php?func=detail&aid=292'))

    def test_flyspray(self):
        self.assertEquals('1234', get_bug_id('https://flyspray.example.com/index.php?do=details&task_id=1234'))
        self.assertEquals('1234', get_bug_id('https://bugs.flyspray.org/task/1234'))

    def test_jira(self):
        self.assertEquals('AB-1234', get_bug_id('http://jiraserver/browse/AB-1234'))
        self.assertEquals('A_B-1234', get_bug_id('http://jiraserver/browse/A_B-1234'))
        self.assertEquals('AB_1-1234', get_bug_id('http://jiraserver/browse/AB_1-1234'))
        self.assertEquals('AB_1A-1234', get_bug_id('http://jiraserver/browse/AB_1A-1234'))
        self.assertEquals(None, get_bug_id('http://jiraserver/browse/1A-1234'))
        self.assertEquals(None, get_bug_id('http://jiraserver/browse/_1A-1234'))
        self.assertEquals(None, get_bug_id('http://jiraserver/browse/A-1234A'))
        self.assertEquals(None, get_bug_id('http://jiraserver/browse/a-1'))
        self.assertEquals(None, get_bug_id('http://jiraserver/browse/a'))
        self.assertEquals(None, get_bug_id('http://jiraserver/browse/A'))
        self.assertEquals(None, get_bug_id('http://jiraserver/browse/A-'))
        self.assertEquals(None, get_bug_id('http://jiraserver/browse/A_1'))
        self.assertEquals('A-1', get_bug_id('http://jiraserver/browse/A-1'))
        self.assertEquals('ZZ12_SA__2__-122222222', get_bug_id('http://jiras1212erver/browse/ZZ12_SA__2__-122222222'))

class TestGetBugTags(TestCase):

    def test_get_user_bug_trackers_tags(self):
        self.assertEqual({}, get_user_bug_trackers_tags([]))
        self.assertEquals({'foo': 'bugtracker',
                           'bar': 'trac',
                           'spam': 'bugzilla'},
                           get_user_bug_trackers_tags([
                                'bugtracker_foo_url',
                                'trac_bar_url',
                                'bugzilla_spam_url',
                                'email',
                                'editor',
                                ]))

    def test_get_unique_bug_tags(self):
        self.assertEqual({'lp': 'unique',
                          'deb': 'unique',
                          'gnome': 'unique',
                          }, get_unique_bug_tags())


class TestGetBugTagsFromConfig(TestCaseWithTransport):

    def test_get_global_bug_tags(self):
        # check empty bazaar.conf
        self.assertEqual({}, get_global_bug_tags())
        # set some options
        cfg = config.GlobalConfig()
        cfg.set_user_option('bugtracker_py_url',
            'http://bugs.python.org/issue{id}')
        cfg.set_user_option('bugzilla_kde_url',
            'http://bugs.kde.org/')
        cfg.set_user_option('trac_mbz_url',
            'http://bugs.musicbrainz.org/ticket/')
        self.assertEquals({
            'py': 'bugtracker',
            'kde': "bugzilla",
            'mbz': 'trac'},
            get_global_bug_tags())

    def test_get_branch_bug_tags(self):
        wt = self.make_branch_and_tree('.')
        branch = wt.branch
        # check empty branch.conf
        self.assertEqual({}, get_branch_bug_tags(branch))
        # set some options
        cfg = branch.get_config()
        cfg.set_user_option('bugtracker_py_url',
            'http://bugs.python.org/issue{id}')
        cfg.set_user_option('bugzilla_kde_url',
            'http://bugs.kde.org/')
        cfg.set_user_option('trac_mbz_url',
            'http://bugs.musicbrainz.org/ticket/')
        self.assertEquals({
            'py': 'bugtracker',
            'kde': "bugzilla",
            'mbz': 'trac'},
            get_branch_bug_tags(branch))


class TestBugUrlsToIds(TestCaseWithTransport):

    def test_wo_branch(self):
        bug_urls = [
            'https://launchpad.net/bugs/261234 fixed',
            'http://bugs.python.org/issue5243 fixed',
            ]
        # w/o global options we can match only unique lp url
        self.assertEqual(['lp:261234'], bug_urls_to_ids(bug_urls))
        # set some options
        cfg = config.GlobalConfig()
        cfg.set_user_option('bugtracker_py_url',
            'http://bugs.python.org/issue{id}')
        cfg.set_user_option('bugzilla_kde_url',
            'http://bugs.kde.org/')
        cfg.set_user_option('trac_mbz_url',
            'http://bugs.musicbrainz.org/')
        self.assertEqual(['lp:261234', 'py:5243'], bug_urls_to_ids(bug_urls))

    def test_w_branch(self):
        bug_urls = [
            'https://launchpad.net/bugs/261234 fixed',
            'http://bugs.python.org/issue5243 fixed',
            'http://bugs.kde.org/show_bug.cgi?id=169104 fixed',
            ]
        wt = self.make_branch_and_tree('.')
        branch = wt.branch
        # w/o user settings we can match only unique lp url
        self.assertEqual(['lp:261234'], bug_urls_to_ids(bug_urls, branch))
        # set some bugtrackers
        g_cfg = config.GlobalConfig()
        g_cfg.set_user_option('bugtracker_py_url',
            'http://bugs.python.org/issue{id}')
        b_cfg = branch.get_config()
        b_cfg.set_user_option('bugzilla_kde_url',
            'http://bugs.kde.org/')
        self.assertEqual(['kde:169104', 'lp:261234', 'py:5243'],
            bug_urls_to_ids(bug_urls, branch))
