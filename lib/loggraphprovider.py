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

import fnmatch
import re
from time import clock

from bzrlib import errors
from bzrlib.transport.local import LocalTransport
from bzrlib.revision import NULL_REVISION, CURRENT_REVISION
from bzrlib.tsort import merge_sort
try:
    from bzrlib.graph import (Graph, StackedParentsProvider)
except ImportError:
    from bzrlib.graph import (Graph,
                    _StackedParentsProvider as StackedParentsProvider)
    
from bzrlib.bzrdir import BzrDir
from bzrlib.inventory import Inventory
from bzrlib.workingtree import WorkingTree
from bzrlib.plugins.qbzr.lib.lazycachedrevloader import (load_revisions,
                                                         cached_revisions)
from bzrlib.plugins.qbzr.lib.util import get_apparent_author

have_search = True
try:
    from bzrlib.plugins.search import errors as search_errors
    from bzrlib.plugins.search import index as search_index
except ImportError:
    have_search = False

class BranchInfo(object):
    """Holds a branch and related information"""
    
    # Instance of this object are typicaly named "bi".
    
    __slots__ = ["tree", "branch", "index"]
    def __init__ (self, tree, branch, index):
        self.tree = tree
        self.branch = branch
        self.index = index
    
    def __hash__(self):
        return self.branch.base.__hash__()

    def __eq__(self, other):
        if isinstance(other, BranchInfo):
            return self.branch.base.__eq__(other.branch.base)
        return False

class RevisionInfo(object):
    """Holds information about a revision."""
    
    # Instance of this object are typicaly named "rev".
    
    __slots__ = ["index", "revid", "merge_depth", "revno_sequence",
                 "end_of_merge", "branch_id", "_revno_str", "filter_cache",
                 "merges", "merged_by", "f_index", "color",
                 "col_index", "lines", "twisty_state", "twisty_branch_ids"]

    def __init__ (self, index, revid, merge_depth, revno_sequence, end_of_merge):
        self.index = index
        """Index in LogGraphProvider.revisions"""
        self.f_index = None
        """Index in LogGraphProvider.filtered_revs.
        
        If None, then this revision is not visible
        """
        self.revid = revid
        self.merge_depth = merge_depth
        self.revno_sequence = revno_sequence
        self.end_of_merge = end_of_merge
        self.branch_id = self.revno_sequence[0:-1]
        self._revno_str = None
        self.filter_cache = True
        """Cache of if this revision is  visible if it's branch is visible"""
        self.merges = []
        """Revision indexes that this revision merges"""
        self.merged_by = None
        """Revision index that merges this revision."""
        self.color = 0
        """Number that repesents a color for the node."""
        self.col_index = None
        """Column index for the node of this revision."""
        self.lines = []
        """Lines that need to be drawn on the same line as this revisions.
        
        List of typle (start, end, color, direct)
        """
        
        # Twisties are the +- buttons to expand and colapes branches.
        self.twisty_state = None
        """Sate of the twisty
        
        If None, then there is no twisty. If False, there a branched that are
        not visilble, and so a + must be shown. If True, all branchs are
        visible, and we need to show a -.
        """
        self.twisty_branch_ids = []
        """Branches that will be expanded/colapsed when the twisty is
        clicked on.
        
        """
    
    def get_revno_str(self):
        if self._revno_str is None:
            self._revno_str = ".".join(["%d" % (revno)
                                for revno in self.revno_sequence])
            if self.revid == CURRENT_REVISION:
                self._revno_str += " ?"
        return self._revno_str
    revno_str = property(get_revno_str)
    
    def __repr__(self):
        return "%s <%s %s>" % (self.__class__.__name__, self.revno_str,
                              self.revid)

class BranchLine(object):
    __slots__ = ["branch_id", "revs", "visible", "merges", "merged_by",
                 "color", "merge_depth", "expanded_by"]
    
    def __init__(self, branch_id, visible):
        self.branch_id = branch_id
        self.visible = visible
        self.revs = []
        self.merges = []
        self.merged_by = []
        self.color = reduce(lambda x, y: x+y, self.branch_id, 0)
        self.merge_depth = 0
        self.expanded_by=None

    def __repr__(self):
        return "%s <%s>" % (self.__class__.__name__, self.branch_id)

class LogGraphProvider(object):
    """Loads and computes revision and graph data for GUI log widgets."""
    
    # Most list/dicts related to revisions are unfiltered. When we do a graph
    # layout, we filter these revisions. A revision may be filter out because:
    # * It's branch is hidden (or colapsed).
    # * We have a sepcified file_id(s), and the revision does not touch the
    #   file_id(s).
    # * We have a search, and the revision does not match the search.
    #
    # The main list of unfiltered revisions is self.revisions. A revisions index
    # in revisions are normaly called index. The main list of filtered revisions
    # is filtered_revs. Revision indexes in this list are called f_index.
    
    def __init__(self, no_graph):
        
        self.no_graph = no_graph

        self.branches = []
        """List of BranchInfo for each branch."""
        
        self.fileids = []
        self.has_dir = False
        
        self.repos = {}
        
        self.local_repo_copies = []
        """A list of repositories that revisions will be aptempted to be loaded        
        from first."""
        
        self.head_revids = []
        """List of revids that are the heads of the graph.
        The order of the heads is mantianed in this list.
        """
        self.revid_head_info = {}
        """Dict with a keys of head revid and value of
            (list of head_infos,
             list of revids that are unique to this head)
        head_info is a tuple of:
            (branch,
            tag,
            is_branch_last_revision)
        """
        self.branch_tags = {}
        """Dict of revid to a list of branch tags. Depends on which revisions
        are visible."""
        
        self.trunk_branch = None
        
        self.revisions = []
        """List of RevisionInfo from merge_sort."""
        
        self.filtered_revs = []
        self.revid_rev = {}
        self.graph_children = {}
        
        self.queue = []
        self.tags = {}      # map revid -> tags set
        
        self.filter_file_id = None
        """Filtered dict of index's that are visible because they touch
        self.fileids
        """
        
        self.sr_field = None
        self.sr_filter_re = None
        self.sr_loading_revisions = False
        self.sr_index_matched_revids = None
        
        # ifcr = invaladate_filter_cache_revs and these fields are related to
        # that method.
        self.ifcr_pending_indexes = []
        self.ifcr_last_run_time = 0
        self.ifcr_last_call_time = 0
    
    def update_ui(self):
        pass
    
    def throbber_show(self):
        pass
    
    def throbber_hide(self):
        pass
    
    def append_repo(self, repo, local_copy = False):
        repo.is_local = isinstance(repo.bzrdir.transport, LocalTransport)
        if repo.base not in self.repos:
            self.repos[repo.base] = repo
        if local_copy:
            self.local_repo_copies.append(repo.base)
    
    def append_branch(self, tree, branch):
        bi = BranchInfo(tree, branch, None)
        if bi not in self.branches:
            bi.index = self.open_search_index(branch)
            self.branches.append(bi)
    
    def open_search_index(self, branch):
        if have_search:
            try:
                return search_index.open_index_branch(branch)
            except search_errors.NoSearchIndex:
                return None
        else:
            return None
    
    def open_branch(self, branch, file_ids=None, tree=None):
        """Open branch and fileids to be loaded. """
        
        repo = branch.repository
        if not tree:
            try:
                # XXX - This dose not work if you have a light weight checkout
                # We should rather make sure that every thing correctly pass
                # us the wt if there is one.
                tree = branch.bzrdir.open_workingtree()
            except errors.NoWorkingTree:
                pass
        self.append_repo(repo)
        self.append_branch(tree, branch)
        
        if file_ids:
            self.fileids.extend(file_ids)
            if not self.has_dir:
                for file_id in file_ids:
                    if tree is None:
                        kind = branch.basis_tree().kind(file_id)
                    else:
                        kind = tree.kind(file_id)
                    if kind in ('directory', 'tree-reference'):
                        self.has_dir = True
                        break
        
        if len(self.branches)==1 and self.trunk_branch == None:
            self.trunk_branch = branch
    
    def open_locations(self, locations):
        """Open branches or repositories and file-ids to be loaded from a list
        of locations strings, inputed by the user (such as at the command line.)
        
        """
        paths_and_branches_err = "It is not possible to specify different file paths and different branches at the same time."
        
        for location in locations:
            tree, br, repo, fp = \
                    BzrDir.open_containing_tree_branch_or_repository(location)
            self.update_ui()
            
            if br is None:
                if fp:
                    raise errors.NotBranchError(fp)
                
                branches = repo.find_branches(using=True) 
                for br in branches:
                    try:
                        tree = br.bzrdir.open_workingtree()
                    except errors.NoWorkingTree:
                        tree = None
                    self.append_branch(tree, br)
                    self.append_repo(br.repository)
                self.update_ui()
            else:
                self.append_repo(repo)
                self.append_branch(tree, br)
                if len(self.branches)==1 and self.trunk_branch == None:
                    self.trunk_branch = br
            
            # If no locations were sepecified, don't do fileids
            # Otherwise it gives you the history for the dir if you are
            # in a sub dir.
            #
            # XXX - There is a case where this does not behave correctly.
            # If we are in subdir and we do "bzr qlog ." then we should filter
            # on subdir. but if we do "bzr qlog" then we should not. To be able
            # to do this, we need to move the implication the no location
            # argument means '.' down in to the method, rather than where it is
            # now. - GaryvdM 29 May 2009
            if fp != '' and locations == [u"."]:
                fp = ''

            if fp != '' :
                if tree is None:
                    tree = br.basis_tree()
                
                file_id = tree.path2id(fp)
                if file_id is None:
                    raise errors.BzrCommandError(
                        "Path does not have any revision history: %s" %
                        location)
                
                kind = tree.kind(file_id)
                if kind in ('directory', 'tree-reference'):
                    self.has_dir = True
                self.update_ui()
                
                self.fileids.append(file_id)
        
        if self.fileids and len(self.branches)>1:
            raise errors.BzrCommandError(paths_and_branches_err)

    def lock_read_branches(self):
        for bi in self.branches:
            bi.branch.lock_read()
        for repo in self.repos.itervalues():
            repo.lock_read()
    
    def unlock_branches(self):
        for bi in self.branches:
            bi.branch.unlock()
        for repo in self.repos.itervalues():
            repo.unlock()
    
    #def lock_read_repos(self):
    #    for repo in self.repos.itervalues():
    #        repo.lock_read()
    #
    #def unlock_repos(self):
    #    for repo in self.repos.itervalues():
    #        repo.unlock()
    
    def append_head_info(self, revid, branch, tag, is_branch_last_revision):
        if not revid==NULL_REVISION:
            if not revid in self.head_revids:
                self.head_revids.append(revid)
                self.revid_head_info[revid] = ([],[])
            self.revid_head_info[revid][0].append ((branch, tag,
                                                    is_branch_last_revision))
            self.revid_branch[revid] = branch
    
    def load_branch_heads(self):
        """Load the tips, tips of the pending merges, and revision of the
        working tree for each branch."""
        
        self.revid_head_info = {}
        self.head_revids = []
        self.revid_branch = {}
        for bi in self.branches:
            
            if len(self.branches) == 1:
                tag = None
            else:
                tag = bi.branch.nick
                if len(tag) > 20:
                    tag = tag[:20]+'...'
            
            branch_last_revision = bi.branch.last_revision()
            self.append_head_info(branch_last_revision, bi.branch, tag, True)
            self.update_ui()
            
            if bi.tree:
                parent_ids = bi.tree.get_parent_ids()
                if parent_ids:
                    # first parent is last revision of the tree
                    revid = parent_ids[0]
                    if revid != branch_last_revision:
                        # working tree is out of date
                        if tag:
                            self.append_head_info(revid, bi.branch,
                                             "%s - Working Tree" % tag, False)
                        else:
                            self.append_head_info(revid, bi.branch,
                                             "Working Tree", False)
                    # other parents are pending merges
                    for revid in parent_ids[1:]:
                        if tag:
                            self.append_head_info(revid, bi.branch,
                                             "%s - Pending Merge" % tag, False)
                        else:
                            self.append_head_info(revid, bi.branch,
                                             "Pending Merge", False)
                self.update_ui()
        
        if len(self.branches)>1:
            if self.trunk_branch == None:
                # Work out which branch we think is trunk.
                # TODO: Make config option.
                trunk_names = "trunk,bzr.dev".split(",")
                for bi in self.branches:
                    if bi.branch.nick in trunk_names:
                        self.trunk_branch = bi.branch
                        break
            
            if self.trunk_branch == None:
                self.trunk_branch = self.branches[0].branch
            
            trunk_tip = self.trunk_branch.last_revision()
            
            head_revs = self.load_revisions(self.head_revids)
            
            def head_revids_cmp(x,y):
                if x == trunk_tip:
                    return -1
                if y == trunk_tip:
                    return 1
                return 0-cmp(head_revs[x].timestamp,
                             head_revs[y].timestamp)
            
            self.head_revids.sort(head_revids_cmp)
    
    def load_tags(self):
        self.tags = {}
        for bi in self.branches:
            branch_tags = bi.branch.tags.get_reverse_tag_dict()  # revid to tags map
            for revid, tags in branch_tags.iteritems():
                if revid in self.tags:
                    self.tags[revid].update(set(tags))
                else:
                    self.tags[revid] = set(tags)

    def repos_cmp_local_higher(self, x, y):
        if x.is_local and not y.is_local:
            return -1
        if y.is_local and not x.is_local:
            return 1
        return 0
    
    def repos_sorted_local_first(self):
        return sorted(self.repos.itervalues(),self.repos_cmp_local_higher)

    def load_graph_all_revisions(self):
        self.load_branch_heads()
        
        if len(self.repos)==1:
            self.graph = self.repos.values()[0].get_graph()
        else:
            parents_providers = [repo._make_parents_provider() \
                                 for repo in self.repos_sorted_local_first()]
            self.graph = Graph(StackedParentsProvider(parents_providers))
        
        self.process_graph_parents(self.graph.iter_ancestry(self.head_revids))
        
        self.compute_loaded_graph()

    def load_graph_all_revisions_for_annotate(self):
        if not len(self.branches) == 1:
            AssertionError("load_graph_pending_merges should only be called \
                           when 1 branch and repo has been opened.")        
        
        self.revid_head_info = {}
        self.head_revids = []
        self.revid_branch = {}
        bi = self.branches[0]
        self.trunk_branch = bi.branch
        
        if bi.tree and isinstance(bi.tree, WorkingTree):
            branch_last_revision = CURRENT_REVISION
            current_parents = bi.tree.get_parent_ids()
        else:
            branch_last_revision = bi.branch.last_revision()
        
        self.append_head_info(branch_last_revision, bi.branch, None, True)
        self.update_ui()
        
        if len(self.repos)==1:
            self.graph = self.repos.values()[0].get_graph()
        else:
            parents_providers = [repo._make_parents_provider() \
                                 for repo in self.repos_sorted_local_first()]
            self.graph = Graph(StackedParentsProvider(parents_providers))
        
        def parents():
            if branch_last_revision == CURRENT_REVISION:
                yield (CURRENT_REVISION, current_parents)
                heads = current_parents
            else:
                heads = self.head_revids
            for p in self.graph.iter_ancestry(heads):
                yield p
        
        self.process_graph_parents(parents())
        
        self.compute_loaded_graph()
    
    def load_graph_pending_merges(self):
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

        
        self.revid_head_info = {}
        self.head_revids = ["root:",]
        self.revid_branch = {}
        
        pending_merges = []
        for head in tree_heads[1:]:
            self.append_head_info(head, bi.branch, None, False)
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
        
        self.process_graph_parents(graph_parents.items())
        self.compute_loaded_graph()
    
    def process_graph_parents(self, graph_parents):
        self.graph_parents = {}
        self.graph_children = {}        
        ghosts = set()
        
        for (revid, parent_revids) \
                    in graph_parents:
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
    
    def compute_loaded_graph(self):
        self.graph_parents["top:"] = self.head_revids
    
        if len(self.graph_parents)>0:
            merge_sorted_revisions = merge_sort(self.graph_parents,
                                                "top:",
                                                generate_revno=True)
            assert merge_sorted_revisions[0][1] == "top:"
            self.revisions = \
                [RevisionInfo(index, revid, merge_depth,
                              revno_sequence, end_of_merge)
                 for (index, (seq, revid, merge_depth,
                              revno_sequence, end_of_merge)) in
                       enumerate(merge_sorted_revisions[1:])]
        else:
            self.revisions = ()
        
        self.revid_rev = {}
        self.revno_rev = {}
        
        for rev in self.revisions:
            self.revid_rev[rev.revid] = rev
            self.revno_rev[rev.revno_sequence] = rev
        
        if not self.no_graph:
            self.compute_branch_lines()
            self.compute_merge_info()
        self.compute_head_info()
        
        if not self.fileids:
            # All revisions start visible
            for rev in self.revisions:
                rev.filter_cache = True
            self.revisions_filter_changed()
        else:
            # Revision visibilaty unknown.
            self.invaladate_filter_cache()
        
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
        
        self.start_branch_ids = []
        """Branch ids that should be initialy visible"""
        
        self.branch_ids = []
        """List of branch ids, sorted in the order that the branches will
        be shown, from left to right on the graph."""
        
        for rev in self.revisions:
            
            branch_line = None
            if rev.branch_id not in self.branch_lines:
                start_branch = rev.revid in self.head_revids
                branch_line = BranchLine(rev.branch_id, start_branch)
                if start_branch:
                    self.start_branch_ids.append(rev.branch_id)
                self.branch_lines[rev.branch_id] = branch_line
            else:
                branch_line = self.branch_lines[rev.branch_id]
            
            branch_line.revs.append(rev)
            branch_line.merge_depth = max(rev.merge_depth, branch_line.merge_depth)
            rev.color = branch_line.color
        
        self.branch_ids = self.branch_lines.keys()
        
        # Note: This greatly affects the layout of the graph.
        def branch_id_cmp(x, y):
            # Branch lines that have a tip (e.g. () - the main line) should be
            # to the left of other branch lines.
            is_start_x = x in self.start_branch_ids
            is_start_y = y in self.start_branch_ids
            if not is_start_x == is_start_y:
                return -cmp(is_start_x, is_start_y)
            
            # Branch line that have a smaller merge depth should be to the left
            # of those with bigger merge depths.
            merge_depth_x = self.branch_lines[x].merge_depth
            merge_depth_y = self.branch_lines[y].merge_depth
            if not merge_depth_x == merge_depth_y:
                return cmp(merge_depth_x, merge_depth_y)
            
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
            if len(x) == 2 and len(y) == 2 and x[0] == y[0]:
                return cmp(x[1], y[1])
            
            # Otherwise, thoes with a greater mainline parent revno should
            # appear to the left.
            return -cmp(x, y)

        self.branch_ids.sort(branch_id_cmp)
    
    def compute_merge_info(self):
        
        def set_merged_by(rev, merged_by):
            if merged_by is not None:
                rev.merged_by = merged_by
                self.revisions[merged_by].merges.append(rev.index)
                branch_id = rev.branch_id
                merged_by_branch_id = self.revisions[merged_by].branch_id
                
                if not branch_id in self.branch_lines[merged_by_branch_id].merges:
                    self.branch_lines[merged_by_branch_id].merges.append(branch_id)
                if not merged_by_branch_id in self.branch_lines[branch_id].merged_by:
                    self.branch_lines[branch_id].merged_by.append(merged_by_branch_id)
        
        for rev in self.revisions:
            
            parents = [self.revid_rev[parent]
                       for parent in self.graph_parents[rev.revid]]
            
            if len(parents) > 0:
                if rev.branch_id == parents[0].branch_id:
                    set_merged_by(parents[0], rev.merged_by)
            
            for parent in parents[1:]:
                if rev.merge_depth<=parent.merge_depth:
                    set_merged_by(parent, rev.index)
        
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
            head_revid_branch = sorted([(revid, branch) \
                                       for revid, (head_info, ur) in \
                                       self.revid_head_info.iteritems()
                                       for (branch, tag, lr) in head_info],
                cmp = self.repos_cmp_local_higher,
                key = lambda x: x[1].repository)
            self.revid_branch = get_revid_head(head_revid_branch)
        else:
            self.revid_branch = {}
        
        if len(self.revid_head_info) > 1:
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
                    other_revids = [self.graph_parents[merged_by_revid][0]]
                else:
                    other_revids = [other_revid for other_revid \
                        in self.revid_head_info.iterkeys() \
                        if not other_revid == revid]
                ur.extend([revid for revid \
                    in self.graph.find_unique_ancestors(revid, other_revids) \
                    if not revid == NULL_REVISION and revid in self.revid_rev])
                ur.sort(key=lambda x: self.revid_rev[x].index)

    def load_filter_file_id_uses_inventory(self):
        return self.has_dir and getattr(Inventory,"filter",None) is not None
    
    def load_filter_file_id(self):
        """Load with revisions affect the fileids
        
        It requires that compute_merge_info has been run.
        
        """
        if self.fileids:
            self.throbber_show()
            
            self.filter_file_id = [False for i in 
                         xrange(len(self.revisions))]
            
            revids = [rev.revid for rev in self.revisions]
            
            for repo, revids in self.get_repo_revids(revids):
                if not self.load_filter_file_id_uses_inventory():
                    chunk_size = 500
                else:
                    chunk_size = 50
                
                for start in xrange(0, len(revids), chunk_size):
                    text_keys = []
                    self.load_filter_file_id_chunk(repo, 
                            revids[start:start + chunk_size])
            
            self.load_filter_file_id_chunk_finished()
    
    def load_filter_file_id_chunk(self, repo, revids):
        def check_text_keys(text_keys):
            changed_indexes = []
            for fileid, revid in repo.texts.get_parent_map(text_keys):
                rev = self.revid_rev[revid]
                self.filter_file_id[rev.index] = True
                changed_indexes.append(rev.index)
            
            self.update_ui()
            self.invaladate_filter_cache_revs(changed_indexes)
            self.update_ui()
        
        repo.lock_read()
        try:
            if not self.load_filter_file_id_uses_inventory():
                text_keys = [(fileid, revid) 
                                for revid in revids
                                for fileid in self.fileids]
                check_text_keys(text_keys)
            else:
                text_keys = []
                # We have to load the inventory for each revisions, to find
                # the children of any directoires.
                for inv, revid in zip(
                            repo.iter_inventories(revids),
                            revids):
                    filterted_inv = inv.filter(self.fileids)
                    for path, entry in filterted_inv.entries():
                        text_keys.append((entry.file_id, revid))
                
                check_text_keys(text_keys)
        finally:
            repo.unlock()

    def load_filter_file_id_chunk_finished(self):
        self.invaladate_filter_cache_revs([], last_call=True)
        self.throbber_hide()
    
    def get_revision_visible(self, index):
        """ Returns wether a revision is visible or not"""
        
        
        return self.revisions[index].f_index is not None
        #branch_id = self.revisions[index].branch_id
        #
        #if not self.no_graph and \
        #        not self.branch_lines[branch_id].visible: # branch colapased
        #    return False
        #
        #return self.get_revision_visible_if_branch_visible_cached(index)

    def get_revision_visible_if_branch_visible_cached(self, index):
        rev = self.revisions[index]
        if rev.filter_cache is None:
            rev.filter_cache = self.get_revision_visible_if_branch_visible(index)
        return rev.filter_cache
    
    def get_revision_visible_if_branch_visible(self, index):
        
        if not self.no_graph:
            rev = self.revisions[index]
            for merged_index in rev.merges:
                if self.get_revision_visible_if_branch_visible_cached(
                                                            merged_index):
                    return True
        
        if self.fileids:
            if self.filter_file_id is None:
                return False
            if not self.filter_file_id[index]:
                return False
        
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
        
        return True

    def invaladate_filter_cache(self):
        for rev in self.revisions:
            rev.filter_cache = None
        self.revisions_filter_changed()
    
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
	
    def compute_graph_lines(self):
        """Recompute the layout of the graph, and store the results in
        self.revision"""
        
        # Overview:
        # Clear the old data from self.revisions.
        # Work out which revision need to be displayed.
        # Assign columns for branches, and lines that go between branches.
        #   These are intermingled, because some of the lines need to come
        #   before it's branch, and others need to come after. Other lines
        #   (such a the line from the last rev in a branch) are treated a
        #   special cases.
        # The calcated data is then copied into self.revisions in a format
        #  that is easy for the TreeView to display.
        
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
                    
                    parents = [self.revid_rev[parent_revid]
                               for parent_revid in self.graph_parents[rev.revid]]
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
                                g_parent_ids = self.graph_parents[parent.revid]
                                
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
                cur_cont_line = []
                
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
        
        self.branch_tags = {}
        for (revid, (head_info,
                     unique_revids)) in self.revid_head_info.iteritems():
            top_visible_revid = None
            
            for unique_revid in unique_revids:
                rev = self.revid_rev[unique_revid]
                if rev.f_index is not None:
                    top_visible_revid = unique_revid
                    break
            
            tags =  [tag for (branch,
                              tag,
                              is_branch_last_revision) in head_info]
            if top_visible_revid:
                self.branch_tags[top_visible_revid] = tags
    
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

    def has_visible_child(self, branch_id):
        for child_branch_id in self.branch_lines[branch_id].merged_by:
            if self.branch_lines[child_branch_id].visible:
                return True
        return False

    def colapse_expand_rev(self, revid, visible):
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
                    
                    collapse_parent = False
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
            return fnmatch.translate(wildcard).rstrip('$')
        
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
    
    def get_revid_branch(self, revid):
        if len(self.branches)==1 and revid not in self.revid_branch:
            return self.branches[0].branch
        return self.revid_branch[revid]
    
    def get_revid_repo(self, revid):
        return self.get_revid_branch(revid).repository
    
    def get_repo_revids(self, revids):
        """Returns list of typle of (repo, revids)"""
        repo_revids = {}
        for repo_base in self.repos.iterkeys():
            repo_revids[repo_base] = []
        
        for local_repo_copy in self.local_repo_copies:
            for revid in self.repos[local_repo_copy].has_revisions(revids):
                revids.remove(revid)
                repo_revids[local_repo_copy].append(revid)
        
        for revid in revids:
            repo = self.get_revid_repo(revid)
            repo_revids[repo.base].append(revid)
        
        return [(repo, repo_revids[repo.base])
                        for repo in self.repos_sorted_local_first()]
    
    def load_revisions(self, revids,
                      *args, **kargs):
        return load_revisions(revids, self.get_repo_revids,
                              *args, **kargs)
    
    def revisions_filter_changed(self):
        pass
