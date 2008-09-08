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

from bzrlib.tests import TestCaseWithTransport, KnownFailure

class TestIsVersioned(TestCaseWithTransport):

    def test_is_versioned(self):
        tree = self.make_branch_and_tree('.')
        self.build_tree_contents([('a', 'foo\n'), ('b', 'bar\n')])
        tree.add(['a'])
        tree.commit('init')
        out, err = self.run_bzr('is-versioned a', retcode=1)
        self.assertEquals('versioned\n', out)
        out, err = self.run_bzr('is-versioned b', retcode=0)
        self.assertEquals('not versioned\n', out)
        out, err = self.run_bzr('is-versioned -q a', retcode=1)
        self.assertEquals('', out)
        out, err = self.run_bzr('is-versioned -q b', retcode=0)
        self.assertEquals('', out)
