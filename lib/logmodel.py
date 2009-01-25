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
from time import (strftime, localtime, clock)

from bzrlib import (lazy_regex, errors)
from bzrlib.transport.local import LocalTransport
from bzrlib.revision import NULL_REVISION
from bzrlib.tsort import merge_sort
from bzrlib.graph import (Graph, _StackedParentsProvider)
from bzrlib.plugins.qbzr.lib.loggraphprovider import LogGraphProvider
from bzrlib.plugins.qbzr.lib.i18n import gettext
from bzrlib.plugins.qbzr.lib.util import (
    extract_name,
    BackgroundJob,
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

class QLogGraphProvider(LogGraphProvider):
    
    def __init__(self, processEvents, report_exception,
                 throbber):
        LogGraphProvider.__init__(self)
        
        self.processEvents = processEvents
        self.report_exception = report_exception
        self.throbber = throbber
    
    def update_ui(self):
        self.processEvents()
    
    def throbber_show(self):
        self.throbber.show()
    
    def throbber_hide(self):
        self.throbber.hide()
    
    def revisions_loaded(self, revisions):
        """Runs after a batch of revisions have been loaded
        
        Reimplement to be notified that revisions have been loaded. But
        remember to call super.
        
        """
        LogGraphProvider.revisions_loaded(self, revisions)
        self.on_revisions_loaded(revisions)
    
    def revisions_filter_changed(self, revisions):
        self.on_filter_changed(revisions)
    
    def delay(self, timeout):
        QtCore.QTimer.singleShot(timeout, self.null)
        self.processEvents(QtCore.QEventLoop.WaitForMoreEvents)
    
    def null(self):
        pass

class LogModel(QtCore.QAbstractTableModel):

    def __init__(self, graph_provider, parent=None):
        QtCore.QAbstractTableModel.__init__(self, parent)
        
        self.graph_provider = graph_provider
        self.graph_provider.on_revisions_loaded = self.on_revisions_loaded
        self.graph_provider.on_filter_changed = self.on_filter_changed
        
        self.horizontalHeaderLabels = [gettext("Rev"),
                                       gettext("Message"),
                                       gettext("Date"),
                                       gettext("Author"),
                                       ]
    
    def loadBranch(self):
        try:
            self.emit(QtCore.SIGNAL("layoutAboutToBeChanged()"))
            self.graph_provider.load_graph_all_revisions()
        finally:
            self.emit(QtCore.SIGNAL("layoutChanged()"))

        
    def compute_lines(self):
        self.graph_provider.compute_graph_lines()
        self.emit(QtCore.SIGNAL("dataChanged(QModelIndex, QModelIndex)"),
                  self.createIndex (0, COL_MESSAGE, QtCore.QModelIndex()),
                  self.createIndex (len(self.graph_provider.merge_sorted_revisions),
                                    COL_MESSAGE, QtCore.QModelIndex()))
    
    def colapse_expand_rev(self, revid, visible):
        has_change = self.graph_provider.colapse_expand_rev(revid, visible)
        if has_change:
            self.compute_lines()
    
    def has_rev_id(self, revid):
        return self.graph_provider.has_revid(revid)
    
    def revid_from_revno(self, revno):
        return self.graph_provider.revid_from_revno(revno)
        
    def ensure_rev_visible(self, revid):
        has_change = self.graph_provider.ensure_rev_visible(revid, visible)
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
        
        if index.row() in self.graph_provider.msri_index:
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
            self.graph_provider.merge_sorted_revisions[index.row()]
        
        if (role == QtCore.Qt.DisplayRole and index.column() == COL_REV) or \
                role == FilterRevnoRole:
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
            if revid in self.graph_provider.heads:
                tags = [tag for (branch, tag, blr) \
                        in self.graph_provider.heads[revid][1] if tag]
            return QtCore.QVariant(QtCore.QStringList(tags))
        
        if role == RevIdRole or role == FilterIdRole:
            return QtCore.QVariant(revid)
        
        #Everything from here foward will need to have the revision loaded.
        if not revid or revid == NULL_REVISION:
            return QtCore.QVariant()
        
        revision = self.graph_provider.revision(revid)
        
        if not revision:
            return QtCore.QVariant()
        
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
    

    def indexFromRevId(self, revid, columns=None):
        msri = self.graph_provider.revid_msri[revid]
        if columns:
            return [self.createIndex (msri, column, QtCore.QModelIndex())\
                    for column in columns]
        return self.createIndex (msri, 0, QtCore.QModelIndex())

    def on_revisions_loaded(self, revisions):
        for revid in revisions:
            indexes = self.indexFromRevId(revid, (COL_MESSAGE, COL_AUTHOR))
            self.emit(QtCore.SIGNAL("dataChanged(QModelIndex, QModelIndex)"),
                      indexes[0], indexes[1])
    
    def on_filter_changed(self, revisions):
        self.compute_lines()
    
class LoadRevisionsBase(BackgroundJob):
    throbber_time = 0.5

    def run(self):
        self.update_time = self.update_time_initial
        self.start_time = clock()
        self.last_update = clock()
        self.revisions_loaded = []
        
        try:
            revision_ids = []
            for revid in self.revision_generator():
                if revid not in self.parent.revisions:
                    revision_ids.append(revid)
                if len(revision_ids)>self.batch_size:
                    self.load_revisions(revision_ids)
            self.load_revisions(revision_ids)
            self.notifyChanges()
        finally:
            self.parent.throbber_hide()
    
    def load_revisions(self, revision_ids):
        for repo in self.parent.repos.itervalues():
            keys = [(key,) for key in revision_ids]
            stream = repo.revisions.get_record_stream(keys, 'unordered', True)
            self.processEvents()
            for record in stream:
                if not record.storage_kind == 'absent':
                    revision_ids.remove(record.key[0])
                    self.revisions_loaded.append(record.key[0])
                    text = record.get_bytes_as('fulltext')
                    rev = repo._serializer.read_revision_from_string(text)
                    rev.repository = repo
                    self.parent.post_revision_load(rev)
                    self.processEvents()
                
                current_time = clock()
                if self.throbber_time < current_time - self.start_time:
                    self.parent.throbber_show()
                
                if self.update_time < current_time - self.last_update:
                    self.notifyChanges()
                    self.update_time = max(self.update_time + self.update_time_increment,
                                           self.update_time_max)
                    self.processEvents()
                    self.last_update = clock()
        
        
        # This should never happen
        if len(revision_ids) > 0 :
            raise errors.NoSuchRevision(self, revision_ids[0])
    
    def notifyChanges(self):
        for revid in self.revisions_loaded:
            indexes = self.parent.indexFromRevId(revid, (COL_MESSAGE, COL_AUTHOR))
            self.parent.graphFilterProxyModel.invalidateCacheRow(indexes[0].row())
            self.parent.emit(QtCore.SIGNAL("dataChanged(QModelIndex, QModelIndex)"),
                      indexes[0], indexes[1])
        revisionsChanged = []

class LoadQueuedRevisions(LoadRevisionsBase):
    update_time_initial = 0.05
    update_time_increment = 0
    update_time_max = 0.05
    
    batch_size = 5
    
    def revision_generator(self):
        while len(self.parent.queue):
            yield self.parent.queue.pop(0)

    def notifyChanges(self):
        # Clear the queue
        self.parent.queue = self.parent.queue[0:1]
        LoadRevisionsBase.notifyChanges(self)

    
class LoadAllRevisions(LoadRevisionsBase):
    update_time_initial = 1
    update_time_increment = 5
    update_time_max = 20
    
    batch_size = 50

    def revision_generator(self):
        for (sequence_number,
             revid,
             merge_depth,
             revno_sequence,
             end_of_merge) in self.parent.merge_sorted_revisions:
            yield revid

    def notifyChanges(self):
        LoadRevisionsBase.notifyChanges(self)
        self.parent.compute_lines()
    
    
class LogFilterProxyModel(QtGui.QSortFilterProxyModel):
    def __init__(self, graph_provider, parent = None):
        QtGui.QSortFilterProxyModel.__init__(self, parent)
        self.graph_provider = graph_provider
        self.old_filter_str = ""
        self.old_filter_role = 0
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
        return self.graph_provider.get_revision_visible(source_row)
    #    (sequence_number,
    #     revid,
    #     merge_depth,
    #     revno_sequence,
    #     end_of_merge) = sm.graph_provider.merge_sorted_revisions[source_row]
    #    
    #    branch_id = revno_sequence[0:-1]
    #    if not sm.branch_lines[branch_id][1]: # branch colapased
    #        return False
    #    
    #    return self.filterAcceptsRowIfBranchVisible(source_row, source_parent)
    #
    #def filterAcceptsRowIfBranchVisible(self, source_row, source_parent):
    #    if source_row not in self.cache:
    #        self.cache[source_row] = self._filterAcceptsRowIfBranchVisible(source_row, source_parent)
    #    return self.cache[source_row]
    #    
    #def _filterAcceptsRowIfBranchVisible(self, source_row, source_parent):
    #    sm = self.sm()
    #    
    #    for parent_msri in sm.merge_info[source_row][0]:
    #        if self.filterAcceptsRowIfBranchVisible(parent_msri, source_parent):
    #            return True
    #    
    #    if sm.touches_file_msri is not None:
    #        if source_row not in sm.touches_file_msri:
    #            return False
    #    
    #    if self.search_matching_revid is not None:
    #        (sequence_number,
    #         revid,
    #         merge_depth,
    #         revno_sequence,
    #         end_of_merge) = sm.merge_sorted_revisions[source_row]
    #        return revid in self.search_matching_revid
    #    
    #    if self.filter_str:
    #        (sequence_number,
    #         revid,
    #         merge_depth,
    #         revno_sequence,
    #         end_of_merge) = sm.merge_sorted_revisions[source_row]
    #        if revid in sm.revisions:
    #            return QtGui.QSortFilterProxyModel.filterAcceptsRow(self, source_row, source_parent)
    #        else:
    #            return False
    #    
    #    return True

 