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

from PyQt4 import QtCore, QtGui
from time import (strftime, localtime)
from bzrlib import (lazy_regex, errors)
from bzrlib.revision import NULL_REVISION
from bzrlib.tsort import merge_sort
from bzrlib.graph import (Graph, _StackedParentsProvider)
from bzrlib.plugins.qbzr.lib.i18n import gettext
from bzrlib.plugins.qbzr.lib.util import (
    extract_name,
    )

have_search = True 
try: 
    from bzrlib.plugins.search import errors as search_errors 
    from bzrlib.plugins.search import index as search_index 
except ImportError: 
    have_search = False 
 
TagsRole = QtCore.Qt.UserRole + 1
BugIdsRole = QtCore.Qt.UserRole + 2
BranchTagsRole = QtCore.Qt.UserRole + 3
GraphNodeRole = QtCore.Qt.UserRole + 4
GraphLinesRole = QtCore.Qt.UserRole + 5
GraphTwistyStateRole = QtCore.Qt.UserRole + 6
RevIdRole = QtCore.Qt.UserRole + 7

FilterIdRole = QtCore.Qt.UserRole + 100
FilterMessageRole = QtCore.Qt.UserRole + 101
FilterAuthorRole = QtCore.Qt.UserRole + 102
FilterRevnoRole = QtCore.Qt.UserRole + 103
FilterSearchRole = QtCore.Qt.UserRole + 104

COL_REV = 0
COL_MESSAGE = 1
COL_DATE = 2
COL_AUTHOR = 3

_bug_id_re = lazy_regex.lazy_compile(r'(?:'
    r'bugs/'                    # Launchpad bugs URL
    r'|ticket/'                 # Trac bugs URL
    r'|show_bug\.cgi\?id='      # Bugzilla bugs URL
    r'|issues/show/'            # Redmine bugs URL
    r')(\d+)(?:\b|$)')


def get_bug_id(bug_url):
    match = _bug_id_re.search(bug_url)
    if match:
        return match.group(1)
    return None



try:
    QVariant_fromList = QtCore.QVariant.fromList
except AttributeError:
    QVariant_fromList = QtCore.QVariant


class GraphModel(QtCore.QAbstractTableModel):

    def __init__(self, process_events_ptr, parent=None):
        QtCore.QAbstractTableModel.__init__(self, parent)
        
        self.horizontalHeaderLabels = [gettext("Rev"),
                                       gettext("Message"),
                                       gettext("Date"),
                                       gettext("Author"),
                                       ]
        
        self.merge_sorted_revisions = []
        self.columns_len = 0
        self.revisions = {}
        self.tags = {}
        self.searchMode = False
        self.touches_file_msri = None
        self.msri_index = {}
        self.closing = False
        self.stop_revision_loading = False
        self.processEvents = process_events_ptr
    
    def setGraphFilterProxyModel(self, graphFilterProxyModel):
        self.graphFilterProxyModel = graphFilterProxyModel
    
    
    def loadBranch(self, branches, heads, specific_fileids = []):
        self.heads = heads
        self.branches = branches
        self.repos = {}
        for branch in self.branches:
            if branch.repository.base not in self.repos:
                self.repos[branch.repository.base] = branch.repository
        
        for branch in self.branches:
            branch.lock_read()
        try:
            self.emit(QtCore.SIGNAL("layoutAboutToBeChanged()"))
            self.tags = {}
            for branch in self.branches:
                branch_tags = branch.tags.get_reverse_tag_dict()  # revid to tags map
                for revid, tags in branch_tags.iteritems():
                    if revid in self.tags:
                        self.tags[revid].update(set(tags))
                    else:
                        self.tags[revid] = set(tags)
            
            self.start_revs = [rev for rev in self.heads if not rev == NULL_REVISION]
            self.start_revs.sort(lambda x, y:cmp(self.heads[x][0], self.heads[y][0]))
            
            parents_providers = [repo._make_parents_provider() for repo in self.repos.itervalues()]
            graph = Graph(_StackedParentsProvider(parents_providers))
            
            self.graph_parents = {}
            ghosts = set()
            self.graph_children = {}
            for (revid, parent_revids) in graph.iter_ancestry(self.start_revs):
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
                    self.processEvents()
            for ghost in ghosts:
                for ghost_child in self.graph_children[ghost]:
                    self.graph_parents[ghost_child] = [p for p in self.graph_parents[ghost_child]
                                                  if p not in ghosts]
            self.graph_parents["top:"] = self.start_revs
        
            if len(self.graph_parents)>0:
                self.merge_sorted_revisions = merge_sort(
                    self.graph_parents,
                    "top:",
                    generate_revno=True)
            else:
                self.merge_sorted_revisions = ()
            
            assert self.merge_sorted_revisions[0][1] == "top:"
            self.merge_sorted_revisions = self.merge_sorted_revisions[1:]
            
            self.revid_head = {}
            for i in xrange(1, len(self.start_revs)):
                head_revid = self.start_revs[i]
                for ancestor_revid in graph.find_unique_ancestors(head_revid, self.start_revs[:i-1]):
                    self.revid_head[ancestor_revid] = head_revid
            
            # This will hold, for each "branch":
            # [a list of revision indexes in the branch,
            #  is the branch visible,
            #  merges,
            #  merged_by].
            #
            # For a revisions, the revsion number less the least significant
            # digit is the branch_id, and used as the key for the dict. Hence
            # revision with the same revsion number less the least significant
            # digit are considered to be in the same branch line. e.g.: for
            # revisions 290.12.1 and 290.12.2, the branch_id would be 290.12,
            # and these two revisions will be in the same branch line. 
            self.branch_lines = {}
            self.revid_msri = {}
            self.revno_msri = {}
            self.start_branch_ids = []
            
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
                    start_branch = revid in self.start_revs
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
            
            # Work out for each revision, which revisions it merges, and what
            # revision it is merged by.
            self.merge_info = []
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
            
            if specific_fileids:
                self.touches_file_msri = {}
            
            self.emit(QtCore.SIGNAL("layoutChanged()"))
            
            if specific_fileids:
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
                            self.touches_file_msri[rev_msri] = True
                            
                            self.graphFilterProxyModel.invalidateCacheRow(rev_msri)
                            index = self.createIndex (rev_msri, 0, QtCore.QModelIndex())
                            self.emit(QtCore.SIGNAL("dataChanged(QModelIndex, QModelIndex)"),
                                      index,index)
                        
                        self.processEvents()
                    
                else:
                    weave_modifed_revisions = set()
                    for specific_fileid in specific_fileids:
                        file_weave = self.branches[0].repository.weave_store.get_weave(specific_fileid,
                                            self.branches[0].repository.get_transaction())
                        for revid in file_weave.versions():
                            rev_msri = self.revid_msri[revid]
                            self.touches_file_msri[rev_msri] = True
                            self.graphFilterProxyModel.invalidateCacheRow(rev_msri)
            
            self.compute_lines()
            self.processEvents()
            
            self._nextRevisionToLoadGen = self._nextRevisionToLoad()
            self.stop_revision_loading = False
            self._loadNextRevision()
        finally:
            for branch in self.branches:
                branch.unlock
        
    def compute_lines(self):
        
        # This will hold for each revision, a list of (msri,
        #                                              node,
        #                                              lines,
        #                                              twisty_state,
        #                                              twisty_branch_ids).
        #
        # Node is a tuple of (column, color) with column being a
        # zero-indexed column number of the graph that this revision
        # represents and color being a zero-indexed color (which doesn't
        # specify any actual color in particular) to draw the node in.
        #
        # Lines is a list of tuples which represent lines you should draw
        # away from the revision, if you also need to draw lines into the
        # revision you should use the lines list from the previous
        # iteration. Each tuples in the list is in the form (start, end,
        # color, direct) with start and end being zero-indexed column
        # numbers and color as in node.
        #
        # twisties are +- buttons to show/hide branches. list branch_ids
        linegraphdata = []
        msri_index = {}
        
        source_parent = QtCore.QModelIndex()
        for msri in xrange(0,len(self.merge_sorted_revisions)):
            if self.graphFilterProxyModel.filterAcceptsRow(msri, source_parent):
                index = len(linegraphdata)
                msri_index[msri] = index
                linegraphdata.append([msri,
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
        empty_column = [False for i in range(len(linegraphdata))]
        # This will hold a bit map for each cell. If the cell is true, then
        # the cell allready contains a node or line. This use when deciding
        # what column to place a branch line or line in, without it
        # overlaping something else.
        columns = [list(empty_column)]
        
        def _branch_line_col_search_order(parent_col_index):
            for col_index in range(parent_col_index, len(columns)):
                yield col_index
            #for col_index in range(parent_col_index-1, -1, -1):
            #    yield col_index
        
        def _line_col_search_order(parent_col_index, child_col_index):
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
        
        def _find_free_column(col_search_order, line_range):
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
        
        def _mark_column_as_used(col_index, line_range):
            column = columns[col_index]
            for row_index in line_range:
                column[row_index] = True
        
        def append_line (child_index, parent_index, direct):
            parent_node = linegraphdata[parent_index][1]
            if parent_node:
                parent_col_index = parent_node[0]
            else:
                parent_col_index = None
            
            child_node = linegraphdata[child_index][1]
            if child_node:
                child_col_index = child_node[0]
            else:
                child_col_index = None
                
            line_col_index = child_col_index
            if parent_index - child_index >1:
                line_range = range(child_index + 1, parent_index)
                col_search_order = \
                        _line_col_search_order(parent_col_index,
                                               child_col_index)
                line_col_index = \
                    _find_free_column(col_search_order,
                                      line_range)
                _mark_column_as_used(line_col_index,
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
                         parent_merge_depth) = self._msri_branch_id_merge_depth(parent_revid)
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
                                     parent_merge_depth) = self._msri_branch_id_merge_depth(parent_revid)
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
                            visible = pb_rev_msri in msri_index or\
                                      self.graphFilterProxyModel.filterAcceptsRowIfBranchVisible(pb_rev_msri, source_parent)
                            if visible:
                                linegraphdata[rev_index][4].append (parent_branch_id)
                                break
                    
                    # Work out if the twisty needs to show a + or -. If all
                    # twisty_branch_ids are visible, show - else +.
                    if len (linegraphdata[rev_index][4])>0:
                        twisty_state = True
                        for twisty_branch_id in linegraphdata[rev_index][4]:
                            if not self.branch_lines[twisty_branch_id][1]:
                                twisty_state = False
                                break
                        linegraphdata[rev_index][3] = twisty_state
                
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
                    parent_node = linegraphdata[parent_index][1]
                    if parent_node:
                        parent_col_index = parent_node[0]
                
                col_search_order = _branch_line_col_search_order(parent_col_index) 
                cur_cont_line = []
                
                # Work out what rows this branch spans
                line_range = []
                first_rev_index = msri_index[branch_rev_msri[0]]
                last_rev_index = msri_index[branch_rev_msri[-1]]
                line_range = range(first_rev_index, last_rev_index+1)
                
                if parent_index:
                    line_range.extend(range(last_rev_index+1, parent_index))
                
                col_index = _find_free_column(col_search_order,
                                              line_range)
                node = (col_index, color)
                # Free column for this branch found. Set node for all
                # revision in this branch.
                for rev_msri in branch_rev_msri:
                    rev_index = msri_index[rev_msri]
                    linegraphdata[rev_index][1] = node
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
        # copy the lines in to linegraphdata.
        for (child_index,
             parent_index,
             line_col_index,
             direct,
             ) in lines:
            
            (child_col_index, child_color) = linegraphdata[child_index][1]
            (parent_col_index, parent_color) = linegraphdata[parent_index][1]
            
            if parent_index - child_index == 1:
                linegraphdata[child_index][2].append(
                    (child_col_index,
                     parent_col_index,
                     parent_color,
                     direct))
            else:
                # line from the child's column to the lines column
                linegraphdata[child_index][2].append(
                    (child_col_index,
                     line_col_index,
                     parent_color,
                     direct))
                # lines down the line's column
                for line_part_index in range(child_index+1, parent_index-1):
                    linegraphdata[line_part_index][2].append(
                        (line_col_index,   
                         line_col_index,
                         parent_color,
                         direct))
                # line from the line's column to the parent's column
                linegraphdata[parent_index-1][2].append(
                    (line_col_index,
                     parent_col_index,
                     parent_color,
                     direct))

        self.linegraphdata = linegraphdata
        self.msri_index = msri_index
        self.emit(QtCore.SIGNAL("dataChanged(QModelIndex, QModelIndex)"),
                  self.createIndex (0, COL_MESSAGE, QtCore.QModelIndex()),
                  self.createIndex (len(self.merge_sorted_revisions), COL_MESSAGE, QtCore.QModelIndex()))
    
    def _msri_branch_id_merge_depth (self, revid):
        msri = self.revid_msri[revid]
        branch_id = self.merge_sorted_revisions[msri][3][0:-1]
        merge_depth = self.merge_sorted_revisions[msri][2]
        return (msri, branch_id, merge_depth)
    
    def _set_branch_visible(self, branch_id, visible, has_change):
        if not self.branch_lines[branch_id][1] == visible:
            has_change = True
        self.branch_lines[branch_id][1] = visible
        return has_change
    
    def _has_visible_child(self, branch_id):
        for child_branch_id in self.branch_lines[branch_id][3]:
            if self.branch_lines[child_branch_id][1]:
                return True
        return False
    
    def colapse_expand_rev(self, revid, visible):
        msri = self.revid_msri[revid]
        if msri not in self.msri_index: return
        index = self.msri_index[msri]
        twisty_branch_ids = self.linegraphdata[index][4]
        has_change = False
        for branch_id in twisty_branch_ids:
            has_change = self._set_branch_visible(branch_id, visible, has_change)
            if not visible:
                for parent_branch_id in self.branch_lines[branch_id][2]:
                    if not parent_branch_id in self.start_branch_ids and not self._has_visible_child(parent_branch_id):
                        has_change = self._set_branch_visible(parent_branch_id, visible, has_change)
        if has_change:
            self.compute_lines()
    
    def has_rev_id(self, revid):
        return revid in self.revid_msri
    
    def revid_from_revno(self, revno):
        if revno not in self.revno_msri:
            return None
        msri = self.revno_msri[revno]
        return self.merge_sorted_revisions[msri][1]
        
    def ensure_rev_visible(self, revid):
        if self.searchMode:
            return
        rev_msri = self.revid_msri[revid]
        branch_id = self.merge_sorted_revisions[rev_msri][3][0:-1]
        has_change = self._set_branch_visible(branch_id, True, False)
        while not branch_id in self.start_branch_ids and self.branch_lines[branch_id][3]:
            branch_id = self.branch_lines[branch_id][3][0]
            has_change = self._set_branch_visible(branch_id, True, has_change)
        if has_change:
            self.compute_lines()
    
    def set_search_mode(self, searchMode):
        if not searchMode == self.searchMode:
            self.searchMode = searchMode
            self._nextRevisionToLoadGen = self._nextRevisionToLoad()
    
    def columnCount(self, parent):
        if parent.isValid():
            return 0
        return len(self.horizontalHeaderLabels)

    def rowCount(self, parent):
        if parent.isValid():
            return 0
        return len(self.merge_sorted_revisions)
    
    def data(self, index, role):
        if not index.isValid():
            return QtCore.QVariant()
        
        if index.row() in self.msri_index:
            (msri, node, lines, twisty_state, twisty_branch_ids) = self.linegraphdata[self.msri_index[index.row()]]
        else:
            (msri, node, lines, twisty_state, twisty_branch_ids) = (index.row(), None, [], None, [])
        
        if role == GraphNodeRole:
            if node is None:
                return QtCore.QVariant()
            return QVariant_fromList([QtCore.QVariant(nodei) for nodei in node])
        if role == GraphLinesRole:
            qlines = []
            for start, end, color, direct in lines:
                qlines.append(QVariant_fromList(
                    [QtCore.QVariant(start),
                     QtCore.QVariant(end),
                     QtCore.QVariant(color),
                     QtCore.QVariant(direct)]))
            return QVariant_fromList(qlines)
        if role == GraphTwistyStateRole:
            if twisty_state is None:
                return QtCore.QVariant()
            return QtCore.QVariant(twisty_state)
        
        (sequence_number, revid, merge_depth, revno_sequence, end_of_merge) = \
            self.merge_sorted_revisions[index.row()]
        
        if (role == QtCore.Qt.DisplayRole and index.column() == COL_REV) or \
                role == FilterRevnoRole:
            revnos = ".".join(["%d" % (revno)
                                      for revno in revno_sequence])
            return QtCore.QVariant(revnos)
        
        if role == TagsRole:
            tags = []
            if revid in self.tags:
                tags = list(self.tags[revid])
            return QtCore.QVariant(QtCore.QStringList(tags))
        
        if role == BranchTagsRole:
            tags = []
            if revid in self.heads:
                tags = [tag for (branch, tag, blr) in self.heads[revid][1] if tag]
            return QtCore.QVariant(QtCore.QStringList(tags))
        
        if role == RevIdRole or role == FilterIdRole:
            return QtCore.QVariant(revid)
        
        if role == FilterMessageRole or role == FilterAuthorRole:
            if revid not in self.revisions:
                return QtCore.QVariant()
        
        #Everything from here foward will need to have the revision loaded.
        if not revid or revid == NULL_REVISION:
            return QtCore.QVariant()
        revision = self._revision(revid)
        
        if role == QtCore.Qt.DisplayRole and index.column() == COL_DATE:
            return QtCore.QVariant(strftime("%Y-%m-%d %H:%M",
                                            localtime(revision.timestamp)))
        if role == QtCore.Qt.DisplayRole and index.column() == COL_AUTHOR:
            return QtCore.QVariant(extract_name(revision.get_apparent_author()))
        if role == QtCore.Qt.DisplayRole and index.column() == COL_MESSAGE:
            return QtCore.QVariant(revision.get_summary())
        if role == BugIdsRole:
            bugtext = gettext("bug #%s")
            bugs = []
            for bug in revision.properties.get('bugs', '').split('\n'):
                if bug:
                    url, status = bug.split(' ')
                    bug_id = get_bug_id(url)
                    if bug_id:
                        bugs.append(bugtext % bug_id)
            return QtCore.QVariant(QtCore.QStringList(bugs))
        
        if role == FilterMessageRole:
            return QtCore.QVariant(revision.message)
        if role == FilterAuthorRole:
            return QtCore.QVariant(revision.get_apparent_author())
        
        #return QtCore.QVariant(item.data(index.column()))
        return QtCore.QVariant()

    def flags(self, index):
        if not index.isValid():
            return QtCore.Qt.ItemIsEnabled

        return QtCore.Qt.ItemIsEnabled | QtCore.Qt.ItemIsSelectable

    def headerData(self, section, orientation, role):
        if orientation == QtCore.Qt.Horizontal and role == QtCore.Qt.DisplayRole:
            return QtCore.QVariant(self.horizontalHeaderLabels[section])
        return QtCore.QVariant()
    
    def _revision(self, revid):
        if revid not in self.revisions:
            revision = None
            for repo in self.repos.itervalues():
                try:
                    revision = repo.get_revisions([revid])[0]
                    revision.repository = repo
                    break
                except errors.NoSuchRevision:
                    pass
            
            self.revisions[revid] = revision
            revno_sequence = self.merge_sorted_revisions[self.revid_msri[revid]][3]
            revision.revno = ".".join(["%d" % (revno)
                                      for revno in revno_sequence])
            revision.tags = sorted(self.tags.get(revision.revision_id, []))
        else:
            revision = self.revisions[revid]
        return revision
    
    def revision(self, revid):
        revision = self._revision(revid)
        if not hasattr(revision, 'parents'):
            revision.parents = [self._revision(i) for i in self.graph_parents[revid]]
        if not hasattr(revision, 'children'):
            revision.children = [self._revision(i) for i in self.graph_children[revid]]
        return revision
    
    def _loadNextRevision(self):
        if self.stop_revision_loading:
            self.stop_revision_loading = False
            return
        try:
            if self.searchMode:
                def notifyChanges(revisionsChanged):
                    if self.closing: return
                    for revid in revisionsChanged:
                        index = self.indexFromRevId(revid)
                        self.graphFilterProxyModel.invalidateCacheRow(index.row())
                        self.emit(QtCore.SIGNAL("dataChanged(QModelIndex, QModelIndex)"),
                                  index,index)
                    revisionsChanged = []
                    self.processEvents()
                    self.compute_lines()
                
                notify_on_count = 10
                revisionsChanged = []
                try:
                    for repo in self.repos:
                        repo.lock_read()
                    try:
                        while self.searchMode and not self.closing:
                            nextRevId = self._nextRevisionToLoadGen.next()
                            self._revision(nextRevId)
                            revisionsChanged.append(nextRevId)
                            self.processEvents()
                            if len(revisionsChanged) >= notify_on_count:
                                notifyChanges(revisionsChanged)
                                notify_on_count = max(notify_on_count * 2, 200)
                    finally:
                        for repo in self.repos:
                            repo.unlock()
                except StopIteration, se:
                    self.graphFilterProxyModel.invalidateCache()
                    notifyChanges(revisionsChanged)
                    raise se
            else:
                nextRevId = self._nextRevisionToLoadGen.next()
                self._revision(nextRevId)
            QtCore.QTimer.singleShot(5, self._loadNextRevision)
        except StopIteration:
            pass
    
    def _nextRevisionToLoad(self):
        if not self.searchMode:
            for (msri, node, lines,
                 twisty_state, twisty_branch_ids) in self.linegraphdata:
                revid = self.merge_sorted_revisions[msri][1]
                if revid not in self.revisions:
                    yield revid
        if self.touches_file_msri is not None:
            for msri in self.touches_file_msri :
                revid = self.merge_sorted_revisions[msri][1]
                if revid not in self.revisions:
                    yield revid
        else:
            for (sequence_number,
                 revid,
                 merge_depth,
                 revno_sequence,
                 end_of_merge) in self.merge_sorted_revisions:
                if revid not in self.revisions:
                    yield revid

    def indexFromRevId(self, revid):
        msri = self.revid_msri[revid]
        return self.createIndex (msri, 0, QtCore.QModelIndex())
    
    def findChildBranchMergeRevision (self, revid):
        msri = self.revid_msri[revid]
        merged_by_msri = self.merge_info[msri][1]
        if merged_by_msri:
            return self.merge_sorted_revisions[merged_by_msri][1]
        else:
            return None
    
    def revisionHeadInfo(self, revid):
        if revid in self.revid_head:
            head_revid = self.revid_head[revid]
        else:
            head_revid = self.start_revs[0]
        return self.heads[head_revid][1]
    
class GraphFilterProxyModel(QtGui.QSortFilterProxyModel):
    def __init__(self, parent = None):
        self.old_filter_str = ""
        self.old_filter_role = 0
        QtGui.QSortFilterProxyModel.__init__(self, parent)
        self.cache = {}
        self.search_matching_revid = None
        self.search_indexes = []
        self.filter_str = u""
        self.filter_role = FilterMessageRole
        self._sourceModel = None
    
    def setFilter(self, str, role):
        if not unicode(str) == self.filter_str or not role == self.filter_role:
            if role == FilterSearchRole:
                self.setFilterSearch(str)
                self.setFilterRegExp("")
            else:
                self.setFilterRegExp(str)
                self.setFilterRole(role)
                self.setFilterSearch("")
            self.invalidateCache()
            self.sm().compute_lines()
            
            self.filter_str = unicode(str)
            self.filter_role = role
    
    def setSearchIndexes(self, indexes):
        self.search_indexes = indexes

    def setFilterSearch(self, s):
        if s == "" or not self.search_indexes or not have_search:
            self.search_matching_revid = None
        else:
            s = str(s).strip()
            query = [(query_item,) for query_item in s.split(" ")]
            self.search_matching_revid = {}
            for index in self.search_indexes:
                for result in index.search(query):
                    if isinstance(result, search_index.RevisionHit):
                        self.search_matching_revid[result.revision_key[0]] = True
                    if isinstance(result, search_index.FileTextHit):
                        self.search_matching_revid[result.text_key[1]] = True
                    if isinstance(result, search_index.PathHit):
                        pass
    
    def sm(self):
        if not self._sourceModel:
            self._sourceModel = self.sourceModel()
        return self._sourceModel
    
    def invalidateCache (self):
        self.cache = {}
        self._sourceModel = None
    
    def invalidateCacheRow (self, source_row):
        if source_row in self.cache:
            del self.cache[source_row]
        merged_by = self.sm().merge_info[source_row][1]
        if merged_by:
            self.invalidateCacheRow(merged_by)
    
    def filterAcceptsRow(self, source_row, source_parent):
        sm = self.sm()
        
        (sequence_number,
         revid,
         merge_depth,
         revno_sequence,
         end_of_merge) = sm.merge_sorted_revisions[source_row]
        
        branch_id = revno_sequence[0:-1]
        if not sm.branch_lines[branch_id][1]: # branch colapased
            return False
        
        return self.filterAcceptsRowIfBranchVisible(source_row, source_parent)

    def filterAcceptsRowIfBranchVisible(self, source_row, source_parent):
        if source_row not in self.cache:
            self.cache[source_row] = self._filterAcceptsRowIfBranchVisible(source_row, source_parent)
        return self.cache[source_row]
        
    def _filterAcceptsRowIfBranchVisible(self, source_row, source_parent):
        sm = self.sm()
        
        for parent_msri in sm.merge_info[source_row][0]:
            if self.filterAcceptsRowIfBranchVisible(parent_msri, source_parent):
                return True
        
        if sm.touches_file_msri is not None:
            if source_row not in sm.touches_file_msri:
                return False
        
        if self.search_matching_revid is not None:
            (sequence_number,
             revid,
             merge_depth,
             revno_sequence,
             end_of_merge) = sm.merge_sorted_revisions[source_row]
            return revid in self.search_matching_revid
        
        if self.filter_str:
            return QtGui.QSortFilterProxyModel.filterAcceptsRow(self, source_row, source_parent)
        
        return True
