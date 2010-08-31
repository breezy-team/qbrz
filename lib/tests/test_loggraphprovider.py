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
    
    def assertComputed(self, expected_list, computed):
        computed_list = [(c_rev.rev.revid,
                          c_rev.col_index,
                          c_rev.twisty_state,
                          c_rev.lines,)
                         for c_rev in computed.filtered_revs]
        self.assertEqual(expected_list, computed_list)
    
    def test_no_commits(self):
        br = self.make_branch('.')
        
        bi = loggraphprovider.BranchInfo('', None, br)
        gp = loggraphprovider.LogGraphProvider([bi], bi, False)
        gp.load()
        
        self.assertEqual(len(gp.revisions), 0)
        
        state = loggraphprovider.GraphProviderFilterState(gp)
        computed = gp.compute_graph_lines(state)
        self.assertEqual(len(computed.revisions), 0)

    def test_basic_branch_line(self):
        wt = self.make_branch_and_tree('.')
        wt.commit('a', rev_id='rev-a')
        wt.commit('b', rev_id='rev-b')
        wt.pull(wt.branch, True, 'rev-a')
        wt.commit('c', rev_id='rev-c')
        wt.pull(wt.branch, True, 'rev-b')
        wt.set_parent_ids(['rev-b', 'rev-c'])
        wt.commit('d', rev_id='rev-d')
        
        bi = loggraphprovider.BranchInfo('', wt, wt.branch)
        gp = loggraphprovider.LogGraphProvider([bi], bi, False)
        gp.load()
        
        state = loggraphprovider.GraphProviderFilterState(gp)
        computed = gp.compute_graph_lines(state)
        
        # only mainline.
        self.assertComputed(
            [('rev-d', 0, False, [(0, 0, 0, True)]),
             ('rev-b', 0, None,  [(0, 0, 0, True)]),
             ('rev-a', 0, None,  []),],
            computed)
        
        state.collapse_expand_rev(computed.filtered_revs[0])
        computed = gp.compute_graph_lines(state)
        
        # expanded branch line.
        self.assertComputed(
            [('rev-d', 0, True, [(0, 0, 0, True), (0, 1, 2, True)]),
             ('rev-c', 1, None, [(0, 0, 0, True), (1, 1, 0, True)]),
             ('rev-b', 0, None, [(0, 0, 0, True), (1, 0, 0, True)]),
             ('rev-a', 0, None, [])],
            computed)
        
