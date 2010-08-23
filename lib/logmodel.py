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

from bzrlib.revision import CURRENT_REVISION, Revision

from bzrlib.plugins.qbzr.lib.bugs import get_bug_id
from bzrlib.plugins.qbzr.lib import loggraphprovider
from bzrlib.plugins.qbzr.lib.lazycachedrevloader import cached_revisions
from bzrlib.plugins.qbzr.lib.revtreeview import RevIdRole as im_RevIdRole
from bzrlib.plugins.qbzr.lib.i18n import gettext
from bzrlib.plugins.qbzr.lib.util import (
    extract_name,
    get_apparent_author,
    runs_in_loading_queue,
    )

RevIdRole = im_RevIdRole
(TagsRole,
 BugIdsRole,
 BranchTagsRole,
 GraphNodeRole,
 GraphLinesRole,
 GraphTwistyStateRole,
) = range(QtCore.Qt.UserRole + 2, QtCore.Qt.UserRole + 8)

header_labels = (gettext("Rev"),
                 gettext("Message"),
                 gettext("Date"),
                 gettext("Author"), )

(COL_REV,
 COL_MESSAGE,
 COL_DATE,
 COL_AUTHOR,
) = range(len(header_labels))


try:
    QVariant_fromList = QtCore.QVariant.fromList
except AttributeError:
    QVariant_fromList = QtCore.QVariant


class WorkingTreeRevision(Revision):
    def __init__(self, revid, tree):
        super(WorkingTreeRevision, self).__init__(revid)
        
        self.parent_ids = tree.get_parent_ids()
        self.committer = tree.branch.get_config().username()
        self.message = "" # todo: try load saved commit message
        self.timestamp = None
        self.tree = tree

class LogGraphProvider(loggraphprovider.LogGraphProvider):
    
    def __init__(self, branches, primary_bi, no_graph,
                 processEvents,  throbber):
        loggraphprovider.LogGraphProvider.__init__(
            self, branches, primary_bi, no_graph)
        self.processEvents = processEvents
        self.throbber = throbber
        self.on_filter_changed = self.compute_graph_lines
    
    def update_ui(self):
        self.processEvents()
    
    def throbber_show(self):
        self.throbber.show()
    
    def throbber_hide(self):
        self.throbber.hide()
    
    def revisions_filter_changed(self):
        self.on_filter_changed()

class PendingMergesGraphProvider(loggraphprovider.PendingMergesGraphProvider,
                                 LogGraphProvider):
    pass

class WithWorkingTreeGraphProvider(loggraphprovider.WithWorkingTreeGraphProvider,
                                   LogGraphProvider):
    
    def load(self):
        super(LogGraphProvider, self).load()
        
        for bi in self.branches:
            if not bi.tree is None:
                wt_revid = CURRENT_REVISION + bi.tree.basedir
                if wt_revid in self.revid_head_info:
                    cached_revisions[wt_revid] = WorkingTreeRevision(wt_revid, bi.tree)

class LogModel(QtCore.QAbstractTableModel):

    def __init__(self, processEvents, throbber, parent=None):
        QtCore.QAbstractTableModel.__init__(self, parent)
        self.processEvents = processEvents
        self.throbber = throbber
        
        self.graph_provider = LogGraphProvider((), None, False,
                                               processEvents, throbber)
        self.state = loggraphprovider.GraphProviderFilterState(self.graph_provider)
        self.computed = loggraphprovider.ComputedGraph(self.graph_provider)

        self.clicked_row = None
        self.last_rev_is_placeholder = False
    
    def load(self, branches, primary_bi, file_ids, no_graph,
             graph_provider_type):
        self.throbber.show()
        self.processEvents()        
        try:
            graph_provider = graph_provider_type(
                branches, primary_bi, no_graph, 
                processEvents=self.processEvents, throbber=self.throbber)
            graph_provider.load()
            graph_provider.on_filter_changed = self.on_filter_changed
            
            state = loggraphprovider.GraphProviderFilterState(graph_provider)
            state.branch_line_state.update(self.state.branch_line_state)
            
            self.emit(QtCore.SIGNAL("layoutAboutToBeChanged()"))
            self.graph_provider = graph_provider
            self.state = state
            self.computed = loggraphprovider.ComputedGraph(graph_provider)
            self.emit(QtCore.SIGNAL("layoutChanged()"))
            
            self.compute_lines()
        finally:
            self.throbber.hide()
        
        # Start later so that it does not run in the loading queue.
        #QtCore.QTimer.singleShot(1, self.graph_provider.load_filter_file_id)
    
    def compute_lines(self):
        self.computed = self.graph_provider.compute_graph_lines(self.state)
        self.emit(QtCore.SIGNAL("dataChanged(QModelIndex, QModelIndex)"),
                  self.createIndex (0, COL_MESSAGE, QtCore.QModelIndex()),
                  self.createIndex (len(self.graph_provider.revisions),
                                    COL_MESSAGE, QtCore.QModelIndex()))
        self.emit(QtCore.SIGNAL("linesUpdated()"))
    
    def collapse_expand_rev(self, revid, visible):
        self.clicked_row = self.graph_provider.revid_rev[revid].index
        clicked_row_index = self.createIndex (self.clicked_row,
                                              COL_MESSAGE,
                                              QtCore.QModelIndex())
        self.emit(QtCore.SIGNAL("dataChanged(QModelIndex, QModelIndex)"),
                  clicked_row_index,
                  clicked_row_index)
        self.graph_provider.update_ui()
        self.clicked_row = None
        has_change = self.graph_provider.collapse_expand_rev(revid, visible)
        
        if has_change:
            self.compute_lines()
        else:
            self.emit(QtCore.SIGNAL("dataChanged(QModelIndex, QModelIndex)"),
                      clicked_row_index,
                      clicked_row_index)
    
    def has_rev_id(self, revid):
        return self.graph_provider.has_revid(revid)
    
    def revid_from_revno(self, revno):
        return self.graph_provider.revid_from_revno(revno)

    def ensure_rev_visible(self, revid):
        has_change = self.graph_provider.ensure_rev_visible(revid)
        if has_change:
            self.compute_lines()
    
    def columnCount(self, parent):
        if parent.isValid():
            return 0
        return len(header_labels)

    def rowCount(self, parent):
        if parent.isValid():
            return 0
        return len(self.graph_provider.revisions)
    
    def data(self, index, role):
        if not index.isValid():
            return QtCore.QVariant()
        
        if self.last_rev_is_placeholder and \
                index.row() == len(gp.revisions) - 1:
            if role == GraphNodeRole:
                return QVariant_fromList([QtCore.QVariant(-1),
                                          QtCore.QVariant(0)])
            return QtCore.QVariant()
        
        c_rev = self.computed.revisions[index.row()]
        
        if role == GraphLinesRole:
            qlines = []
            for start, end, color, direct in c_rev.lines:
                qlines.append(QVariant_fromList(
                    [QtCore.QVariant(start),
                     QtCore.QVariant(end),
                     QtCore.QVariant(color),
                     QtCore.QVariant(direct)]))
            return QVariant_fromList(qlines)
        
        if self.last_rev_is_placeholder and \
                rev_info.index == len(self.computed.revisions) - 1:
            if role == GraphNodeRole:
                return QVariant_fromList([QtCore.QVariant(-1), QtCore.QVariant(0)])
            if role == QtCore.Qt.DisplayRole:
                return QtCore.QVariant("")
            return QtCore.QVariant()

        if role == GraphNodeRole:
            if c_rev.col_index is None:
                return QtCore.QVariant()
            return QVariant_fromList([QtCore.QVariant(c_rev.col_index),
                                      QtCore.QVariant(c_rev.rev.branch.color)])
        
        if role == GraphTwistyStateRole:
            if c_rev.twisty_state is None:
                return QtCore.QVariant()
            if index.row() == self.clicked_row:
                return QtCore.QVariant(-1)
            return QtCore.QVariant(c_rev.twisty_state)
        
        if (role == QtCore.Qt.DisplayRole and index.column() == COL_REV) :
            return QtCore.QVariant(c_rev.rev.revno_str)
        
        if role == TagsRole:
            tags = []
            if c_rev.rev.revid in self.graph_provider.tags:
                tags = list(self.graph_provider.tags[c_rev.rev.revid])
            return QtCore.QVariant(QtCore.QStringList(tags))
        
        if role == BranchTagsRole:
            labels =  [label
                       for (branch_info, label) in c_rev.branch_labels
                       if label]
            return QtCore.QVariant(QtCore.QStringList(labels))
        
        if role == QtCore.Qt.ToolTipRole and index.column() == COL_MESSAGE:
            urls =  [branch_info.branch.base
                     for (branch_info, label) in c_rev.branch_labels
                     if label]
            return QtCore.QVariant('\n'.join(urls))
        
        if role == RevIdRole:
            return QtCore.QVariant(QtCore.QByteArray(str(c_rev.rev.revid)))
        
        #Everything from here foward will need to have the revision loaded.
        if c_rev.rev.revid not in cached_revisions:
            if role == QtCore.Qt.DisplayRole:
                return QtCore.QVariant("")
            return QtCore.QVariant()
        
        revision = cached_revisions[c_rev.rev.revid]
        
        if role == QtCore.Qt.DisplayRole and index.column() == COL_DATE:
            return QtCore.QVariant(strftime("%Y-%m-%d %H:%M",
                                            localtime(revision.timestamp)))
        if role == QtCore.Qt.DisplayRole and index.column() == COL_AUTHOR:
            return QtCore.QVariant(extract_name(get_apparent_author(revision)))
        if role == QtCore.Qt.DisplayRole and index.column() == COL_MESSAGE:
            return QtCore.QVariant(revision.get_summary())
        if role == BugIdsRole:
            bugtext = gettext("bug #%s")
            bugs = []
            for bug in revision.properties.get('bugs', '').split('\n'):
                if bug:
                    url = bug.split(' ', 1)[0]
                    bug_id = get_bug_id(url)
                    if bug_id:
                        bugs.append(bugtext % bug_id)
            return QtCore.QVariant(QtCore.QStringList(bugs))
        
        if role == QtCore.Qt.DisplayRole:
            return QtCore.QVariant("")
        return QtCore.QVariant()

    def flags(self, index):
        if not index.isValid():
            return QtCore.Qt.ItemIsEnabled

        return QtCore.Qt.ItemIsEnabled | QtCore.Qt.ItemIsSelectable

    def headerData(self, section, orientation, role):
        if orientation == QtCore.Qt.Horizontal and role == QtCore.Qt.DisplayRole:
            return QtCore.QVariant(header_labels[section])
        return QtCore.QVariant()

    def indexFromRevId(self, revid, columns=None):
        rev = self.graph_provider.revid_rev[revid]
        if columns:
            return [self.index (rev.index, column, QtCore.QModelIndex())\
                    for column in columns]
        return self.index (rev.index, 0, QtCore.QModelIndex())

    def on_revisions_loaded(self, revisions, last_call):
        for revid in revisions.iterkeys():
            indexes = self.indexFromRevId(revid, (COL_MESSAGE, COL_AUTHOR))
            self.emit(QtCore.SIGNAL("dataChanged(QModelIndex, QModelIndex)"),
                      indexes[0], indexes[1])
    
    def on_filter_changed(self):
        self.compute_lines()


class LogFilterProxyModel(QtGui.QSortFilterProxyModel):
    def __init__(self, parent_log_model, parent = None):
        QtGui.QSortFilterProxyModel.__init__(self, parent)
        self.parent_log_model = parent_log_model
        self.setSourceModel(parent_log_model)
        self.setDynamicSortFilter(True)

    def filterAcceptsRow(self, source_row, source_parent):
        if source_parent.isValid():
            return True
        computed_revisions = self.parent_log_model.computed.revisions
        if source_row >= len(computed_revisions):
            return False
        return computed_revisions[source_row] is not None
    
    def on_revisions_loaded(self, revisions, last_call):
        self.sourceModel().on_revisions_loaded(revisions, last_call)    
    
    def get_repo(self):
        return self.parent_log_model.graph_provider.get_repo_revids
