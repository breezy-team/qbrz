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
from bzrlib.plugins.qbzr.lib.loggraphprovider import LogGraphProvider
from bzrlib.plugins.qbzr.lib.lazycachedrevloader import cached_revisions
from bzrlib.plugins.qbzr.lib.revtreeview import RevIdRole as im_RevIdRole
from bzrlib.plugins.qbzr.lib.i18n import gettext
from bzrlib.plugins.qbzr.lib.util import (
    extract_name,
    get_apparent_author,
    runs_in_loading_queue,
    get_summary,
    )

RevIdRole = im_RevIdRole
(TagsRole,
 BugIdsRole,
 BranchTagsRole,
 GraphNodeRole,
 GraphLinesRole,
 GraphTwistyStateRole,
) = range(QtCore.Qt.UserRole + 2, QtCore.Qt.UserRole + 8)

(COL_REV,
 COL_MESSAGE,
 COL_DATE,
 COL_AUTHOR,
) = range(4)

_bug_id_re = lazy_regex.lazy_compile(r'(?:'
    r'bugs/'                    # Launchpad bugs URL
    r'|ticket/'                 # Trac bugs URL
    r'|show_bug\.cgi\?id='      # Bugzilla bugs URL
    r'|issues/show/'            # Redmine bugs URL
    r'|DispForm.aspx\?ID='      # Microsoft SharePoint URL
    r'|default.asp\?'           # Fogbugz URL
    r'|issue'                   # Roundup issue tracker URL
    r'|bugs/view.php\?id='      # Mantis bug tracker URL
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


class QLogGraphProvider(LogGraphProvider):
    
    def __init__(self, processEvents,  throbber, no_graph):
        LogGraphProvider.__init__(self, no_graph)
        
        self.processEvents = processEvents
        self.throbber = throbber
    
    def update_ui(self):
        self.processEvents()
    
    def throbber_show(self):
        self.throbber.show()
    
    def throbber_hide(self):
        self.throbber.hide()
    
    def revisions_filter_changed(self):
        self.on_filter_changed()

    @runs_in_loading_queue
    def load_filter_file_id_chunk(self, repo, revids):
        LogGraphProvider.load_filter_file_id_chunk(self, repo, revids)

    @runs_in_loading_queue
    def load_filter_file_id_chunk_finished(self):
        LogGraphProvider.load_filter_file_id_chunk_finished(self)

class LogModel(QtCore.QAbstractTableModel):

    def __init__(self, graph_provider, parent=None):
        QtCore.QAbstractTableModel.__init__(self, parent)
        
        self.graph_provider = graph_provider
        self.graph_provider.on_filter_changed = self.on_filter_changed
        
        self.horizontalHeaderLabels = [gettext("Rev"),
                                       gettext("Message"),
                                       gettext("Date"),
                                       gettext("Author"),
                                       ]
        self.clicked_row = None
        self.last_rev_is_placeholder = False
    
    def load_graph_all_revisions(self):
        try:
            self.emit(QtCore.SIGNAL("layoutAboutToBeChanged()"))
            self.graph_provider.load_graph_all_revisions()
        finally:
            self.emit(QtCore.SIGNAL("layoutChanged()"))

    def load_graph_pending_merges(self):
        self.last_rev_is_placeholder = True
        try:
            self.emit(QtCore.SIGNAL("layoutAboutToBeChanged()"))
            self.graph_provider.load_graph_pending_merges()
        finally:
            self.emit(QtCore.SIGNAL("layoutChanged()"))

    def compute_lines(self):
        self.graph_provider.compute_graph_lines()
        self.emit(QtCore.SIGNAL("dataChanged(QModelIndex, QModelIndex)"),
                  self.createIndex (0, COL_MESSAGE, QtCore.QModelIndex()),
                  self.createIndex (len(self.graph_provider.merge_sorted_revisions),
                                    COL_MESSAGE, QtCore.QModelIndex()))
    
    def colapse_expand_rev(self, revid, visible):
        self.clicked_row = self.graph_provider.revid_msri[revid]
        clicked_row_index = self.createIndex (self.clicked_row,
                                              COL_MESSAGE,
                                              QtCore.QModelIndex())
        self.emit(QtCore.SIGNAL("dataChanged(QModelIndex, QModelIndex)"),
                  clicked_row_index,
                  clicked_row_index)
        self.graph_provider.update_ui()
        self.clicked_row = None
        has_change = self.graph_provider.colapse_expand_rev(revid, visible)
        
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
        return len(self.horizontalHeaderLabels)

    def rowCount(self, parent):
        if parent.isValid():
            return 0
        return len(self.graph_provider.merge_sorted_revisions)
    
    def data(self, index, role):
        if not index.isValid():
            return QtCore.QVariant()
        
        if index.row() in self.graph_provider.msri_index \
                and len(self.graph_provider.graph_line_data)> \
                self.graph_provider.msri_index[index.row()]:
            (msri,
             node,
             lines,
             twisty_state,
             twisty_branch_ids) = self.graph_provider.graph_line_data\
                                  [self.graph_provider.msri_index[index.row()]]
        else:
            (msri,
             node,
             lines,
             twisty_state,
             twisty_branch_ids) = (index.row(), None, [], None, [])
        
        if role == GraphLinesRole:
            qlines = []
            for start, end, color, direct in lines:
                qlines.append(QVariant_fromList(
                    [QtCore.QVariant(start),
                     QtCore.QVariant(end),
                     QtCore.QVariant(color),
                     QtCore.QVariant(direct)]))
            return QVariant_fromList(qlines)
        
        if self.last_rev_is_placeholder and \
                msri == len(self.graph_provider.merge_sorted_revisions) - 1:
            if role == GraphNodeRole:
                return QVariant_fromList([QtCore.QVariant(-1), QtCore.QVariant(0)])
            if role == QtCore.Qt.DisplayRole:
                return QtCore.QVariant("")
            return QtCore.QVariant()

        if role == GraphNodeRole:
            if node is None:
                return QtCore.QVariant()
            return QVariant_fromList([QtCore.QVariant(nodei) for nodei in node])
        
        if role == GraphTwistyStateRole:
            if twisty_state is None:
                return QtCore.QVariant()
            if index.row() == self.clicked_row:
                return QtCore.QVariant(-1)
            return QtCore.QVariant(twisty_state)
        
        (sequence_number, revid, merge_depth, revno_sequence, end_of_merge) = \
            self.graph_provider.merge_sorted_revisions[index.row()]
        
        if (role == QtCore.Qt.DisplayRole and index.column() == COL_REV) :
            revnos = ".".join(["%d" % (revno)
                                      for revno in revno_sequence])
            return QtCore.QVariant(revnos)
        
        if role == TagsRole:
            tags = []
            if revid in self.graph_provider.tags:
                tags = list(self.graph_provider.tags[revid])
            return QtCore.QVariant(QtCore.QStringList(tags))
        
        if role == BranchTagsRole:
            tags = []
            if revid in self.graph_provider.branch_tags:
                tags = [tag for tag \
                        in self.graph_provider.branch_tags[revid] if tag]
            return QtCore.QVariant(QtCore.QStringList(tags))
        
        if role == RevIdRole:
            return QtCore.QVariant(revid)
        
        #Everything from here foward will need to have the revision loaded.
        if not revid or revid not in cached_revisions:
            if role == QtCore.Qt.DisplayRole:
                return QtCore.QVariant("")
            return QtCore.QVariant()
        
        revision = cached_revisions[revid]
        
        if role == QtCore.Qt.DisplayRole and index.column() == COL_DATE:
            return QtCore.QVariant(strftime("%Y-%m-%d %H:%M",
                                            localtime(revision.timestamp)))
        if role == QtCore.Qt.DisplayRole and index.column() == COL_AUTHOR:
            return QtCore.QVariant(extract_name(get_apparent_author(revision)))
        if role == QtCore.Qt.DisplayRole and index.column() == COL_MESSAGE:
            return QtCore.QVariant(get_summary(revision))
        if role == BugIdsRole:
            bugtext = gettext("bug #%s")
            bugs = []
            for bug in revision.properties.get('bugs', '').split('\n'):
                if bug:
                    url, space, status = bug.partition(' ')
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
            return QtCore.QVariant(self.horizontalHeaderLabels[section])
        return QtCore.QVariant()
    

    def indexFromRevId(self, revid, columns=None):
        msri = self.graph_provider.revid_msri[revid]
        if columns:
            return [self.index (msri, column, QtCore.QModelIndex())\
                    for column in columns]
        return self.index (msri, 0, QtCore.QModelIndex())

    def on_revisions_loaded(self, revisions, last_call):
        for revid in revisions.iterkeys():
            indexes = self.indexFromRevId(revid, (COL_MESSAGE, COL_AUTHOR))
            self.emit(QtCore.SIGNAL("dataChanged(QModelIndex, QModelIndex)"),
                      indexes[0], indexes[1])
    
    def on_filter_changed(self):
        self.compute_lines()

    
class LogFilterProxyModel(QtGui.QSortFilterProxyModel):
    def __init__(self, graph_provider, parent = None):
        QtGui.QSortFilterProxyModel.__init__(self, parent)
        self.graph_provider = graph_provider

    def filterAcceptsRow(self, source_row, source_parent):
        return self.graph_provider.get_revision_visible(source_row)
    
    def on_revisions_loaded(self, revisions, last_call):
        self.sourceModel().on_revisions_loaded(revisions, last_call)    
    
    def get_repo(self):
        return self.graph_provider.get_repo_revids
