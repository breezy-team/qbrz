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

import fnmatch
import gc
from time import clock

from bzrlib import errors
from bzrlib.transport.local import LocalTransport
from bzrlib.revision import NULL_REVISION, CURRENT_REVISION
from bzrlib.graph import (Graph, StackedParentsProvider, KnownGraph)
    
from bzrlib.workingtree import WorkingTree
from bzrlib.plugins.qbzr.lib.lazycachedrevloader import (load_revisions,
                                                         cached_revisions)
from bzrlib.plugins.qbzr.lib.util import get_apparent_author



class BranchInfo(object):
    """Holds a branch and related information"""
    
    # Instance of this object are typicaly named "bi".
    
    def __init__ (self, label, tree, branch, index=None):
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


class RevisionCache(object):
    """Holds information about a revision that can be cached."""
    
    # Instance of this object are typicaly named "rev_cache".
    
    __slots__ = ["index", "_merge_sort_node", "branch", "_revno_str", 
                 "merges", "merged_by", ]
    def __init__ (self, index, _merge_sort_node):
        self.index = index
        """Index in LogGraphProvider.revisions"""
        self._merge_sort_node = _merge_sort_node
        self.branch = None
        self._revno_str = None
        self.merges = []
        """Revision indexes that this revision merges"""
        self.merged_by = None
        """Revision index that merges this revision."""
    
    revid = property(lambda self: self._merge_sort_node.key)
    merge_depth = property(lambda self: self._merge_sort_node.merge_depth)
    revno_sequence = property(lambda self: self._merge_sort_node.revno)
    end_of_merge = property(lambda self: self._merge_sort_node.end_of_merge)
    branch_id = property(lambda self: self.revno_sequence[0:-1])
    
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

class GhostRevisionError(errors.InternalBzrError):

    _fmt = "{%(revision_id)s} is a ghost."

    def __init__(self, revision_id):
        errors.BzrError.__init__(self)
        self.revision_id = revision_id

class BranchLine(object):
    __slots__ = ["branch_id", "revs", "merges", "merged_by",
                 "color", "merge_depth"]
    
    def __init__(self, branch_id):
        self.branch_id = branch_id
        self.revs = []
        self.merges = []
        self.merged_by = []
        self.color = reduce(lambda x, y: x+y, self.branch_id, 0)
        self.merge_depth = 0

    def __repr__(self):
        return "%s <%s>" % (self.__class__.__name__, self.branch_id)


class LogGraphProvider(object):
    """Loads and computes revision and graph data for GUI log widgets."""
    
    # Most list/dicts related to revisions are unfiltered. When we do a graph
    # layout, we filter these revisions. A revision may be filter out because:
    # * It's branch is hidden (or collapsed).
    # * We have a sepcified file_id(s), and the revision does not touch the
    #   file_id(s).
    # * We have a search, and the revision does not match the search.
    #
    # The main list of unfiltered revisions is self.revisions. A revisions index
    # in revisions are normaly called index. The main list of filtered revisions
    # is filtered_revs. Revision indexes in this list are called f_index.
    
    def __init__(self, branches, primary_bi, no_graph):
        self.branches = branches
        """List of BranchInfo for each branch."""
        self.primary_bi = primary_bi
        self.no_graph = no_graph
        
        self.repos = list(set([bi.branch.repository for bi in branches]))
        self.local_repo_copies = []
        """A list of repositories that revisions will be aptempted to be loaded        
        from first."""
        
        no_local_repos = True
        for repo in self.repos:
            repo.is_local = isinstance(repo.bzrdir.transport, LocalTransport)
            if repo.is_local:
                no_local_repos = False
        if no_local_repos:
            self.load_current_dir_repo()
        self.repos.sort(key=lambda repo: repo.is_local)
        
        self.revid_head_info = {}
        """Dict with a keys of head revid and value of
            (list of (branch, label),
             list of revids that are unique to this head)
            
            We can't just store the BranchInfo, because the label may have
            have addition text in it, e.g. "Working Tree", "Pending Merges"
        """
        
        self.revid_branch_info = {}
        
        self.branch_labels = {}
        """Dict of revid to a list of branch tags. Depends on which revisions
        are visible."""
        
        self.ghosts = set()
        
        self.revisions = []
        """List of RevisionInfo from merge_sort."""
        
        self.revid_rev = {}
        self.graph_children = {}
        
        self.tags = {}      # map revid -> tags set
    
    def load(self):
        self.lock_read_branches()
        try:
            if len(self.repos)==1:
                self.graph = self.repos[0].get_graph()
            else:
                parents_providers = [repo._make_parents_provider() \
                                     for repo in self.repos]
                self.graph = Graph(StackedParentsProvider(parents_providers))
            
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
        # of the current directory, and try load revsions data from
        # this before trying from remote repositories. This makes
        # the common use case of viewing a remote branch that is
        # related to the current branch much faster, because most
        # of the revision can be loaded from the local repoistory.
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
            branch_tags = bi.branch.tags.get_reverse_tag_dict()  # revid to tags map
            for revid, tags in branch_tags.iteritems():
                if revid in self.tags:
                    self.tags[revid].update(set(tags))
                else:
                    self.tags[revid] = set(tags)

    def append_head_info(self, revid, branch_info, tag):
        if not revid==NULL_REVISION:
            if not revid in self.revid_head_info:
                self.revid_head_info[revid] = ([],[])
            self.revid_head_info[revid][0].append ((branch_info, tag))
            
            # So that early calls to get_revid_branch work
            self.revid_branch_info[revid] = branch_info

    def load_branch_heads(self, bi):
        branch_heads = []
        def append_head_info(revid, branch_info, label):
            self.append_head_info(revid, branch_info, label)
            branch_heads.append(revid)
        
        if len(self.branches)>0:
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
                        wt_label =  "%s - Working Tree" % label
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
        
        extra_parents = []
        branches_heads = []
        
        def load_branch_heads(bi, insert_at_begin=False):
            load_heads, sort_heads, extra_parents_ = self.load_branch_heads(bi)
            extra_parents.extend(extra_parents_)
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
        
        def parents_iter():
            for parents in extra_parents:
                yield parents
            for parents in self.graph.iter_ancestry(load_heads):
                yield parents
        
        return sort_heads, parents_iter()
    
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
            if len(graph_parents) % 100 == 0 :
                self.update_ui()
        
        graph_parents["top:"] = head_revids

        if len(graph_parents)>0:
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
            self.revisions = [RevisionCache(index, node)
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
        
    def compute_branch_lines(self):
        self.branch_lines = {}
        
        """A list of branch lines (aka merge lines).
        
        For a revisions, the revsion number less the least significant
        digit is the branch_id, and used as the key for the dict. Hence
        revision with the same revsion number less the least significant
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
            branch_line.merge_depth = max(rev.merge_depth, branch_line.merge_depth)
        
        self.branch_ids = self.branch_lines.keys()
        
        def branch_id_sort_key(x):
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
            # Otherwise, thoes with a greater mainline parent revno should
            # appear to the left.
            
            if len(x)==0:
                return (merge_depth)
            else:
                return (merge_depth, -x[0], x[1])
        
        self.branch_ids.sort(key=branch_id_sort_key)
    
    def compute_merge_info(self):
        
        def set_merged_by(rev, merged_by, merged_by_rev, do_branches=False):
            if merged_by is not None:
                if merged_by_rev is None:
                    merged_by_rev = self.revisions[merged_by]
                rev.merged_by = merged_by
                merged_by_rev.merges.append(rev.index)
                
                if do_branches:
                    branch_id = rev.branch_id
                    merged_by_branch_id = self.revisions[merged_by].branch_id
                    
                    if not branch_id in self.branch_lines[merged_by_branch_id].merges:
                        self.branch_lines[merged_by_branch_id].merges.append(branch_id)
                    if not merged_by_branch_id in self.branch_lines[branch_id].merged_by:
                        self.branch_lines[branch_id].merged_by.append(merged_by_branch_id)
        
        for rev in self.revisions:
            
            parents = [self.revid_rev[parent] for parent in
                       self.known_graph.get_parent_keys(rev.revid)]
            
            if len(parents) > 0:
                if rev.branch_id == parents[0].branch_id:
                    set_merged_by(parents[0], rev.merged_by, None)
            
            for parent in parents[1:]:
                if rev.merge_depth<=parent.merge_depth:
                    set_merged_by(parent, rev.index, rev, do_branches=True)
        
    def compute_head_info(self):
        def get_revid_head(heads):
            map = {}
            for i in xrange(len(heads)):
                prev_revids = [revid for revid, head in heads[:i]]
                for ancestor_revid in self.graph.find_unique_ancestors(heads[i][0],
                                                                prev_revids):
                    map[ancestor_revid] = heads[i][1]
            return map
        
        if len(self.branches) > 1:
            head_revid_branch_info = sorted([(revid, branch_info) \
                                       for revid, (head_info, ur) in \
                                       self.revid_head_info.iteritems()
                                       for (branch, tag) in head_info],
                key = lambda x: x[1].repository.is_local)
            self.revid_branch_info = get_revid_head(head_revid_branch)
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
                    other_revids = [self.known_graph.get_parent_keys(merged_by_revid)[0]]
                else:
                    other_revids = [other_revid for other_revid \
                        in self.revid_head_info.iterkeys() \
                        if not other_revid == revid]
                ur.append(revid)
                ur.extend([revid for revid \
                    in self.graph.find_unique_ancestors(revid, other_revids) \
                    if not revid == NULL_REVISION and revid in self.revid_rev])
                ur.sort(key=lambda x: self.revid_rev[x].index)
    
    
    def compute_graph_lines(self, state):
        """Recompute the layout of the graph, and store the results in
        self.revision"""
        
        # Overview:
        # Work out which revision need to be displayed.
        # Create ComputedGraph and ComputedRevision objects
        # Assign columns for branches, and lines that go between branches.
        #   These are intermingled, because some of the lines need to come
        #   before it's branch, and others need to come after. Other lines
        #   (such a the line from the last rev in a branch) are treated a
        #   special cases.
        # Return ComputedGraph object
        
        for rev in self.filtered_revs:
            rev.f_index = None
            rev.col_index = None
            rev.lines = []
            rev.twisty_state = None
            rev.twisty_branch_ids = []
        
        self.filtered_revs = []
        
        # This is a performance hack. The code will work without it, but will be
        # slower.
        if self.no_graph:
            rev_whos_branch_is_visible = self.revisions
        else:
            rev_whos_branch_is_visible = []
            for branch_line in self.branch_lines.itervalues():
                if branch_line.visible:
                    rev_whos_branch_is_visible.extend(branch_line.revs)
            rev_whos_branch_is_visible.sort(key=lambda rev: rev.index)
        
        # The following commented line would be use without the above
        # performance hack.
        #for index in xrange(0,len(self.revisions)):
        for rev in rev_whos_branch_is_visible:
            # The following would use just get_revision_visible without the
            # above performance hack.
            if self.get_revision_visible_if_branch_visible_cached(rev.index): 
                rev.f_index = len(self.filtered_revs)
                self.filtered_revs.append(rev)
        
        if self.no_graph:
            return
        
        # This will hold a tuple of (child_index, parent_index, col_index,
        # direct) for each line that needs to be drawn. If col_index is not
        # none, then the line is drawn along that column, else the the line can
        # be drawn directly between the child and parent because either the
        # child and parent are in the same branch line, or the child and parent
        # are 1 row apart.
        lines = []
        lines_by_column = []
        lines_by_parent_can_overlap = {}
        
        def branch_line_col_search_order(parent_col_index):
            for col_index in range(parent_col_index, len(lines_by_column)):
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
            while max_index + i < len(lines_by_column) or \
                  min_index - i > -1:
                if max_index + i < len(lines_by_column):
                    yield max_index + i
                #if min_index - i > -1:
                #    yield min_index - i
                i += 1
        
        def is_col_free_for_range(col_index, child_f_index, parent_f_index,
                                  ignore_to_same_parent=False):
            col_lines = lines_by_column[col_index]
            has_overlaping_line = False
            for (line_child_f_index, line_parent_f_index) in col_lines:
                if (parent_f_index == line_parent_f_index
                                        and ignore_to_same_parent):
                    continue
                
                # child_f_index is in between or
                # parent_f_index is in between or
                # we compleatly overlap.
                if (
                        child_f_index > line_child_f_index
                    and
                        child_f_index < line_parent_f_index
                   ) or (
                        parent_f_index > line_child_f_index
                    and
                        parent_f_index < line_parent_f_index
                   ) or (
                        child_f_index <= line_child_f_index
                    and
                        parent_f_index >= line_parent_f_index
                   ):
                    has_overlaping_line = True
                    break
            return not has_overlaping_line
        
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
        
        def append_line (child, parent, direct, col_index=None):
            
            line_length = parent.f_index - child.f_index
            can_overlap = (col_index is None or not direct) \
                            and line_length > 1
            
            line_col_index = None
            if col_index is not None:
                line_col_index = col_index
            # Try find a line to a parent that we can overlap on.
            elif (not direct or col_index is None) \
                        and parent_f_index in lines_by_parent_can_overlap:
                # ol = overlaping line
                for (ol_child_f_index,
                     ol_col_index,
                     ol_direct) in lines_by_parent_can_overlap[parent_f_index]:
                    if ol_direct == direct \
                            and is_col_free_for_range(ol_col_index,
                                                      child_f_index,
                                                      parent_f_index,
                                                      True):
                        line_col_index = ol_col_index
                        break
            #else:
            if line_col_index is None:
                line_col_index = child.col_index
                if line_length > 1:
                    col_search_order = line_col_search_order(parent.col_index,
                                                             child.col_index)
                    line_col_index = find_free_column(col_search_order,
                                                      child.f_index,
                                                      parent.f_index)
            
            lines.append((child.f_index,
                          parent.f_index,
                          line_col_index,
                          direct,
                          ))
            if line_col_index is not None:
                lines_by_column[line_col_index].append(
                                            (child.f_index, parent.f_index))
            if can_overlap:
                if parent.f_index not in lines_by_parent_can_overlap:
                    lines_by_parent_can_overlap[parent.f_index] = []
                lines_by_parent_can_overlap[parent.f_index].append(
                    (child.f_index,
                    line_col_index,
                    direct ))
        
        for branch_id in self.branch_ids:
            branch_line = self.branch_lines[branch_id]
            
            if branch_line.visible:
                branch_revs = [rev for rev in branch_line.revs
                                    if rev.f_index is not None]
            else:
                branch_revs = []
                
            if branch_revs:
                # In this loop:
                # * Find visible parents.
                # * Populate twisty_branch_ids and twisty_state
                branch_rev_visible_parents = {}
                
                for rev in branch_revs:
                    # Find parents that are currently visible
                    rev_visible_parents = [] # List of (parent_rev, is_direct)
                    
                    parents = [self.revid_rev[parent_revid] for parent_revid in 
                               self.known_graph.get_parent_keys(rev.revid)]
                    # Don't include left hand parents (unless this is the last
                    # revision of the branch.) All of these parents in the
                    # branch can be drawn with one line.
                    last_in_branch = rev.index == branch_revs[-1].index
                    if not last_in_branch:
                        parents = parents[1:]
                    
                    twisty_hidden_parents = []
                    # Find and add nessery twisties
                    for parent in parents:
                        if parent.branch_id == branch_id:
                            continue
                        if parent.branch_id == ():
                            continue
                        if parent.branch_id in branch_line.merged_by:
                            continue
                        parent_branch = self.branch_lines[parent.branch_id]
                        # Does this branch have any visible revisions
                        for pb_rev in parent_branch.revs:
                            visible = pb_rev.f_index is not None or \
                                self.get_revision_visible_if_branch_visible_cached (pb_rev.index)
                            if visible:
                                rev.twisty_branch_ids.append (parent.branch_id)
                                parent_branch = self.branch_lines[parent.branch_id]
                                if not parent_branch.visible:
                                    twisty_hidden_parents.append(parent.index)
                                break
                    
                    # Work out if the twisty needs to show a + or -. If all
                    # twisty_branch_ids are visible, show - else +.
                    if len (rev.twisty_branch_ids)>0:
                        rev.twisty_state = True
                        for twisty_branch_id in rev.twisty_branch_ids:
                            if not self.branch_lines[twisty_branch_id].visible:
                                rev.twisty_state = False
                                break
                    
                    for i, parent in enumerate(parents):
                        if parent.f_index is not None:
                            rev_visible_parents.append((parent, True))
                        else:
                            if (parent.index in twisty_hidden_parents and
                                not (i==0 and last_in_branch)):
                                # no need to draw a line if there is a twisty,
                                # except if this is the last in the branch.
                                continue
                            # The parent was not visible. Search for a ansestor
                            # that is. Stop searching if we make a hop, i.e. we
                            # go away from our branch, and we come back to it.
                            has_seen_different_branch = False
                            while parent.f_index is None:
                                if not parent.branch_id == branch_id:
                                    has_seen_different_branch = True
                                # find grand parent.
                                g_parent_ids = self.known_graph.get_parent_keys(parent.revid)
                                
                                if len(g_parent_ids) == 0:
                                    parent = None
                                    break
                                else:
                                    parent = self.revid_rev[g_parent_ids[0]]
                                
                                if has_seen_different_branch and parent.branch_id == branch_id:
                                    # We have gone away and come back to our
                                    # branch. Stop.
                                    parent = None
                                    break
                            if parent:
                                rev_visible_parents.append((parent, False)) # Not Direct
                    branch_rev_visible_parents[rev.index]=rev_visible_parents
                
                # Find the first parent of the last rev in the branch line
                last_parent = None
                last_rev = branch_revs[-1]
                if branch_rev_visible_parents[last_rev.index]:
                    last_parent = branch_rev_visible_parents[last_rev.index].pop(0)
                
                children_with_sprout_lines = {}
                # In this loop:
                # * Append lines that need to go to parents before the branch
                #   (say inbetween the main line and the branch). Remove the
                #   ones we append from rev_visible_parents so they don't get
                #   added again later on.
                # * Append lines to chilren for sprouts.
                for rev in branch_revs:
                    rev_visible_parents = branch_rev_visible_parents[rev.index]
                    i = 0
                    while i < len(rev_visible_parents):
                        (parent, direct) = rev_visible_parents[i]
                        
                        if (rev.index <> last_rev.index or i > 0 )and \
                           branch_id <> () and \
                           self.branch_ids.index(parent.branch_id) <= self.branch_ids.index(branch_id) and\
                           (last_parent and not direct and last_parent[0].index >= parent.index or not last_parent or direct):
                            
                            if parent.f_index - rev.f_index >1:
                                rev_visible_parents.pop(i)
                                i -= 1
                                append_line(rev, parent, direct)
                        i += 1
                    
                    # This may be a sprout. Add line to first visible child
                    if rev.merged_by is not None:
                        merged_by = self.revisions[rev.merged_by]
                        if merged_by.f_index is None and\
                           rev.index == merged_by.merges[0]:
                            # The revision that merges this revision is not
                            # visible, and it is the first revision that is
                            # merged by that revision. This is a sprout.
                            #
                            # XXX What if multiple merges with --force,
                            # aka ocutpus merge?
                            #
                            # Search until we find a decendent that is visible.
                            
                            while merged_by is not None and \
                                  merged_by.f_index is None:
                                if merged_by.merged_by is not None:
                                    merged_by = self.revisions[merged_by.merged_by]
                                else:
                                    merged_by = None
                            
                            if merged_by is not None:
                                # Ensure only one line to a decendent.
                                if merged_by.index not in children_with_sprout_lines:
                                    children_with_sprout_lines[merged_by.index] = True
                                    if merged_by.f_index is not None:
                                        append_line(merged_by, rev, False)
                
                # Find a column for this branch.
                #
                # Find the col_index for the direct parent branch. This will
                # be the starting point when looking for a free column.
                
                parent_col_index = 0
                parent_f_index = None
                
                if last_parent and last_parent[0].col_index is not None:
                    parent_col_index = last_parent[0].col_index
                
                if not branch_id == ():
                    parent_col_index = max(parent_col_index, 1)
                
                col_search_order = branch_line_col_search_order(parent_col_index) 
                
                if last_parent:
                    col_index = find_free_column(col_search_order,
                                                 branch_revs[0].f_index,
                                                 last_parent[0].f_index)
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
                    append_line(branch_revs[-1], last_parent[0],
                                last_parent[1], col_index)
                
                # In this loop:
                # * Append the remaining lines to parents.
                for rev in reversed(branch_revs):
                    for (parent, direct) in branch_rev_visible_parents[rev.index]:
                        append_line(rev, parent, direct)
        
        # It has now been calculated which column a line must go into. Now
        # copy the lines in to graph_line_data.
        for (child_f_index,
             parent_f_index,
             line_col_index,
             direct,
             ) in lines:
            
            child = self.filtered_revs[child_f_index]
            parent = self.filtered_revs[parent_f_index]
            
            line_length = parent_f_index - child_f_index
            if line_length == 0:
                # Nothing to do
                pass
            elif line_length == 1:
                child.lines.append(
                    (child.col_index,
                     parent.col_index,
                     parent.color,
                     direct))
            else:
                # line from the child's column to the lines column
                child.lines.append(
                    (child.col_index,
                     line_col_index,
                     parent.color,
                     direct))
                # lines down the line's column
                for line_part_f_index in range(child_f_index+1, parent_f_index-1):
                    self.filtered_revs[line_part_f_index].lines.append(
                        (line_col_index,
                         line_col_index,
                         parent.color,
                         direct))
                # line from the line's column to the parent's column
                self.filtered_revs[parent.f_index-1].lines.append(
                    (line_col_index,
                     parent.col_index,
                     parent.color,
                     direct))
        
        self.branch_labels = {}
        for (revid, (head_info,
                     unique_revids)) in self.revid_head_info.iteritems():
            top_visible_revid = None
            
            for unique_revid in unique_revids:
                rev = self.revid_rev[unique_revid]
                if rev.f_index is not None:
                    top_visible_revid = unique_revid
                    break
            
            if top_visible_revid:
                self.branch_labels[top_visible_revid] = head_info

    def has_rev_id(self, revid):
        return revid in self.revid_rev
    
    def revid_from_revno(self, revno):
        if revno not in self.revno_rev:
            return None
        rev = self.revno_rev[revno]
        return rev.revid
    
    def find_child_branch_merge_revision(self, revid):
        rev = self.revid_rev[revid]
        if rev.merged_by:
            return self.revisions[rev.merged_by].revid
        else:
            return None

    def search_indexes(self):
        for bi in self.branches:
            if bi.index is not None:
                yield bi.index
    
    
    def get_revid_branch_info(self, revid):
        if revid in self.ghosts:
            raise GhostRevisionError(revid)
        
        if len(self.branches)==1 or revid not in self.revid_branch_info:
            return self.branches[0]
        return self.revid_branch_info[revid]
    
    def get_revid_branch(self, revid):
        return self.get_revid_branch_info(revid).branch
    
    def get_revid_repo(self, revid):
        return self.get_revid_branch_info(revid).branch.repository
    
    def get_repo_revids(self, revids):
        """Returns list of typle of (repo, revids)"""
        repo_revids = {}
        for repo in self.repos:
            repo_revids[repo] = []
        
        for repo in self.local_repo_copies:
            for revid in repo.has_revisions(revids):
                revids.remove(revid)
                repo_revids[repo].append(revid)
        
        for revid in revids:
            try:
                repo = self.get_revid_repo(revid)
            except GhostRevisionError:
                pass
            else:
                repo_revids[repo].append(revid)
        
        return [(repo, repo_revids[repo]) for repo in self.repos]
    
    def load_revisions(self, revids,
                      *args, **kargs):
        return load_revisions(revids, self.get_repo_revids,
                              *args, **kargs)

class PendingMergesGraphProvider(LogGraphProvider):
    
    def load_graph_parents(self):
        if not len(self.branches) == 1 or not len(self.repos) == 1:
            AssertionError("load_graph_pending_merges should only be called \
                           when 1 branch and repo has been opened.")
        
        bi = self.branches[0]
        if bi.tree is None:
            AssertionError("load_graph_pending_merges must have a working tree.")
        
        self.graph = bi.branch.repository.get_graph()
        tree_heads = bi.tree.get_parent_ids()
        other_revisions = [tree_heads[0],]
        self.update_ui()
        
        self.append_head_info('root:', bi, None)
        pending_merges = []
        for head in tree_heads[1:]:
            self.append_head_info(head, bi, None)
            pending_merges.extend(
                self.graph.find_unique_ancestors(head,other_revisions))
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
        
        return ["root:",] + tree_heads[1:], graph_parents.items()


class WithWorkingTreeGraphProvider(LogGraphProvider):
    
    def load_branch_heads(self, bi):
        # returns load_heads, sort_heads and also calls append_head_info.
        #
        # == For branch with tree ==
        # Graph                     | load_heads | sort_heads | append_head_info
        # wt                        | No         | Yes        | Yes   
        # | \                       |            |            |
        # | 1.1.2 (pending merge)   | Yes        | No         | Yes
        # 2 |     (basis rev)       | Yes        | No         | Yes
        #
        # == For branch with tree not up to date ==
        # Graph                     | load_heads | sort_heads | append_head_info
        #   wt                      | No         | Yes        | Yes   
        #   | \                     |            |            |
        #   | 1.1.2 (pending merge) | Yes        | No         | Yes
        # 3/  |     (branch tip)    | Yes        | Yes        | Yes      
        # 2   |     (basis rev)     | Yes        | No         | No
        #
        # == For branch without tree ==
        # branch tip                | Yes        | head       | yes
        
        load_heads = []
        sort_heads = []
        extra_parents = []
        
        
        if len(self.branches)>0:
            label = bi.label
        else:
            label = None
        
        branch_last_revision = bi.branch.last_revision()
        self.append_head_info(branch_last_revision, bi, bi.label)
        load_heads.append(branch_last_revision)
        self.update_ui()
        
        if bi.tree:
            wt_revid = CURRENT_REVISION + bi.tree.basedir
            if label:
                wt_label =  "%s - Working Tree" % label
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
                    append_head_info(revid, bi, pm_label)
            
            sort_heads.append(wt_revid)
            self.update_ui()
        else:
            sort_heads.append(branch_last_revision)
        
        return load_heads, sort_heads, extra_parents


class GraphProviderFilterState(object):
    
    def __init__(self, graph_provider):
        self.graph_provider = graph_provider
        self.branch_line_state = {}
        "If a branch_id is in this dict, it is visible. The value of the dict "
        "indicates which branches expanded this branch."
        
        for revid in self.graph_provider.revid_head_info:
            rev_cache = self.graph_provider.revid_rev[revid]
            self.branch_line_state[rev_cache.branch_id] = []
        
        self.filters = []
    
    def get_revision_visible_if_branch_visible(self, index):
        #This was previously cached. TODO: Check if this is still needed.
        if not self.no_graph:
            rev = self.revisions[index]
            for merged_index in rev.merges:
                if self.get_revision_visible_if_branch_visible_cached(
                                                            merged_index):
                    return True
        
        for filter in self.filters:
            filter_value = filter.get_revision_visible(index)
            if filter_value is not None:
                return filter_value
        
        return True
    
    def set_branch_visible(self, branch_id, visible, has_change):
        if not self.branch_lines[branch_id].visible == visible:
            has_change = True
        self.branch_lines[branch_id].visible = visible
        return has_change
    
    def ensure_rev_visible(self, revid):
        if self.no_graph:
            return False
        
        branch_id = self.revid_rev[revid].branch_id
        has_change = self.set_branch_visible(branch_id, True, False)
        #while (not branch_id in self.start_branch_ids and
        #       self.branch_lines[branch_id].merged_by):
        #    branch_id = self.branch_lines[branch_id].merged_by[0]
        #    has_change = self.set_branch_visible(branch_id, True, has_change)
        return has_change
    

    def collapse_expand_rev(self, revid, visible):
        rev = self.revid_rev[revid]
        #if rev.f_index is not None: return
        branch_ids = zip(rev.twisty_branch_ids,
                         [rev.branch_id]* len(rev.twisty_branch_ids))
        processed_branch_ids = []
        has_change = False
        while branch_ids:
            branch_id, expanded_by = branch_ids.pop()
            processed_branch_ids.append(branch_id)
            has_change = self.set_branch_visible(branch_id,
                                                 visible,
                                                 has_change)
            if not visible:
                self.branch_lines[branch_id].expanded_by = None
                for parent_branch_id in self.branch_lines[branch_id].merges:
                    parent = self.branch_lines[parent_branch_id]
                    if (not parent.visible or 
                        parent_branch_id in branch_ids or 
                        parent_branch_id in processed_branch_ids):
                        continue
                    
                    if parent.expanded_by == branch_id:
                        branch_ids.append((parent_branch_id, branch_id))
                    else:
                        # Check if this parent has any other visible branches
                        # that merge it.
                        has_visible = False
                        for merged_by_branch_id in parent.merged_by:
                            if self.branch_lines[merged_by_branch_id].visible:
                                has_visible = True
                                break
                        if not has_visible:
                            branch_ids.append((parent_branch_id, branch_id))
            else:
                self.branch_lines[branch_id].expanded_by = expanded_by
        return has_change
    

class FileIdFilter (object):
    def __init__(self, graph_provider, filter_changed_callback, file_ids):
        self.graph_provider = graph_provider
        self.filter_changed_callback = filter_changed_callback
        self.file_ids = file_ids
        self._has_dir = False
        self.filter_file_id = None
    
    def uses_inventory(self):
        return self.has_dir
    
    def load(self):
        """Load which revisions affect the file_ids"""
        if self.file_ids:
            self.throbber_show()
            
            if len(self.branches)>1:
                raise errors.BzrCommandError(paths_and_branches_err)
            
            bi = self.branches[0]
            tree = bi.tree
            if tree is None:
                tree = bi.branch.basis_tree()
            
            tree.lock_read()
            try:
                self.has_dir = False
                for file_id in self.file_ids:
                    if tree.kind(file_id) in ('directory', 'tree-reference'):
                        self.has_dir = True
                        break
            finally:
                tree.unlock()
            
            self.filter_file_id = [False for i in 
                         xrange(len(self.revisions))]
            
            revids = [rev.revid for rev in self.revisions]
            
            for repo, revids in self.get_repo_revids(revids):
                if not self.load_filter_file_id_uses_inventory():
                    chunk_size = 500
                else:
                    chunk_size = 500
                
                for start in xrange(0, len(revids), chunk_size):
                    self.load_filter_file_id_chunk(repo, 
                            revids[start:start + chunk_size])
            
            self.load_filter_file_id_chunk_finished()
    
    def load_filter_file_id_chunk(self, repo, revids):
        def check_text_keys(text_keys):
            changed_indexes = []
            for file_id, revid in repo.texts.get_parent_map(text_keys):
                rev = self.revid_rev[revid]
                self.filter_file_id[rev.index] = True
                changed_indexes.append(rev.index)
            
            self.update_ui()
            self.invaladate_filter_cache_revs(changed_indexes)
            self.update_ui()
        
        repo.lock_read()
        try:
            if not self.load_filter_file_id_uses_inventory():
                text_keys = [(file_id, revid) 
                                for revid in revids
                                for file_id in self.file_ids]
                check_text_keys(text_keys)
            else:
                text_keys = []
                # We have to load the inventory for each revisions, to find
                # the children of any directoires.
                for inv, revid in zip(
                            repo.iter_inventories(revids),
                            revids):
                    for path, entry in inv.iter_entries_by_dir(
                                            specific_file_ids = self.file_ids):
                        text_keys.append((entry.file_id, revid))
                        if entry.kind == "directory":
                            for rc_path, rc_entry in inv.iter_entries(from_dir = entry):
                                text_keys.append((rc_entry.file_id, revid))
                    
                    self.update_ui()
                
                check_text_keys(text_keys)
        finally:
            repo.unlock()

    def load_filter_file_id_chunk_finished(self):
        self.invaladate_filter_cache_revs([], last_call=True)
        self.throbber_hide()
    
    def get_revision_visible(self, index):
        if self.filter_file_id is None:
            return False
        if not self.filter_file_id[index]:
            return False

class PropertySearchFilter (object):
    def __init__(self, graph_provider, field, filter_re):
        self.graph_provider = graph_provider
        self.field = field
        self.filter_re = filter_re
        self._cache = None
    
    def set_search(self, str, field):
        """Set search string for specified kind of data.
        @param  str:    string to search (interpreted based on field value)
        @param  field:  kind of data to search, based on some field
            of revision metadata. Possible values:
                - message
                - index (require bzr-search plugin)
                - author
                - tag
                - bug

        Value of `str` interpreted based on field value. For index it's used
        as input value for bzr-search engine.
        For message, author, tag and bug it's used as shell pattern
        (glob pattern) to search in corresponding metadata of revisions.
        """
        self.sr_field = field
        
        def revisions_loaded(revisions, last_call):
            indexes = [self.revid_rev[revid].index
                       for revid in revisions.iterkeys()]
            self.invaladate_filter_cache_revs(indexes, last_call)
        
        def before_batch_load(repo, revids):
            if self.sr_filter_re is None:
                return True
            return False

        def wildcard2regex(wildcard):
            """Translate shel pattern to regexp."""
            return fnmatch.translate(wildcard + '*')
        
        if str is None or str == u"":
            self.sr_filter_re = None
            self.sr_index_matched_revids = None
            self.invaladate_filter_cache()
        else:
            if self.sr_field == "index":
                self.sr_filter_re = None
                indexes = self.search_indexes()
                if not indexes:
                    self.sr_index_matched_revids = None
                else:
                    str = str.strip()
                    query = [(query_item,) for query_item in str.split(" ")]
                    self.sr_index_matched_revids = {}
                    for index in indexes:
                        for result in index.search(query):
                            if isinstance(result, search_index.RevisionHit):
                                self.sr_index_matched_revids\
                                        [result.revision_key[0]] = True
                            if isinstance(result, search_index.FileTextHit):
                                self.sr_index_matched_revids\
                                        [result.text_key[1]] = True
                            if isinstance(result, search_index.PathHit):
                                pass
            elif self.sr_field == "tag":
                self.sr_filter_re = None
                filter_re = re.compile(wildcard2regex(str), re.IGNORECASE)
                self.sr_index_matched_revids = {}
                for revid in self.tags:
                    for t in self.tags[revid]:
                        if filter_re.search(t):
                            self.sr_index_matched_revids[revid] = True
                            break
            else:
                self.sr_filter_re = re.compile(wildcard2regex(str),
                    re.IGNORECASE)
                self.sr_index_matched_revids = None
            
            self.invaladate_filter_cache()
            
            if self.sr_filter_re is not None\
               and not self.sr_loading_revisions:
                
                revids = [rev.revid for rev in self.revisions ]
                
                self.load_revisions(revids,
                                    time_before_first_ui_update = 0,
                                    local_batch_size = 100,
                                    remote_batch_size = 10,
                                    before_batch_load = before_batch_load,
                                    revisions_loaded = revisions_loaded)
    
    def get_revision_visible(self, index):
        revid = self.revisions[index].revid
        
        if self.sr_filter_re:
            if revid not in cached_revisions:
                return False
            revision = cached_revisions[revid]
            
            filtered_str = None
            if self.sr_field == "message":
                filtered_str = revision.message
            elif self.sr_field == "author":
                filtered_str = get_apparent_author(revision)
            elif self.sr_field == "bug":
                rbugs = revision.properties.get('bugs', '')
                if rbugs:
                    filtered_str = rbugs.replace('\n', ' ')
                else:
                    return False

            if filtered_str is not None:
                if self.sr_filter_re.search(filtered_str) is None:
                    return False
        
        if self.sr_index_matched_revids is not None:
            if revid not in self.sr_index_matched_revids:
                return False        

class FilterScheduler(object):
    def __init__(self):
        self.pending_indexes = []
        self.last_run_time = 0
        self.last_call_time = 0
    def invaladate_filter_cache_revs(self, indexes, last_call=False):
        self.ifcr_pending_indexes.extend(indexes)
        # Only notify that there are changes every so often.
        # invaladate_filter_cache_revs causes compute_graph_lines to run, and it
        # runs slowly because it has to update the filter cache. How often we
        # update is bases on a ratio of 10:1. If we spend 1 sec calling
        # invaladate_filter_cache_revs, don't call it again until we have spent
        # 10 sec else where.
        if last_call or \
                clock() - self.ifcr_last_call_time > \
                self.ifcr_last_run_time * 10:
            
            start_time = clock()        
            prev_cached_indexes = []
            processed_indexes = []
            while self.ifcr_pending_indexes:
                index = self.ifcr_pending_indexes.pop(0)
                
                if index in processed_indexes:
                    continue
                rev = self.revisions[index]
                
                if rev.filter_cache is not None:
                    prev_cached_indexes.append((index, rev.filter_cache))
                rev.filter_cache = None
                
                if not self.no_graph:
                    if rev.merged_by is not None:
                        if rev.merged_by not in self.ifcr_pending_indexes and \
                           rev.merged_by not in processed_indexes:
                            self.ifcr_pending_indexes.append(rev.merged_by)
            
            # Check if any visibilities have changes. If they have, call
            # revisions_filter_changed
            for index, prev_visible in prev_cached_indexes:
                if not self.no_graph:
                    merged_by = self.revisions[index].merged_by
                else:
                    merged_by = None
                
                if not merged_by or \
                    self.get_revision_visible_if_branch_visible_cached(merged_by):
                    visible = self.get_revision_visible_if_branch_visible_cached(index)
                    if visible <> prev_visible:
                        self.revisions_filter_changed()
                        break
            
            self.ifcr_last_run_time = clock() - start_time
            self.ifcr_last_call_time = clock()
        
        if last_call:
            self.ifcr_last_run_time = 0
            self.ifcr_last_call_time = 0

class ComputedRevision(object):
    __slots__ = ['rev_cache', 'f_index', 'lines', 'col_index', 'branch_tags',
                 'twisty_state', 'twisty_expands_branch_ids']

class ComputedGraph(object):
    def __init__(self, graph_provider):
        self.filtered_revisions = []
        self.revisions = []
        