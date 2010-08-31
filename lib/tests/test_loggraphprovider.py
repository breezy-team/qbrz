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
from StringIO import StringIO


from bzrlib.plugins.qbzr.lib import loggraphprovider

class TestLogGraphProvider(TestCaseWithTransport):
    
    def computed_to_list(self, computed):
        return [(c_rev.rev.revid,
                 c_rev.col_index,
                 c_rev.twisty_state,
                 c_rev.lines,)
                for c_rev in computed.filtered_revs]
    
    def assertComputed(self, expected_list, computed):
        computed_list = self.computed_to_list(computed)
        if not expected_list == computed_list:
            raise AssertionError("not equal: \nexpected_list = \n%scomputed_list = \n%s"
                % (format_graph_lines(expected_list, use_unicode=False),
                   format_graph_lines(computed_list, use_unicode=False),))
    
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
            [('rev-d', 0, True, [(0, 0, 0, True), (0, 1, 2, True)]), # ⊖─╮ 
                                                                     # │ │ 
             ('rev-c', 1, None, [(0, 0, 0, True), (1, 1, 0, True)]), # │ ○ 
                                                                     # │ │ 
             ('rev-b', 0, None, [(0, 0, 0, True), (1, 0, 0, True)]), # ○─╯ 
                                                                     # │   
             ('rev-a', 0, None, [])                                ],# ○ 
            computed)


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
        
        tl_char = {' ': '/',}
    
        tr_char = {' ': '\\'}
    
        bl_char = {' ': '\\'}
        
        br_char = {' ': '/'}
    
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
        
        revid, col_index, twisty_state, lines = item
        all_cols = [col_index]
        all_cols += [start for start, end, color, direct in lines]
        all_cols += [end for start, end, color, direct in lines]
        num_cols = (max(all_cols) + 1) * 2
        this_line = [' ' for i in range(num_cols)]
        next_line = [' ' for i in range(num_cols)]
        
        for start, end, color, direct in lines:
            if start == end:
                this_line[start * 2] = ver_char[direct]
                next_line[start * 2] = ver_char[direct]
            else:
                next_line[end * 2] = ver_char[direct]
        
        def replace_char(i, char_dict):
            old_char = this_line[i]
            if old_char in char_dict:
                this_line[i] = char_dict[old_char]
            
        for start, end, color, direct in lines:
            if start < end:
                for i in range(start * 2 + 1, end * 2):
                    replace_char(i, hor_char[direct])
                replace_char(start * 2, bl_char)
                replace_char(end * 2, tr_char)
            elif start > end:
                for i in range(end * 2 + 1, start * 2):
                    replace_char(i, hor_char[direct])
                replace_char(start * 2, br_char)
                replace_char(end * 2, tl_char)
        
        this_line[col_index * 2] = twisty_char[twisty_state]
        
        s.write(''.join(this_line))
        s.write('\n')
        
        if not row == len(list)-1:
            s.write('# '.rjust(repr_width + 5))
            s.write(''.join(next_line))
            s.write('\n')
    return s.getvalue()