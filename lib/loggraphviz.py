# -*- coding: utf-8 -*-
#
# QBzr - Qt frontend to Bazaar commands
# Copyright (C) 2006-2010 Gary van der Merwe <garyvdm@gmail.com>
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

"""
Layout a revision graph for visual representation, allowing for filtering and
collapsible branches.

Usage example
=============

.. python::
  bi = loggraphviz.BranchInfo('branch-label', tree, branch)
  graph_viz = loggraphviz.GraphVizLoader([bi], bi, False)
  graph_viz.load()
  state = loggraphviz.GraphVizFilterState(graph_viz)
  computed = graph_viz.compute_viz(state)

"""

import gc
from itertools import izip

from bzrlib import errors
from bzrlib.bzrdir import BzrDir
from bzrlib.transport.local import LocalTransport
from bzrlib.revision import NULL_REVISION, CURRENT_REVISION
from bzrlib.graph import (
    Graph,
    StackedParentsProvider,
    KnownGraph,
    DictParentsProvider,
    )


class BranchInfo(object):
    """Wrapper for a branch, it's working tree, if available, and a label."""
    
    def __init__(self, label, tree, branch, index=None):
        self.label = label
        self.tree = tree
        self.branch = branch
        self.index = index
    
    def __hash__(self):
        return self.branch.base.__hash__()

    def __eq__(self, other):
        if isinstance(other, BranchInfo):
            return self.branch.base.__eq__(other.branch.base)
        return False


class RevisionData(object):
    """
    Container for data for a revision in the graph that gets calculated
    when the graph is loaded.
    """
    
    # Instance of this object are typically named "rev".
    
    __slots__ = ["index", "_merge_sort_node", "branch", "_revno_str",
                 "merges", "merged_by", 'branch_id', 'color']
    
    def __init__(self, index, merge_sort_node):
        """Create a new RevisionData instance."""
        self.index = index
        self._merge_sort_node = merge_sort_node
        self.branch = None
        self._revno_str = None
        self.merges = []
        """Revision indexes that this revision merges"""
        self.merged_by = None
        """Revision index that merges this revision."""
        self.branch_id = self._merge_sort_node.revno[0:-1]
        self.color = reduce(lambda x, y: x + y, self.branch_id, 0)
    
    revid = property(lambda self: self._merge_sort_node.key)
    merge_depth = property(lambda self: self._merge_sort_node.merge_depth)
    revno_sequence = property(lambda self: self._merge_sort_node.revno)
    end_of_merge = property(lambda self: self._merge_sort_node.end_of_merge)
    
    def get_revno_str(self):
        if self._revno_str is None:
            self._revno_str = ".".join(["%d" % (revno)
                                for revno in self.revno_sequence])
            if self.revid.startswith(CURRENT_REVISION):
                self._revno_str += " ?"
        return self._revno_str
    revno_str = property(get_revno_str)
    
    def __repr__(self):
        return "%s <%s %s>" % (self.__class__.__name__, self.revno_str,
                              self.revid)

class BranchLine(object):
    """Container for data for a branch line, aka merge line."""
    
    __slots__ = ["branch_id", "revs", "merges", "merged_by",
                 "color", "merge_depth"]
    
    def __init__(self, branch_id):
        self.branch_id = branch_id
        self.revs = []
        self.merges = []
        self.merged_by = []
        self.merge_depth = 0

    def __repr__(self):
        return "%s <%s>" % (self.__class__.__name__, self.branch_id)


class GhostRevisionError(errors.InternalBzrError):

    _fmt = "{%(revision_id)s} is a ghost."

    def __init__(self, revision_id):
        errors.BzrError.__init__(self)
        self.revision_id = revision_id


class GraphVizLoader(object):
    """
    Loads graph for branches and provides computed layout for visual
    representation.
    """
    
    # Most list/dicts related to revisions are unfiltered. When we do a graph
    # layout, we filter these revisions. A revision may be filter out because:
    # * It's branch is hidden (or collapsed).
    # * We have a specified file_id(s), and the revision does not touch the
    #   file_id(s).
    # * We have a search, and the revision does not match the search.
    #
    # The main list of unfiltered revisions is self.revisions. A revisions
    # index in revisions are normally called index. The main list of filtered
    # revisions is filtered_revs. Revision indexes in this list are called
    # f_index.
    
    def __init__(self, branches, primary_bi, no_graph):
        self.branches = branches
        """List of BranchInfo for each branch."""
        self.primary_bi = primary_bi
        self.no_graph = no_graph
        
        self.repos = []
        self.local_repo_copies = []
        """A list of repositories that revisions will be attempted to be loaded        
        from first."""
        
        self.revid_head_info = {}
        """Dict with a keys of head revid and value of
            (list of (branch, label),
             list of revids that are unique to this head)
            
            We can't just store the BranchInfo, because the label may have
            have addition text in it, e.g. "Working Tree", "Pending Merges"
        """
        
        self.revid_branch_info = {}
        
        self.ghosts = set()
        
        self.revisions = []
        """List of RevisionInfo from merge_sort."""
        
        self.revid_rev = {}
        self.graph_children = {}
        
        self.tags = {}      # map revid -> tags set
    
    def load(self):
        # Get a unique list of repositories. If the url is the same,
        # we consider it the same repositories
        repo_urls = set()
        for bi in self.branches:
            repo = bi.branch.repository
            if repo.base not in repo_urls:
                repo_urls.add(repo.base)
                self.repos.append(repo)
        
        no_local_repos = True
        for repo in self.repos:
            if repo_is_local(repo):
                no_local_repos = False
        if no_local_repos:
            self.load_current_dir_repo()
        self.repos.sort(key=lambda repo: not repo_is_local(repo))

        self.lock_read_branches()
        try:
            head_revids, graph_parents = self.load_graph_parents()
            self.process_graph_parents(head_revids, graph_parents)
            
            self.compute_head_info()
            del self.graph
            
            if not self.no_graph:
                self.compute_branch_lines()
                self.compute_merge_info()
            
            self.load_tags()
        finally:
            self.unlock_branches()
    
    
    def load_current_dir_repo(self):
        # There are no local repositories. Try open the repository
        # of the current directory, and try load revisions data from
        # this before trying from remote repositories. This makes
        # the common use case of viewing a remote branch that is
        # related to the current branch much faster, because most
        # of the revision can be loaded from the local repository.
        try:
            bzrdir, relpath = BzrDir.open_containing(u".")
            repo = bzrdir.find_repository()
            self.repos.add(repo)
            self.local_repo_copies.append(repo)
        except Exception:
            pass
    
    def update_ui(self):
        pass
    
    def throbber_show(self):
        pass
    
    def throbber_hide(self):
        pass

    def lock_read_branches(self):
        for bi in self.branches:
            bi.branch.lock_read()
        for repo in self.repos:
            repo.lock_read()
    
    def unlock_branches(self):
        for bi in self.branches:
            bi.branch.unlock()
        for repo in self.repos:
            repo.unlock()
    
    #def lock_read_repos(self):
    #    for repo in self.repos.itervalues():
    #        repo.lock_read()
    #
    #def unlock_repos(self):
    #    for repo in self.repos.itervalues():
    #        repo.unlock()
    
    def load_tags(self):
        self.tags = {}
        for bi in self.branches:
            # revid to tags map
            branch_tags = bi.branch.tags.get_reverse_tag_dict()
            for revid, tags in branch_tags.iteritems():
                if revid in self.tags:
                    self.tags[revid].update(set(tags))
                else:
                    self.tags[revid] = set(tags)

    def append_head_info(self, revid, branch_info, tag):
        if not revid == NULL_REVISION:
            if not revid in self.revid_head_info:
                self.revid_head_info[revid] = ([], [])
            self.revid_head_info[revid][0].append((branch_info, tag))
            
            # So that early calls to get_revid_branch work
            self.revid_branch_info[revid] = branch_info

    def load_branch_heads(self, bi):
        branch_heads = []
        
        def append_head_info(revid, branch_info, label):
            self.append_head_info(revid, branch_info, label)
            branch_heads.append(revid)
        
        if len(self.branches) > 0:
            label = bi.label
        else:
            label = None
        
        branch_last_revision = bi.branch.last_revision()
        append_head_info(branch_last_revision, bi, bi.label)
        self.update_ui()
        
        if bi.tree:
            parent_ids = bi.tree.get_parent_ids()
            if parent_ids:
                # first parent is last revision of the tree
                revid = parent_ids[0]
                if revid != branch_last_revision:
                    # working tree is out of date
                    if label:
                        wt_label = "%s - Working Tree" % label
                    else:
                        wt_label = "Working Tree"
                    append_head_info(revid, bi, wt_label)
                # other parents are pending merges
                for revid in parent_ids[1:]:
                    if label:
                        pm_label = "%s - Pending Merge" % label
                    else:
                        pm_label = "Pending Merge"
                    append_head_info(revid, bi, pm_label)
            self.update_ui()
        return branch_heads, branch_heads, ()
    
    def load_graph_parents(self):
        """Load the heads of the graph, and the graph parents"""
        
        extra_parents = {}
        branches_heads = []
        
        def load_branch_heads(bi, insert_at_begin=False):
            load_heads, sort_heads, extra_parents_ = self.load_branch_heads(bi)
            for key, parents in extra_parents_:
                extra_parents[key] = parents
            if insert_at_begin:
                branches_heads.insert(0, (load_heads, sort_heads))
            else:
                branches_heads.append((load_heads, sort_heads))
        
        for bi in self.branches:
            # Don't do the primary branch, as that will be inserted later at
            # the first position.
            if bi != self.primary_bi:
                load_branch_heads(bi)
        
        if len(branches_heads) >= 2:
            head_revids = [revid for load_heads, sort_heads in branches_heads
                                 for revid in load_heads]
            head_revs = self.load_revisions(head_revids)
            
            get_max_timestamp = lambda branch_heads: max(
                [head_revs[revid].timestamp for revid in branch_heads[0]])
            branches_heads.sort(key=get_max_timestamp, reverse=True)
        
        if self.primary_bi:
            load_branch_heads(self.primary_bi, True)
        
        load_heads = [revid for load_heads_, sort_heads_ in branches_heads
                      for revid in load_heads_]
        sort_heads = [revid for load_heads_, sort_heads_ in branches_heads
                      for revid in sort_heads_]
        
        parents_providers = [repo._make_parents_provider() \
                             for repo in self.repos]
        parents_providers.append(DictParentsProvider(extra_parents))
        self.graph = Graph(StackedParentsProvider(parents_providers))
        
        return sort_heads, self.graph.iter_ancestry(sort_heads)
    
    def process_graph_parents(self, head_revids, graph_parents_iter):
        graph_parents = {}
        self.ghosts = set()
        
        for (revid, parent_revids) in graph_parents_iter:
            if revid == NULL_REVISION:
                continue
            if parent_revids is None:
                #Ghost
                graph_parents[revid] = ()
                self.ghosts.add(revid)
            elif parent_revids == (NULL_REVISION,):
                graph_parents[revid] = ()
            else:
                graph_parents[revid] = parent_revids
            if len(graph_parents) % 100 == 0:
                self.update_ui()
        
        graph_parents["top:"] = head_revids

        if len(graph_parents) > 0:
            enabled = gc.isenabled()
            if enabled:
                gc.disable()
            
            def make_kg():
                return KnownGraph(graph_parents)
            self.known_graph = make_kg()
            
            merge_sorted_revisions = self.known_graph.merge_sort('top:')
            # So far, we are a bit faster than the pure-python code. But the
            # last step hurts. Specifically, we take
            #   377ms KnownGraph(self.graph_parents)
            #   263ms kg.merge_sort() [640ms combined]
            #  1322ms self.revisions = [...]
            # vs 
            #  1152ms tsort.merge_sort(self.graph_parents)
            #   691ms self.revisions = [...]
            #
            # It is a gc thing... :(
            # Adding gc.disable() / gc.enable() around this whole loop changes
            # things to be:
            #   100ms   KnownGraph(self.graph_parents)
            #    77ms   kg.merge_sort() [177ms combined]
            #   174ms   self.revisions = [...]
            # vs
            #   639ms   tsort.merge_sort(self.graph_parents)
            #   150ms   self.revisions = [...]
            # Also known as "wow that's a lot faster". This is because KG()
            # creates a bunch of Python objects, then merge_sort() creates a
            # bunch more. And then self.revisions() creates another whole set.
            # And all of these are moderately long lived, so you have a *lot*
            # of allocations without removals (which triggers the gc checker
            # over and over again.) And they probably don't live in cycles
            # anyway, so you can skip it for now, and just run at the end.
            
            # self.revisions *is* a little bit slower. Probably because pyrex
            # MergeSortNodes use long integers rather than PyIntObject and thus
            # create them on-the-fly.

            # Get rid of the 'top:' revision
            merge_sorted_revisions.pop(0)
            self.revisions = [RevisionData(index, node)
                for index, node in enumerate(merge_sorted_revisions)]
            if enabled:
                gc.enable()
        else:
            self.revisions = ()
        
        self.revid_rev = {}
        self.revno_rev = {}
        
        self.max_mainline_revno = 0
        
        for rev in self.revisions:
            self.max_mainline_revno = max(self.max_mainline_revno, 
                                          rev.revno_sequence[0])
            self.revid_rev[rev.revid] = rev
            self.revno_rev[rev.revno_sequence] = rev
        
    def branch_id_sort_key(self, x):
        merge_depth = self.branch_lines[x].merge_depth
        
        # Note: This greatly affects the layout of the graph.
        #
        # Branch line that have a smaller merge depth should be to the left
        # of those with bigger merge depths.
        #
        # For branch lines that have the same parent in the mainline -
        # those with bigger branch numbers to be to the rights. E.g. for
        # the following dag, you want the graph to appear as on the left,
        # not as on the right:
        #
        # 3     F_       F
        #       | \      |\
        # 1.2.1 |  E     | E
        #       |  |     | \
        # 2     D  |     D_|
        #       |\ |     | +_
        # 1.1.2 | C|     | | C
        #       | |/     |  \|
        # 1.1.1 | B      |   B
        #       |/       | /
        # 1     A        A
        #
        # Otherwise, those with a greater mainline parent revno should
        # appear to the left.
        
        if len(x) == 0:
            return (merge_depth)
        else:
            return (merge_depth, -x[0], x[1])
    
    def compute_branch_lines(self):
        self.branch_lines = {}
        
        """A list of branch lines (aka merge lines).
        
        For a revisions, the revision number less the least significant
        digit is the branch_id, and used as the key for the dict. Hence
        revision with the same revision number less the least significant
        digit are considered to be in the same branch line. e.g.: for
        revisions 290.12.1 and 290.12.2, the branch_id would be 290.12,
        and these two revisions will be in the same branch line.
        
        """
        
        self.branch_ids = []
        """List of branch ids, sorted in the order that the branches will
        be shown, from left to right on the graph."""
        
        for rev in self.revisions:
            
            branch_line = None
            if rev.branch_id not in self.branch_lines:
                branch_line = BranchLine(rev.branch_id)
                self.branch_lines[rev.branch_id] = branch_line
            else:
                branch_line = self.branch_lines[rev.branch_id]
            
            branch_line.revs.append(rev)
            branch_line.merge_depth = max(rev.merge_depth,
                                          branch_line.merge_depth)
            rev.branch = branch_line
        
        self.branch_ids = self.branch_lines.keys()
        
        self.branch_ids.sort(key=self.branch_id_sort_key)
    
    def compute_merge_info(self):
        
        def set_merged_by(rev, merged_by, merged_by_rev, do_branches=False):
            if merged_by is None:
                return
            
            if merged_by_rev is None:
                merged_by_rev = self.revisions[merged_by]
            rev.merged_by = merged_by
            merged_by_rev.merges.append(rev.index)
            
            if do_branches:
                branch_id = rev.branch_id
                branch_merged_by = self.branch_lines[branch_id].merged_by
                merged_by_branch_id = self.revisions[merged_by].branch_id
                merged_by_branch_merges = \
                    self.branch_lines[merged_by_branch_id].merges
                
                if not branch_id in merged_by_branch_merges:
                    merged_by_branch_merges.append(branch_id)
                if not merged_by_branch_id in branch_merged_by:
                    branch_merged_by.append(merged_by_branch_id)
        
        for rev in self.revisions:
            
            parents = [self.revid_rev[parent] for parent in
                       self.known_graph.get_parent_keys(rev.revid)]
            
            if len(parents) > 0:
                if rev.branch_id == parents[0].branch_id:
                    set_merged_by(parents[0], rev.merged_by, None)
            
            for parent in parents[1:]:
                if rev.merge_depth <= parent.merge_depth:
                    set_merged_by(parent, rev.index, rev, do_branches=True)
        
    def compute_head_info(self):
        def get_revid_head(heads):
            map = {}
            for i in xrange(len(heads)):
                prev_revids = [revid for revid, head in heads[:i]]
                unique_ancestors = self.graph.find_unique_ancestors(
                    heads[i][0], prev_revids)
                for ancestor_revid in unique_ancestors:
                    map[ancestor_revid] = heads[i][1]
            return map
        
        if len(self.branches) > 1:
            head_revid_branch_info = sorted(
                [(revid, branch_info)
                 for revid, (head_info, ur) in self.revid_head_info.iteritems()
                 for (branch_info, tag) in head_info],
                key=lambda x: not repo_is_local(x[1].branch.repository))
            self.revid_branch_info = get_revid_head(head_revid_branch_info)
        else:
            self.revid_branch_info = {}
        
        head_count = 0
        for head_info, ur in self.revid_head_info.itervalues():
            head_count += len(head_info)
        
        if head_count > 1:
            # Populate unique revisions for heads
            for revid, (head_info, ur) in self.revid_head_info.iteritems():
                rev = None
                if revid in self.revid_rev:
                    rev = self.revid_rev[revid]
                if rev and rev.merged_by:
                    # This head has been merged.
                    # d
                    # |\
                    # b c
                    # |/
                    # a
                    # if revid == c,then we want other_revids = [b]
                    
                    merged_by_revid = self.revisions[rev.merged_by].revid
                    other_revids = [self.known_graph
                                    .get_parent_keys(merged_by_revid)[0]]
                else:
                    other_revids = [other_revid for other_revid \
                        in self.revid_head_info.iterkeys() \
                        if not other_revid == revid]
                ur.append(revid)
                ur.extend([revid for revid \
                    in self.graph.find_unique_ancestors(revid, other_revids) \
                    if not revid == NULL_REVISION and revid in self.revid_rev])
                ur.sort(key=lambda x: self.revid_rev[x].index)
    
    def compute_viz(self, state):
        
        # Overview:
        # Work out which revision need to be displayed.
        # Create ComputedGraphViz and ComputedRevisionData objects
        # Assign columns for branches, and lines that go between branches.
        #   These are intermingled, because some of the lines need to come
        #   before it's branch, and others need to come after. Other lines
        #   (such a the line from the last rev in a branch) are treated a
        #   special cases.
        # Return ComputedGraphViz object
        gc_enabled = gc.isenabled()
        gc.disable()
        try:
            computed = ComputedGraphViz(self)
            computed.filtered_revs = [ComputedRevisionData(rev) for rev in
                                      state.get_filtered_revisions()]
            
            c_revisions = computed.revisions
            for f_index, c_rev in enumerate(computed.filtered_revs):
                c_revisions[c_rev.rev.index] = c_rev
                c_rev.f_index = f_index
            
            for (revid, (head_info,
                         unique_revids)) in self.revid_head_info.iteritems():
                
                for unique_revid in unique_revids:
                    rev = self.revid_rev[unique_revid]
                    c_rev = c_revisions[rev.index]
                    if c_rev is not None:
                        c_rev.branch_labels.extend(head_info)
                        break
        finally:
            if gc_enabled:
                gc.enable()
        
        if self.no_graph:
            for c_rev in computed.filtered_revs:
                c_rev.col_index = c_rev.rev.merge_depth * 0.5
            return computed
        
        # This will hold a tuple of (child, parent, col_index, direct) for each
        # line that needs to be drawn. If col_index is not none, then the line
        # is drawn along that column, else the the line can be drawn directly
        # between the child and parent because either the child and parent are
        # in the same branch line, or the child and parent are 1 row apart.
        lines = []
        lines_by_column = []
        
        def branch_line_col_search_order(start_col_index):
            for col_index in range(start_col_index, len(lines_by_column)):
                yield col_index
            #for col_index in range(parent_col_index-1, -1, -1):
            #    yield col_index
        
        def line_col_search_order(parent_col_index, child_col_index):
            if parent_col_index is not None and child_col_index is not None:
                max_index = max(parent_col_index, child_col_index)
                min_index = min(parent_col_index, child_col_index)
                # First yield the columns between the child and parent.
                for col_index in range(max_index, min_index - 1, -1):
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
            while max_index + i < len(lines_by_column) or \
                  min_index - i > -1:
                if max_index + i < len(lines_by_column):
                    yield max_index + i
                #if min_index - i > -1:
                #    yield min_index - i
                i += 1
        
        def is_col_free_for_range(col_index, child_f_index, parent_f_index):
            return not any(
                range_overlaps(child_f_index, parent_f_index,
                               line_child_f_index, line_parent_f_index)
                for line_child_f_index, line_parent_f_index
                in lines_by_column[col_index])
        
        def find_free_column(col_search_order, child_f_index, parent_f_index):
            for col_index in col_search_order:
                if is_col_free_for_range(col_index,
                                             child_f_index, parent_f_index):
                    break
            else:
                # No free columns found. Add an empty one on the end.
                col_index = len(lines_by_column)
                lines_by_column.append([])
            return col_index
        
        def append_line(child, parent, direct, col_index=None):
            lines.append((child, parent, col_index, direct))
            
            if col_index is not None:
                lines_by_column[int(round(col_index))].append(
                    (child.f_index, parent.f_index))
        
        def find_visible_parent(c_rev, parent, twisty_hidden_parents):
            if c_revisions[parent.index] is not None:
                return (c_rev, c_revisions[parent.index], True)
            else:
                if parent.index in twisty_hidden_parents:
                    # no need to draw a line if there is a twisty,
                    # except if this is the last in the branch.
                    return None
                # The parent was not visible. Search for a ancestor
                # that is. Stop searching if we make a hop, i.e. we
                # go away from our branch, and we come back to it.
                has_seen_different_branch = False
                while c_revisions[parent.index] is None:
                    if not parent.branch_id == c_rev.rev.branch_id:
                        has_seen_different_branch = True
                    # find grand parent.
                    g_parent_ids = (self.known_graph
                                    .get_parent_keys(parent.revid))
                    
                    if len(g_parent_ids) == 0:
                        return None
                    else:
                        parent = self.revid_rev[g_parent_ids[0]]
                    
                    if (has_seen_different_branch and
                        parent.branch_id == branch_id):
                        # We have gone away and come back to our
                        # branch. Stop.
                        return None
                if parent:
                    # Not Direct
                    return (c_rev, c_revisions[parent.index], False)
        
        def append_branch_parent_lines(branch_rev_visible_parents):
            groups = group_overlapping(branch_rev_visible_parents)
            for parents, start, end, group_key in groups:
                # Since all parents go from the same branch line to the
                # same branch line, we can use the col indexes of the
                # parent.
                if end - start == 1:
                    col_index = None
                else:
                    col_search_order = line_col_search_order(
                        parents[0][1].col_index, parents[0][0].col_index)                        
                    col_index = find_free_column(col_search_order,
                                                 start, end)
                
                col_offset_increment = 1.0 / len(parents)
                for i, (c_rev, parent_c_rev, direct) in enumerate(parents):
                    if col_index is None:
                        col_index_offset = None
                    else:
                        col_index_offset = (col_index - 0.5 +
                                            (i * col_offset_increment) +
                                            (col_offset_increment / 2))
                    append_line(c_rev, parent_c_rev,
                                direct, col_index_offset)
        
        for branch_id in self.branch_ids:
            if not branch_id in state.branch_line_state:
                continue
            
            branch_line = self.branch_lines[branch_id]
            branch_revs = [c_revisions[rev.index]
                           for rev in branch_line.revs
                           if c_revisions[rev.index] is not None]
            
            if not branch_revs:
                continue
            
            branch_rev_visible_parents_post = []
            branch_rev_visible_parents_pre = []
            # Lists of ([(c_rev, parent_c_rev, is_direct)],
            #            start, end, group_key]
            
            last_c_rev = branch_revs[-1]
            last_rev_left_parents = (self.known_graph
                                     .get_parent_keys(last_c_rev.rev.revid))
            if last_rev_left_parents:
                last_parent = find_visible_parent(
                    last_c_rev, self.revid_rev[last_rev_left_parents[0]], [])
            else:
                last_parent = None
            
            sprout_with_lines = {}
            
            merged_by_max_col_index = 0
            
            # In this loop:
            # * Populate twisty_branch_ids and twisty_state
            # * Find visible parents.
            # * Append lines that go before the branch line.
            # * Append lines to children for sprouts.
            for c_rev in branch_revs:
                rev = c_rev.rev
                
                if rev.merged_by is not None:
                    merged_by_c_rev = c_revisions[rev.merged_by]
                    if merged_by_c_rev:
                        merged_by_max_col_index = max(
                            merged_by_max_col_index, merged_by_c_rev.col_index)
                
                parents = [self.revid_rev[parent_revid] for parent_revid in 
                           self.known_graph.get_parent_keys(rev.revid)]
                
                twisty_hidden_parents = []
                # Find and add necessary twisties
                for parent in parents:
                    if parent.branch_id == branch_id:
                        continue
                    if parent.branch_id == ():
                        continue
                    if parent.branch_id in branch_line.merged_by:
                        continue
                    parent_branch = self.branch_lines[parent.branch_id]
                    # Does this branch have any visible revisions
                    pb_visible = (parent_branch.branch_id in
                                  state.branch_line_state)
                    for pb_rev in parent_branch.revs:
                        if pb_visible:
                            visible = c_revisions[pb_rev.index] is not None
                        else:
                            visible = state\
                                .get_revision_visible_if_branch_visible(pb_rev)
                        if visible:
                            (c_rev.twisty_expands_branch_ids
                             .append(parent_branch.branch_id))
                            if not pb_visible:
                                twisty_hidden_parents.append(parent.index)
                            break
                
                # Work out if the twisty needs to show a + or -. If all
                # twisty_branch_ids are visible, show - else +.
                if len(c_rev.twisty_expands_branch_ids) > 0:
                    c_rev.twisty_state = True
                    for twisty_branch_id in c_rev.twisty_expands_branch_ids:
                        if not twisty_branch_id in state.branch_line_state:
                            c_rev.twisty_state = False
                            break
                
                # Don't include left hand parents All of these parents in the
                # branch can be drawn with one line.
                parents = parents[1:]
                
                branch_id_sort_key = self.branch_id_sort_key(branch_id)
                for i, parent in enumerate(parents):
                    parent_info = find_visible_parent(c_rev, parent,
                                                      twisty_hidden_parents)
                    if parent_info:
                        c_rev, parent_c_rev, direct = parent_info
                        if (last_parent and
                            parent_c_rev.f_index <= last_parent[1].f_index and
                            self.branch_id_sort_key(parent_c_rev.rev.branch_id)
                            < branch_id_sort_key):
                            # This line goes before the branch line
                            dest = branch_rev_visible_parents_pre
                        else:
                            # This line goes after
                            dest = branch_rev_visible_parents_post
                        
                        line_len = parent_c_rev.f_index - c_rev.f_index
                        if line_len == 1:
                            group_key = None
                        else:
                            group_key = parent_c_rev.rev.branch_id
                        
                        dest.append(([parent_info],
                                     c_rev.f_index,
                                     parent_c_rev.f_index,
                                     group_key))
                
                # This may be a sprout. Add line to first visible child
                if c_rev.rev.merged_by is not None:
                    merged_by = self.revisions[c_rev.rev.merged_by]
                    if c_revisions[merged_by.index] is None and\
                       branch_revs[0].f_index == c_rev.f_index:
                        # The revision that merges this revision is not
                        # visible, and it is the first visible revision in
                        # the branch line. This is a sprout.
                        #
                        # XXX What if multiple merges with --force,
                        # aka octopus merge?
                        #
                        # Search until we find a descendant that is visible.
                        
                        while merged_by is not None and \
                              c_revisions[merged_by.index] is None:
                            if merged_by.merged_by is not None:
                                merged_by = self.revisions[merged_by.merged_by]
                            else:
                                merged_by = None
                        
                        if merged_by is not None:
                            # Ensure only one line to a descendant.
                            if (merged_by.index not in sprout_with_lines):
                                sprout_with_lines[merged_by.index] = True
                                parent = c_revisions[merged_by.index]
                                if parent is not None:
                                    if c_rev.f_index - parent.f_index == 1:
                                        col_index = None
                                    else:
                                        col_search_order = line_col_search_order(
                                            parent.col_index, c_rev.col_index)
                                        col_index = find_free_column(
                                            col_search_order,
                                            parent.f_index, c_rev.f_index)
                                    append_line(parent, c_rev, False,
                                                col_index)
            
            # Find a column for this branch.
            #
            # Find the col_index for the direct parent branch. This will
            # be the starting point when looking for a free column.
            
            append_branch_parent_lines(branch_rev_visible_parents_pre)
            
            if branch_id == ():
                start_col_index = 0
            else:
                start_col_index = 1
            
            if last_parent and last_parent[0].col_index is not None:
                parent_col_index = last_parent[1].col_index
                start_col_index = max(start_col_index, parent_col_index)
            
            start_col_index = max(start_col_index, merged_by_max_col_index)
            
            col_search_order = branch_line_col_search_order(start_col_index) 
            
            if last_parent:
                col_index = find_free_column(col_search_order,
                                             branch_revs[0].f_index,
                                             last_parent[1].f_index)
            else:
                col_index = find_free_column(col_search_order,
                                             branch_revs[0].f_index,
                                             branch_revs[-1].f_index)
            
            # Free column for this branch found. Set node for all
            # revision in this branch.
            for rev in branch_revs:
                rev.col_index = col_index
            
            append_line(branch_revs[0], branch_revs[-1], True, col_index)
            if last_parent:
                append_line(last_parent[0], last_parent[1],
                            last_parent[2], col_index)
            
            branch_rev_visible_parents_post.reverse()
            append_branch_parent_lines(branch_rev_visible_parents_post)
        
        # It has now been calculated which column a line must go into. Now
        # copy the lines in to computed_revisions.
        for (child, parent, line_col_index, direct) in lines:
            
            parent_color = parent.rev.color
            
            line_length = parent.f_index - child.f_index
            if line_length == 0:
                # Nothing to do
                pass
            elif line_length == 1:
                child.lines.append(
                    (child.col_index,
                     parent.col_index,
                     parent_color,
                     direct))
            else:
                # line from the child's column to the lines column
                child.lines.append(
                    (child.col_index,
                     line_col_index,
                     parent_color,
                     direct))
                # lines down the line's column
                for line_part_f_index in range(child.f_index + 1,
                                               parent.f_index - 1):
                    computed.filtered_revs[line_part_f_index].lines.append(
                        (line_col_index,
                         line_col_index,
                         parent_color,
                         direct))
                # line from the line's column to the parent's column
                computed.filtered_revs[parent.f_index - 1].lines.append(
                    (line_col_index,
                     parent.col_index,
                     parent_color,
                     direct))
        
        return computed
    
    def get_revid_branch_info(self, revid):
        """This returns a branch info whos branch contains the revision.
        
        If the revision exists more than one branch, it will only return the
        first branch info. """
        
        if revid in self.ghosts:
            raise GhostRevisionError(revid)
        
        if len(self.branches) == 1 or revid not in self.revid_branch_info:
            return self.branches[0]
        return self.revid_branch_info[revid]
    
    def get_revid_branch(self, revid):
        return self.get_revid_branch_info(revid).branch
    
    def get_revid_repo(self, revid):
        return self.get_revid_branch_info(revid).branch.repository
    
    def get_repo_revids(self, revids):
        """Returns list of tuple of (repo, revids)"""
        repo_revids = {}
        for repo in self.repos:
            repo_revids[repo.base] = []
        
        for local_repo_copy in self.local_repo_copies:
            for revid in self.repos[local_repo_copy].has_revisions(revids):
                revids.remove(revid)
                repo_revids[local_repo_copy].append(revid)
        
        for revid in revids:
            try:
                repo = self.get_revid_repo(revid)
            except GhostRevisionError:
                pass
            else:
                repo_revids[repo.base].append(revid)
        
        return [(repo, repo_revids[repo.base])
                for repo in self.repos]
    
    def load_revisions(self, revids):
        return_revisions = {}
        for repo, revids in self.get_repo_revids(revids):
            if revids:
                repo.lock_read()
                try:
                    self.update_ui()
                    for rev in repo.get_revisions(revids):
                        return_revisions[rev.revision_id] = rev
                finally:
                    repo.unlock()
        return return_revisions


def repo_is_local(repo):
    return isinstance(repo.bzrdir.transport, LocalTransport)

def group_overlapping(groups):
    """ Groups items with overlapping ranges together.
    
    :param groups: List of uncollapsed groups.
    :param group: (start of range, end of range, items in group)
    :return: List of collapsed groups.
    
    """

    has_change = True
    while has_change:
        has_change = False
        a = 0
        while a < len(groups):
            inner_has_change = False
            items_a, start_a, end_a, group_key_a = groups[a]
            if group_key_a is not None:
                b = a + 1
                while b < len(groups):
                    items_b, start_b, end_b, group_key_b = groups[b]
                    if (group_key_a == group_key_b and
                        range_overlaps(start_a, end_a, start_b, end_b)):
                            # overlaps. Merge b into a
                            items_a.extend(items_b)
                            start_a = min(start_a, start_b)
                            end_a = max(end_a, end_b)
                            del groups[b]
                            has_change = True
                            inner_has_change = True
                    else:
                        b += 1
                if inner_has_change:
                    groups[a] = (items_a, start_a, end_a, group_key_a)
            a += 1
    
    return groups

def range_overlaps (start_a, end_a, start_b, end_b):
    """Tests if two ranges overlap."""
    return (start_b < start_a < end_b or
            start_b < end_a < end_b or
            (start_a <= start_b and end_a >= end_b))


class PendingMergesGraphVizLoader(GraphVizLoader):
    """GraphVizLoader that only loads pending merges.
    
    As only the pending merges are passed to merge_sort, the revno
    are incorrect, and should be ignored.
    
    Only works on a single branch.
    
    """
    
    def load_graph_parents(self):
        if not len(self.branches) == 1 or not len(self.repos) == 1:
            AssertionError("load_graph_pending_merges should only be called \
                           when 1 branch and repo has been opened.")
        
        bi = self.branches[0]
        if bi.tree is None:
            AssertionError("PendingMergesGraphVizLoader must have a working "
                           "tree.")
        
        self.graph = bi.branch.repository.get_graph()
        tree_heads = bi.tree.get_parent_ids()
        other_revisions = [tree_heads[0], ]
        self.update_ui()
        
        self.append_head_info('root:', bi, None)
        pending_merges = []
        for head in tree_heads[1:]:
            self.append_head_info(head, bi, None)
            pending_merges.extend(
                self.graph.find_unique_ancestors(head, other_revisions))
            other_revisions.append(head)
            self.update_ui()
        
        graph_parents = self.graph.get_parent_map(pending_merges)
        graph_parents["root:"] = ()
        self.update_ui()
        
        for (revid, parents) in graph_parents.items():
            new_parents = []
            for index, parent in enumerate(parents):
                if parent in graph_parents:
                    new_parents.append(parent)
                elif index == 0:
                    new_parents.append("root:")
            graph_parents[revid] = tuple(new_parents)
        
        return ["root:", ] + tree_heads[1:], graph_parents.items()


class WithWorkingTreeGraphVizLoader(GraphVizLoader):
    """
    GraphVizLoader that shows uncommitted working tree changes as a node
    in the graph, as if it was already committed.
    """
    
    def tree_revid(self, tree):
        return CURRENT_REVISION + tree.basedir.encode('unicode-escape')
    
    def load(self):
        self.working_trees = {}
        for bi in self.branches:
            if not bi.tree is None:
                self.working_trees[self.tree_revid(bi.tree)] = bi.tree
        
        super(WithWorkingTreeGraphVizLoader, self).load()
    
    def load_branch_heads(self, bi):
        # returns load_heads, sort_heads and also calls append_head_info.
        #
        # == For branch with tree ==
        # Graph                   | load_heads | sort_heads | append_head_info
        # wt                      | No         | Yes        | Yes   
        # | \                     |            |            |
        # | 1.1.2 pending merge   | Yes        | No         | Yes
        # 2 |     basis rev       | Yes        | No         | Yes
        #
        # == For branch with tree not up to date ==
        # Graph                   | load_heads | sort_heads | append_head_info
        #   wt                    | No         | Yes        | Yes   
        #   | \                   |            |            |
        #   | 1.1.2 pending merge | Yes        | No         | Yes
        # 3/  |     branch tip    | Yes        | Yes        | Yes      
        # 2   |     basis rev     | Yes        | No         | No
        #
        # == For branch without tree ==
        # branch tip              | Yes        | head       | yes
        
        load_heads = []
        sort_heads = []
        extra_parents = []
        
        if len(self.branches) > 0:
            label = bi.label
        else:
            label = None
        
        branch_last_revision = bi.branch.last_revision()
        self.append_head_info(branch_last_revision, bi, bi.label)
        load_heads.append(branch_last_revision)
        self.update_ui()
        
        if bi.tree:
            wt_revid = self.tree_revid(bi.tree)
            if label:
                wt_label = "%s - Working Tree" % label
            else:
                wt_label = "Working Tree"
            self.append_head_info(wt_revid, bi, wt_label)
            parent_ids = bi.tree.get_parent_ids()
            
            extra_parents.append((wt_revid, parent_ids))
            load_heads.extend(parent_ids)
            
            if parent_ids:
                # first parent is last revision of the tree
                if parent_ids[0] != branch_last_revision:
                    # tree is not up to date.
                    sort_heads.append(branch_last_revision)
                
                # other parents are pending merges
                for revid in parent_ids[1:]:
                    if label:
                        pm_label = "%s - Pending Merge" % label
                    else:
                        pm_label = "Pending Merge"
                    self.append_head_info(revid, bi, pm_label)
            
            sort_heads.append(wt_revid)
            self.update_ui()
        else:
            sort_heads.append(branch_last_revision)
        
        return load_heads, sort_heads, extra_parents


class GraphVizFilterState(object):
    """
    Records the state of which branch lines are expanded, and what filters
    are applied.
    """
    
    def __init__(self, graph_viz, filter_changed_callback=None):
        self.graph_viz = graph_viz
        self.filter_changed_callback = filter_changed_callback
        
        self.branch_line_state = {}
        "If a branch_id is in this dict, it is visible. The value of the dict "
        "indicates which branches expanded this branch."
        
        for revid in self.graph_viz.revid_head_info:
            rev = self.graph_viz.revid_rev[revid]
            self.branch_line_state[rev.branch_id] = None
        
        self.filters = []
        
        # This keeps a cache of the filter state so that when one of the
        # filters notifies us of a change, we can check if anything did change.
        
        self.filter_cache = [None for rev in self.graph_viz.revisions]
    
    def get_filtered_revisions(self):
        if self.graph_viz.no_graph:
            rev_whos_branch_is_visible = self.graph_viz.revisions
        else:
            rev_whos_branch_is_visible = []
            for branch_id in self.branch_line_state.iterkeys():
                try:
                    branch_line = self.graph_viz.branch_lines[branch_id]
                except KeyError:
                    continue
                rev_whos_branch_is_visible.extend(branch_line.revs)
            rev_whos_branch_is_visible.sort(key=lambda rev: rev.index)
        
        visible = self.get_revision_visible_if_branch_visible
        return (rev for rev in rev_whos_branch_is_visible if visible(rev))
    
    def get_revision_visible_if_branch_visible(self, rev):
        rev_filter_cache = self.filter_cache[rev.index]
        if rev_filter_cache is None:
            rev_filter_cache = \
                self._get_revision_visible_if_branch_visible(rev)
            self.filter_cache[rev.index] = rev_filter_cache
        return rev_filter_cache
    
    def _get_revision_visible_if_branch_visible(self, rev):
        filters_value = True
        for filter in self.filters:
            if not filter.get_revision_visible(rev):
                filters_value = False
                break
        if filters_value:
            return True
        
        if not self.graph_viz.no_graph:
            for merged_index in rev.merges:
                merged_rev = self.graph_viz.revisions[merged_index]
                if self.get_revision_visible_if_branch_visible(merged_rev):
                    return True
        
        return False
    
    def filter_changed(self, revs=None, last_call=True):
        if revs is None:
            self.filter_cache = [None for rev in self.graph_viz.revisions]
            if self.filter_changed_callback:
                self.filter_changed_callback()
        else:
            pending_revs = revs
            processed_revs = set()
            prev_cached_revs = []
            while pending_revs:
                rev = pending_revs.pop(0)
                if rev in processed_revs:
                    continue
                processed_revs.add(rev)
                
                rev_filter_cache = self.filter_cache[rev.index]
                
                if rev_filter_cache is not None:
                    prev_cached_revs.append((rev, rev_filter_cache))
                self.filter_cache[rev.index] = None
                
                if not self.graph_viz.no_graph:
                    if rev.merged_by is not None:
                        pending_revs.append(
                            self.graph_viz.revisions[rev.merged_by])
           
            # Check if any visibilities have changes. If they have, call
            # filter_changed_callback
            for rev, prev_visible in prev_cached_revs:
                visible = self.get_revision_visible_if_branch_visible(rev)
                if visible != prev_visible:
                    if self.filter_changed_callback:
                        self.filter_changed_callback()
                    break
    
    def ensure_rev_visible(self, rev):
        if self.graph_viz.no_graph:
            return False
        
        branch_id = rev.branch_id
        if branch_id not in self.branch_line_state:
            self.branch_line_state[branch_id] = None
            if self.filter_changed_callback:
                self.filter_changed_callback()
            return True
        return False
    
    def collapse_expand_rev(self, c_rev):
        if c_rev is None:
            return False
        visible = not c_rev.twisty_state
        branch_ids = zip(
            c_rev.twisty_expands_branch_ids,
            [c_rev.rev.branch_id] * len(c_rev.twisty_expands_branch_ids))
        
        seen_branch_ids = set(branch_id
                              for branch_id, expanded_by in branch_ids)
        has_change = False
        while branch_ids:
            branch_id, expanded_by = branch_ids.pop()
            if (branch_id in self.branch_line_state) != visible:
                has_change = True
            if not visible:
                del self.branch_line_state[branch_id]
                parents = self.graph_viz.branch_lines[branch_id].merges
                for parent_branch_id in parents:
                    parent_visible = parent_branch_id in self.branch_line_state
                    if (not parent_visible or 
                        parent_branch_id in seen_branch_ids):
                        continue
                    
                    if self.branch_line_state[parent_branch_id] == branch_id:
                        # This branch expanded the parent branch, so we must
                        # collapse it.
                        branch_ids.append((parent_branch_id, branch_id))
                        seen_branch_ids.add(parent_branch_id)
                    else:
                        # Check if this parent has any other visible branches
                        # that merge it.
                        has_visible = False
                        parent = self.graph_viz.branch_lines[parent_branch_id]
                        for merged_by_branch_id in parent.merged_by:
                            if merged_by_branch_id in self.branch_line_state:
                                has_visible = True
                                break
                        if not has_visible:
                            branch_ids.append((parent_branch_id, branch_id))
                            seen_branch_ids.add(parent_branch_id)
            else:
                self.branch_line_state[branch_id] = expanded_by
        if has_change and self.filter_changed_callback:
            self.filter_changed_callback()
    
    def expand_all_branch_lines(self):
        for branch_id in self.graph_viz.branch_lines.keys():
            if branch_id not in self.branch_line_state:
                self.branch_line_state[branch_id] = None
    

class FileIdFilter (object):
    """
    Filter that only shows revisions that modify one of the specified files.
    """
    
    def __init__(self, graph_viz, filter_changed_callback, file_ids):
        self.graph_viz = graph_viz
        self.filter_changed_callback = filter_changed_callback
        self.file_ids = file_ids
        self.has_dir = False
        self.filter_file_id = [False for rev in self.graph_viz.revisions]
        
        # don't filter working tree nodes
        if isinstance(self.graph_viz, WithWorkingTreeGraphVizLoader):
            for wt_revid in self.graph_viz.working_trees.iterkeys():
                try:
                    rev_index = self.graph_viz.revid_rev[wt_revid].index
                    self.filter_file_id[rev_index] = True
                except KeyError:
                    pass
        
    
    def uses_inventory(self):
        return self.has_dir
    
    def load(self, revids=None):
        """Load which revisions affect the file_ids"""
        if self.file_ids:
            self.graph_viz.throbber_show()
            
            for bi in self.graph_viz.branches:
                tree = bi.tree
                if tree is None:
                    tree = bi.branch.basis_tree()
                
                tree.lock_read()
                try:
                    for file_id in self.file_ids:
                        if tree.kind(file_id) in ('directory',
                                                  'tree-reference'):
                            self.has_dir = True
                            break
                    if self.has_dir:
                        break
                finally:
                    tree.unlock()
            
            if revids is None:
                revids = [rev.revid for rev in self.graph_viz.revisions]
            revids = [revid for revid in revids
                      if not revid.startswith(CURRENT_REVISION)]
            
            for repo, revids in self.graph_viz.get_repo_revids(revids):
                if self.uses_inventory():
                    chunk_size = 200
                else:
                    chunk_size = 500
                
                for start in xrange(0, len(revids), chunk_size):
                    self.load_filter_file_id_chunk(repo, 
                            revids[start:start + chunk_size])
            
            self.load_filter_file_id_chunk_finished()
    
    def load_filter_file_id_chunk(self, repo, revids):
        def check_text_keys(text_keys):
            changed_revs = []
            for file_id, revid in repo.texts.get_parent_map(text_keys):
                rev = self.graph_viz.revid_rev[revid]
                self.filter_file_id[rev.index] = True
                changed_revs.append(rev)
            
            self.graph_viz.update_ui()
            self.filter_changed_callback(changed_revs, False)
            self.graph_viz.update_ui()
        
        repo.lock_read()
        try:
            if not self.uses_inventory():
                text_keys = [(file_id, revid) 
                                for revid in revids
                                for file_id in self.file_ids]
                check_text_keys(text_keys)
            else:
                text_keys = []
                # We have to load the inventory for each revisions, to find
                # the children of any directories.
                for inv, revid in izip(repo.iter_inventories(revids), revids):
                    entries = inv.iter_entries_by_dir(
                                         specific_file_ids=self.file_ids)
                    for path, entry in entries:
                        text_keys.append((entry.file_id, revid))
                        if entry.kind == "directory":
                            sub_entries = inv.iter_entries(from_dir=entry)
                            for rc_path, rc_entry in sub_entries:
                                text_keys.append((rc_entry.file_id, revid))
                    
                    self.graph_viz.update_ui()
                
                check_text_keys(text_keys)
        finally:
            repo.unlock()

    def load_filter_file_id_chunk_finished(self):
        self.filter_changed_callback([], True)
        self.graph_viz.throbber_hide()
    
    def get_revision_visible(self, rev):
        return self.filter_file_id[rev.index]


class WorkingTreeHasChangeFilter(object):
    """
    Filter out working trees that don't have any changes.
    """
    
    def __init__(self, graph_viz, filter_changed_callback, file_ids):
        self.graph_viz = graph_viz
        self.file_ids = file_ids
        if not isinstance(graph_viz, WithWorkingTreeGraphVizLoader):
            raise TypeError('graph_viz expected to be a '
                            'WithWorkingTreeGraphVizLoader')
        self.filter_changed_callback = filter_changed_callback
        self.tree_revids_with_changes = set()
    
    def load(self):
        """Load if the working trees have changes."""
        self.tree_revids_with_changes = set()
        self.graph_viz.throbber_show()
        try:
            for wt_revid, tree in self.graph_viz.working_trees.iteritems():
                if self.has_changes(tree):
                    self.tree_revids_with_changes.add(wt_revid)
                rev = self.graph_viz.revid_rev[wt_revid]
                self.filter_changed_callback([rev], False)
            self.filter_changed_callback([], True) 
        finally:
            self.graph_viz.throbber_hide()

    def has_changes(self, tree):
        """Quickly check that the tree contains at least one commitable change.

        :param _from_tree: tree to compare against to find changes (default to
            the basis tree and is intended to be used by tests).

        :return: True if a change is found. False otherwise
        """
        tree.lock_read()
        try:
            # Copied from mutabletree, cause we need file_ids too.
            # Check pending merges
            if len(tree.get_parent_ids()) > 1:
                return True
            from_tree = tree.basis_tree()
            
            specific_files = None
            if self.file_ids:
                specific_files = [tree.id2path(file_id)
                                  for file_id in self.file_ids]
            
            changes = tree.iter_changes(from_tree,
                                        specific_files=specific_files)
            try:
                change = changes.next()
                # Exclude root (talk about black magic... --vila 20090629)
                if change[4] == (None, None):
                    change = changes.next()
                return True
            except StopIteration:
                # No changes
                return False
        finally:
            tree.unlock()
    
    def get_revision_visible(self, rev):
        if rev.revid.startswith(CURRENT_REVISION):
            return rev.revid in self.tree_revids_with_changes
        else:
            return True


class ComputedRevisionData(object):
    """Container for computed layout data for a revision.
    
    :ivar rev: Reference to RevisionData. Use to get revno, revid, color and
        others.
    :ivar f_index: Index in `ComputedGraphViz.filtered_revs`.
    :ivar col_index: Column index to place node for revision in.
    :ivar lines: Lines that need to be drawn from from this revision's line to
        the next revision's line. Note that not all these lines relate to this
        revision, but be a part of a longer line that is passing this revision.
        
        Each line is a tuple of `(end col_index, start col_index, color,
        direct)`.
        
        If direct is False, it indicates that this line represents an
        ancestry, with revisions that are filtered. This should be shown as
        a dotted line.
        
    :ivar branch_labels: Labels for branch tips.
    :ivar twisty_state: State of the revision:
        
        * None: No twisty.
        * True: There are branch lines that this revision merges that can
          expanded. Show a '+'.
        * False: All branches that this revision merges are already expanded.
          Show a '-'.
    :ivar twisty_expands_branch_ids: Branch lines that will be expanded if the
        twisty is clicked.
    """
    
    # Instance of this object are typically named "c_rev".    
    __slots__ = ['rev', 'f_index', 'lines', 'col_index', 'branch_labels',
                 'twisty_state', 'twisty_expands_branch_ids']
    
    def __init__(self, rev):
        self.rev = rev
        self.lines = []
        self.col_index = None
        self.twisty_state = None
        self.twisty_expands_branch_ids = []
        self.branch_labels = []


class ComputedGraphViz(object):
    """Computed layout data for a graph.
    
    :ivar graph_viz: Reference to parent `GraphVizLoader`. 
    :ivar filtered_revs: List `ComputedRevisionData`. Only visible revisions
        are included.
    :ivar revisions: List `ComputedRevisionData`. Revision that are not
        visible are None.
    """
    def __init__(self, graph_viz):
        self.graph_viz = graph_viz
        self.filtered_revs = []
        self.revisions = [None for i in xrange(len(graph_viz.revisions))]
