# -*- coding: utf-8 -*-
#
# QBzr - Qt frontend to Bazaar commands
# Copyright (C) 2006 Lukáš Lalinský <lalinsky@gmail.com>
# Copyright (C) 2005 Dan Loda <danloda@gmail.com>
# Copyright (C) 2009 Gary van der Merwe <garyvdm@gmail.com>
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

from bzrlib.revision import CURRENT_REVISION
from bzrlib.errors import (
        NoSuchRevision, 
        NoSuchRevisionInTree,
        PathsNotVersionedError)
from bzrlib.plugins.qbzr.lib.i18n import gettext
from bzrlib.plugins.qbzr.lib.util import (
    BTN_CLOSE, BTN_REFRESH,
    QBzrWindow,
    ToolBarThrobberWidget,
    get_apparent_author_name,
    get_set_encoding,
    runs_in_loading_queue,
    get_icon,
    FindToolbar,
    get_monospace_font,
    StandardButton,
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
from bzrlib.revisiontree import RevisionTree
from bzrlib.plugins.qbzr.lib.encoding_selector import EncodingMenuSelector
from bzrlib.plugins.qbzr.lib.diffwindow import DiffItem
from bzrlib.patiencediff import PatienceSequenceMatcher as SequenceMatcher
from bzrlib.shelf import Unshelver
''')

class ShelveListWindow(QBzrWindow):

    def __init__(self, file_list = None, complete = False, encoding = None, parent = None, ui_mode=True):
        QBzrWindow.__init__(self,
                            [gettext("Shelve List")],
                            parent, ui_mode=ui_mode)
        self.restoreSize("shelvelist", (780, 680))

        self.file_list = file_list
        self.encoding = encoding
        self.directory = '.'
        self.throbber = ToolBarThrobberWidget(self)

        self.current_diffs = []
        self.complete = False

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

        vsplitter = QtGui.QSplitter(QtCore.Qt.Horizontal)
        vsplitter.addWidget(self.file_view)
        vsplitter.addWidget(self.stack)

        splitter = QtGui.QSplitter(QtCore.Qt.Vertical)
        splitter.addWidget(self.shelve_view)
        splitter.addWidget(vsplitter)
        splitter.setStretchFactor(0, 1)
        splitter.setStretchFactor(1, 3)

        vbox = QtGui.QVBoxLayout(self.centralwidget)
        vbox.addWidget(splitter)

        # build toolbar
        toolbar = self.addToolBar(gettext("Shelve"))
        toolbar.setMovable (False)
        toolbar.setToolButtonStyle(QtCore.Qt.ToolButtonTextBesideIcon)
        
        shelve_button = QtGui.QAction(get_icon("shelve"), gettext("Shelve"), self)
        shelve_button.setShortcuts(QtGui.QKeySequence.New)
        toolbar.addAction(shelve_button)

        button = QtGui.QAction(get_icon("unshelve"), gettext("Unshelve"), self)
        button.setEnabled(False)
        toolbar.addAction(button)
        self.unshelve_button = button

        button = QtGui.QAction(get_icon("delete"), gettext("Delete"), self)
        button.setShortcuts(QtGui.QKeySequence.Delete)
        button.setEnabled(False)
        toolbar.addAction(button)
        self.delete_button = button

        toolbar.addSeparator()
        
        show_view_menu = QtGui.QAction(get_icon("document-properties"), gettext("&View Options"), self)
        view_menu = QtGui.QMenu(gettext('View Options'), self)
        show_view_menu.setMenu(view_menu)

        self.encoding_selector = EncodingMenuSelector(self.encoding,
            gettext("Encoding"),
            self.encoding_changed)
        
        unidiff_menu = QtGui.QAction(get_icon("unidiff", size=16), gettext("Unified diff"), self)
        unidiff_menu.setCheckable(True)
        unidiff_menu.setChecked(False)

        complete_menu = QtGui.QAction(get_icon("complete", size=16), gettext("Complete"), self)
        complete_menu.setCheckable(True)
        complete_menu.setChecked(False)
        
        view_menu.addMenu(self.encoding_selector)
        view_menu.addAction(unidiff_menu)
        view_menu.addAction(complete_menu)

        toolbar.addAction(show_view_menu)
        
        spacer = QtGui.QWidget()
        spacer.setSizePolicy(QtGui.QSizePolicy.Expanding, QtGui.QSizePolicy.Expanding)
        toolbar.addWidget(spacer) 
        toolbar.addWidget(self.throbber)

        # build buttonbox
        buttonbox = self.create_button_box(BTN_CLOSE)
        refresh = StandardButton(BTN_REFRESH)
        buttonbox.addButton(refresh, QtGui.QDialogButtonBox.ActionRole)
        vbox.addWidget(buttonbox)

        # set signals
        self.connect(refresh, QtCore.SIGNAL("clicked()"),
                     self.refresh_clicked)
        self.connect(self.shelve_view, QtCore.SIGNAL("itemSelectionChanged()"),
                self.selected_shelve_changed)
        self.connect(self.file_view, QtCore.SIGNAL("itemSelectionChanged()"),
                self.selected_files_changed)
        self.connect(complete_menu, QtCore.SIGNAL("toggled(bool)"),
                self.complete_toggled)
        self.connect(unidiff_menu, QtCore.SIGNAL("toggled(bool)"),
                self.unidiff_toggled)


    def show(self):
        QBzrWindow.show(self)
        QtCore.QTimer.singleShot(0, self.initial_load)

    @runs_in_loading_queue
    @ui_current_widget
    @reports_exception()
    def initial_load(self):
        """Called to perform the initial load of the form.  Enables a
        throbber window, then loads the branches etc if they weren't specified
        in our constructor.
        """
        self.throbber.show()
        self.shelve_view.clear()
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
                item.setIcon(0, get_icon("file", 16))
                item.shelf_id = shelf_id
                self.shelve_view.addTopLevelItem(item)
            self.tree = tree
            self.manager = manager

        finally:
            tree.unlock()
            self.throbber.hide()

    def show_changes(self, shelf_id):
        shelf_file = self.manager.read_shelf(shelf_id)
        try:
            records = Unshelver.iter_records(shelf_file)
            revid = Unshelver.parse_metadata(records)['revision_id']
            try:
                base_tree = self.tree.revision_tree(revid)
            except NoSuchRevisionInTree:
                base_tree = self.tree.branch.repository.revision_tree(revid)
            tt = transform.TransformPreview(base_tree)
            tt.deserialize(records)

            self.load_diff(tt.get_preview_tree(), base_tree)

        finally:
            shelf_file.close()

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
        cur_len = len(self.current_diffs)
        if not refresh and cur_len <= len(diffs) and self.current_diffs == diffs[0:cur_len]:
            appends = diffs[cur_len:]
        else:
            for view in self.diffviews:
                view.clear()
            appends = diffs 
        self.current_diffs = diffs
        for d in appends:
            lines = d.lines
            groups = d.groups(self.complete)
            dates = d.dates[:]  # dates will be changed in append_diff
            ulines = d.encode((self.encoding_selector.encoding,
                               self.encoding_selector.encoding))
            data = [''.join(l) for l in ulines]
            for view in self.diffviews:
                view.append_diff(list(d.paths), d.file_id, d.kind, d.status, dates, 
                                 d.versioned, d.binary, ulines, groups, 
                                 data, d.properties_changed)

            
    def selected_shelve_changed(self):
        items = self.shelve_view.selectedItems()
        if len(items) != 1:
            self.unshelve_button.setEnabled(False)
            self.delete_button.setEnabled(False)
            self.file_view.clear()
        else:
            self.unshelve_button.setEnabled(True)
            self.delete_button.setEnabled(True)
            self.show_changes(items[0].shelf_id)

        
    def selected_files_changed(self):
        self.show_selected_diff()

    def show_selected_diff(self, refresh = False):
        diffs = [x.diffitem for x in self.file_view.selectedItems()]
        diffs.sort(key=lambda x:x.paths[0] or x.paths[1])
        self.show_diff(diffs, refresh)

    def unidiff_toggled(self, state):
        index = 1 if state else 0
        self.diffviews[index].rewind()
        self.stack.setCurrentIndex(index)

    def complete_toggled(self, state):
        self.complete = state
        self.show_selected_diff(refresh = True)

    def refresh_clicked(self):
        self.initial_load()
    

    def encoding_changed(self, encoding):
        self.show_selected_diff(refresh = True)
        
