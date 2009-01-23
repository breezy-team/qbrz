# -*- coding: utf-8 -*-
#
# QBzr - Qt frontend to Bazaar commands
# Copyright (C) 2006-2007 Gary van der Merwe <garyvdm@gmail.com> 
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

import sys
from time import clock

from bzrlib import errors
from bzrlib.transport.local import LocalTransport
from bzrlib.revision import NULL_REVISION
from bzrlib.tsort import merge_sort
from bzrlib.graph import (Graph, _StackedParentsProvider)
from bzrlib.bzrdir import BzrDir
from bzrlib.branch import Branch

have_search = True
try:
    from bzrlib.plugins.search import errors as search_errors
    from bzrlib.plugins.search import index as search_index
except ImportError:
    have_search = False

class LogGraphProvider():
    """Loads and computes revision and graph data for GUI log widgets."""

    def __init__(self):
        
        """List of unique repositories"""
        self.branches = []
        """List of tuple(tree, branch, repo )"""
        self.file_ids = []
        
        self.repos = {}
        
        self.head_revids = []
        """List of revids that are the heads of the graph.
        The order of the heads is mantianed in this list.
        """
        self.revid_head_info = {}
        """Dict of revid to a list of head_infos. head_info is a tuple of:
            (branch,
            tag,
            is_branch_last_revision)
        """
        
        self.merge_sorted_revisions = []
        self.msri_index = {}
        
        self.revisions = {}
        self.queue = []
        self.tags = {}
        
        self.filter_file_id = None
        """Filtered dict of msri's that are visible because they touch
        self.file_ids
        """
        
        self.graph_line_data = []
        """ list containing for visible revisions:
                [msri,
                 node,
                 lines,
                 twisty_state,
                 twisty_branch_ids].
        
        Node is a tuple of (column, color) with column being a
        zero-indexed column number of the graph that this revision
        represents and color being a zero-indexed color (which doesn't
        specify any actual color in particular) to draw the node in.
        
        Lines is a list of tuples which represent lines you should draw
        away from the revision, if you also need to draw lines into the
        revision you should use the lines list from the previous
        iteration. Each tuples in the list is in the form (start, end,
        color, direct) with start and end being zero-indexed column
        numbers and color as in node.
        
        twisties are +- buttons to show/hide branches. list branch_ids
        
        """
        
        self.load_revisions_call_count = sys.maxint
    
    def update_ui(self):
        pass
    
    def throbber_show(self):
        pass
    
    def throbber_hide(self):
        pass
    
    def append_repo(self, repo):
        repo.is_local = isinstance(repo.bzrdir.transport, LocalTransport)
        if repo.base not in self.repos:
            self.repos[repo.base] = repo
    
    def open_branch(self, branch, file_id):
        """Open branch and file_ids to be loaded. """
        
        repo = branch.repository
        try:
            tree = branch.bzrdir.open_workingtree()
        except errors.NoWorkingTree:
            tree = None
        self.append_repo(repo)
        self.branches.append((tree, branch, repo))
        
        if file_id:
            self.file_ids.append(file_id)
    
    def open_locations(self, locations):
        """Open branches or repositories and file-ids to be loaded from a list
        of locations strings, inputed by the user (such as at the command line.)
        
        """
        
        paths_and_branches_err = "It is not possible to specify different file paths and different branches at the same time."
        
        for location in locations:
            tree, br, repo, fp = \
                    BzrDir.open_containing_tree_branch_or_repository(location)
            self.update_ui()
            
            if br == None:
                repo_brs = repo.find_branches(using=True)
                self.update_ui()
                
                # Sort the loaded branches so that the trunk is first.
                trunk_names = ["trunk", "bzr.dev", "dev"]
                def branch_cmp_trunk_first(x,y):
                    x_is_trunk = x.nick in trunk_names
                    y_is_trunk = y.nick in trunk_names
                    if x_is_trunk and y_is_trunk:
                        return cmp(trunk_names.index(x.nick),
                                   trunk_names.index(y.nick))
                    if x_is_trunk:
                        return -1
                    if y_is_trunk:
                        return 1
                    return cmp(x.nick, y.nick)
                repo_brs.sort(branch_cmp_trunk_first)
                
                for br in repo_brs:             
                    try:
                        tree = br.bzrdir.open_workingtree()
                    except errors.NoWorkingTree:
                        tree = None
                    self.append_repo(repo)
                    self.branches.append((tree, br, repo))
            else:
                self.append_repo(repo)
                self.branches.append((tree, br, repo))
            
            # If no locations were sepecified, don't do file_ids
            # Otherwise it gives you the history for the dir if you are
            # in a sub dir.
            if fp != '' and locations==["."]:
                fp = ''

            if fp != '' : 
                if tree is None:
                    file_id = br.basis_tree().path2id(fp)
                else:
                    file_id = tree.path2id(fp)
                self.update_ui()
                
                if file_id is None:
                    raise errors.BzrCommandError(
                        "Path does not have any revision history: %s" %
                        location)
                self.file_ids.append(file_id)
        
        if self.file_ids and len(self.branches)>1:
            raise errors.BzrCommandError(paths_and_branches_err)

    def lock_read_branches(self):
        for (tree, branch, repo) in self.branches:
            branch.lock_read()
    
    def unlock_branches(self):
        for (tree, branch, repo) in self.branches:
            branch.unlock()
    
    def lock_read_repos(self):
        for repo in self.repos.itervalues():
            repo.lock_read()
    
    def unlock_repos(self):
        for repo in self.repos.itervalues():
            repo.unlock()
    
    def append_head_info(self, revid, branch, tag, is_branch_last_revision):
        if not revid in self.head_revids:
            self.head_revids.append(revid)
            self.revid_head_info[revid] = []
        self.revid_head_info[revid].append ((branch, tag,
                                             is_branch_last_revision))
    
    def load_branch_heads(self):
        """Load the tips, tips of the pending merges, and revision of the
        working tree for each branch."""
        
        self.heads = {}
        
        for (tree, branch, repo) in self.branches:
            
            if len(self.branches) == 1:
                tag = None
            else:
                tag = branch.nick
                if len(tag) < 20:
                    tag = tag[:20]+'...'
            
            branch_last_revision = branch.last_revision()
            self.append_head_info(branch_last_revision, branch, tag, True)
            self.update_ui()
            
            if tree:
                parent_ids = tree.get_parent_ids()
                if parent_ids:
                    # first parent is last revision of the tree
                    revid = parent_ids[0]
                    if revid != branch_last_revision:
                        # working tree is out of date
                        if tag:
                            append_head_info(revid, branch,
                                             "%s - Working Tree" % tag, False)
                        else:
                            append_head_info(revid, branch,
                                             "Working Tree", False)
                    # other parents are pending merges
                    for revid in parent_ids[1:]:
                        if tag:
                            append_head_info(revid, branch,
                                             "%s - Pending Merge" % tag, False)
                        else:
                            append_head_info(revid, branch,
                                             "Pending Merge", False)
                self.update_ui()
    
    def load_tags(self):
        self.tags = {}
        for (tree, branch, repo) in self.branches:
            branch_tags = branch.tags.get_reverse_tag_dict()  # revid to tags map
            for revid, tags in branch_tags.iteritems():
                if revid in self.tags:
                    self.tags[revid].update(set(tags))
                else:
                    self.tags[revid] = set(tags)

    def repos_sorted_local_first(self):
        def cmp(x, y):
            if x.is_local and not y.is_local:
                return 1
            if y.is_local and not x.is_local:
                return -1
            return 0
        return sorted([repo 
                       for repo in self.repos.itervalues()],
                       cmp)

    def load_graph_all_revisions(self):
        parents_providers = [repo._make_parents_provider() \
                             for repo in self.repos_sorted_local_first()]
        graph = Graph(_StackedParentsProvider(parents_providers))
        self.graph_parents = {}
        self.graph_children = {}
        ghosts = set()
        
        for (revid, parent_revids) in graph.iter_ancestry(self.head_revids):
            if parent_revids is None:
                ghosts.add(revid)
                continue
            if parent_revids == (NULL_REVISION,):
                self.graph_parents[revid] = ()
            else:
                self.graph_parents[revid] = parent_revids
            for parent in parent_revids:
                self.graph_children.setdefault(parent, []).append(revid)
            self.graph_children.setdefault(revid, [])
            if len(self.graph_parents) % 100 == 0 :
                self.update_ui()
        for ghost in ghosts:
            for ghost_child in self.graph_children[ghost]:
                self.graph_parents[ghost_child] = [p
                        for p in self.graph_parents[ghost_child] if p not in ghosts]
        self.graph_parents["top:"] = self.head_revids
    
        if len(self.graph_parents)>0:
            self.merge_sorted_revisions = merge_sort(
                self.graph_parents,
                "top:",
                generate_revno=True)
        else:
            self.merge_sorted_revisions = ()
        
        assert self.merge_sorted_revisions[0][1] == "top:"
        self.merge_sorted_revisions = self.merge_sorted_revisions[1:]
        
        def get_revid_head(heads):
            map = {}
            for i in xrange(1, len(heads)):
                for ancestor_revid in graph.find_unique_ancestors(heads[i][0],
                                                                heads[:i-1][0]):
                    map[ancestor_revid] = heads[i][1]
            return map
        
        self.revid_head_revid = \
                get_revid_head([(revid, revid) for revid in self.head_revids])
        
        head_revid_repo = sorted([(revid, branch.repository.base) \
                                  for revid, head_info in \
                                  self.revid_head_info.iteritems()
                                  for (branch, tag, lr) in head_info],
                                 lambda x: self.repos_sorted_local_first.cmp(x[1]))
        self.default_repo = head_revid_repo[0][1]
        self.revid_repo = get_revid_head(head_revid_repo)
    
    def compute_branch_lines(self):
        self.branch_lines = {}
        """A list of each "branch", containing
            [a list of revision indexes in the branch,
             is the branch visible,
             merges,
             merged_by].
        
        For a revisions, the revsion number less the least significant
        digit is the branch_id, and used as the key for the dict. Hence
        revision with the same revsion number less the least significant
        digit are considered to be in the same branch line. e.g.: for
        revisions 290.12.1 and 290.12.2, the branch_id would be 290.12,
        and these two revisions will be in the same branch line.
        
        """
        
        self.revid_msri = {}
        self.revno_msri = {}
        self.start_branch_ids = []
        """Branch ids that should be initialy visible"""
        
        for (rev_index, (sequence_number,
                         revid,
                         merge_depth,
                         revno_sequence,
                         end_of_merge)) in enumerate(self.merge_sorted_revisions):
            branch_id = revno_sequence[0:-1]
            
            self.revid_msri[revid] = rev_index
            self.revno_msri[revno_sequence] = rev_index
            
            branch_line = None
            if branch_id not in self.branch_lines:
                start_branch = revid in self.head_revids
                branch_line = [[],
                               start_branch,
                               [],
                               []]
                if start_branch:
                    self.start_branch_ids.append(branch_id)
                self.branch_lines[branch_id] = branch_line
            else:
                branch_line = self.branch_lines[branch_id]
            
            branch_line[0].append(rev_index)
        
        self.branch_ids = self.branch_lines.keys()
        
        def branch_id_cmp(x, y):
            is_start_x = x in self.start_branch_ids
            is_start_y = y in self.start_branch_ids
            if not is_start_x == is_start_y:
                return - cmp(is_start_x, is_start_y)
            merge_depth_x = self.merge_sorted_revisions[self.branch_lines[x][0][0]][2]
            merge_depth_y = self.merge_sorted_revisions[self.branch_lines[y][0][0]][2]
            if not merge_depth_x == merge_depth_y:
                return cmp(merge_depth_x, merge_depth_y)
            return -cmp(x, y)
        
        self.branch_ids.sort(branch_id_cmp)
    
    def compute_merge_info(self):
        self.merge_info = []
        """List containing for each revision:
            (which revisions it merges,
            (revision it is merged by).
        
        """
        
        current_merge_stack = [None]
        for (msri, (sequence_number,
                    revid,
                    merge_depth,
                    revno_sequence,
                    end_of_merge)) in enumerate(self.merge_sorted_revisions):
            
            if merge_depth == len(current_merge_stack):
                current_merge_stack.append(msri)
            else:
                del current_merge_stack[merge_depth + 1:]
                current_merge_stack[-1] = msri
            
            merged_by = None
            if merge_depth>0:
                merged_by = current_merge_stack[-2]
                if merged_by is not None:
                    self.merge_info[merged_by][0].append(msri)
                    branch_id = revno_sequence[0:-1]
                    merged_by_branch_id = self.merge_sorted_revisions[merged_by][3][0:-1]
                    
                    if not branch_id in self.branch_lines[merged_by_branch_id][3]: 
                        self.branch_lines[merged_by_branch_id][2].append(branch_id) 
                    if not merged_by_branch_id in self.branch_lines[branch_id][2]: 
                        self.branch_lines[branch_id][3].append(merged_by_branch_id) 
                    
            self.merge_info.append(([],merged_by))
        
    def load_filter_file_id(self):
        """Load with revisions affect the file_ids
        
        It requires that compute_merge_info has been run.
        
        """
        
        if self.file_ids:
            self.filter_file_id = {}
            try:
                self.branches[0].repository.texts.get_parent_map([])
                use_texts = True
            except AttributeError:
                use_texts = False
            
            if use_texts:
                chunk_size = 500
                for start in xrange(0, len(self.merge_sorted_revisions), chunk_size):
                    text_keys = [(specific_fileid, revid) \
                        for sequence_number,
                            revid,
                            merge_depth,
                            revno_sequence,
                            end_of_merge in self.merge_sorted_revisions[start:start + chunk_size] \
                        for specific_fileid in specific_fileids]
                    
                    for fileid, revid in self.branches[0].repository.texts.get_parent_map(text_keys):
                        rev_msri = self.revid_msri[revid]
                        self.filter_file_id[rev_msri] = True
                        
                        #self.graphFilterProxyModel.invalidateCacheRow(rev_msri)
                        #index = self.createIndex (rev_msri, 0, QtCore.QModelIndex())
                        #self.emit(QtCore.SIGNAL("dataChanged(QModelIndex, QModelIndex)"),
                        #          index,index)
                    self.update_ui()
            else:
                weave_modifed_revisions = set()
                for specific_fileid in specific_fileids:
                    file_weave = self.branches[0].repository.weave_store.get_weave(specific_fileid,
                                        self.branches[0].repository.get_transaction())
                    for revid in file_weave.versions():
                        rev_msri = self.revid_msri[revid]
                        self.touches_file_msri[rev_msri] = True
                        #self.graphFilterProxyModel.invalidateCacheRow(rev_msri)

    def get_revision_visible(self, msri):
        """ Returns wether a revision is visible or not"""
        
        (sequence_number,
         revid,
         merge_depth,
         revno_sequence,
         end_of_merge) = self.merge_sorted_revisions[msri]
        
        branch_id = revno_sequence[0:-1]
        if not self.branch_lines[branch_id][1]: # branch colapased
            return False
        
        return self.get_revision_visible_if_branch_visible(msri)

    
    def get_revision_visible_if_branch_visible(self, msri):
        if self.filter_file_id is not None:
            if msri not in self.filter_file_id:
                return False
        
        return True

    def compute_graph_lines(self):
        graph_line_data = []
        """See self.graph_line_data"""
        msri_index = {}
        
        for msri in xrange(0,len(self.merge_sorted_revisions)):
            if self.get_revision_visible(msri):
                index = len(graph_line_data)
                msri_index[msri] = index
                graph_line_data.append([msri,
                                        None,
                                        [],
                                        None,
                                        [],
                                        ])
        
        # This will hold a tuple of (child_index, parent_index, col_index,
        # direct) for each line that needs to be drawn. If col_index is not
        # none, then the line is drawn along that column, else the the line can
        # be drawn directly between the child and parent because either the
        # child and parent are in the same branch line, or the child and parent
        # are 1 row apart.
        lines = []
        empty_column = [False for i in range(len(graph_line_data))]
        # This will hold a bit map for each cell. If the cell is true, then
        # the cell allready contains a node or line. This use when deciding
        # what column to place a branch line or line in, without it
        # overlaping something else.
        columns = [list(empty_column)]
        
        def branch_line_col_search_order(parent_col_index):
            for col_index in range(parent_col_index, len(columns)):
                yield col_index
            #for col_index in range(parent_col_index-1, -1, -1):
            #    yield col_index
        
        def line_col_search_order(parent_col_index, child_col_index):
            if parent_col_index is not None and child_col_index is not None:
                max_index = max(parent_col_index, child_col_index)
                min_index = min(parent_col_index, child_col_index)
                # First yield the columns between the child and parent.
                for col_index in range(max_index, min_index -1, -1):
                    yield col_index
            elif child_col_index is not None:
                max_index = child_col_index
                min_index = child_col_index
                yield child_col_index
            elif parent_col_index is not None:
                max_index = parent_col_index
                min_index = parent_col_index
                yield parent_col_index
            else:
                max_index = 0
                min_index = 0
                yield 0
            i = 1
            # then yield the columns on either side.
            while max_index + i < len(columns) or \
                  min_index - i > -1:
                if max_index + i < len(columns):
                    yield max_index + i
                #if min_index - i > -1:
                #    yield min_index - i
                i += 1
        
        def find_free_column(col_search_order, line_range):
            for col_index in col_search_order:
                column = columns[col_index]
                has_overlaping_line = False
                for row_index in line_range:
                    if column[row_index]:
                        has_overlaping_line = True
                        break
                if not has_overlaping_line:
                    break
            else:
                # No free columns found. Add an empty one on the end.
                col_index = len(columns)
                column = list(empty_column)
                columns.append(column)
            return col_index
        
        def mark_column_as_used(col_index, line_range):
            column = columns[col_index]
            for row_index in line_range:
                column[row_index] = True
        
        def append_line (child_index, parent_index, direct):
            parent_node = graph_line_data[parent_index][1]
            if parent_node:
                parent_col_index = parent_node[0]
            else:
                parent_col_index = None
            
            child_node = graph_line_data[child_index][1]
            if child_node:
                child_col_index = child_node[0]
            else:
                child_col_index = None
                
            line_col_index = child_col_index
            if parent_index - child_index >1:
                line_range = range(child_index + 1, parent_index)
                col_search_order = \
                        line_col_search_order(parent_col_index,
                                               child_col_index)
                line_col_index = \
                    find_free_column(col_search_order,
                                      line_range)
                mark_column_as_used(line_col_index,
                                     line_range)
            lines.append((child_index,
                          parent_index,
                          line_col_index,
                          direct,
                          ))            
        
        for branch_id in self.branch_ids:
            (branch_rev_msri,
             branch_visible,
             branch_merges,
             branch_merged_by) = self.branch_lines[branch_id]
            
            if branch_visible:
                branch_rev_msri = [rev_msri for rev_msri in branch_rev_msri
                                   if rev_msri in msri_index]
            else:
                branch_rev_msri = []
                
            if branch_rev_msri:
                color = reduce(lambda x, y: x+y, branch_id, 0)
                
                # In this loop:
                # * Find visible parents.
                # * Populate twisty_branch_ids and twisty_state
                branch_rev_visible_parents = {}
                
                for rev_msri in branch_rev_msri:
                    rev_index = msri_index[rev_msri]
                    (sequence_number,
                         revid,
                         merge_depth,
                         revno_sequence,
                         end_of_merge) = self.merge_sorted_revisions[rev_msri]
                    
                    # Find parents that are currently visible
                    rev_visible_parents = []
                    for parent_revid in self.graph_parents[revid]:
                        (parent_msri,
                         parent_branch_id,
                         parent_merge_depth) = self.msri_branch_id_merge_depth(parent_revid)
                        if parent_msri in msri_index:
                            rev_visible_parents.append((parent_revid,
                                                        parent_msri,
                                                        parent_branch_id,
                                                        parent_merge_depth,
                                                        True))
                        else:
                            # The parent was not visible. Search for a ansestor
                            # that is. Stop searching if we make a hop, i.e. we
                            # go away for our branch, and we come back to it
                            has_seen_different_branch = False
                            if not parent_branch_id == branch_id:
                                has_seen_different_branch = True
                            while parent_revid and parent_msri not in msri_index:
                                parents = self.graph_parents[parent_revid]
                                if len(parents) == 0:
                                    parent_revid = None
                                else:
                                    parent_revid = parents[0]
                                    (parent_msri,
                                     parent_branch_id,
                                     parent_merge_depth) = self.msri_branch_id_merge_depth(parent_revid)
                                if not parent_branch_id == branch_id:
                                    has_seen_different_branch = True
                                if has_seen_different_branch and parent_branch_id == branch_id:
                                    parent_revid = None
                                    break
                            if parent_revid:
                                rev_visible_parents.append((parent_revid,
                                                            parent_msri,
                                                            parent_branch_id,
                                                            parent_merge_depth,
                                                            False))
                    branch_rev_visible_parents[rev_msri]=rev_visible_parents
                    
                    # Find and add nessery twisties
                    for parent_msri in self.merge_info[rev_msri][0]:
                        parent_branch_id = self.merge_sorted_revisions[parent_msri][3][0:-1]
                        parent_merge_depth = self.merge_sorted_revisions[parent_msri][2]
                        
                        # Does this branch have any visible revisions
                        parent_branch_rev_msri = self.branch_lines[parent_branch_id][0]
                        for pb_rev_msri in parent_branch_rev_msri:
                            visible = pb_rev_msri in msri_index or \
                                self.get_revision_visible_if_branch_visible (pb_rev_msri)
                            if visible:
                                graph_line_data[rev_index][4].append (parent_branch_id)
                                break
                    
                    # Work out if the twisty needs to show a + or -. If all
                    # twisty_branch_ids are visible, show - else +.
                    if len (graph_line_data[rev_index][4])>0:
                        twisty_state = True
                        for twisty_branch_id in graph_line_data[rev_index][4]:
                            if not self.branch_lines[twisty_branch_id][1]:
                                twisty_state = False
                                break
                        graph_line_data[rev_index][3] = twisty_state
                
                last_parent_msri = None
                if branch_rev_visible_parents[branch_rev_msri[-1]]: 
                    last_parent_msri = branch_rev_visible_parents[branch_rev_msri[-1]][0][1]
                
                children_with_sprout_lines = {}
                # In this loop:
                # * Append lines that need to go to parents before the branch
                #   (say inbetween the main line and the branch). Remove the
                #   ones we append from rev_visible_parents so they don't get
                #   added again later on.
                # * Append lines to chilren for sprouts.
                for rev_msri in branch_rev_msri:
                    rev_index = msri_index[rev_msri]
                    (sequence_number,
                         revid,
                         merge_depth,
                         revno_sequence,
                         end_of_merge) = self.merge_sorted_revisions[rev_msri]
                    
                    rev_visible_parents = branch_rev_visible_parents[rev_msri]
                    i = 0
                    while i < len(rev_visible_parents):
                        (parent_revid,
                         parent_msri,
                         parent_branch_id,
                         parent_merge_depth,
                         direct) = rev_visible_parents[i]
                        
                        parent_index = msri_index[parent_msri]
                        if (rev_msri <> branch_rev_msri[-1] or i > 0 )and \
                           parent_branch_id <> branch_id and\
                           branch_id <> () and \
                           parent_merge_depth <= merge_depth and\
                           (last_parent_msri and not direct and last_parent_msri >= parent_msri or not last_parent_msri or direct):
                            
                            if parent_index - rev_index >1:
                                rev_visible_parents.pop(i)
                                i -= 1
                                append_line(rev_index, parent_index, direct)
                        i += 1
                    
                    # This may be a sprout. Add line to first visible child
                    merged_by_msri = self.merge_info[rev_msri][1]
                    if merged_by_msri and\
                       not merged_by_msri in msri_index and\
                       rev_msri == self.merge_info[merged_by_msri][0][0]:
                        # The revision that merges this revision is not
                        # visible, and it is the first revision that is
                        # merged by that revision. This is a sprout.
                        #
                        # XXX What if multiple merges with --force,
                        # aka ocutpus merge?
                        #
                        # Search until we find a decendent that is visible.
                        child_msri = self.merge_info[rev_msri][1]
                        while not child_msri is None and \
                              not child_msri in msri_index:
                            child_msri = self.merge_info[child_msri][1]
                        # Ensure only one line to a decendent.
                        if child_msri not in children_with_sprout_lines:
                            children_with_sprout_lines[child_msri] = True
                            if child_msri in msri_index:
                                child_index = msri_index[child_msri]
                                append_line(child_index, rev_index, False)
                
                # Find a column for this branch.
                #
                # Find the col_index for the direct parent branch. This will
                # be the starting point when looking for a free column.
                
                if branch_id == ():
                    parent_col_index = 0
                else:
                    parent_col_index = 1
                parent_index = None
                
                if last_parent_msri:
                    parent_index = msri_index[last_parent_msri]
                    parent_node = graph_line_data[parent_index][1]
                    if parent_node:
                        parent_col_index = parent_node[0]
                
                col_search_order = branch_line_col_search_order(parent_col_index) 
                cur_cont_line = []
                
                # Work out what rows this branch spans
                line_range = []
                first_rev_index = msri_index[branch_rev_msri[0]]
                last_rev_index = msri_index[branch_rev_msri[-1]]
                line_range = range(first_rev_index, last_rev_index+1)
                
                if parent_index:
                    line_range.extend(range(last_rev_index+1, parent_index))
                
                col_index = find_free_column(col_search_order,
                                              line_range)
                node = (col_index, color)
                # Free column for this branch found. Set node for all
                # revision in this branch.
                for rev_msri in branch_rev_msri:
                    rev_index = msri_index[rev_msri]
                    graph_line_data[rev_index][1] = node
                    columns[col_index][rev_index] = True
                
                # In this loop:
                # * Append the remaining lines to parents.
                for rev_msri in reversed(branch_rev_msri):
                    rev_index = msri_index[rev_msri]
                    (sequence_number,
                         revid,
                         merge_depth,
                         revno_sequence,
                         end_of_merge) = self.merge_sorted_revisions[rev_msri]
                    for (parent_revid,
                         parent_msri,
                         parent_branch_id,
                         parent_merge_depth,
                         direct) in branch_rev_visible_parents[rev_msri]:
                        
                        parent_index = msri_index[parent_msri]
                        append_line(rev_index, parent_index, direct)
        
        # It has now been calculated which column a line must go into. Now
        # copy the lines in to graph_line_data.
        for (child_index,
             parent_index,
             line_col_index,
             direct,
             ) in lines:
            
            (child_col_index, child_color) = graph_line_data[child_index][1]
            (parent_col_index, parent_color) = graph_line_data[parent_index][1]
            
            if parent_index - child_index == 1:
                graph_line_data[child_index][2].append(
                    (child_col_index,
                     parent_col_index,
                     parent_color,
                     direct))
            else:
                # line from the child's column to the lines column
                graph_line_data[child_index][2].append(
                    (child_col_index,
                     line_col_index,
                     parent_color,
                     direct))
                # lines down the line's column
                for line_part_index in range(child_index+1, parent_index-1):
                    graph_line_data[line_part_index][2].append(
                        (line_col_index,   
                         line_col_index,
                         parent_color,
                         direct))
                # line from the line's column to the parent's column
                graph_line_data[parent_index-1][2].append(
                    (line_col_index,
                     parent_col_index,
                     parent_color,
                     direct))

        self.graph_line_data = graph_line_data
        self.msri_index = msri_index

    def msri_branch_id_merge_depth (self, revid):
        msri = self.revid_msri[revid]
        branch_id = self.merge_sorted_revisions[msri][3][0:-1]
        merge_depth = self.merge_sorted_revisions[msri][2]
        return (msri, branch_id, merge_depth)
    
    def set_branch_visible(self, branch_id, visible, has_change):
        if not self.branch_lines[branch_id][1] == visible:
            has_change = True
        self.branch_lines[branch_id][1] = visible
        return has_change
    
    def ensure_rev_visible(self, revid):
        rev_msri = self.revid_msri[revid]
        branch_id = self.merge_sorted_revisions[rev_msri][3][0:-1]
        has_change = self._set_branch_visible(branch_id, True, False)
        while not branch_id in self.start_branch_ids and self.branch_lines[branch_id][3]:
            branch_id = self.branch_lines[branch_id][3][0]
            has_change = self.set_branch_visible(branch_id, True, has_change)
        return has_change

    def has_visible_child(self, branch_id):
        for child_branch_id in self.branch_lines[branch_id][3]:
            if self.branch_lines[child_branch_id][1]:
                return True
        return False

    def colapse_expand_rev(self, revid, visible):
        msri = self.revid_msri[revid]
        if msri not in self.msri_index: return
        index = self.msri_index[msri]
        twisty_branch_ids = self.graph_line_data[index][4]
        has_change = False
        for branch_id in twisty_branch_ids:
            has_change = self.set_branch_visible(branch_id,
                                                 visible,
                                                 has_change)
            if not visible:
                for parent_branch_id in self.branch_lines[branch_id][2]:
                    if not parent_branch_id in self.start_branch_ids and \
                       not self.has_visible_child(parent_branch_id):
                        has_change = self.set_branch_visible(parent_branch_id,
                                                             visible,
                                                             has_change)
        return has_change

    def has_rev_id(self, revid):
        return revid in self.revid_msri
    
    def revid_from_revno(self, revno):
        if revno not in self.revno_msri:
            return None
        msri = self.revno_msri[revno]
        return self.merge_sorted_revisions[msri][1]
        
    def find_child_branch_merge_revision(self, revid):
        msri = self.revid_msri[revid]
        merged_by_msri = self.merge_info[msri][1]
        if merged_by_msri:
            return self.merge_sorted_revisions[merged_by_msri][1]
        else:
            return None        
    
    def revision(self, revid):
        """Load and return a revision from a repository.
        
        If loading from a remote repository, this function will return None,
        and you will be notified when the revision has been loaded by
        revisions_loaded. At which point, you can call this function again.
        This is to allow you not to block your ui.
        
        """
        if revid not in self.revisions:
            return None
        
        return self.revisions[revid]
    
    def get_revid_repo(self, revid):
        if revid in self.revid_repo:
            return self.revid_repo[revid]
        
        return self.default_repo
    
    def load_revisions(self, revids,
                       update_time_initial=0.1,
                       update_time_increment=0,
                       update_time_max=0.05,
                       batch_size = 5):
        
        if self.load_revisions_call_count == sys.maxint:
            self.throbber_start_time = clock()
            self.load_revisions_call_count = 0
        
        self.load_revisions_call_count += 1
        current_call_count = self.load_revisions_call_count
        
        update_time = update_time_initial
        start_time = clock()
        last_update = clock()
        throbber_time = 1.0
        revisions_loaded = []
        
        repo_revids = {}
        for repo_base in self.repos.iterkeys():
            repo_revids[repo_base] = []
        
        for revid in revids:
            if revid not in self.revisions:
                repo_base = self.get_revid_repo(revid)
                repo_revids[repo_base].append(revid)
        
        try:
            for repo in self.repos_sorted_local_first():
                if current_call_count < self.load_revisions_call_count:
                    break
                
                revids = repo_revids[repo.base]
                for offset in range(0, len(revids), batch_size):
                    if current_call_count < self.load_revisions_call_count:
                        break
                    
                    current_time = clock()
                    needs_update_ui = False
                    if throbber_time < current_time - self.throbber_start_time:
                        self.throbber_show()
                        needs_update_ui = True
                    
                    if update_time < current_time - last_update:
                        self.revisions_loaded(revisions_loaded)
                        revisions_loaded = []
                        update_time = max(update_time + update_time_increment,
                                               update_time_max)
                        needs_update_ui = True
                        last_update = current_time
                    elif not repo.is_local:
                        needs_update_ui = True
                    
                    if needs_update_ui:
                        self.update_ui()
                    
                    if current_call_count < self.load_revisions_call_count:
                        break
                    
                    revisions = repo.get_revisions(revids[offset:offset+batch_size])
                    for rev in revisions:
                        revisions_loaded.append(rev.revision_id)
                        rev.repository = repo
                        self.post_revision_load(rev)
                        
            self.revisions_loaded(revisions_loaded)
        finally:
            if self.load_revisions_call_count == current_call_count:
                # This is the last running method
                self.throbber_hide()
                self.load_revisions_call_count = sys.maxint
    
    def post_revision_load(self, revision):
        self.revisions[revision.revision_id] = revision
        revno_sequence = self.merge_sorted_revisions[self.revid_msri[revision.revision_id]][3]
        revision.revno = ".".join(["%d" % (revno)
                                  for revno in revno_sequence])
        revision.tags = sorted(self.tags.get(revision.revision_id, []))
        revision.child_ids = self.graph_children[revision.revision_id]
        
        if revision.revision_id in self.revid_head_revid:
            head_revid = self.revid_head_revid[revid]
        else:
            head_revid = self.head_revids[0]
        revision.branch = self.revid_head_info[head_revid][0][0]
    
    def revisions_loaded(self, revisions):
        """Runs after a batch of revisions have been loaded
        
        Reimplement to be notified that revisions have been loaded. But
        remember to call super.
        
        """
        pass