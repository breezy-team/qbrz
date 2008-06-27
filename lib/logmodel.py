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

#TODO: This list just coppied and pasted. Work out what we really need.
import sys
import re
from PyQt4 import QtCore, QtGui
from time import (strftime, localtime)
from bzrlib import bugtracker, lazy_regex
from bzrlib.log import LogFormatter, show_log
from bzrlib.revision import NULL_REVISION
from bzrlib.tsort import merge_sort
from bzrlib.plugins.qbzr.lib.diff import DiffWindow
from bzrlib.plugins.qbzr.lib.i18n import gettext
from bzrlib.plugins.qbzr.lib.util import (
    BTN_CLOSE,
    QBzrWindow,
    extract_name,
    format_revision_html,
    format_timestamp,
    htmlize,
    open_browser,
    RevisionMessageBrowser,
    )

TagsRole = QtCore.Qt.UserRole + 1
BugIdsRole = QtCore.Qt.UserRole + 2
GraphNodeRole = QtCore.Qt.UserRole + 3
GraphLinesRole = QtCore.Qt.UserRole + 4
GraphTwistiesRole = QtCore.Qt.UserRole + 5

FilterIdRole = QtCore.Qt.UserRole + 100
FilterMessageRole = QtCore.Qt.UserRole + 101
FilterAuthorRole = QtCore.Qt.UserRole + 102
FilterRevnoRole = QtCore.Qt.UserRole + 103

COL_REV = 0
COL_GRAPH = 1
COL_DATE = 2
COL_AUTHOR = 3
COL_MESSAGE = 4

_bug_id_re = lazy_regex.lazy_compile(r'(?:bugs/|ticket/|show_bug\.cgi\?id=)(\d+)(?:\b|$)')

def get_bug_id(branch, bug_url):
    match = _bug_id_re.search(bug_url)
    if match:
        return match.group(1)
    return None

class TreeModel(QtCore.QAbstractTableModel):
    def __init__(self, parent=None):
        QtCore.QAbstractTableModel.__init__(self, parent)
        
        self.horizontalHeaderLabels = [gettext("Rev"),
                                       gettext("Graph"),
                                       gettext("Date"),
                                       gettext("Author"),
                                       gettext("Message"),
                                       ]
        
        self.linegraphdata = []
        self.index = {}
        self.columns_len = 0
        self.revisions = {}
        self.tags = {}
    
    def loadBranch(self, branch, start_revs = None):
        self.branch = branch
        branch.lock_read()
        try:
            self.revisions = {}
            if start_revs is None:
                start_revs = [branch.last_revision()]
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
            # the branch, is the branch visible].
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
                
                branch_line = None
                if branch_id not in self.branch_lines:
                    #initialy, only the main line is visible
                    branch_line = [[], len(branch_id)==0]
                    self.branch_lines[branch_id] = branch_line
                else:
                    branch_line = self.branch_lines[branch_id]
                
                branch_line[0].append(rev_index)
                self.revid_msri[revid] = rev_index
                self.revno_msri[revno_sequence] = rev_index
        
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
            self.tags = branch.tags.get_reverse_tag_dict()
            
            self.compute_lines()
        finally:
            branch.unlock
        
    def compute_lines(self, broken_line_length = None):
        self.emit(QtCore.SIGNAL("layoutAboutToBeChanged()"))
        try:
            # This will hold for each revision, a list of (msri,
            #                                              node,
            #                                              lines,
            #                                              twisties).
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
            # color) with start and end being zero-indexed column numbers and
            # color as in node.
            #
            # twisties are +- buttons to show/hide branches. list of Tuple of
            # (column, open, branch_id, color)
            self.linegraphdata = []
            
            msri_index = {}
            
            rev_index = 0
            for branch_id in self.branch_ids:
                branch_rev_msri, branch_visible = self.branch_lines[branch_id]
                if branch_visible:
                    for rev_msri in branch_rev_msri:
                        self.linegraphdata.append([rev_msri,
                                                   None,
                                                   [],
                                                   [],
                                                  ])
            self.linegraphdata.sort(lambda x, y: cmp(x[0], y[0]))
            
            for rev_index, (msri, node, lines, twisties) in \
                    enumerate(self.linegraphdata):
                msri_index[msri] = rev_index
            
            # This will hold a tuple of (child_index, parent_index, col_index,
            # parent_color, twisty_branch_id) for each line that needs to be
            # drawn. If col_index is not none, then the line is drawn along that
            # column, else the the line can be drawn directly between the child
            # and parent because either the child and parent are in the same
            # branch line, or the child and parent are 1 row apart.
            lines = []
            empty_column = [False for i in range(len(self.linegraphdata))]
            # This will hold a bit map for each cell. If the cell is true, then
            # the cell allready contains a node or line. This use when deciding
            # what column to place a branch line or line in, without it
            # overlaping something else.
            columns = [list(empty_column)]
            
            
            for branch_id in self.branch_ids:
                branch_rev_indexes, branch_visible = self.branch_lines[branch_id]
                
                if branch_visible:
                    color = reduce(lambda x, y: x+y, branch_id, 0)
                    
                    # Find a column for this branch.
                    #
                    # Find the col_index for the direct parent branch. This will
                    # be the starting point when looking for a free column.
                    parent_col_index = 0
                    parent_index = None
                    if len(branch_id) > 1:
                        parent_revno = branch_id[0:-1]
                        parent_msri = self.revno_msri[parent_revno]
                        if parent_msri in msri_index:
                            parent_index = msri_index[parent_msri]
                            parent_node = self.linegraphdata[parent_index][1]
                            if parent_node:
                                parent_col_index = parent_node[0]
                    
                    col_search_order = _branch_line_col_search_order(columns,
                                                                     parent_col_index)
                    cur_cont_line = []
                    
                    # Work out what rows this branch spans
                    line_range = []
                    last_rev_index = None
                    for rev_msri in branch_rev_indexes:
                        rev_index = msri_index[rev_msri]
                        if last_rev_index:
                            if broken_line_length and \
                               rev_index - last_rev_index > broken_line_length:
                                line_range.append(last_rev_index+1)
                                line_range.append(rev_index-1)
                            else:
                                line_range.extend(range(last_rev_index+1, rev_index))
                        
                        line_range.append(rev_index)
                        last_rev_index = rev_index
                    
                    if parent_index:
                        if broken_line_length and \
                           parent_index - last_rev_index > broken_line_length:
                            line_range.append(last_rev_index+1)
                        else:
                            line_range.extend(range(last_rev_index+1, parent_index))
                    
                    col_index = _find_free_column(columns,
                                                  empty_column,
                                                  col_search_order,
                                                  line_range)
                    node = (col_index, color)
                    # Free column for this branch found. Set node for all
                    # revision in this branch.
                    for rev_msri in branch_rev_indexes:
                        rev_index = msri_index[rev_msri]
                        self.linegraphdata[rev_index][1] = node
                        columns[col_index][rev_index] = True
                    
                    # Find columns for lines for each parent of each
                    # revision in the branch.
                    for rev_msri in branch_rev_indexes:
                        rev_index = msri_index[rev_msri]
                        (sequence_number,
                             revid,
                             merge_depth,
                             revno_sequence,
                             end_of_merge) = self.merge_sorted_revisions[rev_msri]
                        
                        col_index = self.linegraphdata[rev_index][1][0]
                        
                        for parent_revid in self.graph_parents[revid]:
                            parent_msri = self.revid_msri[parent_revid]
                            # We have to recalculate the color of the parent,
                            # because it may be hidden, an not yet calculated
                            parent_branch_id = \
                                self.merge_sorted_revisions[parent_msri][3][0:-1]
                            
                            parent_color = \
                                reduce(lambda x, y: x+y, parent_branch_id, 0)
                            
                            
                            if not parent_branch_id == branch_id and \
                               not parent_branch_id == ():
                                twisty_branch_id = parent_branch_id
                            else:
                                twisty_branch_id = None
                            
                            if parent_msri in msri_index:
                                parent_index = msri_index[parent_msri]                            
                                parent_node = self.linegraphdata[parent_index][1]
                                if parent_node:
                                    parent_col_index = parent_node[0]
                                else:
                                    parent_col_index = None
                                col_search_order = \
                                        _line_col_search_order(columns,
                                                               parent_col_index,
                                                               col_index)
                                    
                                # If this line is really long, break it.
                                if len(branch_id) > 0 and \
                                   broken_line_length and \
                                   parent_index - rev_index > broken_line_length:
                                    child_line_col_index = \
                                        _find_free_column(columns,
                                                          empty_column,
                                                          col_search_order,
                                                          (rev_index + 1,))
                                    _mark_column_as_used(columns,
                                                         child_line_col_index,
                                                         (rev_index + 1,))
                                    
                                    # Recall _line_col_search_order to reset it back to
                                    # the start.
                                    col_search_order = \
                                            _line_col_search_order(columns,
                                                                   parent_col_index,
                                                                   col_index)
                                    parent_col_line_index = \
                                        _find_free_column(columns,
                                                          empty_column,
                                                          col_search_order,
                                                          (parent_index - 1,))
                                    _mark_column_as_used(columns,
                                                         parent_col_line_index,
                                                         (parent_index - 1,))
                                    lines.append((rev_index,
                                                  parent_index,
                                                  (child_line_col_index,
                                                   parent_col_line_index),
                                                  parent_color,
                                                  twisty_branch_id))
                                else :
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
                                                  parent_color,
                                                  twisty_branch_id))
                            else:
                                # The parent is probably hidden. Just show a
                                # broken stub.
                                col_search_order = \
                                        _line_col_search_order(columns,
                                                               parent_col_index,
                                                               col_index)
                                child_line_col_index = \
                                    _find_free_column(columns,
                                                      empty_column,
                                                      col_search_order,
                                                      (rev_index + 1,))
                                
                                _mark_column_as_used(columns,
                                                     child_line_col_index,
                                                     (rev_index + 1,))
                                lines.append((rev_index,
                                              None,
                                              (child_line_col_index, None),
                                              parent_color,
                                              twisty_branch_id))                                
            
            # It has now been calculated which column a line must go into. Now
            # copy the lines in to linegraphdata.
            for (child_index,
                 parent_index,
                 line_col_indexes,
                 parent_color,
                 twisty_branch_id) in lines:
                
                (child_col_index, child_color) = self.linegraphdata[child_index][1]
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
                             parent_color))
                        if parent_col_index == child_col_index:
                            twisty_col_index = parent_col_index                                        
                        elif parent_col_index < child_col_index:
                            twisty_col_index = parent_col_index + 0.5
                        else:
                            twisty_col_index = parent_col_index - 0.5                        
                    else:
                        # line from the child's column to the lines column
                        self.linegraphdata[child_index][2].append(
                            (child_col_index,
                             line_col_indexes[0],
                             parent_color))
                        # lines down the line's column
                        for line_part_index in range(child_index+1, parent_index-1):
                            self.linegraphdata[line_part_index][2].append(
                                (line_col_indexes[0],   
                                 line_col_indexes[0],
                                 parent_color))
                        # line from the line's column to the parent's column
                        self.linegraphdata[parent_index-1][2].append(
                            (line_col_indexes[0],
                             parent_col_index,
                             parent_color))
                        
                        if line_col_indexes[0] == child_col_index:
                            twisty_col_index = line_col_indexes[0]                                        
                        elif line_col_indexes[0] < child_col_index:
                            twisty_col_index = line_col_indexes[0] + 0.5
                        else:
                            twisty_col_index = line_col_indexes[0] - 0.5                        
                else:
                    # Broken line
                    # line from the child's column to the lines column
                    self.linegraphdata[child_index][2].append(
                        (child_col_index,
                         line_col_indexes[0],
                         parent_color))
                    # Broken line end
                    self.linegraphdata[child_index+1][2].append(
                        (line_col_indexes[0],
                         None,
                         parent_color))
                    
                    if line_col_indexes[1] is not None:
                        # Broken line end 
                        self.linegraphdata[parent_index-2][2].append(
                            (None,
                             line_col_indexes[1],
                             parent_color))
                        # line from the line's column to the parent's column
                        self.linegraphdata[parent_index-1][2].append(
                            (line_col_indexes[1],
                             parent_col_index,
                             parent_color))
                    
                    if line_col_indexes[0] == child_col_index:
                        twisty_col_index = line_col_indexes[0]                                        
                    elif line_col_indexes[0] < child_col_index:
                        twisty_col_index = line_col_indexes[0] + 0.5
                    else:
                        twisty_col_index = line_col_indexes[0] - 0.5
                
                if twisty_branch_id is not None:
                    self.linegraphdata[child_index][3].append (\
                        (twisty_col_index,
                         self.branch_lines[twisty_branch_id][1],
                         twisty_branch_id,
                         parent_color))
        
        finally:
            self.emit(QtCore.SIGNAL("layoutChanged()"))

    def columnCount(self, parent):
        if parent.isValid():
            return 0
        return len(self.horizontalHeaderLabels)

    def rowCount(self, parent):
        if parent.isValid():
            return 0
        return len(self.linegraphdata)
    
    def data(self, index, role):
        if not index.isValid():
            return QtCore.QVariant()
        
        (msri, node, lines, twisties) = self.linegraphdata[index.row()]
        
        if role == GraphNodeRole:
            return QtCore.QVariant([QtCore.QVariant(nodei) for nodei in node])
        if role == GraphLinesRole:
            qlines = []
            for start, end, color in lines:
                if start is None: start = -1
                if end is None: end = -1
                qlines.append(QtCore.QVariant([QtCore.QVariant(start),
                                               QtCore.QVariant(end),
                                               QtCore.QVariant(color)]))
            return QtCore.QVariant(qlines)
        if role == GraphTwistiesRole:
            qtwisties = []
            for column, open, branch_id, color in twisties:
                branch_id = [QtCore.QVariant(i) for i in branch_id]
                qtwisties.append(QtCore.QVariant([QtCore.QVariant(column),
                                                  QtCore.QVariant(open),
                                                  QtCore.QVariant(branch_id),
                                                  QtCore.QVariant(color)]))
            return QtCore.QVariant(qtwisties)
        
        (sequence_number, revid, merge_depth, revno_sequence, end_of_merge) = \
            self.merge_sorted_revisions[msri]
        
        if role == QtCore.Qt.DisplayRole and index.column() == COL_REV:
            revnos = ".".join(["%d" % (revno)
                                      for revno in revno_sequence])
            return QtCore.QVariant(revnos)
        
        if role == TagsRole:
            tags = []
            if revid in self.tags:
                tags = self.tags[revid]
            return QtCore.QVariant(tags)
        
        #Everything from here foward will need to have the revision loaded.
        if not revid or revid == NULL_REVISION:
            return QtCore.QVariant()
        if revid not in self.revisions:
            revision = self.branch.repository.get_revisions([revid])[0]
            self.revisions[revid] = revision
        else:
            revision = self.revisions[revid]
        
        if role == QtCore.Qt.DisplayRole and index.column() == COL_DATE:
            return QtCore.QVariant(strftime("%Y-%m-%d %H:%M",
                                            localtime(revision.timestamp)))
        if role == QtCore.Qt.DisplayRole and index.column() == COL_AUTHOR:
            return QtCore.QVariant(extract_name(revision.committer))
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