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

from bzrlib.plugins.qbzr.lib.revtreeview import (RevisionTreeView,
                                                 RevNoItemDelegate,
                                                 get_text_color)
from bzrlib.revision import NULL_REVISION, CURRENT_REVISION
from bzrlib.plugins.qbzr.lib.util import (
    runs_in_loading_queue,
    )
from bzrlib.plugins.qbzr.lib.trace import reports_exception, SUB_LOAD_METHOD
from bzrlib.plugins.qbzr.lib.uifactory import ui_current_widget

from bzrlib.lazy_import import lazy_import
lazy_import(globals(), '''
from bzrlib.bzrdir import BzrDir
from bzrlib.revisionspec import RevisionSpec
from bzrlib.plugins.qbzr.lib.tag import TagWindow, CallBackTagWindow
from bzrlib.plugins.qbzr.lib import logmodel
from bzrlib.plugins.qbzr.lib import diff
from bzrlib.plugins.qbzr.lib.i18n import gettext
from bzrlib.plugins.qbzr.lib.subprocess import SimpleSubProcessDialog
''')


class LogList(RevisionTreeView):
    """TreeView widget to show log with metadata and graph of revisions."""

    def __init__(self, processEvents, throbber, parent=None,
                 view_commands=True, action_commands=False):
        """Costructing new widget.
        @param  throbber:   throbber widget in parent window
        @param  parent:     parent window
        """
        RevisionTreeView.__init__(self, parent)
        self.setContextMenuPolicy(QtCore.Qt.CustomContextMenu)
        self.setSelectionMode(QtGui.QAbstractItemView.ContiguousSelection)
        self.setUniformRowHeights(True)
        self.setAllColumnsShowFocus(True)
        self.setRootIsDecorated (False)
        self.setVerticalScrollBarPolicy(QtCore.Qt.ScrollBarAlwaysOn)

        self.setItemDelegateForColumn(logmodel.COL_MESSAGE,
                                      GraphTagsBugsItemDelegate(self))
        self.rev_no_item_delegate = RevNoItemDelegate(parent=self)
        self.setItemDelegateForColumn(logmodel.COL_REV,
                                      self.rev_no_item_delegate)

        self.log_model = logmodel.LogModel(processEvents, throbber, self)
        self.lines_updated_selection = []
        self.lines_updated_selection_current = None
        self.setModel(self.log_model)    
        self.connect(self.log_model,
                     QtCore.SIGNAL("layoutAboutToBeChanged()"),
                     self.lines_updated_remember_selection)
        self.connect(self.log_model,
                     QtCore.SIGNAL("layoutChanged()"),
                     self.lines_updated_restore_selection)
        
        header = self.header()
        header.setStretchLastSection(False)
        header.setResizeMode(logmodel.COL_REV, QtGui.QHeaderView.Interactive)
        header.setResizeMode(logmodel.COL_MESSAGE, QtGui.QHeaderView.Stretch)
        header.setResizeMode(logmodel.COL_DATE, QtGui.QHeaderView.Interactive)
        header.setResizeMode(logmodel.COL_AUTHOR, QtGui.QHeaderView.Interactive)
        fm = self.fontMetrics()
        
        col_margin = (self.style().pixelMetric(QtGui.QStyle.PM_FocusFrameHMargin,
                                               None, self) + 1) *2
        header.resizeSection(logmodel.COL_REV,
                             fm.width("8888.8.888") + col_margin)
        header.resizeSection(logmodel.COL_DATE,
                             # [bialix 2013/07/11]     v  I've added a space to sample string below to workaround bug https://bugs.launchpad.net/qbzr/+bug/430502
                             #                         v  If this is a problem on non-Windows platforms - please let me know and I'll add a platform check
                             fm.width("88-88-8888 88:88 ") + col_margin)
        header.resizeSection(logmodel.COL_AUTHOR,
                             fm.width("Joe I have a Long Name") + col_margin)

        self.view_commands = view_commands
        self.action_commands = action_commands
        
        if self.view_commands:
            self.connect(self,
                         QtCore.SIGNAL("doubleClicked(QModelIndex)"),
                         self.default_action)
        self.context_menu = QtGui.QMenu(self)
        self.context_menu_initialized = False

    def load(self, *args, **kargs):
        self.load_args = (args, kargs)
        self.log_model.load(*args, **kargs)
        self.create_context_menu()
        self._adjust_revno_column()
    
    @runs_in_loading_queue
    @ui_current_widget
    def refresh(self, b=True):
        (args, kargs) = self.load_args
        self.load(*args, **kargs)
    
    def create_context_menu(self, diff_is_default_action=True):
        if self.context_menu_initialized:
            return
        self.context_menu_initialized = True
        branch_count = len(self.log_model.graph_viz.branches)
        has_file_filter = bool(self.log_model.file_id_filter)
        
        self.context_menu = QtGui.QMenu(self)
        self.connect(self,
                     QtCore.SIGNAL("customContextMenuRequested(QPoint)"),
                     self.show_context_menu)
        
        if self.view_commands:
            if has_file_filter:
                if diff.has_ext_diff():
                    diff_menu = diff.ExtDiffMenu(
                        self, set_default=diff_is_default_action)
                    diff_menu.setTitle(gettext("Show file &differences"))
                    self.context_menu.addMenu(diff_menu)
                    self.connect(diff_menu, QtCore.SIGNAL("triggered(QString)"),
                                 self.show_diff_specified_files_ext)
                    
                    all_diff_menu = diff.ExtDiffMenu(self, set_default=False)
                    all_diff_menu.setTitle(gettext("Show all &differences"))
                    self.context_menu.addMenu(all_diff_menu)
                    self.connect(all_diff_menu, QtCore.SIGNAL("triggered(QString)"),
                                 self.show_diff_ext)
                else:
                    show_diff_action = self.context_menu.addAction(
                                        gettext("Show file &differences..."),
                                        self.show_diff_specified_files)
                    if diff_is_default_action:
                        self.context_menu.setDefaultAction(show_diff_action)
                    self.context_menu.addAction(
                                        gettext("Show all &differences..."),
                                        self.show_diff)
            else:
                if diff.has_ext_diff():
                    diff_menu = diff.ExtDiffMenu(
                        self, set_default=diff_is_default_action)
                    self.context_menu.addMenu(diff_menu)
                    self.connect(diff_menu, QtCore.SIGNAL("triggered(QString)"),
                                 self.show_diff_ext)
                else:
                    show_diff_action = self.context_menu.addAction(
                                        gettext("Show &differences..."),
                                        self.show_diff)
                    if diff_is_default_action:
                        self.context_menu.setDefaultAction(show_diff_action)

            self.context_menu_show_tree = self.context_menu.addAction(
                gettext("Show &tree..."), self.show_revision_tree)
        
        if self.action_commands:
            self.context_menu.addSeparator()
            def add_branch_action(text, triggered, require_wt=False):
                if branch_count == 1:
                    action = self.context_menu.addAction(text, triggered)
                    if require_wt:
                        action.setDisabled(
                            self.log_model.graph_viz.branches[0].tree is None)
                else:
                    menu = BranchMenu(text, self, self.log_model.graph_viz,
                                      require_wt)
                    self.connect(menu,
                                 QtCore.SIGNAL("bm_triggered"),
                                 triggered)
                    action = self.context_menu.addMenu(menu)
                return action
            
            self.context_menu_tag = add_branch_action(
                gettext("Tag &revision..."), self.tag_revision)
            
            self.context_menu_revert = add_branch_action(
                gettext("R&evert to this revision"), self.revert_to_revision,
                require_wt=True)
            
            self.context_menu_update = add_branch_action(
                gettext("&Update to this revision"), self.update_to_revision,
                require_wt=True)
            
            # In theory we should have a select branch option like push.
            # But merge is orentated to running in a branch, and selecting a
            # branch to merge form, so it does not really work well.
            if branch_count > 1:
                self.context_menu_cherry_pick = add_branch_action(
                    gettext("&Cherry pick"), self.cherry_pick,
                    require_wt=True)
            else:
                self.context_menu_cherry_pick = None
            
            self.context_menu_reverse_cherry_pick = add_branch_action(
                gettext("Re&verse Cherry pick"), self.reverse_cherry_pick,
                require_wt=True)

    def _adjust_revno_column(self):
        # update the data
        max_mainline_digits = self.rev_no_item_delegate.set_max_revno(
            self.log_model.graph_viz.max_mainline_revno)
        # resize the column
        header = self.header()
        fm = self.fontMetrics()
        col_margin = (self.style().pixelMetric(QtGui.QStyle.PM_FocusFrameHMargin,
                                               None, self) + 1) *2
        header.resizeSection(logmodel.COL_REV,
            fm.width(("8"*max_mainline_digits)+".8.888") + col_margin)

    def refresh_tags(self):
        self.log_model.graph_viz.lock_read_branches()
        try:
            self.log_model.graph_viz.load_tags()
        finally:
            self.log_model.graph_viz.unlock_branches()

    def get_c_rev_under_twisty_pos(self, pos):
        index = self.indexAt(pos)
        rect = self.visualRect(index)
        boxsize = rect.height()
        c_rev = self.log_model.c_rev_from_index(index)
        if c_rev and c_rev.twisty_state is not None:
            twistyRect = QtCore.QRect (rect.x() + boxsize * c_rev.col_index,
                                       rect.y() ,
                                       boxsize,
                                       boxsize)
            if twistyRect.contains(pos):
                return c_rev
    
    def mousePressEvent(self, e):
        collapse_expand_click = False
        if e.button() & QtCore.Qt.LeftButton:
            c_rev = self.get_c_rev_under_twisty_pos(e.pos())
            if c_rev:
                collapse_expand_click = True
                self.log_model.collapse_expand_rev(c_rev)
                new_index = self.log_model.index_from_rev(c_rev.rev)
                if new_index:
                    self.scrollTo(new_index)
                e.accept ()
        if not collapse_expand_click:
            QtGui.QTreeView.mousePressEvent(self, e)
    
    def mouseMoveEvent(self, e):
        # This prevents the selection from changing when the mouse is over
        # a twisty.
        if not self.get_c_rev_under_twisty_pos(e.pos()):
            QtGui.QTreeView.mouseMoveEvent(self, e)

    def keyPressEvent(self, e):
        e_key = e.key()
        if e_key in (QtCore.Qt.Key_Enter, QtCore.Qt.Key_Return) and self.view_commands:
            e.accept()
            self.default_action()
        elif e_key in (QtCore.Qt.Key_Left, QtCore.Qt.Key_Right):
            e.accept()
            indexes = self.get_selection_indexes()
            if not indexes:
                return
            c_rev = self.log_model.c_rev_from_index(indexes[0])
            
            if (e.key() == QtCore.Qt.Key_Right
                and c_rev and not c_rev.twisty_state):
                self.log_model.collapse_expand_rev(c_rev)
            if e.key() == QtCore.Qt.Key_Left:
                if c_rev and c_rev.twisty_state:
                    self.log_model.collapse_expand_rev(c_rev)
                else:
                    # Find the revision the merges us.
                    if c_rev.rev.merged_by:
                        merged_by = self.log_model.computed.revisions[
                                                        c_rev.rev.merged_by]
                        self.setCurrentIndex(self.log_model.index_from_c_rev(merged_by))
            self.scrollTo(self.currentIndex())
        else:
            QtGui.QTreeView.keyPressEvent(self, e)

    def select_revid(self, revid):
        try:
            rev = self.log_model.graph_viz.revid_rev[revid]
        except KeyError:
            return
        self.log_model.ensure_rev_visible(rev)
        index = self.log_model.index_from_rev(rev)
        if index:
            self.setCurrentIndex(index)
    
    # Remember the selection across layout changes.
    # This use to be handeled by the fact that we use to use a proxy model to
    # do filtering, but even that did not work 100%. I trided doing this by
    # updating the models QPersistentModelIndex, but there is a bug with
    # that in qt that not all columns are remembered.
    def lines_updated_remember_selection(self):
        selection_model = self.selectionModel()
        rows = selection_model.selectedRows()
        expand_indexes_to_ids = \
            lambda l: [str(i.data(logmodel.RevIdRole).toString())
                       for i in l]
        # Note: we don't do anything is there are 0 selected rows
        if rows:
            self.lines_updated_selection = \
                expand_indexes_to_ids((rows[0], rows[-1]))
        current_index = self.currentIndex()
        if current_index.isValid():
            self.lines_updated_selection_current = \
                str(current_index.data(logmodel.RevIdRole).toString())
        else:
            self.lines_updated_selection_current = None

    def lines_updated_restore_selection(self):
        selection_model = self.selectionModel()
        indexes = [self.log_model.index_from_revid(revid)
                   for revid in self.lines_updated_selection]
        selection_model.clear()
        if self.lines_updated_selection_current:
            current_index = self.log_model.index_from_revid(
                                    self.lines_updated_selection_current)
            if current_index:
                self.setCurrentIndex(current_index)
        if not len(indexes) == 0 and indexes[0]:
            if not indexes[1]:
                indexes[1] = indexes[0]
            selection = QtGui.QItemSelection(*indexes)
            selection_model.select(selection,
                                   (QtGui.QItemSelectionModel.SelectCurrent |
                                    QtGui.QItemSelectionModel.Rows))
    
    def get_selection_indexes(self, index=None):
        if index is None:
            return sorted(self.selectionModel().selectedRows(0), 
                          key=lambda x: x.row())
        else:
            return [index]
    
    def get_selection_and_merged_revids(self, index=None):
        indexes = self.get_selection_indexes(index)
        revids = set()
        for index in indexes:
            revid = str(index.data(logmodel.RevIdRole).toString())
            revids.add(revid)
            merges = [self.log_model.graph_viz.revisions[rev_index].revid
                      for rev_index in
                        self.log_model.graph_viz.revid_rev[revid].merges]
            revids.update(set(merges))
        return revids
    
    def get_selection_top_and_parent_revids_and_count(self, index=None):
        indexes = self.get_selection_indexes(index)
        if len(indexes) == 0:
            return (None, None), 0
        top_revid = str(indexes[0].data(logmodel.RevIdRole).toString())
        bot_revid = str(indexes[-1].data(logmodel.RevIdRole).toString())
        parents = self.log_model.graph_viz.known_graph.get_parent_keys(bot_revid)
        if parents:
            # We need a ui to select which parent.
            parent_revid = parents[0]
            
            # This is ugly. It is for the PendingMergesList in commit/revert.
            if parent_revid == "root:":
                parent_revid = self.log_model.graph_viz.graph.get_parent_map([bot_revid])[bot_revid][0]
        else:
            parent_revid = NULL_REVISION
        return (top_revid, parent_revid), len(indexes)
    
    def set_search(self, str, field):
        self.log_model.prop_search_filter.set_search(str, field)
    
    def default_action(self, index=None):
        self.show_diff_specified_files()
        
    def tag_revision(self, selected_branch_info=None):
        gv = self.log_model.graph_viz
        
        if selected_branch_info:
            selected_branch_info = selected_branch_info
        else:
            assert(len(gv.branches)==1)
            selected_branch_info = gv.branches[0]
        
        revid = str(self.currentIndex().data(logmodel.RevIdRole).toString())
        revno = gv.revid_rev[revid].revno_str
        revs = [RevisionSpec.from_string(revno)]
        branch = selected_branch_info.branch
        action = TagWindow.action_from_options(force=False, delete=False)
        window = CallBackTagWindow(branch, self.refresh_tags, action=action, revision=revs)
        window.show()
        self.window().windows.append(window)
    
    def sub_process_action(self, selected_branch_info, get_dialog,
                           auto_run=False, refresh_method=None):
        gv = self.log_model.graph_viz
        (top_revid, old_revid), rev_count = \
                self.get_selection_top_and_parent_revids_and_count()
        top_revno_str = gv.revid_rev[top_revid].revno_str
        if old_revid==NULL_REVISION:
            old_revno_str = 0
        else:
            old_revno_str = gv.revid_rev[old_revid].revno_str
        
        if selected_branch_info:
            single_branch = False
        else:
            assert(len(gv.branches)==1)
            selected_branch_info = gv.branches[0]
            single_branch = True
        
        dialog = get_dialog(rev_count,
                            top_revid, old_revid,
                            top_revno_str, old_revno_str,
                            selected_branch_info, single_branch)
        
        if refresh_method:
            QtCore.QObject.connect(dialog,
                                   QtCore.SIGNAL("subprocessFinished(bool)"),
                                   refresh_method)
        
        dialog.show()
        self.window().windows.append(dialog)
        
        if auto_run:
            dialog.do_accept()
    
    def revert_to_revision(self, selected_branch_info=None):
        def get_dialog(rev_count,
                       top_revid, old_revid,
                       top_revno_str, old_revno_str,
                       selected_branch_info, single_branch):
            assert(rev_count==1)
            
            if single_branch:
                desc = (gettext("Revert to revision %s revid:%s.") %
                        (top_revno_str, top_revid))
            else:
                desc = (gettext("Revert %s to revision %s revid:%s.") %
                        (selected_branch_info.label, top_revno_str, top_revid))
            
            args = ["revert", '-r', 'revid:%s' % top_revid]
            return SimpleSubProcessDialog(
                gettext("Revert"), desc=desc, args=args,
                dir=selected_branch_info.tree.basedir,
                parent=self)
        
        self.sub_process_action(selected_branch_info, get_dialog)
    
    def update_to_revision(self, selected_branch_info=None):
        def get_dialog(rev_count,
                       top_revid, old_revid,
                       top_revno_str, old_revno_str,
                       selected_branch_info, single_branch):
            assert(rev_count==1)
            
            if single_branch:
                desc = (gettext("Update to revision %s revid:%s.") %
                        (top_revno_str, top_revid))
            else:
                desc = (gettext("Update %s to revision %s revid:%s.") %
                        (selected_branch_info.label, top_revno_str, top_revid))
            
            args = ["update", '-r', 'revid:%s' % top_revid]
            return SimpleSubProcessDialog(
                gettext("Update"), desc=desc, args=args,
                dir=selected_branch_info.tree.basedir,
                parent=self)
        
        self.sub_process_action(selected_branch_info, get_dialog, True,
                                self.refresh)
        # TODO, we should just update the branch tags, rather than a full
        # refresh.

    def cherry_pick(self, selected_branch_info=None):
        def get_dialog(rev_count,
                       top_revid, old_revid,
                       top_revno_str, old_revno_str,
                       selected_branch_info, single_branch):
            from_branch_info = self.log_model.graph_viz.get_revid_branch_info(top_revid)
            
            desc = (gettext("Cherry-pick revisions %s - %s from %s to %s.") %
                    (old_revno_str, top_revno_str,
                     from_branch_info.label, selected_branch_info.label))
            
            args = ["merge", from_branch_info.branch.base,
                    '-r', 'revid:%s..revid:%s' % (old_revid, top_revid)]
            return SimpleSubProcessDialog(
                gettext("Cherry-pick"), desc=desc, args=args,
                dir=selected_branch_info.tree.basedir,
                parent=self)
        
        self.sub_process_action(selected_branch_info, get_dialog)
        # No refresh, because we don't track cherry-picks yet :-(

    def reverse_cherry_pick(self, selected_branch_info=None):
        def get_dialog(rev_count,
                       top_revid, old_revid,
                       top_revno_str, old_revno_str,
                       selected_branch_info, single_branch):
            if single_branch:
                desc = (gettext("Reverse cherry-pick revisions %s - %s") %
                        (old_revno_str, top_revno_str))
            else:
                desc = (gettext("Reverse cherry-pick revisions %s - %s in %s.") %
                        (old_revno_str, top_revno_str, selected_branch_info.label))

            args = ["merge", '.',
                    '-r', 'revid:%s..revid:%s' % (top_revid, old_revid)]
            return SimpleSubProcessDialog(
                gettext("Reverse cherry-pick"), desc=desc, args=args,
                dir=selected_branch_info.tree.basedir,
                parent=self)
        
        self.sub_process_action(selected_branch_info, get_dialog)
        # No refresh, because we don't track cherry-picks yet :-(
    
    def show_diff(self, index=None,
                  specific_files=None, specific_file_ids=None,
                  ext_diff=None):
        
        (new_revid, old_revid), count = \
            self.get_selection_top_and_parent_revids_and_count(index)
        if new_revid is None and old_revid is None:
            # No revision selection.
            return
        new_branch = self.log_model.graph_viz.get_revid_branch(new_revid)
        old_branch =  self.log_model.graph_viz.get_revid_branch(old_revid)
        
        def get_tree_if_current(revid):
            if (revid.startswith(CURRENT_REVISION) and
                isinstance(self.log_model.graph_viz,
                            logmodel.WithWorkingTreeGraphVizLoader)):
                return self.log_model.graph_viz.working_trees[revid]
        
        arg_provider = diff.InternalDiffArgProvider(
            old_revid, new_revid,
            old_branch, new_branch,
            old_tree=get_tree_if_current(old_revid),
            new_tree=get_tree_if_current(new_revid), 
            specific_files = specific_files,
            specific_file_ids = specific_file_ids)
        
        
        diff.show_diff(arg_provider, ext_diff=ext_diff,
                       parent_window=self.window(), context=self.diff_context)
    
    def show_diff_specified_files(self, ext_diff=None):
        if self.log_model.file_id_filter:
            self.show_diff(
                ext_diff=ext_diff,
                specific_file_ids = self.log_model.file_id_filter.file_ids)
        else:
            self.show_diff(ext_diff=ext_diff)
    
    def show_diff_ext(self, ext_diff):
        self.show_diff(ext_diff=ext_diff)

    def show_diff_specified_files_ext(self, ext_diff=None):
        self.show_diff_specified_files(ext_diff=ext_diff)
    
    def show_revision_tree(self):
        from bzrlib.plugins.qbzr.lib.browse import BrowseWindow
        revid = str(self.currentIndex().data(logmodel.RevIdRole).toString())
        gv = self.log_model.graph_viz
        if revid.startswith(CURRENT_REVISION):
            location = gv.working_trees[revid].abspath(u'')
            window = BrowseWindow(location=location, parent=self)
        else:
            revno = gv.revid_rev[revid].revno_str
            branch = gv.get_revid_branch(revid)
            window = BrowseWindow(branch=branch, revision_id=revid,
                                  revision_spec=revno, parent=self)
        window.show()
        self.window().windows.append(window)

    def show_context_menu(self, pos):
        branch_count = len(self.log_model.graph_viz.branches)
        (top_revid, old_revid), count = \
              self.get_selection_top_and_parent_revids_and_count()

        wt_selected = top_revid.startswith(CURRENT_REVISION)
         
        def filter_rev_ancestor(action, is_ancestor=True):
            branch_menu = action.menu()
            if branch_menu:
                vis_branch_count = branch_menu.filter_rev_ancestor(
                                                        top_revid, is_ancestor)
                if vis_branch_count == 0:
                    action.setVisible(False)
        
        if self.view_commands:
            self.context_menu_show_tree.setVisible(count == 1)
        
        if self.action_commands:
            self.context_menu_tag.setVisible(count == 1 and not wt_selected)
            if count == 1:
                filter_rev_ancestor(self.context_menu_tag)
            self.context_menu_revert.setVisible(count == 1 and not wt_selected)
            self.context_menu_update.setVisible(count == 1 and not wt_selected)
            
            if branch_count>1:
                if wt_selected:
                    self.context_menu_cherry_pick.setVisible(False)
                else:
                    filter_rev_ancestor(self.context_menu_cherry_pick,
                                        is_ancestor=False)
            
            if wt_selected:
                self.context_menu_reverse_cherry_pick.setVisible(False)
            else:
                filter_rev_ancestor(self.context_menu_reverse_cherry_pick)
            
        self.context_menu.popup(self.viewport().mapToGlobal(pos))


class BranchMenu(QtGui.QMenu):
    
    def __init__ (self, text, parent, graphprovider, require_wt):
        QtGui.QMenu.__init__(self, text, parent)
        self.graphprovider = graphprovider
        for branch in self.graphprovider.branches:
            action = QtGui.QAction(branch.label, self)
            action.setData(QtCore.QVariant(branch))
            self.addAction(action)
            if require_wt and branch.tree is None:
                action.setDisabled(True)
        
        self.connect(self, QtCore.SIGNAL("triggered(QAction *)"),
                     self.triggered)
    
    def filter_rev_ancestor(self, rev, is_ancestor=True):
        visible_action_count = 0
        
        for action in self.actions():
            branch_info = action.data().toPyObject()
            branch_tip = branch_info.branch.last_revision()
            is_ancestor_ = (
                frozenset((branch_tip,)) ==
                self.graphprovider.known_graph.heads((branch_tip, rev)))
            visible = is_ancestor_== is_ancestor
            action.setVisible(visible)
            if visible:
                visible_action_count += 1
        
        return visible_action_count
    
    def triggered(self, action):
        branch_info = action.data().toPyObject()
        self.emit(QtCore.SIGNAL("bm_triggered"), branch_info)


class GraphTagsBugsItemDelegate(QtGui.QStyledItemDelegate):

    _twistyColor = QtCore.Qt.black

    def paint(self, painter, option, index):
        data = index.data(logmodel.GraphDataRole)
        if data.isValid():
            draw_graph = True
            if QtCore.PYQT_VERSION_STR.startswith('4.5.'):
                # toPyObject is buggy in 4.5
                def toPy (x):
                    if isinstance(x, QtCore.QVariant):
                        return x.toPyObject()
                    else:
                        return x
                c_rev, prev_c_rev, labels, is_clicked = (
                    toPy(item) for item in data.toPyObject())
                labels = [[toPy(x) for x in toPy(label)]
                           for label in toPy(labels)]
            else:
                c_rev, prev_c_rev, labels, is_clicked = data.toPyObject()
            
        else:
            draw_graph = False
        
        option = QtGui.QStyleOptionViewItemV4(option)
        self.initStyleOption(option, index)
        widget = self.parent()
        style = widget.style()
        
        text_margin = style.pixelMetric(QtGui.QStyle.PM_FocusFrameHMargin,
                                        None, widget) + 1
        
        painter.save()
        painter.setClipRect(option.rect)
        style.drawPrimitive(QtGui.QStyle.PE_PanelItemViewItem,
                            option, painter, widget)
        
        graphCols = 0
        rect = option.rect
        if draw_graph:
            painter.save()
            try:
                painter.setRenderHint(QtGui.QPainter.Antialiasing)            
                boxsize = float(rect.height())
                dotsize = 0.7
                pen = QtGui.QPen()
                penwidth = 1
                pen.setWidth(penwidth)
                pen.setCapStyle(QtCore.Qt.FlatCap)
                #this is to try get lines 1 pixel wide to actualy be 1 pixel wide.
                painter.translate(0.5, 0.5)
                
                # Draw lines into the cell
                if prev_c_rev:
                    for start, end, color, direct in prev_c_rev.lines:
                        self.drawLine (painter, pen, rect, boxsize,
                                       rect.y(), boxsize,
                                       start, end, color, direct)
                        graphCols = max((graphCols, min(start, end)))
        
                # Draw lines out of the cell
                if c_rev:
                    for start, end, color, direct in c_rev.lines:
                        self.drawLine (painter, pen, rect,boxsize,
                                       rect.y() + boxsize, boxsize,
                                       start, end, color, direct)
                        graphCols = max((graphCols, min(start, end)))
                
                # Draw the revision node in the right column
                
                if c_rev.col_index is not None:
                    graphCols = max((graphCols, c_rev.col_index))
                    pen.setColor(self.get_color(c_rev.rev.color, False))
                    painter.setPen(pen)
                    if not is_clicked:
                        painter.setBrush(QtGui.QBrush(
                            self.get_color(c_rev.rev.color,True)))
                    else:
                        painter.setBrush(QtGui.QBrush(QtCore.Qt.white))
                        
                    centerx = rect.x() + boxsize * (c_rev.col_index + 0.5)
                    centery = rect.y() + boxsize * 0.5
                    painter.drawEllipse(
                        QtCore.QRectF(centerx - (boxsize * dotsize * 0.5 ),
                                      centery - (boxsize * dotsize * 0.5 ),
                                     boxsize * dotsize, boxsize * dotsize))
    
                    # Draw twisty
                    if not is_clicked and c_rev.twisty_state is not None:
                        linesize = 0.35
                        pen.setColor(self._twistyColor)
                        painter.setPen(pen)
                        
                        painter.drawLine(QtCore.QLineF
                                         (centerx - boxsize * linesize / 2,
                                          centery,
                                          centerx + boxsize * linesize / 2,
                                          centery))
                        if not c_rev.twisty_state:
                            painter.drawLine(QtCore.QLineF
                                             (centerx,
                                              centery - boxsize * linesize / 2,
                                              centerx,
                                              centery + boxsize * linesize / 2))
                
            finally:
                painter.restore()
                rect.adjust( (graphCols + 1.5) * boxsize, 0, 0, 0)        
                
            painter.save()
            x = 0
            try:
                tagFont = QtGui.QFont(option.font)
                tagFont.setPointSizeF(tagFont.pointSizeF() * 9 / 10)
        
                for label, bg_color, text_color in labels:
                    tagRect = rect.adjusted(1, 1, -1, -1)
                    tagRect.setWidth(QtGui.QFontMetrics(tagFont).width(label) + 6)
                    tagRect.moveLeft(tagRect.x() + x)
                    painter.setPen(bg_color)
                    painter.fillRect(tagRect.adjusted(1, 1, -1, -1), bg_color)
                    tl = tagRect.topLeft()
                    br = tagRect.bottomRight()
                    painter.drawLine(tl.x(), tl.y() + 1, tl.x(), br.y() - 1)
                    painter.drawLine(br.x(), tl.y() + 1, br.x(), br.y() - 1)
                    painter.drawLine(tl.x() + 1, tl.y(), br.x() - 1, tl.y())
                    painter.drawLine(tl.x() + 1, br.y(), br.x() - 1, br.y())
                    painter.setFont(tagFont)
                    painter.setPen(text_color)
                    painter.drawText(tagRect.left() + 3, tagRect.bottom() - option.fontMetrics.descent() + 1, label)
                    x += tagRect.width() + text_margin
            finally:
                painter.restore()
            rect.adjust(x, 0, 0, 0)
        
        if not option.text.isEmpty():
            painter.setPen(get_text_color(option, style))
            text_rect = rect.adjusted(0, 0, -text_margin, 0)
            painter.setFont(option.font)
            fm = painter.fontMetrics()
            text_width = fm.width(option.text)
            text = option.text
            if text_width > text_rect.width():
                text = self.elidedText(fm, text_rect.width(),
                                       QtCore.Qt.ElideRight, text)
            
            painter.drawText(text_rect, QtCore.Qt.AlignLeft, text)
        
        painter.restore()
    
    def get_color(self, color, back):
        qcolor = QtGui.QColor()
        if color == 0:
            if back:
                qcolor.setHsvF(0,0,0.8)
            else:
                qcolor.setHsvF(0,0,0)
        else:
            h = float(color % 6) / 6
            if back:
                qcolor.setHsvF(h,0.4,1)
            else:
                qcolor.setHsvF(h,1,0.7)
        
        return qcolor
    
    def drawLine(self, painter, pen, rect, boxsize, mid, height,
                 start, end, color, direct):
        pen.setColor(self.get_color(color,False))
        if direct:
            pen.setStyle(QtCore.Qt.SolidLine)
        else:
            pen.setStyle(QtCore.Qt.DotLine)            
        painter.setPen(pen)
        startx = round(rect.x() + boxsize * start + boxsize / 2)
        endx = round(rect.x() + boxsize * end + boxsize / 2)
        
        path = QtGui.QPainterPath()
        path.moveTo(QtCore.QPointF(startx, mid - height / 2))
        
        if start - end == 0 :
            path.lineTo(QtCore.QPointF(endx, mid + height / 2)) 
        else:
            path.cubicTo(QtCore.QPointF(startx, mid - height / 5),
                         QtCore.QPointF(startx, mid - height / 5),
                         QtCore.QPointF(startx + (endx - startx) / 2, mid))

            path.cubicTo(QtCore.QPointF(endx, mid + height / 5),
                         QtCore.QPointF(endx, mid + height / 5),
                         QtCore.QPointF(endx, mid + height / 2 + 1))
        painter.drawPath(path)
        pen.setStyle(QtCore.Qt.SolidLine)
    
    def sizeHint(self, option, index):
        size = QtGui.QStyledItemDelegate.sizeHint(self, option, index)
        height = size.height()
        # sizes smaller that this are to small.
        if height < 14:
            height = 14
        
        # even sizes blur less
        if height % 2 == 1:
            height += 1
        
        size.setHeight(height)
        return size
