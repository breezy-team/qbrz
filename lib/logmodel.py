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
import re
import fnmatch

from bzrlib.revision import CURRENT_REVISION, Revision

from bzrlib.plugins.qbzr.lib.bugs import get_bug_id
from bzrlib.plugins.qbzr.lib import loggraphprovider
from bzrlib.plugins.qbzr.lib.lazycachedrevloader import (load_revisions,
                                                         cached_revisions)
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

    def load_revisions(self, revids):
        return load_revisions(revids, self.get_repo_revids)


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

class FilterScheduler(object):
    def __init__(self, filter_changed_callback):
        self.pending_revs = []
        self.last_run_time = 0
        self.last_call_time = 0
        self.filter_changed_callback = filter_changed_callback
    
    def filter_changed(self, revs, last_call=True):
        if revs is None:
            self.pending_revs = None
        else:
            self.pending_revs.extend(revs)
        # Only notify that there are changes every so often.
        # GraphProviderFilterState.filter_changed invaladates it's cache, and
        # causes compute_graph_lines to run, and it runs slowly because it has
        # to update the filter cache. How often we update is bases on a ratio of
        # 10:1. If we spend 1 sec calling invaladate_filter_cache_revs, don't
        # call it again until we have spent 10 sec else where.
        if (last_call or revs is None or 
            clock() - self.last_call_time > self.last_run_time * 10):
            
            start_time = clock()
            self.filter_changed_callback(self.pending_revs, last_call)
            self.pending_revs = []
            self.last_run_time = clock() - start_time
            self.last_call_time = clock()
        
        if last_call:
            self.last_run_time = 0
            self.last_call_time = 0

class LogModel(QtCore.QAbstractTableModel):

    def __init__(self, processEvents, throbber, parent=None):
        QtCore.QAbstractTableModel.__init__(self, parent)
        self.processEvents = processEvents
        self.throbber = throbber
        
        self.graph_provider = LogGraphProvider((), None, False,
                                               processEvents, throbber)
        self.state = loggraphprovider.GraphProviderFilterState(
            self.graph_provider, self.compute_lines)
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
            
            state = loggraphprovider.GraphProviderFilterState(
                graph_provider, self.compute_lines)
            # Copy the expanded branches from the old state to the new.
            state.branch_line_state.update(self.state.branch_line_state)
            scheduler = FilterScheduler(state.filter_changed)
            if file_ids:
                file_id_filter = loggraphprovider.FileIdFilter(
                    graph_provider, scheduler.filter_changed, file_ids)
                state.filters.append(file_id_filter)
            else:
                file_id_filter = None
            prop_search_filter = PropertySearchFilter(graph_provider,
                                                      scheduler.filter_changed)
            state.filters.append(prop_search_filter)
            
            self.emit(QtCore.SIGNAL("layoutAboutToBeChanged()"))
            self.graph_provider = graph_provider
            self.state = state
            self.file_id_filter = file_id_filter
            self.prop_search_filter = prop_search_filter
            self.computed = loggraphprovider.ComputedGraph(graph_provider)
            self.emit(QtCore.SIGNAL("layoutChanged()"))
            
            self.compute_lines()
            if self.file_id_filter:
                # Start later so that it does not run in the loading queue.
                QtCore.QTimer.singleShot(1, self.file_id_filter.load)
        finally:
            self.throbber.hide()
    
    def compute_lines(self):
        self.computed = self.graph_provider.compute_graph_lines(self.state)
        self.emit(QtCore.SIGNAL("dataChanged(QModelIndex, QModelIndex)"),
                  self.createIndex (0, COL_MESSAGE, QtCore.QModelIndex()),
                  self.createIndex (len(self.graph_provider.revisions),
                                    COL_MESSAGE, QtCore.QModelIndex()))
        self.emit(QtCore.SIGNAL("linesUpdated()"))
    
    def collapse_expand_rev(self, index):
        self.clicked_row = index
        clicked_row_index = self.createIndex (self.clicked_row,
                                              COL_MESSAGE,
                                              QtCore.QModelIndex())
        self.emit(QtCore.SIGNAL("dataChanged(QModelIndex, QModelIndex)"),
                  clicked_row_index,
                  clicked_row_index)
        self.graph_provider.update_ui()
        self.clicked_row = None
        
        c_rev = self.computed.revisions[index]
        self.state.collapse_expand_rev(c_rev)
        
        self.emit(QtCore.SIGNAL("dataChanged(QModelIndex, QModelIndex)"),
                  clicked_row_index,
                  clicked_row_index)
    
    def ensure_rev_visible(self, rev):
        self.state.ensure_rev_visible(rev)
    
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

    def on_revisions_loaded(self, revisions, last_call):
        for revid in revisions.iterkeys():
            rev = self.graph_provider.revid_rev[revid]
            self.emit(
                QtCore.SIGNAL("dataChanged(QModelIndex, QModelIndex)"),
                self.index(rev.index, COL_MESSAGE, QtCore.QModelIndex()),
                self.index(rev.index, COL_AUTHOR, QtCore.QModelIndex()))
    
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

class PropertySearchFilter (object):
    def __init__(self, graph_provider, filter_changed_callback):
        self.graph_provider = graph_provider
        self.filter_changed_callback = filter_changed_callback
        self.field = None
        self.filter_re = None
        self.cache = None
        self.index_matched_revids = None
        self.loading_revisions = False
    
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
        self.field = field
        
        def revisions_loaded(revisions, last_call):
            revs = [self.graph_provider.revid_rev[revid]
                    for revid in revisions.iterkeys()]
            self.filter_changed_callback(revs, last_call)
        
        def before_batch_load(repo, revids):
            if self.filter_re is None:
                return True
            return False

        def wildcard2regex(wildcard):
            """Translate shel pattern to regexp."""
            return fnmatch.translate(wildcard + '*')
        
        if str is None or str == u"":
            self.filter_re = None
            self.index_matched_revids = None
            self.filter_changed_callback(None, True)
        else:
            if self.field == "index":
                from bzrlib.plugins.search import index as search_index
                self.filter_re = None
                indexes = [bi.index for bi in self.graph_provider.branches
                           if bi.index is not None]
                if not indexes:
                    self.index_matched_revids = None
                else:
                    str = str.strip()
                    query = [(query_item,) for query_item in str.split(" ")]
                    self.index_matched_revids = {}
                    for index in indexes:
                        for result in index.search(query):
                            if isinstance(result, search_index.RevisionHit):
                                self.index_matched_revids\
                                        [result.revision_key[0]] = True
                            if isinstance(result, search_index.FileTextHit):
                                self.index_matched_revids\
                                        [result.text_key[1]] = True
                            if isinstance(result, search_index.PathHit):
                                pass
            elif self.field == "tag":
                self.filter_re = None
                filter_re = re.compile(wildcard2regex(str), re.IGNORECASE)
                self.index_matched_revids = {}
                for revid in self.tags:
                    for t in self.tags[revid]:
                        if filter_re.search(t):
                            self.index_matched_revids[revid] = True
                            break
            else:
                self.filter_re = re.compile(wildcard2regex(str),
                    re.IGNORECASE)
                self.index_matched_revids = None
            
            self.filter_changed_callback(None, True)
            
            if self.filter_re is not None\
               and not self.loading_revisions:
                
                self.loading_revisions = True
                try:
                    revids = [rev.revid
                              for rev in self.graph_provider.revisions ]
                    load_revisions(revids, self.graph_provider.get_repo_revids,
                                   time_before_first_ui_update = 0,
                                   local_batch_size = 100,
                                   remote_batch_size = 10,
                                   before_batch_load = before_batch_load,
                                   revisions_loaded = revisions_loaded)
                finally:
                    self.loading_revisions = False
    
    def get_revision_visible(self, rev):
        
        revid = rev.revid
        
        if self.filter_re:
            if revid not in cached_revisions:
                return False
            revision = cached_revisions[revid]
            
            filtered_str = None
            if self.field == "message":
                filtered_str = revision.message
            elif self.field == "author":
                filtered_str = get_apparent_author(revision)
            elif self.field == "bug":
                rbugs = revision.properties.get('bugs', '')
                if rbugs:
                    filtered_str = rbugs.replace('\n', ' ')
                else:
                    return False

            if filtered_str is not None:
                if self.filter_re.search(filtered_str) is None:
                    return False
        
        if self.index_matched_revids is not None:
            if revid not in self.index_matched_revids:
                return False        