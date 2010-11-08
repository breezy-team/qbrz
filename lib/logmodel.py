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
from bzrlib.plugins.qbzr.lib import loggraphviz
from bzrlib.plugins.qbzr.lib.lazycachedrevloader import (load_revisions,
                                                         cached_revisions)
from bzrlib.plugins.qbzr.lib.revtreeview import RevIdRole as im_RevIdRole
from bzrlib.plugins.qbzr.lib.i18n import gettext
from bzrlib.plugins.qbzr.lib.util import (
    extract_name,
    get_apparent_author,
    runs_in_loading_queue,
    run_in_loading_queue
    )

RevIdRole = im_RevIdRole
GraphDataRole = QtCore.Qt.UserRole + 2

header_labels = (gettext("Rev"),
                 gettext("Message"),
                 gettext("Date"),
                 gettext("Author"), )

(COL_REV,
 COL_MESSAGE,
 COL_DATE,
 COL_AUTHOR,
) = range(len(header_labels))


class WorkingTreeRevision(Revision):
    def __init__(self, revid, tree):
        super(WorkingTreeRevision, self).__init__(revid)
        
        self.parent_ids = tree.get_parent_ids()
        self.committer = tree.branch.get_config().username()
        self.message = "" # todo: try load saved commit message
        self.timestamp = None
        self.tree = tree

class GraphVizLoader(loggraphviz.GraphVizLoader):
    
    def __init__(self, branches, primary_bi, no_graph,
                 processEvents,  throbber):
        self.processEvents = processEvents
        self.throbber = throbber
        loggraphviz.GraphVizLoader.__init__(
            self, branches, primary_bi, no_graph)
    
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


class PendingMergesGraphVizLoader(
        loggraphviz.PendingMergesGraphVizLoader,
        GraphVizLoader):
    pass

class WithWorkingTreeGraphVizLoader(
        loggraphviz.WithWorkingTreeGraphVizLoader,
        GraphVizLoader):
    
    def load(self):
        super(WithWorkingTreeGraphVizLoader, self).load()
        
        for wt_revid, tree in self.working_trees.iteritems():
            # bla - nasty hack.
            cached_revisions[wt_revid] = WorkingTreeRevision(wt_revid, tree)


class FileIdFilter(loggraphviz.FileIdFilter):
    @runs_in_loading_queue
    def load(self, revids=None):
        super(FileIdFilter, self).load(revids)


class WorkingTreeHasChangeFilter(loggraphviz.WorkingTreeHasChangeFilter):
    @runs_in_loading_queue
    def load(self):
        super(WorkingTreeHasChangeFilter, self).load()


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
        # GraphVizFilterState.filter_changed invaladates it's cache, and
        # causes compute_viz to run, and it runs slowly because it has
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
        
        self.graph_viz = GraphVizLoader((), None, False,
                                               processEvents, throbber)
        self.state = loggraphviz.GraphVizFilterState(
            self.graph_viz, self.compute_lines)
        self.computed = loggraphviz.ComputedGraphViz(self.graph_viz)

        self.clicked_f_index = None
        self.last_rev_is_placeholder = False
        self.bugtext = gettext("bug #%s")
    
    def load(self, branches, primary_bi, file_ids, no_graph,
             graph_provider_type):
        self.throbber.show()
        self.processEvents()        
        try:
            graph_viz = graph_provider_type(
                branches, primary_bi, no_graph, 
                processEvents=self.processEvents, throbber=self.throbber)
            graph_viz.load()
            graph_viz.on_filter_changed = self.on_filter_changed
            
            state = loggraphviz.GraphVizFilterState(
                graph_viz, self.compute_lines)
            # Copy the expanded branches from the old state to the new.
            for (branch_id, value) in self.state.branch_line_state.iteritems():
                if branch_id in graph_viz.branch_lines:
                    state.branch_line_state[branch_id] = value
            
            #for branch_id in graph_viz.branch_lines.keys():
            #    state.branch_line_state[branch_id] = None
            
            scheduler = FilterScheduler(state.filter_changed)
            if file_ids:
                file_id_filter = FileIdFilter(
                    graph_viz, scheduler.filter_changed, file_ids)
                state.filters.append(file_id_filter)
            else:
                file_id_filter = None
            
            if isinstance(graph_viz, WithWorkingTreeGraphVizLoader):
                working_tree_filter = WorkingTreeHasChangeFilter(
                    graph_viz, scheduler.filter_changed, file_ids)
                state.filters.append(working_tree_filter)
            else:
                working_tree_filter = None
            
            prop_search_filter = PropertySearchFilter(graph_viz,
                                                      scheduler.filter_changed)
            state.filters.append(prop_search_filter)
            
            self.emit(QtCore.SIGNAL("layoutAboutToBeChanged()"))
            self.graph_viz = graph_viz
            self.state = state
            self.file_ids = file_ids
            self.file_id_filter = file_id_filter
            self.working_tree_filter = working_tree_filter
            self.prop_search_filter = prop_search_filter
            self.computed = loggraphviz.ComputedGraphViz(graph_viz)
            self.emit(QtCore.SIGNAL("layoutChanged()"))
            
            self.compute_lines()
            # Start later so that it does not run in the loading queue.
            if self.working_tree_filter:
                QtCore.QTimer.singleShot(1, self.working_tree_filter.load)
            if self.file_id_filter:
                QtCore.QTimer.singleShot(1, self.file_id_filter.load)
        finally:
            self.throbber.hide()
    
    def compute_lines(self):
        computed = self.graph_viz.compute_viz(self.state)
        if self.last_rev_is_placeholder:
            computed.filtered_revs[-1].col_index = None
        self.emit(QtCore.SIGNAL("layoutAboutToBeChanged()"))
        self.computed = computed
        self.emit(QtCore.SIGNAL("layoutChanged()"))
    
    def collapse_expand_rev(self, c_rev):
        self.clicked_f_index = c_rev.f_index
        clicked_row_index = self.createIndex (c_rev.f_index,
                                              COL_MESSAGE,
                                              QtCore.QModelIndex())
        self.emit(QtCore.SIGNAL("dataChanged(QModelIndex, QModelIndex)"),
                  clicked_row_index,
                  clicked_row_index)
        self.graph_viz.update_ui()
        self.clicked_f_index = None
        
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
        return len(self.computed.filtered_revs)
    
    def data(self, index, role):
        
        if not index.isValid():
            return QtCore.QVariant()
        
        def blank():
            if role == QtCore.Qt.DisplayRole:
                return QtCore.QVariant("")
            return QtCore.QVariant()
        
        c_rev = self.computed.filtered_revs[index.row()]
        if c_rev is None:
            return blank()
        
        if c_rev.rev.revid in cached_revisions:
            revision = cached_revisions[c_rev.rev.revid]
        else:
            revision = None
        
        if role == GraphDataRole:
            prev_c_rev = None
            prev_c_rev_f_index = c_rev.f_index - 1
            if prev_c_rev_f_index >= 0:
                prev_c_rev = self.computed.filtered_revs[prev_c_rev_f_index]
            
            tags = []
            # Branch labels
            tags.extend([(label,
                          QtGui.QColor(24, 80, 200),
                          QtGui.QColor(QtCore.Qt.white))
                         for (branch_info, label) in c_rev.branch_labels
                         if label])
            # Tags
            if c_rev.rev.revid in self.graph_viz.tags:
                tags.extend(
                    [(tag,
                      QtGui.QColor(80, 128, 32),
                      QtGui.QColor(QtCore.Qt.white))
                     for tag in self.graph_viz.tags[c_rev.rev.revid]])
            
            # Bugs
            if revision:
                if hasattr(revision, '_qlog_bugs'):
                    bugs = revision._qlog_bugs
                else:
                    bugs = []
                    for bug in revision.properties.get('bugs', '').split('\n'):
                        if bug:
                            url = bug.split(' ', 1)[0]
                            bug_id = get_bug_id(url)
                            if bug_id:
                                bugs.append(self.bugtext % bug_id)
                    revision._qlog_bugs = bugs
                tags.extend([(bug,
                              QtGui.QColor(164, 0, 0),
                              QtGui.QColor(QtCore.Qt.white))
                             for bug in bugs])
            is_clicked = c_rev.f_index == self.clicked_f_index
            
            return QtCore.QVariant((c_rev, prev_c_rev, tags, is_clicked))
        
        if (role == QtCore.Qt.DisplayRole and index.column() == COL_REV):
            return QtCore.QVariant(c_rev.rev.revno_str)
        
        if role == QtCore.Qt.ToolTipRole and index.column() == COL_MESSAGE:
            urls =  [branch_info.branch.base
                     for (branch_info, label) in c_rev.branch_labels
                     if label]
            return QtCore.QVariant('\n'.join(urls))
        
        if role == RevIdRole:
            return QtCore.QVariant(c_rev.rev.revid)
        
        #Everything from here foward will need to have the revision loaded.
        if revision is None:
            return blank()
        
        if role == QtCore.Qt.DisplayRole and index.column() == COL_DATE:
            return QtCore.QVariant(strftime("%Y-%m-%d %H:%M",
                                            localtime(revision.timestamp)))
        if role == QtCore.Qt.DisplayRole and index.column() == COL_AUTHOR:
            return QtCore.QVariant(extract_name(get_apparent_author(revision)))
        if role == QtCore.Qt.DisplayRole and index.column() == COL_MESSAGE:
            return QtCore.QVariant(revision.get_summary())
        
        return blank()

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
            rev = self.graph_viz.revid_rev[revid]
            self.emit(
                QtCore.SIGNAL("dataChanged(QModelIndex, QModelIndex)"),
                self.index(rev.index, COL_MESSAGE, QtCore.QModelIndex()),
                self.index(rev.index, COL_AUTHOR, QtCore.QModelIndex()))
    
    def on_filter_changed(self):
        self.compute_lines()

    def get_repo(self):
        return self.graph_viz.get_repo_revids
    
    def index_from_revid(self, revid, column=0):
        try:
            rev = self.graph_viz.revid_rev[revid]
        except KeyError:
            return
        return self.index_from_rev(rev)
    
    def index_from_rev(self, rev, column=0):
        try:
            c_rev = self.computed.revisions[rev.index]
        except IndexError:
            return
        if c_rev is None:
            return
        return self.index_from_c_rev(c_rev, column)
    
    def index_from_c_rev(self, c_rev, column=0):
        return self.index(c_rev.f_index, column, QtCore.QModelIndex())
    
    def c_rev_from_index(self, index):
        f_index = index.row()
        try: 
            return self.computed.filtered_revs[f_index]
        except IndexError:
            return None    

class PropertySearchFilter (object):
    def __init__(self, graph_viz, filter_changed_callback):
        self.graph_viz = graph_viz
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
            revs = [self.graph_viz.revid_rev[revid]
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
                indexes = [bi.index for bi in self.graph_viz.branches
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
                for revid in self.graph_viz.tags:
                    for t in self.graph_viz.tags[revid]:
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
                              for rev in self.graph_viz.revisions ]
                    load_revisions(revids, self.graph_viz.get_repo_revids,
                                   time_before_first_ui_update = 0,
                                   local_batch_size = 100,
                                   remote_batch_size = 10,
                                   before_batch_load = before_batch_load,
                                   revisions_loaded = revisions_loaded)
                finally:
                    self.loading_revisions = False
    
    def get_revision_visible(self, rev):
        
        if self.filter_re:
            revid = rev.revid
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
            revid = rev.revid
            if revid not in self.index_matched_revids:
                return False
        
        return True
