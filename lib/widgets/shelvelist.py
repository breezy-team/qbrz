# -*- coding: utf-8 -*-
#
# QBzr - Qt frontend to Bazaar commands
# Copyright (C) 2011 QBzr Developers
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

import sys, time
from PyQt4 import QtCore, QtGui
from PyQt4.QtGui import QKeySequence

from bzrlib.revision import CURRENT_REVISION
from bzrlib.errors import (
        NoSuchRevision, 
        NoSuchRevisionInTree,
        PathsNotVersionedError)
from bzrlib.plugins.qbzr.lib.i18n import gettext, N_
from bzrlib.plugins.qbzr.lib.util import (
    ToolBarThrobberWidget,
    get_apparent_author_name,
    get_set_encoding,
    runs_in_loading_queue,
    get_icon,
    get_monospace_font,
    StandardButton,
    get_tab_width_pixels,
    get_qbzr_config,
    )
from bzrlib.plugins.qbzr.lib.widgets.toolbars import (
    FindToolbar, ToolbarPanel, LayoutSelector
    )
from bzrlib.plugins.qbzr.lib.diffview import (
    SidebySideDiffView,
    SimpleDiffView,
    )

from bzrlib.plugins.qbzr.lib.uifactory import ui_current_widget
from bzrlib.plugins.qbzr.lib.trace import reports_exception
from bzrlib.plugins.qbzr.lib.logwidget import LogList
from bzrlib.lazy_import import lazy_import
lazy_import(globals(), '''
from bzrlib import transform
from bzrlib.workingtree import WorkingTree
from bzrlib.plugins.qbzr.lib.encoding_selector import EncodingMenuSelector
from bzrlib.plugins.qbzr.lib.diffwindow import DiffItem
from bzrlib.shelf import Unshelver
from bzrlib.shelf_ui import Unshelver as Unshelver_ui
''')

class ShelveListWidget(ToolbarPanel):

    def __init__(self, directory=None, complete=False, ignore_whitespace=False, 
                 encoding=None, splitters=None, parent=None):
        ToolbarPanel.__init__(self, slender=False, icon_size=22, parent=parent)

        self.encoding = encoding
        self.directory = directory

        self.current_diffs = []
        self.complete = complete
        self.ignore_whitespace = ignore_whitespace
        self.show_files = False
        self.load_settings()

        # build main widgets
        self.shelve_view = QtGui.QTreeWidget(self)
        self.shelve_view.setHeaderLabels([gettext("Id"), gettext("Message")])
        header = self.shelve_view.header()
        header.setResizeMode(0, QtGui.QHeaderView.ResizeToContents)

        self.file_view = QtGui.QTreeWidget(self)
        self.file_view.setHeaderLabels([gettext("File Name"), gettext("Status")])
        self.file_view.setSelectionMode(QtGui.QAbstractItemView.ExtendedSelection)
        header = self.file_view.header()
        header.setStretchLastSection(False)
        header.setResizeMode(0, QtGui.QHeaderView.Stretch)
        header.setResizeMode(1, QtGui.QHeaderView.ResizeToContents)
        self.stack = QtGui.QStackedWidget(self)
        self.diffviews = (SidebySideDiffView(self), SimpleDiffView(self))
        for view in self.diffviews:
            self.stack.addWidget(view)
        for browser in self.diffviews[0].browsers:
            browser.installEventFilter(self)

        diff_panel = ToolbarPanel(self)

        # build diffpanel toolbar
        show_find = diff_panel.add_toolbar_button(
                        N_("Find"), icon_name="edit-find", checkable=True,
                        shortcut=QtGui.QKeySequence.Find)
        diff_panel.add_separator()
        diff_panel.add_toolbar_button(N_("Unidiff"), icon_name="unidiff", 
                checkable=True, shortcut="Ctrl+U", onclick=self.unidiff_toggled)

        view_menu = QtGui.QMenu(gettext('View Options'), self)
        view_menu.addAction(
                diff_panel.create_button(N_("&Complete"), icon_name="complete", 
                    checkable=True, checked=complete, onclick=self.complete_toggled)
                )
        view_menu.addAction(
                diff_panel.create_button(N_("Ignore whitespace"), icon_name="whitespace", 
                    checkable=True, checked=ignore_whitespace, onclick=self.whitespace_toggled)
                )
        self.encoding_selector = EncodingMenuSelector(self.encoding,
                                    gettext("Encoding"), self.encoding_changed)
        self.encoding_selector.setIcon(get_icon("format-text-bold", 16))
        view_menu.addMenu(self.encoding_selector)
        diff_panel.add_toolbar_menu(
                N_("&View Options"), view_menu, icon_name="document-properties",
                shortcut="Alt+V")

        self.find_toolbar = FindToolbar(self, self.diffviews[0].browsers[0], show_find)
        diff_panel.add_widget(self.find_toolbar)
        diff_panel.add_widget(self.stack)
        self.find_toolbar.hide()

        # Layout widgets
        self.splitter1 = QtGui.QSplitter(QtCore.Qt.Horizontal)
        self.splitter1.addWidget(self.shelve_view)

        self.splitter2 = QtGui.QSplitter(QtCore.Qt.Horizontal)
        self.splitter2.addWidget(self.file_view)
        self.splitter2.addWidget(diff_panel)

        self.splitter = QtGui.QSplitter(QtCore.Qt.Vertical)
        self.splitter.addWidget(self.splitter1)
        self.splitter.addWidget(self.splitter2)
        self.splitter.setStretchFactor(0, 1)

        if splitters:
            splitters.add("shelvelist_splitter", self.splitter)
            splitters.add("shelvelist_splitter1", self.splitter1)
            splitters.add("shelvelist_splitter2", self.splitter2)

        self.splitter.setStretchFactor(1, 3)

        pal = QtGui.QPalette()
        pal.setColor(QtGui.QPalette.Window, QtGui.QColor(0,0,0,0))
        self.splitter.setPalette(pal)

        layout = QtGui.QVBoxLayout()
        layout.setMargin(10)
        layout.addWidget(self.splitter)
        self.add_layout(layout)
        
        # build main toolbar
        self.unshelve_button = self.add_toolbar_button(N_("Unshelve"), icon_name="unshelve", 
                                enabled=False, onclick=self.unshelve_clicked)
        self.delete_button = self.add_toolbar_button(N_("Delete"), icon_name="delete", 
                                enabled=False, onclick=self.delete_clicked)
        self.add_separator()

        layout_selector = \
                LayoutSelector(num=3, onchanged=lambda val:self.set_layout(type=val),
                    parent=self, initial_no=self.current_layout)

        layout_selector.addSeparator()
        layout_selector.addAction(
                self.create_button(gettext("Show filelist"),
                    icon_name="file", icon_size=16, checkable=True, 
                    checked=self.show_files, shortcut="Ctrl+L", 
                    onclick=lambda val:self.set_layout(show_files=val))
                )

        self.add_toolbar_menu(N_("&Layout"), layout_selector, 
                icon_name="internet-news-reader", shortcut="Alt+L")

        self.add_toolbar_button(N_("&Refresh"), icon_name="view-refresh", 
                shortcut="Ctrl+R", onclick=self.refresh)

        self.shelf_id = None

        self.set_layout()

        # set signals
        self.connect(self.shelve_view, QtCore.SIGNAL("itemSelectionChanged()"),
                self.selected_shelve_changed)
        self.connect(self.file_view, QtCore.SIGNAL("itemSelectionChanged()"),
                self.selected_files_changed)

        self.splitter.setChildrenCollapsible(False)
        self.splitter1.setChildrenCollapsible(False)
        self.splitter2.setChildrenCollapsible(False)

        self.loaded = False
        self._loading_diff = False
        self._pending_info = None
        self._selecting_all_files = False

    def set_layout(self, type=None, show_files=None):
        if type is not None:
            self.current_layout = type
        if show_files is not None:
            self.show_files = show_files

        self.file_view.setParent(None)
        if self.current_layout == 1:
            self.splitter.setOrientation(QtCore.Qt.Vertical)
            self.splitter1.setOrientation(QtCore.Qt.Horizontal)
            if self.show_files:
                self.splitter1.insertWidget(1, self.file_view)
        elif self.current_layout == 2:
            self.splitter.setOrientation(QtCore.Qt.Horizontal)
            self.splitter1.setOrientation(QtCore.Qt.Vertical)
            if self.show_files:
                self.splitter1.insertWidget(1, self.file_view)
        else:
            self.splitter.setOrientation(QtCore.Qt.Vertical)
            self.splitter2.setOrientation(QtCore.Qt.Horizontal)
            if self.show_files:
                self.splitter2.insertWidget(0, self.file_view)

        for sp in (self.splitter, self.splitter1, self.splitter2):
            if sp.count() != 2:
                continue
            size = sum(sp.sizes())
            if sp.orientation() == QtCore.Qt.Vertical:
                size1 = int(size * 0.2)
            else:
                size1 = int(size * 0.3)
            sp.setSizes((size1, size - size1))

        if show_files == False:
            # When filelist is hidden, select all files always.
            self.select_all_files()

    def refresh(self):
        self.loaded = False
        self.clear()
        tree = WorkingTree.open_containing(self.directory)[0]
        tree.lock_read()
        try:
            manager = tree.get_shelf_manager()
            shelves = manager.active_shelves()
            for shelf_id in reversed(shelves):

                message = manager.get_metadata(shelf_id).get('message')
                item = QtGui.QTreeWidgetItem()
                item.setText(0, unicode(shelf_id))
                item.setText(1, message or gettext('<no message>'))
                item.setIcon(0, get_icon("folder", 16))
                item.shelf_id = shelf_id
                self.shelve_view.addTopLevelItem(item)
            self.tree = tree
            self.manager = manager

        finally:
            tree.unlock()
        self.update()
        self.loaded = True

    def update(self):
        for view in (self.shelve_view.viewport(), self.file_view.viewport()) + self.diffviews:
            view.update()

    def clear(self):
        self.shelve_view.clear()
        self.manager = None

    def show_changes(self, shelf_id):
        cleanup = []
        shelf_file = self.manager.read_shelf(shelf_id)
        cleanup.append(shelf_file.close)
        try:
            records = Unshelver.iter_records(shelf_file)
            revid = Unshelver.parse_metadata(records)['revision_id']
            try:
                base_tree = self.tree.revision_tree(revid)
            except NoSuchRevisionInTree:
                base_tree = self.tree.branch.repository.revision_tree(revid)
            preview = transform.TransformPreview(base_tree)
            cleanup.append(preview.finalize)
            preview.deserialize(records)

            tabwidth = get_tab_width_pixels(self.tree.branch)
            self.diffviews[0].setTabStopWidths((tabwidth, tabwidth))
            self.diffviews[1].setTabStopWidth(tabwidth)
            
            self.load_diff(preview.get_preview_tree(), base_tree)

        finally:
            for func in cleanup:
                func()

    def load_diff(self, tree, base_tree):
        self.file_view.clear()

        changes = tree.iter_changes(base_tree)

        def changes_key(change):
            return change[1][1] or change[1][0]
        
        for (file_id, paths, changed_content, versioned, parent, 
                name, kind, executable) in sorted(changes, key=changes_key):
            di = DiffItem.create([base_tree, tree], file_id, paths, changed_content,
                    versioned, parent, name, kind, executable)
            if not di:
                continue

            di.load()

            old_path, new_path = di.paths
            if di.versioned == (True, False):
                text = old_path
                color = 'red'
            elif di.versioned == (False, True):
                text = new_path
                color = 'blue'
            elif di.paths[0] != di.paths[1]:
                text = u'%s => %s' % (old_path, new_path)
                color = 'purple'
            else:
                text = old_path
                color = None
                
            item = QtGui.QTreeWidgetItem()
            item.setText(0, text)
            item.setText(1, gettext(di.status))
            item.setIcon(0, get_icon("file", 16))
            item.diffitem = di
            if color:
                item.setData(0, QtCore.Qt.TextColorRole, color)
            self.file_view.addTopLevelItem(item)

    def show_diff(self, diffs, refresh):
        self._loading_diff = True 
        try:
            cur_len = len(self.current_diffs)
            if not refresh and cur_len <= len(diffs) and self.current_diffs == diffs[0:cur_len]:
                appends = diffs[cur_len:]
            else:
                for view in self.diffviews:
                    view.clear()
                self.current_diffs = []
                appends = diffs 
            for d in appends:
                lines = d.lines
                groups = d.groups(self.complete, self.ignore_whitespace)
                dates = d.dates[:]  # dates will be changed in append_diff
                ulines = d.encode((self.encoding_selector.encoding,
                                   self.encoding_selector.encoding))
                data = [''.join(l) for l in ulines]
                for view in self.diffviews:
                    view.append_diff(list(d.paths), d.file_id, d.kind, d.status, dates, 
                                     d.versioned, d.binary, ulines, groups, 
                                     data, d.properties_changed)
                self.current_diffs.append(d)
                if self._pending_info is not None:
                    # Interrupted
                    break
        finally:
            self._loading_diff = False

    def selected_shelve_changed(self):
        items = self.shelve_view.selectedItems()
        if len(items) != 1:
            self.shelf_id = None
            self.unshelve_button.setEnabled(False)
            self.delete_button.setEnabled(False)
            self.file_view.clear()
        else:
            self.shelf_id = items[0].shelf_id
            self.unshelve_button.setEnabled(True)
            self.delete_button.setEnabled(True)
            self.show_changes(self.shelf_id)
            if self.show_files:
                self.select_first_file()
            else:
                self.select_all_files()
        self.file_view.viewport().update()

    def selected_files_changed(self):
        if not self._selecting_all_files:
            self.show_selected_diff()

    def select_all_files(self):
        try:
            self._selecting_all_files = True
            for i in range(0, self.file_view.topLevelItemCount()):
                self.file_view.topLevelItem(i).setSelected(True)
        finally:
            self._selecting_all_files = False
            self.selected_files_changed()

    def select_first_file(self):
        if self.file_view.topLevelItemCount() > 0:
            self.file_view.topLevelItem(0).setSelected(True)

    def show_selected_diff(self, refresh = False):
        # NOTE: SideBySideDiffView.append_diff uses processEvents internally. 
        #       So, show_selected_diff can be called during another 
        #       show_selected_diff is running.
        if self._loading_diff:
            if self._pending_info is None:
                self._pending_info = (refresh,)
                self.show_selected_diff_delay()
            elif refresh and not self._pending_info[0]:
                self._pending_info = (True,)
        else:
            diffs = [x.diffitem for x in self.file_view.selectedItems()]
            diffs.sort(key=lambda x:x.paths[0] or x.paths[1])
            self.show_diff(diffs, refresh)

    def show_selected_diff_delay(self):
        if self._pending_info == None:
            return
        if self._loading_diff:
            QtCore.QTimer.singleShot(100, self.show_selected_diff_delay)
            return
        refresh = self._pending_info[0]
        self._pending_info = None
        self.show_selected_diff(refresh)

    def unidiff_toggled(self, state):
        index = 1 if state else 0
        self.diffviews[index].rewind()
        self.stack.setCurrentIndex(index)
        if index == 0:
            self.find_toolbar.text_edit = self.diffviews[0].browsers[0]
        else:
            self.find_toolbar.text_edit = self.diffviews[1]

    def complete_toggled(self, state):
        self.complete = state
        self.show_selected_diff(refresh = True)

    def whitespace_toggled(self, state):
        self.ignore_whitespace = state
        self.show_selected_diff(refresh = True)

    def shelve_clicked(self):
        window = ShelveWindow(encoding=self.encoding, directory=self.directory, complete=self.complete, parent=self)
        try:
            if window.exec_() == QtGui.QDialog.Accepted:
                self.refresh()
        finally:
            window.cleanup()

    def prompt_bool(self, prompt, warning=False):
        if warning:
            func = QtGui.QMessageBox.warning
        else:
            func = QtGui.QMessageBox.question
        ret = func(self, gettext('Shelve'), gettext(prompt), 
                    QtGui.QMessageBox.Ok | QtGui.QMessageBox.Cancel)
        return (ret == QtGui.QMessageBox.Ok)

    def unshelve_clicked(self):
        if not self.shelf_id:
            return
        if not self.prompt_bool(
                N_('Changes in shelf[%d] will be applied to working tree.') % self.shelf_id):
            return

        self.unshelve(self.shelf_id, 'apply')
        self.refresh()

    def delete_clicked(self):
        if not self.shelf_id:
            return
        if not self.prompt_bool(
                N_('Shelf[%d] will be deleted without applying.') % self.shelf_id, 
                warning=True):
            return

        self.unshelve(self.shelf_id, 'delete-only')
        self.refresh()

    def encoding_changed(self, encoding):
        self.show_selected_diff(refresh = True)
        
    def unshelve(self, id, action):
        unshelver = Unshelver_ui.from_args(id, action, directory=self.directory)
        try:
            unshelver.run()
        finally:
            unshelver.tree.unlock()

    def eventFilter(self, object, event):
        if event.type() == QtCore.QEvent.FocusIn:
            if object in self.diffviews[0].browsers:
                self.find_toolbar.text_edit = object
        return ToolbarPanel.eventFilter(self, object, event)
    
    def load_settings(self):
        config = get_qbzr_config()
        layout = config.get_option("shelvelist_layout")
        if layout not in ("2", "3"):
            layout = "1"
        self.current_layout = int(layout)
        self.show_files = not not config.get_option_as_bool("shelvelist_show_filelist")

    def save_settings(self):
        config = get_qbzr_config()
        config.set_option("shelvelist_layout", str(self.current_layout))
        config.set_option("shelvelist_show_filelist", str(self.show_files))
        config.save()

    def hideEvent(self, event):
        self.save_settings()

