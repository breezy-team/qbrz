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
from bzrlib import lazy_regex
from bzrlib.revision import NULL_REVISION
from bzrlib.tsort import merge_sort
from bzrlib.plugins.qbzr.lib.diff import DiffWindow
from bzrlib.plugins.qbzr.lib.i18n import gettext
from bzrlib.plugins.qbzr.lib.util import (
    extract_name,
    )

TagsRole = QtCore.Qt.UserRole + 1
BugIdsRole = QtCore.Qt.UserRole + 2
GraphNodeRole = QtCore.Qt.UserRole + 3
GraphLinesRole = QtCore.Qt.UserRole + 4
GraphTwistyStateRole = QtCore.Qt.UserRole + 5
RevIdRole = QtCore.Qt.UserRole + 6

FilterIdRole = QtCore.Qt.UserRole + 100
FilterMessageRole = QtCore.Qt.UserRole + 101
FilterAuthorRole = QtCore.Qt.UserRole + 102
FilterRevnoRole = QtCore.Qt.UserRole + 103

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

def get_bug_id(branch, bug_url):
    match = _bug_id_re.search(bug_url)
    if match:
        return match.group(1)
    return None


class GraphModel(QtCore.QAbstractTableModel):

    def __init__(self, parent=None):
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
    
    def setGraphFilterProxyModel(self, graphFilterProxyModel):
        self.graphFilterProxyModel = graphFilterProxyModel
    
    
    def loadBranch(self, branch, start_revs = None, specific_fileid = None):
        self.branch = branch
        branch.lock_read()
        try:
            self.emit(QtCore.SIGNAL("layoutAboutToBeChanged()"))
            self.tags = branch.tags.get_reverse_tag_dict()  # revid to tags map
            self.revisions = {}
            if start_revs is None:
                start_revs = [branch.last_revision()]
            start_revs = [rev for rev in start_revs if not rev == NULL_REVISION]
            graph = branch.repository.get_graph()
            self.graph_parents = {}
            ghosts = set()
            self.graph_children = {}
            for (revid, parent_revids) in graph.iter_ancestry(start_revs):
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
                    QtCore.QCoreApplication.processEvents()
            for ghost in ghosts:
                for ghost_child in self.graph_children[ghost]:
                    self.graph_parents[ghost_child] = [p for p in self.graph_parents[ghost_child]
                                                  if p not in ghosts]
            self.graph_parents["top:"] = start_revs
        
            if len(self.graph_parents)>0:
                self.merge_sorted_revisions = merge_sort(
                    self.graph_parents,
                    "top:",
                    generate_revno=True)
            else:
                self.merge_sorted_revisions = ()
            
            assert self.merge_sorted_revisions[0][1] == "top:"
            self.merge_sorted_revisions = self.merge_sorted_revisions[1:]
            
            # This will hold, for each "branch", [a list of revision indexes in
            # the branch, is the branch visible, parents, children].
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
                    #initialy, only the main line is visible
                    branch_line = [[],
                                   len(branch_id)==0,
                                   set(),
                                   set()]
                    self.branch_lines[branch_id] = branch_line
                else:
                    branch_line = self.branch_lines[branch_id]
                
                branch_line[0].append(rev_index)
                for child_revid in self.graph_children[revid]:
                    child_msri = self.revid_msri[child_revid]
                    child_branch_id = self.merge_sorted_revisions[child_msri][3][0:-1]
                    if not child_branch_id == branch_id and child_branch_id in self.branch_lines:
                        branch_line[3].add(child_branch_id)
                        self.branch_lines[child_branch_id][2].add(branch_id)
            
            self.branch_ids = self.branch_lines.keys()
        
            def branch_id_cmp(x, y):
                """Compaire branch_id's first by the number of digits, then reversed
                by their value"""
                len_x = len(x)
                len_y = len(y)
                if len_x == len_y:
                    return -cmp(x, y)
                return cmp(len_x, len_y)
            
            self.branch_ids.sort(branch_id_cmp)
            
            self.emit(QtCore.SIGNAL("layoutChanged()"))
            
            if specific_fileid is not None:
                self.touches_file_msri = []
                try:
                    branch.repository.texts.get_parent_map([])
                    use_texts = True
                except AttributeError:
                    use_texts = False
                    file_weave = branch.repository.weave_store.get_weave(specific_fileid,
                                        branch.repository.get_transaction())
                    weave_modifed_revisions = set(file_weave.versions())
                
                for rev_msri, (sequence_number,
                               revid,
                               merge_depth,
                               revno_sequence,
                               end_of_merge) in enumerate(self.merge_sorted_revisions):
                    if use_texts:
                        text_key = (specific_fileid, revid)
                        modified_text_versions = branch.repository.texts.get_parent_map([text_key])
                        changed = text_key in modified_text_versions
                    else:
                        changed = revid in weave_modifed_revisions
                    
                    if changed:
                        self.touches_file_msri.append(rev_msri)
                        index = self.createIndex (rev_msri, 0, QtCore.QModelIndex())
                        self.emit(QtCore.SIGNAL("dataChanged(QModelIndex, QModelIndex)"),
                                  index,index)
                    
                    if rev_msri % 100 == 0 :
                        self.graphFilterProxyModel.invalidateFilter()
                        QtCore.QCoreApplication.processEvents()
            
            self.graphFilterProxyModel.invalidateFilter()
            self.compute_lines()
            QtCore.QCoreApplication.processEvents()
            
            self._nextRevisionToLoadGen = self._nextRevisionToLoad()
            self._loadNextRevision()
        finally:
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
        self.linegraphdata = []
        self.msri_index = {}
        self.visible_msri = {}
        
        source_parent = QtCore.QModelIndex()
        for msri in xrange(0,len(self.merge_sorted_revisions)):
            if self.graphFilterProxyModel.filterAcceptsRowIfBranchVisible(msri, source_parent):
                self.visible_msri[msri] = True
            
            if self.graphFilterProxyModel.filterAcceptsRow(msri, source_parent):
                index = len(self.linegraphdata)
                self.msri_index[msri] = index
                self.linegraphdata.append([msri,
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
        empty_column = [False for i in range(len(self.linegraphdata))]
        # This will hold a bit map for each cell. If the cell is true, then
        # the cell allready contains a node or line. This use when deciding
        # what column to place a branch line or line in, without it
        # overlaping something else.
        columns = [list(empty_column)]
        
        
        for branch_id in self.branch_ids:
            (branch_rev_msri,
             branch_visible,
             branch_parents,
             branch_children) = self.branch_lines[branch_id]
            
            if branch_visible:
                branch_rev_msri = [rev_msri for rev_msri in branch_rev_msri
                                   if rev_msri in self.msri_index]
            else:
                branch_rev_msri = []
                
            if branch_rev_msri:
                color = reduce(lambda x, y: x+y, branch_id, 0)
                
                # Find columns for lines for each parent of each revision in
                # the branch that are long and need to go between the parent
                # branch and the child branch. Also add branch_ids to
                # twisty_branch_ids.
                parents_with_lines = []
                visible_parents = []
                for rev_msri in branch_rev_msri:
                    rev_index = self.msri_index[rev_msri]
                    (sequence_number,
                         revid,
                         merge_depth,
                         revno_sequence,
                         end_of_merge) = self.merge_sorted_revisions[rev_msri]
                    rev_visible_parents = list(\
                        self._find_visible_relations(revid,
                                                     self.graph_parents,
                                                     self.visible_msri))
                    visible_parents.append(rev_visible_parents)
                    
                    for (parent_revid, parent_msri, direct) in rev_visible_parents:
                        parent_branch_id = \
                            self.merge_sorted_revisions[parent_msri][3][0:-1]
                        parent_merge_depth = self.merge_sorted_revisions[parent_msri][2]

                        if (parent_branch_id != branch_id and  # Different Branch
                            (parent_merge_depth >= merge_depth or # Parent branch is deeeper
                             not self.branch_lines[parent_branch_id])): # Parent branch is not visible
                            self.linegraphdata[rev_index][4].append (parent_branch_id)
                        
                        if revno_sequence[-1] == 1 or \
                                parent_branch_id == branch_id or\
                                branch_id == ():
                            continue
                        
                        if parent_msri in self.msri_index:
                            parent_index = self.msri_index[parent_msri]                            
                            parent_node = self.linegraphdata[parent_index][1]
                            if parent_node:
                                parent_col_index = parent_node[0]
                            else:
                                parent_col_index = 0
                            col_search_order = \
                                _branch_line_col_search_order(columns, parent_col_index)
                                
                            
                            line_col_index = parent_col_index
                            if parent_index - rev_index >1:
                                line_range = range(rev_index + 1, parent_index)
                                line_col_index = \
                                    _find_free_column(columns,
                                                      empty_column,
                                                      col_search_order,
                                                      line_range)
                                _mark_column_as_used(columns,
                                                     line_col_index,
                                                     line_range)
                                lines.append((rev_index,
                                              parent_index,
                                              (line_col_index,),
                                              direct,
                                              ))
                                parents_with_lines.append(parent_revid)
                    
                    # Work out if the twisty needs to show a + or -. If all
                    # twisty_branch_ids are visible, show - else +.
                    if len (self.linegraphdata[rev_index][4])>0:
                        twisty_state = True
                        for twisty_branch_id in self.linegraphdata[rev_index][4]:
                            if not self.branch_lines[twisty_branch_id][1]:
                                twisty_state = False
                                break
                        self.linegraphdata[rev_index][3] = twisty_state
                
                # Find a column for this branch.
                #
                # Find the col_index for the direct parent branch. This will
                # be the starting point when looking for a free column.
                
                parent_col_index = 0
                parent_index = None
                
                if visible_parents[-1]:
                    parent_msri = self.revid_msri[visible_parents[-1][0][0]]
                    parent_index = self.msri_index[parent_msri]
                    parent_node = self.linegraphdata[parent_index][1]
                    if parent_node:
                        parent_col_index = parent_node[0]
                
                col_search_order = _branch_line_col_search_order(columns,
                                                                 parent_col_index)
                cur_cont_line = []
                
                # Work out what rows this branch spans
                line_range = []
                first_rev_index = self.msri_index[branch_rev_msri[0]]
                last_rev_index = self.msri_index[branch_rev_msri[-1]]
                line_range = range(first_rev_index, last_rev_index+1)
                
                if parent_index:
                    line_range.extend(range(last_rev_index+1, parent_index))
                
                col_index = _find_free_column(columns,
                                              empty_column,
                                              col_search_order,
                                              line_range)
                node = (col_index, color)
                # Free column for this branch found. Set node for all
                # revision in this branch.
                for rev_msri in branch_rev_msri:
                    rev_index = self.msri_index[rev_msri]
                    self.linegraphdata[rev_index][1] = node
                    columns[col_index][rev_index] = True
                
                # Find columns for lines for each parent of each
                # revision in the branch.
                for i, rev_msri in enumerate(branch_rev_msri):
                    rev_index = self.msri_index[rev_msri]
                    (sequence_number,
                         revid,
                         merge_depth,
                         revno_sequence,
                         end_of_merge) = self.merge_sorted_revisions[rev_msri]
                    
                    col_index = self.linegraphdata[rev_index][1][0]
                    
                    for (parent_revid, parent_msri, direct) in visible_parents[i]:
                        if parent_revid in parents_with_lines:
                            continue
                        if parent_msri in self.msri_index:
                            parent_index = self.msri_index[parent_msri]                            
                            parent_node = self.linegraphdata[parent_index][1]
                            if parent_node:
                                parent_col_index = parent_node[0]
                            else:
                                parent_col_index = None
                            col_search_order = \
                                    _line_col_search_order(columns,
                                                           parent_col_index,
                                                           col_index)
                                
                            line_col_index = col_index
                            if parent_index - rev_index >1:
                                line_range = range(rev_index + 1, parent_index)
                                line_col_index = \
                                    _find_free_column(columns,
                                                      empty_column,
                                                      col_search_order,
                                                      line_range)
                                _mark_column_as_used(columns,
                                                     line_col_index,
                                                     line_range)
                            lines.append((rev_index,
                                          parent_index,
                                          (line_col_index,),
                                          direct,
                                          ))
                    
                    if i == 0:
                        for (child_revid, child_msri, direct) in \
                                self._find_visible_relations(revid,
                                                             self.graph_children,
                                                             self.msri_index):
                            if not direct:
                                if child_msri in self.msri_index:
                                    child_index = self.msri_index[child_msri]                            
                                    child_node = self.linegraphdata[child_index][1]
                                    if child_node:
                                        child_col_index = child_node[0]
                                    else:
                                        child_col_index = None
                                    col_search_order = \
                                            _line_col_search_order(columns,
                                                                   child_col_index,
                                                                   col_index)
                                        
                                    line_col_index = col_index
                                    if child_index - rev_index >1:
                                        line_range = range(child_index + 1, rev_index)
                                        line_col_index = \
                                            _find_free_column(columns,
                                                              empty_column,
                                                              col_search_order,
                                                              line_range)
                                        _mark_column_as_used(columns,
                                                             line_col_index,
                                                             line_range)
                                    lines.append((child_index,
                                                  rev_index,
                                                  (line_col_index,),
                                                  direct,
                                                  ))
        
        # It has now been calculated which column a line must go into. Now
        # copy the lines in to linegraphdata.
        for (child_index,
             parent_index,
             line_col_indexes,
             direct,
             ) in lines:
            
            if child_index is not None:
                (child_col_index, child_color) = self.linegraphdata[child_index][1]
            else:
                (child_col_index, child_color) = self.linegraphdata[parent_index][1]
            
            if parent_index is not None:
                (parent_col_index, parent_color) = self.linegraphdata[parent_index][1]
            else:
                (parent_col_index, parent_color) = (child_col_index, parent_color)
            
            if len(line_col_indexes) == 1:
                assert parent_index is not None
                if parent_index - child_index == 1:
                    self.linegraphdata[child_index][2].append(
                        (child_col_index,
                         parent_col_index,
                         parent_color,
                         direct))
                else:
                    # line from the child's column to the lines column
                    self.linegraphdata[child_index][2].append(
                        (child_col_index,
                         line_col_indexes[0],
                         parent_color,
                         direct))
                    # lines down the line's column
                    for line_part_index in range(child_index+1, parent_index-1):
                        self.linegraphdata[line_part_index][2].append(
                            (line_col_indexes[0],   
                             line_col_indexes[0],
                             parent_color,
                             direct))
                    # line from the line's column to the parent's column
                    self.linegraphdata[parent_index-1][2].append(
                        (line_col_indexes[0],
                         parent_col_index,
                         parent_color,
                         direct))

        self.emit(QtCore.SIGNAL("dataChanged(QModelIndex, QModelIndex)"),
                  self.createIndex (0, COL_MESSAGE, QtCore.QModelIndex()),
                  self.createIndex (len(self.merge_sorted_revisions), COL_MESSAGE, QtCore.QModelIndex()))
    
    def _find_visible_relations(self, revid, graph, visible):
        for rel_revid in graph[revid]:
            rel_msri = self.revid_msri[rel_revid]
            if rel_msri in visible:
                yield (rel_revid, rel_msri, True)
            else:
                while rel_revid and rel_msri not in visible:
                    rels = graph[rel_revid]
                    if len(rels) == 0:
                        rel_revid = None
                    else:
                        rel_revid = rels[0]
                        rel_msri = self.revid_msri[rel_revid]
                if rel_revid:
                    yield (rel_revid, rel_msri, False)
    
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
                    if not parent_branch_id==() and not self._has_visible_child(parent_branch_id):
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
        while not branch_id == () and not self._has_visible_child(branch_id):
            branch_id = list(self.branch_lines[branch_id][3])[0]
            has_change = self._set_branch_visible(branch_id, True, has_change)
        if has_change:
            self.compute_lines()
    
    def set_search_mode(self, searchMode):
        if not searchMode == self.searchMode:
            self.searchMode = searchMode
            if searchMode:
                self._nextRevisionToLoadGen = self._nextRevisionToLoad()
            else:
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
            return QtCore.QVariant([QtCore.QVariant(nodei) for nodei in node])
        if role == GraphLinesRole:
            qlines = []
            for start, end, color, direct in lines:
                if start is None: start = -1
                if end is None: end = -1
                qlines.append(QtCore.QVariant([QtCore.QVariant(start),
                                               QtCore.QVariant(end),
                                               QtCore.QVariant(color),
                                               QtCore.QVariant(direct)]))
            return QtCore.QVariant(qlines)
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
                tags = self.tags[revid]
            return QtCore.QVariant(tags)
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
                    bug_id = get_bug_id(self.branch, url)
                    if bug_id:
                        bugs.append(bugtext % bug_id)
            return QtCore.QVariant(bugs)
        
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
            revision = self.branch.repository.get_revisions([revid])[0]
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
        try:
            if self.searchMode:
                revisionsChanged = []
                while self.searchMode:
                    try:
                        nextRevId = self._nextRevisionToLoadGen.next()
                        self._revision(nextRevId)
                        revisionsChanged.append(nextRevId)
                        QtCore.QCoreApplication.processEvents()
                    finally:
                        if len(revisionsChanged) == 100:
                            for revid in revisionsChanged:
                                index = self.indexFromRevId(revid)
                                self.emit(QtCore.SIGNAL("dataChanged(QModelIndex, QModelIndex)"),
                                          index,index)
                            revisionsChanged = []
                            QtCore.QCoreApplication.processEvents()
            else:
                nextRevId = self._nextRevisionToLoadGen.next()
                self._revision(nextRevId)
            QtCore.QTimer.singleShot(5, self._loadNextRevision)
        except StopIteration:
            # All revisions are loaded.
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
        branch_id = self.merge_sorted_revisions[self.revid_msri[revid]][3][0:-1]
        current_revid = revid
        result_revid = None
        while current_revid is not None and result_revid is None:
            child_revids = self.graph_children[current_revid]
            current_revid = None
            for child_revid in child_revids:
                child_branch_id = self.merge_sorted_revisions[self.revid_msri[child_revid]][3][0:-1]
                if child_branch_id == branch_id:
                    current_revid = child_revid
                else:
                    if self.branch_lines[child_branch_id][1]:
                        result_revid = child_revid
                        break
        return result_revid
    
class GraphFilterProxyModel(QtGui.QSortFilterProxyModel):
    def __init__(self, parent = None):
        QtGui.QSortFilterProxyModel.__init__(self, parent)
        self.cache = {}
    
    def invalidateFilter (self):
        self.cache = {}
        QtGui.QSortFilterProxyModel.invalidateFilter(self)
    
    def filterAcceptsRow(self, source_row, source_parent):
        graphModel = self.sourceModel()
        
        (sequence_number,
         revid,
         merge_depth,
         revno_sequence,
         end_of_merge) = graphModel.merge_sorted_revisions[source_row]
        
        branch_id = revno_sequence[0:-1]
        if not graphModel.branch_lines[branch_id][1]: # branch colapased
            return False
        
        return self.filterAcceptsRowIfBranchVisible(source_row, source_parent)

    def filterAcceptsRowIfBranchVisible(self, source_row, source_parent):
        if source_row not in self.cache:
            self.cache[source_row] = self._filterAcceptsRowIfBranchVisible(source_row, source_parent)
        return self.cache[source_row]
        
    def _filterAcceptsRowIfBranchVisible(self, source_row, source_parent):
        graphModel = self.sourceModel()
        
        searchAccepts = QtGui.QSortFilterProxyModel.filterAcceptsRow(self, source_row, source_parent)
        if graphModel.touches_file_msri is not None:
            fileAccepts = source_row in graphModel.touches_file_msri
        else:
            fileAccepts = True
        
        if searchAccepts and fileAccepts:
            return True
        
        (sequence_number,
         revid,
         merge_depth,
         revno_sequence,
         end_of_merge) = graphModel.merge_sorted_revisions[source_row]
        branch_id = revno_sequence[0:-1]
        
        # Is any of the parents that this rev merges visible?
        for parent_revid in graphModel.graph_parents[revid]:
            parent_msri = graphModel.revid_msri[parent_revid]
            parent_branch_id = graphModel.merge_sorted_revisions[parent_msri][3][0:-1]
            if not branch_id==parent_branch_id:
                for parent_msri in graphModel.branch_lines[parent_branch_id][0]:
                    parent_merge_depth = graphModel.merge_sorted_revisions[parent_msri][2]
                    if parent_merge_depth > merge_depth:
                        if self.filterAcceptsRowIfBranchVisible(parent_msri, source_parent):
                            return True
        
        return False

    
def _branch_line_col_search_order(columns, parent_col_index):
    for col_index in range(parent_col_index, len(columns)):
        yield col_index
    for col_index in range(parent_col_index-1, -1, -1):
        yield col_index

def _line_col_search_order(columns, parent_col_index, child_col_index):
    if parent_col_index is not None:
        max_index = max(parent_col_index, child_col_index)
        min_index = min(parent_col_index, child_col_index)
        for col_index in range(max_index, min_index -1, -1):
            yield col_index
    else:
        max_index = child_col_index
        min_index = child_col_index
        yield child_col_index
    i = 1
    while max_index + i < len(columns) or \
          min_index - i > -1:
        if max_index + i < len(columns):
            yield max_index + i
        if min_index - i > -1:
            yield min_index - i
        i += 1

def _find_free_column(columns, empty_column, col_search_order, line_range):
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
        col_index = len(columns)
        column = list(empty_column)
        columns.append(column)
    return col_index

def _mark_column_as_used(columns, col_index, line_range):
    column = columns[col_index]
    for row_index in line_range:
        column[row_index] = True
