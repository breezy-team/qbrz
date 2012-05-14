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
    get_set_tab_width_chars,
    get_qbzr_config,
    )
from bzrlib.plugins.qbzr.lib.widgets.toolbars import (
    FindToolbar, ToolbarPanel, LayoutSelector 
    )
from bzrlib.plugins.qbzr.lib.widgets.tab_width_selector import TabWidthMenuSelector
from bzrlib.plugins.qbzr.lib.diffview import (
    SidebySideDiffView,
    SimpleDiffView,
    )

from bzrlib.plugins.qbzr.lib.uifactory import ui_current_widget
from bzrlib.plugins.qbzr.lib.trace import reports_exception
from bzrlib.plugins.qbzr.lib.logwidget import LogList
from bzrlib.plugins.qbzr.lib.decorators import lazy_call
from bzrlib.plugins.qbzr.lib.widgets.texteditaccessory import setup_guidebar_for_find
from bzrlib.lazy_import import lazy_import
lazy_import(globals(), '''
from bzrlib import transform
from bzrlib.workingtree import WorkingTree
from bzrlib.plugins.qbzr.lib.encoding_selector import EncodingMenuSelector
from bzrlib.plugins.qbzr.lib.diff import DiffItem
from bzrlib.shelf import Unshelver
from bzrlib.shelf_ui import Unshelver as Unshelver_ui
from bzrlib.plugins.qbzr.lib.subprocess import SimpleSubProcessDialog
import sip
''')


class ShelveListWidget(ToolbarPanel):

    def __init__(self, directory=None, complete=False, ignore_whitespace=False, 
                 encoding=None, splitters=None, parent=None):
        ToolbarPanel.__init__(self, slender=False, icon_size=22, parent=parent)

        self.initial_encoding = encoding
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
        self.tabwidth_selector = TabWidthMenuSelector(label_text=gettext("Tab width"), 
                                    onChanged=self.on_tabwidth_changed)
        view_menu.addMenu(self.tabwidth_selector)
        self.encoding_selector = EncodingMenuSelector(encoding,
                                    gettext("Encoding"), self.encoding_changed)
        self.encoding_selector.setIcon(get_icon("format-text-bold", 16))
        view_menu.addMenu(self.encoding_selector)
        diff_panel.add_toolbar_menu(
                N_("&View Options"), view_menu, icon_name="document-properties",
                shortcut="Alt+V")

        self.find_toolbar = FindToolbar(self, self.diffviews[0].browsers, show_find)
        diff_panel.add_widget(self.find_toolbar)
        diff_panel.add_widget(self.stack)
        self.find_toolbar.hide()
        for gb in self.diffviews[0].guidebar_panels:
            setup_guidebar_for_find(gb, self.find_toolbar, 1)
        setup_guidebar_for_find(self.diffviews[1], self.find_toolbar, 1)

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

        for sp in (self.splitter, self.splitter1, self.splitter2):
            sp.setChildrenCollapsible(False)
            sp.setStretchFactor(0, 3)
            sp.setStretchFactor(1, 7)

        pal = QtGui.QPalette()
        pal.setColor(QtGui.QPalette.Window, QtGui.QColor(0,0,0,0))
        self.splitter.setPalette(pal)

        layout = QtGui.QVBoxLayout()
        layout.setMargin(10)
        layout.addWidget(self.splitter)
        self.add_layout(layout)
        
        # build main toolbar
        unshelve_menu = QtGui.QMenu(gettext("Unshelve"), self)
        unshelve_menu.addAction(self.create_button(N_("Dry run"), 
                                    onclick=lambda:self.do_unshelve('dry-run')))
        unshelve_menu.addAction(self.create_button(N_("Keep"),
                                    onclick=lambda:self.do_unshelve('keep')))
        unshelve_menu.addAction(self.create_button(N_("Delete"),
                                    onclick=lambda:self.do_unshelve('delete-only')))
        
        self.unshelve_button = self.add_toolbar_button(N_("Unshelve"), icon_name="unshelve", 
                                    enabled=False, onclick=lambda:self.do_unshelve('apply'), 
                                    menu=unshelve_menu)
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

        self.loaded = False
        self._interrupt_switch = False
        self._need_refresh = False
        self._selecting_all_files = False
        self.brushes = {
            'added' : QtGui.QBrush(QtCore.Qt.blue),
            'removed' : QtGui.QBrush(QtCore.Qt.red),
            'renamed' : QtGui.QBrush(QtGui.QColor(160, 32, 240)), # purple
            'renamed and modified' : QtGui.QBrush(QtGui.QColor(160, 32, 240)),
        }

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

        if type is not None:
            # Reset splitter pos after changing type.
            for sp in (self.splitter, self.splitter1, self.splitter2):
                if sp.count() != 2:
                    continue
                size = sum(sp.sizes())
                if size > 0:
                    size1 = int(size * 0.3)
                    sp.setSizes((size1, size - size1))

        if show_files == False:
            # When filelist is hidden, select all files always.
            self.select_all_files()

    def on_tabwidth_changed(self, width):
        get_set_tab_width_chars(self.tree.branch, tab_width_chars=width)
        self._on_tabwidth_changed(width)

    def _on_tabwidth_changed(self, width):
        pixels = get_tab_width_pixels(tab_width_chars=width)
        self.diffviews[0].setTabStopWidths((pixels, pixels))
        self.diffviews[1].setTabStopWidth(pixels)

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

            branch = tree.branch
            if self.initial_encoding is None:
                encoding = get_set_encoding(None, branch)
                self.initial_encoding = encoding            # save real encoding for the next time
                self.encoding_selector.encoding = encoding  # set encoding selector
            tabwidth = get_set_tab_width_chars(branch)
            self.tabwidth_selector.setTabWidth(tabwidth)
            self._on_tabwidth_changed(tabwidth)

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
        
        for di in DiffItem.iter_items((base_tree, tree), lock_trees=False):
            di.load()

            old_path, new_path = di.paths
            if di.versioned == (True, False):
                text = old_path
            elif di.versioned == (False, True):
                text = new_path
            elif di.paths[0] != di.paths[1]:
                text = u'%s => %s' % (old_path, new_path)
            else:
                text = old_path
                
            item = QtGui.QTreeWidgetItem()
            item.setText(0, text)
            item.setText(1, gettext(di.status))
            if (di.kind[1] or di.kind[0]) == 'directory':
                item.setIcon(0, get_icon("folder", 16))
            else:
                item.setIcon(0, get_icon("file", 16))
            item.diffitem = di
            brush = self.brushes.get(di.status)
            if brush:
                item.setForeground(0, brush)
                item.setForeground(1, brush)
            self.file_view.addTopLevelItem(item)

    @lazy_call(100, per_instance=True)
    @runs_in_loading_queue
    def _show_selected_diff(self):
        if sip.isdeleted(self):
            return
        self._interrupt_switch = False 
        try:
            refresh = self._need_refresh
            self._need_refresh = False
            
            diffs = [x.diffitem for x in self.file_view.selectedItems()]
            diffs.sort(key=lambda x:x.paths[0] or x.paths[1])

            cur_len = len(self.current_diffs)
            if not refresh and cur_len <= len(diffs) and self.current_diffs == diffs[0:cur_len]:
                appends = diffs[cur_len:]
            else:
                for view in self.diffviews:
                    view.set_complete(self.complete)
                    view.clear()
                self.current_diffs = []
                appends = diffs 
            for d in appends:
                lines = d.lines
                groups = d.groups(self.complete, self.ignore_whitespace)
                dates = d.dates[:]  # dates will be changed in append_diff
                ulines = d.get_unicode_lines(
                    (self.encoding_selector.encoding,
                     self.encoding_selector.encoding))
                data = [''.join(l) for l in ulines]
                for view in self.diffviews:
                    view.append_diff(list(d.paths), d.file_id, d.kind, d.status, dates, 
                                     d.versioned, d.binary, ulines, groups, 
                                     data, d.properties_changed)
                self.current_diffs.append(d)
                if self._interrupt_switch:
                    # Interrupted
                    break
        finally:
            self._interrupt_switch = False
            for view in self.diffviews[0].browsers + (self.diffviews[1],):
                view.emit(QtCore.SIGNAL("documentChangeFinished()"))

    def selected_shelve_changed(self):
        self._change_current_shelve()

    @lazy_call(100, per_instance=True)
    @runs_in_loading_queue
    def _change_current_shelve(self):
        if sip.isdeleted(self):
            return
        items = self.shelve_view.selectedItems()
        if len(items) != 1:
            self.shelf_id = None
            self.unshelve_button.setEnabled(False)
            self.file_view.clear()
        else:
            self.shelf_id = items[0].shelf_id
            self.unshelve_button.setEnabled(True)
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
        self._need_refresh = refresh or self._need_refresh
        self._show_selected_diff()

    def unidiff_toggled(self, state):
        index = 1 if state else 0
        self.diffviews[index].rewind()
        if index == 0:
            self.find_toolbar.set_text_edits(self.diffviews[0].browsers)
        else:
            self.find_toolbar.set_text_edits([self.diffviews[1].view])
        self.stack.setCurrentIndex(index)

    def complete_toggled(self, state):
        self.complete = state
        self.show_selected_diff(refresh = True)

    def whitespace_toggled(self, state):
        self.ignore_whitespace = state
        self.show_selected_diff(refresh = True)

    def prompt_bool(self, prompt, warning=False):
        if warning:
            func = QtGui.QMessageBox.warning
        else:
            func = QtGui.QMessageBox.question
        ret = func(self, gettext('Shelve'), gettext(prompt), 
                    QtGui.QMessageBox.Ok | QtGui.QMessageBox.Cancel)
        return (ret == QtGui.QMessageBox.Ok)

    prompts = {
        "apply" :
            N_("Apply changes in shelf[%(id)d], and remove from the shelf"),
        "dry-run" :
            N_("Simulate to apply changes in shelf[%(id)d] without changing working tree"),
        "keep" :
            N_("Apply changes in shelf[%(id)d], but keep it shelved"),
        "delete-only" :
            N_("Remove shelf[%(id)d] without applying"),
        }

    def do_unshelve(self, action):
        if not self.shelf_id:
            return
        
        prompt = gettext(self.prompts[action]) % {"id":self.shelf_id}
        if action != "dry-run":
            if not self.prompt_bool(prompt, warning=(action=="delete-only")):
                return
        self.unshelve(self.shelf_id, prompt, action)
        self.refresh()

    def unshelve(self, id, desc, action):
        args = ["unshelve", str(id), '--' + action]
        window = SimpleSubProcessDialog(gettext("Shelve Manager"),
                                        desc=gettext(desc),
                                        args=args,
                                        dir=self.directory,
                                        immediate=True,
                                        parent=self.window())
        def finished(result):
            if result:
                self.emit(QtCore.SIGNAL("unshelved(int, QString*)"), 
                          self.shelf_id, action)

        self.connect(window, QtCore.SIGNAL("subprocessFinished(bool)"), finished)

        window.exec_()
        self.refresh()

    def encoding_changed(self, encoding):
        self.show_selected_diff(refresh = True)
        
    def eventFilter(self, object, event):
        if event.type() == QtCore.QEvent.FocusIn:
            if object in self.diffviews[0].browsers:
                self.find_toolbar.set_text_edit(object)
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


