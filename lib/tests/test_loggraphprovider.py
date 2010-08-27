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

from bzrlib.tests import TestCase, TestCaseWithTransport

from bzrlib.plugins.qbzr.lib import loggraphprovider

class TestLogGraphProvider(TestCaseWithTransport):
    
    def test_no_commits(self):
        wt = self.make_branch_and_tree('.')
        
        bi = loggraphprovider.BranchInfo('', wt, wt.branch)
        gp = loggraphprovider.LogGraphProvider([bi], bi, False)
        gp.load()
        
        self.assertEqual(len(gp.revisions), 0)
        
        state = loggraphprovider.GraphProviderFilterState(gp)
        computed = gp.compute_graph_lines(state)
        self.assertEqual(len(computed.revisions), 0)
