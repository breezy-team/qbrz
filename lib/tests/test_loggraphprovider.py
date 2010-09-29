# -*- coding: utf-8 -*-
#
# Copyright (C) 2010 Gary van der Merwe <garyvdm@gmail.com> 
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
from StringIO import StringIO

from bzrlib.plugins.qbzr.lib import loggraphprovider
from bzrlib.revision import NULL_REVISION

# TODO:
# Tag loading
# Branch labels + Filtering
# Ghosts
# file_ids filtering

class TestLogGraphProviderMixin(object):
    def computed_to_list(self, computed, branch_labels=False):
        if not branch_labels:
            item = lambda c_rev: (c_rev.rev.revid,
                                  c_rev.col_index,
                                  c_rev.twisty_state,
                                  sorted(c_rev.lines),)
        else:
            item = lambda c_rev: (c_rev.rev.revid,
                                  c_rev.col_index,
                                  c_rev.twisty_state,
                                  sorted(c_rev.lines),
                                  [label for bi, label in c_rev.branch_labels])
        
        return [item(c_rev) for c_rev in computed.filtered_revs]
    
    def assertComputed(self, expected_list, computed, branch_labels=False):
        computed_list = self.computed_to_list(computed, branch_labels)
        if not expected_list == computed_list:
            raise AssertionError(
                "not equal: \nexpected_list = \n%scomputed_list = \n%s"
                % (format_graph_lines(expected_list, use_unicode=True),
                   format_graph_lines(computed_list, use_unicode=True),))
    

class TestLogGraphProviderWithBranches(TestCaseWithTransport,
                                       TestLogGraphProviderMixin):

    def test_no_commits(self):
        br = self.make_branch('.')
        
        bi = loggraphprovider.BranchInfo('', None, br)
        gp = loggraphprovider.LogGraphProvider([bi], bi, False)
        gp.load()
        
        self.assertEqual(len(gp.revisions), 0)
        
        state = loggraphprovider.GraphProviderFilterState(gp)
        computed = gp.compute_graph_lines(state)
        self.assertEqual(len(computed.revisions), 0)

    def test_branch_tips_date_sorted(self):
        builder = self.make_branch_builder('trunk')
        builder.start_series()
        builder.build_snapshot('rev-a', None, [
            ('add', ('', 'TREE_ROOT', 'directory', '')),])
        builder.build_snapshot('rev-old', ['rev-a'], [])
        builder.build_snapshot('rev-new', ['rev-a'], [])
        builder.build_snapshot('rev-trunk', ['rev-a'], [])
        builder.finish_series()
        
        trunk = builder.get_branch()
        #trunk.set_last_revision('rev-trunk')
        
        old = trunk.bzrdir.sprout('../old', revision_id='rev-old').open_branch()
        
        new = trunk.bzrdir.sprout('../new', revision_id='rev-new').open_branch()
        
        trunk_bi = loggraphprovider.BranchInfo('trunk', None, trunk)
        gp = loggraphprovider.LogGraphProvider(
            [trunk_bi,
             loggraphprovider.BranchInfo('old', None, old),
             loggraphprovider.BranchInfo('new', None, new),],
            trunk_bi, False)
        gp.load()
        
        state = loggraphprovider.GraphProviderFilterState(gp)
        computed = gp.compute_graph_lines(state)
        
        self.assertComputed(
            [('rev-new', 2, None, [(2, 2, 0, True)])                 , #     ○ 
                                                                       #     │ 
             ('rev-old', 1, None, [(1, 1, 0, True), (2, 2, 0, True)]), #   ○ │ 
                                                                       #   │ │ 
             ('rev-trunk', 0, None, [(0, 0, 0, True), (1, 0, 0, True), # ○ │ │ 
                                     (2, 0, 0, True)]),                # ├─╯─╯ 
             ('rev-a', 0, None, [])                                  ],# ○ 
            computed)
    
    def make_tree_with_pending_merge(self, path):
        builder = self.make_branch_builder('branch')
        builder.start_series()
        builder.build_snapshot('rev-a', None, [
            ('add', ('', 'TREE_ROOT', 'directory', '')),])
        builder.build_snapshot('rev-b', ['rev-a'], [])
        builder.finish_series()
        
        branch = builder.get_branch()
        branch.set_last_revision_info(1, 'rev-a') # go back to rev-a
        tree = branch.bzrdir.create_workingtree()
        tree.merge_from_branch(branch, to_revision='rev-b')
        
        return tree
    
    def make_tree_not_up_to_date(self, path):
        builder = self.make_branch_builder('branch')
        builder.start_series()
        builder.build_snapshot('rev-a', None, [
            ('add', ('', 'TREE_ROOT', 'directory', '')),])
        builder.build_snapshot('rev-b', ['rev-a'], [])
        builder.finish_series()
        
        branch = builder.get_branch()
        tree = branch.bzrdir.create_workingtree()
        tree.update(revision='rev-a')
        return tree
    
    def test_pending_merge(self):
        tree = self.make_tree_with_pending_merge('branch')
        
        bi = loggraphprovider.BranchInfo(None, tree, tree.branch)
        gp = loggraphprovider.LogGraphProvider([bi], bi, False)
        gp.load()
        
        state = loggraphprovider.GraphProviderFilterState(gp)
        computed = gp.compute_graph_lines(state)
        
        self.assertComputed(
            [('rev-b', 1, None, [(1, 0, 0, True)], ['Pending Merge']), #   ○ 
                                                                       # ╭─╯ 
             ('rev-a', 0, None, [], [None])                          ],# ○ 
            computed, branch_labels=True)

    def test_out_of_date_wt(self):
        tree = self.make_tree_not_up_to_date('branch')
        bi = loggraphprovider.BranchInfo(None, tree, tree.branch)
        gp = loggraphprovider.LogGraphProvider([bi], bi, False)
        gp.load()
        
        state = loggraphprovider.GraphProviderFilterState(gp)
        computed = gp.compute_graph_lines(state)
        
        self.assertComputed(
            [('rev-b', 0, None, [(0, 0, 0, True)], [None]), # ○ 
                                                            # │ 
             ('rev-a', 0, None, [], ['Working Tree'])     ],# ○
            computed, branch_labels=True)
    
    def test_with_working_tree_provider(self):
        tree = self.make_tree_with_pending_merge('branch')
        
        bi = loggraphprovider.BranchInfo('branch', tree, tree.branch)
        gp = loggraphprovider.WithWorkingTreeGraphProvider([bi], bi, False)
        gp.load()
        
        state = loggraphprovider.GraphProviderFilterState(gp)
        computed = gp.compute_graph_lines(state)
        
        self.assertComputed(
            [(u'current:%s' % tree.basedir, 0, True,                # ⊖  
              [(0, 0, 0, True), (0, 1, 2, True)],                   # ├─╮ 
              ['branch - Working Tree']),                           # │ │ 
             ('rev-b', 1, None, [(0, 0, 0, True), (1, 0, 0, True)], # │ ○ 
              ['branch - Pending Merge']),                          # ├─╯ 
             ('rev-a', 0, None, [], ['branch'])],                   # ○ 
            computed, branch_labels=True)
    
    def test_with_working_tree_provider_out_of_date_wt(self):
        tree = self.make_tree_not_up_to_date('branch')
        bi = loggraphprovider.BranchInfo('branch', tree, tree.branch)
        gp = loggraphprovider.WithWorkingTreeGraphProvider([bi], bi, False)
        gp.load()
        
        state = loggraphprovider.GraphProviderFilterState(gp)
        computed = gp.compute_graph_lines(state)
        
        self.assertComputed(
            [(u'current:%s' % tree.basedir, 1, None, [(1, 1, 0, True)], #   ○ 
              ['branch - Working Tree']),                               #   │ 
             ('rev-b', 0, None, [(0, 0, 0, True), (1, 0, 0, True)],     # ○ │ 
              ['branch']),                                              # ├─╯ 
             ('rev-a', 0, None, [], []) ],                              # ○
            computed, branch_labels=True)

    def test_pending_merges_provider(self):
        tree = self.make_tree_with_pending_merge('branch')
        
        bi = loggraphprovider.BranchInfo(None, tree, tree.branch)
        gp = loggraphprovider.PendingMergesGraphProvider([bi], bi, False)
        gp.load()
        
        state = loggraphprovider.GraphProviderFilterState(gp)
        computed = gp.compute_graph_lines(state)
        
        self.assertComputed(
            [('rev-b', 1, None, [(1, 0, 0, True)]), #   ○ 
                                                    # ╭─╯ 
             ('root:', 0, None, [])               ],# ○ 
            computed)
    
    def test_with_ghost(self):
        tree = self.make_branch_and_tree('tree')
        tree.commit('a', rev_id='rev-a')
        tree.add_parent_tree_id('rev-b')
        tree.commit('c', rev_id='rev-c')
        # rev-b is a ghost. We think he is there, but he dose not exist. Boo!
        
        bi = loggraphprovider.BranchInfo(None, tree, tree.branch)
        gp = loggraphprovider.LogGraphProvider([bi], bi, False)
        gp.load()
        
        state = loggraphprovider.GraphProviderFilterState(gp)
        state.expand_all_branch_lines()
        computed = gp.compute_graph_lines(state)
        
        self.assertComputed(
            [('rev-c', 0, True, [(0, 0, 0, True), (0, 1, 1, True)]), # ⊖   
                                                                     # ├─╮ 
             ('rev-b', 1, None, [(0, 0, 0, True)])                 , # │ ○ 
                                                                     # │   
             ('rev-a', 0, None, [])                                ],# ○ 
            computed)

    def test_with_ghost_mainline(self):
        tree = self.make_branch_and_tree('tree')
        tree.add_parent_tree_id('rev-a', allow_leftmost_as_ghost=True)
        tree.commit('b', rev_id='rev-b')
        
        bi = loggraphprovider.BranchInfo(None, tree, tree.branch)
        gp = loggraphprovider.LogGraphProvider([bi], bi, False)
        gp.load()
        
        state = loggraphprovider.GraphProviderFilterState(gp)
        computed = gp.compute_graph_lines(state)
        
        self.assertComputed(
            [('rev-b', 0, None, [(0, 0, 0, True)]), # ○ 
                                                    # │ 
             ('rev-a', 0, None, [])               ],# ○
            computed)

    def test_get_revid_branch_info(self):
        builder = self.make_branch_builder('trunk')
        builder.start_series()
        builder.build_snapshot('rev-a', None, [
            ('add', ('', 'TREE_ROOT', 'directory', '')),])
        builder.build_snapshot('rev-branch', ['rev-a'], [])
        builder.build_snapshot('rev-trunk', ['rev-a'], [])
        builder.finish_series()
        #   ○ branch
        #   │ 
        # ○ │ trunk
        # ├─╯ 
        # ○ rev-a
        
        trunk = builder.get_branch()
        #trunk.set_last_revision('rev-trunk')
        
        branch = trunk.bzrdir.sprout('../branch',
                                     revision_id='rev-branch').open_branch()
        
        trunk_bi = loggraphprovider.BranchInfo('trunk', None, trunk)
        branch_bi = loggraphprovider.BranchInfo('branch', None, branch)
        gp = loggraphprovider.LogGraphProvider(
            [trunk_bi, branch_bi],
            trunk_bi, False)
        gp.load()
        
        self.assertEqual(trunk_bi, gp.get_revid_branch_info('rev-trunk'))
        self.assertEqual(branch_bi, gp.get_revid_branch_info('rev-branch'))
        
        # may return either 
        self.assertIn(gp.get_revid_branch_info('rev-a'),
                      (branch_bi, trunk_bi))

    def test_get_revid_branch_info_with_ghost(self):
        tree = self.make_branch_and_tree('tree')
        tree.commit('a', rev_id='rev-a')
        tree.add_parent_tree_id('rev-b')
        tree.commit('c', rev_id='rev-c')
        # rev-b is a ghost. We think he is there, but he dose not exist. Boo!
        # c 
        # ├─╮
        # │ b
        # │ 
        # a 

        bi = loggraphprovider.BranchInfo(None, tree, tree.branch)
        gp = loggraphprovider.LogGraphProvider([bi], bi, False)
        gp.load()
        
        self.assertRaises(loggraphprovider.GhostRevisionError,
                          gp.get_revid_branch_info, 'rev-b')

class TestLogGraphProviderLayouts(TestCase, TestLogGraphProviderMixin):
    
    def test_basic_branch_line(self):
        gp = BasicTestLogGraphProvider(('rev-d',), {
         'rev-a': (NULL_REVISION, ), 
         'rev-b': ('rev-a', ),
         'rev-c': ('rev-a', ),
         'rev-d': ('rev-b', 'rev-c'),
        })
        gp.load()
        
        state = loggraphprovider.GraphProviderFilterState(gp)
        computed = gp.compute_graph_lines(state)
        
        # only mainline.
        self.assertComputed(
            [('rev-d', 0, False, [(0, 0, 0, True)]), # ⊕ 
                                                     # │ 
             ('rev-b', 0, None, [(0, 0, 0, True)]) , # ○ 
                                                     # │ 
             ('rev-a', 0, None, [])                ],# ○ 
             computed)
      
        state.collapse_expand_rev(computed.filtered_revs[0])
        computed = gp.compute_graph_lines(state)
        
        # expanded branch line.
        self.assertComputed(
            [('rev-d', 0, True, [(0, 0, 0, True), (0, 1, 2, True)]), # ⊖   
                                                                     # ├─╮ 
             ('rev-c', 1, None, [(0, 0, 0, True), (1, 1, 0, True)]), # │ ○ 
                                                                     # │ │ 
             ('rev-b', 0, None, [(0, 0, 0, True), (1, 0, 0, True)]), # ○ │ 
                                                                     # ├─╯ 
             ('rev-a', 0, None, [])                                ],# ○ 
            computed)
    
    def test_branch_line_order(self):
        gp = BasicTestLogGraphProvider(('rev-f',), {
         'rev-a': (NULL_REVISION, ), 
         'rev-b': ('rev-a', ),
         'rev-c': ('rev-b', ),
         'rev-d': ('rev-a', 'rev-c'),
         'rev-e': ('rev-b', ),
         'rev-f': ('rev-d', 'rev-e' ),
        })
        gp.load()
        
        state = loggraphprovider.GraphProviderFilterState(gp)
        state.expand_all_branch_lines()
        computed = gp.compute_graph_lines(state)
        
        # branch lines should not cross over
        self.assertComputed(
            [('rev-f', 0, True, [(0, 0, 0, True), (0, 2, 3, True)])                 , # ⊖     
                                                                                      # ├───╮ 
             ('rev-e', 2, True, [(0, 0, 0, True), (2, 2, 2, True)])                 , # │   ⊖ 
                                                                                      # │   │ 
             ('rev-d', 0, True, [(0, 0, 0, True), (0, 1, 2, True), (2, 2, 2, True)]), # ⊖   │ 
                                                                                      # ├─╮ │ 
             ('rev-c', 1, None, [(0, 0, 0, True), (1, 1, 2, True), (2, 1, 2, True)]), # │ ○ │ 
                                                                                      # │ ├─╯ 
             ('rev-b', 1, None, [(0, 0, 0, True), (1, 0, 0, True)])                 , # │ ○ 
                                                                                      # ├─╯ 
             ('rev-a', 0, None, [])                                                 ],# ○ 
             computed)

    def test_branch_line_order2(self):
        gp = BasicTestLogGraphProvider(('rev-h',), {
         'rev-a': (NULL_REVISION, ), 
         'rev-b': ('rev-a', ),
         'rev-c': ('rev-b', ),
         'rev-d': ('rev-a', ),
         'rev-e': ('rev-d', 'rev-b' ),
         'rev-f': ('rev-e', ),
         'rev-g': ('rev-e', 'rev-f' ),
         'rev-h': ('rev-c', 'rev-g' ),
        })
        gp.load()
        
        state = loggraphprovider.GraphProviderFilterState(gp)
        state.expand_all_branch_lines()
        computed = gp.compute_graph_lines(state)

        # branch lines should not cross over
        self.assertComputed(
            [('rev-h', 0, True, [(0, 0, 0, True), (0, 2, 2, True)])                 , # ⊖     
                                                                                      # ├───╮ 
             ('rev-g', 2, True, [(0, 0, 0, True), (2, 2, 2, True), (2, 3, 3, True)]), # │   ⊖   
                                                                                      # │   ├─╮ 
             ('rev-f', 3, None, [(0, 0, 0, True), (2, 2, 2, True), (3, 2, 2, True)]), # │   │ ○ 
                                                                                      # │   ├─╯ 
             ('rev-e', 2, None, [(0, 0, 0, True), (2, 1, 0, True), (2, 2, 2, True)]), # │   ○ 
                                                                                      # │ ╭─┤ 
             ('rev-d', 2, None, [(0, 0, 0, True), (1, 1, 0, True), (2, 2, 0, True)]), # │ │ ○ 
                                                                                      # │ │ │ 
             ('rev-c', 0, None, [(0, 0, 0, True), (1, 0, 0, True), (2, 2, 0, True)]), # ○ │ │ 
                                                                                      # ├─╯ │ 
             ('rev-b', 0, None, [(0, 0, 0, True), (2, 0, 0, True)])                 , # ○   │ 
                                                                                      # ├───╯ 
             ('rev-a', 0, None, [])                                                 ],# ○ 
             computed)

    def test_octopus_merge(self):
        gp = BasicTestLogGraphProvider(('rev-e',), {
         'rev-a': (NULL_REVISION, ), 
         'rev-b': ('rev-a', ),
         'rev-c': ('rev-a', ),
         'rev-d': ('rev-a', ),
         'rev-e': ('rev-a', 'rev-b', 'rev-c', 'rev-d'),
        })
        gp.load()
        
        state = loggraphprovider.GraphProviderFilterState(gp)
        state.expand_all_branch_lines()
        computed = gp.compute_graph_lines(state)
        
        self.assertComputed(
            [('rev-e', 0, True, [(0, 0, 0, True), (0, 1, 2, True), (0, 2, 3, True), (0, 3, 4, True)]), # ⊖       
                                                                                                       # ├─╮─╮─╮ 
             ('rev-b', 3, None, [(0, 0, 0, True), (1, 1, 2, True), (2, 2, 3, True), (3, 3, 0, True)]), # │ │ │ ○ 
                                                                                                       # │ │ │ │ 
             ('rev-c', 2, None, [(0, 0, 0, True), (1, 1, 2, True), (2, 2, 0, True), (3, 3, 0, True)]), # │ │ ○ │ 
                                                                                                       # │ │ │ │ 
             ('rev-d', 1, None, [(0, 0, 0, True), (1, 0, 0, True), (2, 0, 0, True), (3, 0, 0, True)]), # │ ○ │ │ 
                                                                                                       # ├─╯─╯─╯ 
             ('rev-a', 0, None, [])                                                                  ],# ○
            computed)

    def test_lots_of_merges_between_branch_lines(self):
        gp = BasicTestLogGraphProvider(('rev-g',), {
         'rev-a': (NULL_REVISION, ), 
         'rev-b': ('rev-a', ),
         'rev-c': ('rev-b', ),
         'rev-d': ('rev-a', ),
         'rev-e': ('rev-d', 'rev-b',),
         'rev-f': ('rev-e', 'rev-c',),
         'rev-g': ('rev-c', 'rev-f',),
        })
        gp.load()
        
        state = loggraphprovider.GraphProviderFilterState(gp)
        state.expand_all_branch_lines()
        computed = gp.compute_graph_lines(state)

        self.assertComputed(
            [('rev-g', 0, True, [(0, 0, 0, True), (0, 2, 2, True)])                                           , # ⊖     
                                                                                                                # ├───╮ 
             ('rev-f', 2, None, [(0, 0, 0, True), (2, 0.75, 0, True), (2, 2, 2, True)])                       , # │   ○ 
                                                                                                                # │ ╭─┤ 
             ('rev-e', 2, None, [(0, 0, 0, True), (0.75, 0.75, 0, True), (2, 1.25, 0, True), (2, 2, 2, True)]), # │ │ ○ 
                                                                                                                # │ ├─┤ 
             ('rev-d', 2, None, [(0, 0, 0, True), (0.75, 0, 0, True), (1.25, 1.25, 0, True), (2, 2, 0, True)]), # │ │ ○ 
                                                                                                                # ├─┤ │ 
             ('rev-c', 0, None, [(0, 0, 0, True), (1.25, 0, 0, True), (2, 2, 0, True)])                       , # ○ │ │ 
                                                                                                                # ├─╯ │ 
             ('rev-b', 0, None, [(0, 0, 0, True), (2, 0, 0, True)])                                           , # ○   │ 
                                                                                                                # ├───╯ 
             ('rev-a', 0, None, [])                                                                           ],# ○ 
            computed)
    
    def test_hidden_branch_line_hides_child_line(self):
        gp = BasicTestLogGraphProvider(('rev-g',), {
         'rev-a': (NULL_REVISION, ), 
         'rev-b': ('rev-a', ),
         'rev-c': ('rev-a', ),
         'rev-d': ('rev-b', 'rev-c', ),
         'rev-e': ('rev-b', 'rev-d', ),
         'rev-f': ('rev-c', ),
         'rev-g': ('rev-e', 'rev-f', ),
        })
        gp.load()
        
        state = loggraphprovider.GraphProviderFilterState(gp)
        state.branch_line_state[(2, 1)] = None
        computed = gp.compute_graph_lines(state)
        
        self.assertComputed(
            [('rev-g', 0, False, [(0, 0, 0, True)])                 , # ⊕ 
                                                                      # │ 
             ('rev-e', 0, True, [(0, 0, 0, True), (0, 1, 3, True)]) , # ⊖   
                                                                      # ├─╮ 
             ('rev-d', 1, False, [(0, 0, 0, True), (1, 0, 0, True)]), # │ ⊕ 
                                                                      # ├─╯ 
             ('rev-b', 0, None, [(0, 0, 0, True)])                  , # ○ 
                                                                      # │ 
             ('rev-a', 0, None, [])                                 ],# ○ 
             computed)
    
    def test_merge_line_hidden(self):
        gp = BasicTestLogGraphProvider(('rev-d',), {
         'rev-a': (NULL_REVISION, ), 
         'rev-b': ('rev-a', ),
         'rev-c': ('rev-a', 'rev-b'),
         'rev-d': ('rev-a', 'rev-c'),
        })
        gp.load()
        
        state = loggraphprovider.GraphProviderFilterState(gp)
        state.branch_line_state[(1, 1)] = None
        
        computed = gp.compute_graph_lines(state)
        # when the merge by branch line, we should show a non direct line
        self.assertComputed(
            [('rev-d', 0, False, [(0, 0, 0, True), (0, 1, 2, False)]), # ⊕   
                                                                       # ├┄╮ 
             ('rev-b', 1, None, [(0, 0, 0, True), (1, 0, 0, True)])  , # │ ○ 
                                                                       # ├─╯ 
             ('rev-a', 0, None, [])                                  ],# ○ 
            computed)    

    def test_merge_line_hidden_merge_rev_filtered(self):
        gp = BasicTestLogGraphProvider(('rev-e',), {
         'rev-a': (NULL_REVISION, ), 
         'rev-b': ('rev-a', ),
         'rev-c': ('rev-b', ),
         'rev-d': ('rev-a', 'rev-c'),
         'rev-e': ('rev-a', 'rev-d'),
        })
        gp.load()
        
        state = loggraphprovider.GraphProviderFilterState(gp)
        state.filters.append(BasicFilterer(set(['rev-c'])))
        state.branch_line_state[(1, 1)] = None
        
        computed = gp.compute_graph_lines(state)
        
        # when the merge by branch line, we should show a non direct line
        self.assertComputed(
            [('rev-e', 0, False, [(0, 0, 0, True), (0, 1, 2, False)]), # ⊕   
                                                                       # ├┄╮ 
             ('rev-b', 1, None, [(0, 0, 0, True), (1, 0, 0, True)])  , # │ ○ 
                                                                       # ├─╯ 
             ('rev-a', 0, None, [])                                  ],# ○ 
            computed)    

    def test_non_direct_hidden_branch(self):
        gp = BasicTestLogGraphProvider(('rev-f',), {
         'rev-a': (NULL_REVISION, ), 
         'rev-b': ('rev-a', ),
         'rev-c': ('rev-b', ),
         'rev-d': ('rev-a', 'rev-c', ),
         'rev-e': ('rev-b', ),
         'rev-f': ('rev-d', 'rev-e', ),
        })
        gp.load()
        
        state = loggraphprovider.GraphProviderFilterState(gp)
        state.branch_line_state[(1, 2)] = None
        
        computed = gp.compute_graph_lines(state)
        
        self.assertComputed(
            [('rev-f', 0, True, [(0, 0, 0, True), (0, 1, 3, True)])  , # ⊖   
                                                                       # ├─╮ 
             ('rev-e', 1, False, [(0, 0, 0, True), (1, 1, 0, False)]), # │ ⊕ 
                                                                       # │ ┆ 
             ('rev-d', 0, False, [(0, 0, 0, True), (1, 0, 0, False)]), # ⊕ ┆ 
                                                                       # ├┄╯ 
             ('rev-a', 0, None, [])                                  ],# ○
            computed)

    def test_non_direct_hidden_parent(self):
        gp = BasicTestLogGraphProvider(('rev-e',), {
         'rev-a': (NULL_REVISION, ), 
         'rev-b': ('rev-a', ),
         'rev-c': ('rev-b', ),
         'rev-d': ('rev-a', 'rev-c'),
         'rev-e': ('rev-a', 'rev-d'),
        })
        gp.load()
        
        state = loggraphprovider.GraphProviderFilterState(gp)
        state.filters.append(BasicFilterer(set(['rev-c'])))
        state.expand_all_branch_lines()
        
        computed = gp.compute_graph_lines(state)
        
        self.assertComputed(
            [('rev-e', 0, True, [(0, 0, 0, True), (0, 1, 3, True)])                  , # ⊖   
                                                                                       # ├─╮ 
             ('rev-d', 1, True, [(0, 0, 0, True), (1, 1, 0, True), (1, 2, 2, False)]), # │ ⊖   
                                                                                       # │ ├┄╮ 
             ('rev-b', 2, None, [(0, 0, 0, True), (1, 0, 0, True), (2, 0, 0, True)]) , # │ │ ○ 
                                                                                       # ├─╯─╯ 
             ('rev-a', 0, None, [])                                                  ],# ○
            computed)


class TestLogGraphProviderState(TestCase):

    def assertFilteredRevisions(self, expected_revids, state):
        revids = [rev.revid for rev in state.get_filtered_revisions()]
        self.assertEqual(list(expected_revids), revids)
    
    def test_collapse_expand_rev_basic(self):
        gp = BasicTestLogGraphProvider(('c',), {
         'a': (NULL_REVISION, ), 
         'b': ('a', ),
         'c': ('a', 'b'),
        })
        gp.load()
        # c  
        # ├─╮ 
        # │ b
        # ├─╯ 
        # a
        
        state = loggraphprovider.GraphProviderFilterState(gp)
        
        # just mainline showing
        self.assertFilteredRevisions('ca', state)
        
        # bla - we need a computed to call collapse_expand_rev
        # expand 'c'
        state.collapse_expand_rev(gp.compute_graph_lines(state).filtered_revs[0])
        
        # all should be showing
        self.assertFilteredRevisions('cba', state)
        
        # colapse 'c'
        state.collapse_expand_rev(gp.compute_graph_lines(state).filtered_revs[0])
        
        # just mainline showing
        self.assertFilteredRevisions('ca', state)

    def get_expanded_by_graph_provider(self):
        gp = BasicTestLogGraphProvider(('f',), {
         'a': (NULL_REVISION, ), 
         'b': ('a', ),
         'c': ('a', 'b'),
         'd': ('a', 'c', ),
         'e': ('b', ),
         'f': ('d', 'e')
        })
        gp.load()
        # f     
        # ├───╮ 
        # │   e
        # │   │ 
        # d   │ 
        # ├─╮ │ 
        # │ c │ 
        # │ │\│ 
        # │ │ b
        # ├─╯─╯ 
        # a 
        return gp
    
    def test_collapse_colapses_sub_expand(self):
        gp = self.get_expanded_by_graph_provider()
        
        state = loggraphprovider.GraphProviderFilterState(gp)
        # just mainline showing
        self.assertFilteredRevisions('fda', state)
        
        # expand 'd'
        state.collapse_expand_rev(gp.compute_graph_lines(state).revisions[2])
        # branchline c now showing
        self.assertFilteredRevisions('fdca', state)
        
        # expand 'c'
        state.collapse_expand_rev(gp.compute_graph_lines(state).revisions[3])
        # all showing
        self.assertFilteredRevisions('fedcba', state)
        
        # colapse 'd'
        state.collapse_expand_rev(gp.compute_graph_lines(state).filtered_revs[2])
        # cause c expaned branchline eb, and d expanded c, d colapses 
        # just mainline showing
        self.assertFilteredRevisions('fda', state)

    def test_collapse_dosent_colapses_prev_expand(self):
        gp = self.get_expanded_by_graph_provider()
        
        state = loggraphprovider.GraphProviderFilterState(gp)
        # just mainline showing
        self.assertFilteredRevisions('fda', state)
        
        # expand 'f'
        state.collapse_expand_rev(gp.compute_graph_lines(state).revisions[0])
        # branchline eb now showing
        self.assertFilteredRevisions('fedba', state)
        
        # expand 'd'
        state.collapse_expand_rev(gp.compute_graph_lines(state).revisions[2])
        # all showing
        self.assertFilteredRevisions('fedcba', state)
        
        # colapse 'd'
        state.collapse_expand_rev(gp.compute_graph_lines(state).filtered_revs[2])
        # cause branchline eb was expanded by f, and not d, collapsing d dose
        # not collapse branchline eb, even though it expanded it
        # branchline eb and mainline left showing
        self.assertFilteredRevisions('fedba', state)

    def test_collapse_deep_expanded_by(self):
        # This use to error at one point
        gp = BasicTestLogGraphProvider(('g',), {
         'a': (NULL_REVISION, ), 
         'b': ('a', ),
         'c': ('a', 'b'),
         'd': ('a', 'c', ),
         'e': ('b', ),
         'f': ('d', 'e'),
         'g': ('a', 'f'),
        })
        # g v-----1.3 
        # ├─╮ 
        # │ f   v-1.1
        # │ ├───╮ 
        # │ │   e
        # │ │   │ 
        # │ d v-│-1.2
        # │ ├─╮ │ 
        # │ │ c │ 
        # │ │ │\│ 
        # │ │ │ b
        # ├─╯─╯─╯ 
        # a 
        
        gp.load()
        
        state = loggraphprovider.GraphProviderFilterState(gp)
        # just mainline showing
        self.assertFilteredRevisions('ga', state)
        
        # expand 'g'
        state.collapse_expand_rev(gp.compute_graph_lines(state).revisions[0])
        # branchline fd now showing
        self.assertFilteredRevisions('gfda', state)
        
        # expand 'f'
        state.collapse_expand_rev(gp.compute_graph_lines(state).revisions[1])
        # branchline eb now showing
        self.assertFilteredRevisions('gfedba', state)
        
        # expand 'd'
        state.collapse_expand_rev(gp.compute_graph_lines(state).revisions[3])
        # branchline c now showing (all showing)
        self.assertFilteredRevisions('gfedcba', state)

        # colapse 'g'
        state.collapse_expand_rev(gp.compute_graph_lines(state).filtered_revs[0])
        # back to just mainline showing
        self.assertFilteredRevisions('ga', state)
    
    def test_filter(self):
        gp = BasicTestLogGraphProvider(('e',), {
         'a': (NULL_REVISION, ), 
         'b': ('a', ),
         'c': ('a', 'b'),
         'd': ('c', ),
         'e': ('d', ),
        })
        gp.load()
        # e
        # │
        # d
        # │
        # c  
        # ├─╮ 
        # │ b
        # ├─╯ 
        # a
        
        state = loggraphprovider.GraphProviderFilterState(gp)
        
        # expand 'c'
        state.collapse_expand_rev(gp.compute_graph_lines(state).filtered_revs[2])
        
        # all should be showing
        self.assertFilteredRevisions('edcba', state)
        
        state.filters.append(BasicFilterer(('d', 'c', 'a')))
        state.filter_changed()
        # d and a not showing bucause of filter
        # c shows even though it is filtered, because it merges a revision
        # that is not filtered.
        self.assertFilteredRevisions('ecb', state)


    
class BasicTestLogGraphProvider(loggraphprovider.LogGraphProvider):
    
    def __init__(self, heads, graph_dict, no_graph=False):
        self.heads = heads
        self.graph_dict = graph_dict
        bi = loggraphprovider.BranchInfo(None, None, None)
        loggraphprovider.LogGraphProvider.__init__(self, [bi], bi, no_graph)
    
    def load(self):
        for head in self.heads:
            self.append_head_info(head, self.branches[0], head)
        
        self.process_graph_parents(self.heads, self.graph_dict.items())
        
        self.compute_head_info()
        
        if not self.no_graph:
            self.compute_branch_lines()
            self.compute_merge_info()


class BasicFilterer(object):
    def __init__(self, filtered_revids):
        self.filtered_revids = filtered_revids
    
    def get_revision_visible(self, rev):
         return rev.revid not in self.filtered_revids

def print_computed(computed):
    print_lines([(c_rev.rev.revid,
                 c_rev.col_index,
                 c_rev.twisty_state,
                 c_rev.lines,)
                for c_rev in computed.filtered_revs])

def print_lines(list):
    print ''
    print format_graph_lines(list)

def format_graph_lines(list, use_unicode=True):
    if not list:
        return list.__repr__() + '\n'
    s = StringIO()
    item_repr = [item.__repr__() for item in list]
    repr_width = max([len(repr) for repr in item_repr])
    if use_unicode:
        twisty_char = {None: u'○',
                      True: u'⊖',
                      False: u'⊕'}
        ver_char = {True: u'│',
                    False: u'┆'}
        
        hor_char = {True: {u' ': u'─',
                           u'│': u'┼',
                           u'┆': u'┼'},
                    False: {u' ': u'┄',
                           u'│': u'┼',
                           u'┆': u'┼'}}
        
        tl_char = {u' ': u'╭',
                   u'│': u'├',
                   u'┆': u'├',
                   u'─': u'┬',
                   u'┄': u'┬',
                   u'┴': u'┼',
                   u'┤': u'┼',}
    
        tr_char = {u' ': u'╮',
                   u'│': u'┤',
                   u'┆': u'┤',
                   u'─': u'┬',
                   u'┄': u'┬',
                   u'┴': u'┼',
                   u'├': u'┼',}
    
        bl_char = {u' ': u'╰',
                   u'│': u'├',
                   u'┆': u'├',
                   u'─': u'┴',
                   u'┄': u'┴',
                   u'┬': u'┼',
                   u'┤': u'┼',}
        
        br_char = {u' ': u'╯',
                   u'│': u'┤',
                   u'┆': u'┤',
                   u'─': u'┴',
                   u'┄': u'┴',
                   u'┬': u'┼',
                   u'├': u'┼',}
    else:
        twisty_char = {None: '*',
                      True: '~',
                      False: '+'}
        ver_char = {True: '|',
                    False: ':'}
        
        hor_char = {True: {' ': '-',},
                    False: {' ': '-'}}
        
        tl_char = {}
    
        tr_char = {}
    
        bl_char = {}
        
        br_char = {}
    
    for row, (item, repr) in enumerate(zip(list, item_repr)):
        if row == 0:
            s.write('[')
        else:
            s.write(' ')
        s.write(repr.ljust(repr_width))
        if row == len(list)-1:
            s.write('] # ')
        else:
            s.write(', # ')
        
        if len(item) == 4:
            revid, col_index, twisty_state, lines = item
        if len(item) == 5:
            revid, col_index, twisty_state, lines, labels = item
        
        all_cols = [col_index]
        all_cols += [start for start, end, color, direct in lines]
        all_cols += [end for start, end, color, direct in lines]
        num_cols = (max(all_cols) + 1) * 2
        this_line = [' ' for i in range(num_cols)]
        next_line = [' ' for i in range(num_cols)]
        
        for start, end, color, direct in lines:
            start = int(round(start))
            end = int(round(end))
            if start == end:
                this_line[start * 2] = ver_char[direct]
                next_line[start * 2] = ver_char[direct]
            else:
                this_line[start * 2] = ver_char[direct]
        
        def replace_char(line, i, char_dict):
            old_char = line[i]
            if old_char in char_dict:
                line[i] = char_dict[old_char]
            
        for start, end, color, direct in lines:
            start = int(round(start))
            end = int(round(end))
            if start < end:
                for i in range(start * 2 + 1, end * 2):
                    replace_char(next_line, i, hor_char[direct])
                replace_char(next_line, start * 2, bl_char)
                replace_char(next_line, end * 2, tr_char)
            elif start > end:
                for i in range(end * 2 + 1, start * 2):
                    replace_char(next_line, i, hor_char[direct])
                replace_char(next_line, start * 2, br_char)
                replace_char(next_line, end * 2, tl_char)
        
        this_line[int(col_index * 2)] = twisty_char[twisty_state]
        
        s.write(''.join(this_line))
        s.write('\n')
        
        if not row == len(list)-1:
            s.write('# '.rjust(repr_width + 5))
            s.write(''.join(next_line))
            s.write('\n')
    return s.getvalue()


class TestGroupOverlaping(TestCase):
    def test_group_overlaping(self):
        lines = [
            (['a1'], 1, 3, 'a'),
            (['a2'], 2, 5, 'a'),
            (['a3'], 4, 6, 'a'),
            (['a4'], 6, 8, 'a'),
            (['b1'], 1, 3, 'b'),
            (['b2'], 2, 5, 'b'),
            (['n1'], 1, 8, None),
            (['n2'], 1, 8, None),
            ]
        groups = loggraphprovider.group_overlaping(lines)
        self.assertEqual(
            [(['a1', 'a2', 'a3'], 1, 6, 'a'),
             (['a4'], 6, 8, 'a'),
             (['b1', 'b2'], 1, 5, 'b'),
             (['n1'], 1, 8, None),
             (['n2'], 1, 8, None)],
            groups)
