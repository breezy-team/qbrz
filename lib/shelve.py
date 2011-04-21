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
        PathsNotVersionedError,
        BinaryFile)
from bzrlib.plugins.qbzr.lib.i18n import gettext
from bzrlib.plugins.qbzr.lib.util import (
    BTN_OK, BTN_CLOSE, BTN_REFRESH,
    get_apparent_author_name,
    get_global_config,
    get_set_encoding,
    runs_in_loading_queue,
    get_icon,
    QBzrWindow,
    ToolBarThrobberWidget,
    get_monospace_font,
    StandardButton,
    )
from bzrlib.plugins.qbzr.lib.uifactory import ui_current_widget
from bzrlib.plugins.qbzr.lib.trace import reports_exception
from bzrlib.plugins.qbzr.lib.logwidget import LogList
from bzrlib.patches import HunkLine, ContextLine, InsertLine, RemoveLine
from bzrlib.lazy_import import lazy_import
lazy_import(globals(), '''
from bzrlib import transform, textfile
from bzrlib.workingtree import WorkingTree
from bzrlib.revisiontree import RevisionTree
from bzrlib.plugins.qbzr.lib.encoding_selector import EncodingMenuSelector
from bzrlib.plugins.qbzr.lib.commit import TextEdit
from bzrlib.plugins.qbzr.lib.spellcheck import SpellCheckHighlighter, SpellChecker
from bzrlib.patiencediff import PatienceSequenceMatcher as SequenceMatcher
from bzrlib.shelf import ShelfCreator
from bzrlib.shelf_ui import Shelver
''')

class DummyDiffWriter(object):
    def __init__(self):
        pass
    def write(self, *args, **kwargs):
        pass

class ShelveWindow(QBzrWindow):

    def __init__(self, file_list=None, encoding=None, dialog=True, parent=None, ui_mode=True):
        QBzrWindow.__init__(self,
                            [gettext("Shelve")],
                            parent, ui_mode=ui_mode)
        self.restoreSize("shelvelist", (780, 680))

        self.revision = None
        self.file_list = file_list
        self.message = None
        self.directory = None

        self.encoding = encoding

        self.throbber = ToolBarThrobberWidget(self)

        splitter = QtGui.QSplitter(QtCore.Qt.Vertical, self)
        message_groupbox = QtGui.QGroupBox(gettext("Message"), splitter)
        message_layout = QtGui.QVBoxLayout(message_groupbox)
        splitter.addWidget(message_groupbox)

        language = get_global_config().get_user_option('spellcheck_language') or 'en'
        spell_checker = SpellChecker(language)
        
        self.message = TextEdit(spell_checker, message_groupbox, main_window=self)
        self.message.setToolTip(gettext("Enter the commit message"))
        self.completer = QtGui.QCompleter()
        self.completer_model = QtGui.QStringListModel(self.completer)
        self.completer.setModel(self.completer_model)
        self.message.setCompleter(self.completer)
        self.message.setAcceptRichText(False)
        SpellCheckHighlighter(self.message.document(), spell_checker)

        message_layout.addWidget(self.message)

        hsplitter = QtGui.QSplitter(QtCore.Qt.Horizontal, splitter)
        splitter.addWidget(hsplitter)

        fileview_panel = QtGui.QWidget()
        hsplitter.addWidget(fileview_panel)
        vbox = QtGui.QVBoxLayout(fileview_panel)
        
        self.file_view = QtGui.QTreeWidget(self)
        self.file_view.setHeaderLabels(
                [gettext("File Name"), gettext("Status"), gettext("Hunks")])
        header = self.file_view.header()
        header.setStretchLastSection(False)
        header.setResizeMode(0, QtGui.QHeaderView.Stretch)
        header.setResizeMode(1, QtGui.QHeaderView.ResizeToContents)
        header.setResizeMode(2, QtGui.QHeaderView.ResizeToContents)

        vbox.addWidget(self.file_view)

        selectall_checkbox = QtGui.QCheckBox(gettext("Select / deselect all"), fileview_panel)
        vbox.addWidget(selectall_checkbox)

        hunk_panel = QtGui.QWidget(self)
        hsplitter.addWidget(hunk_panel)
        vbox = QtGui.QVBoxLayout(hunk_panel)

        toolbar = QtGui.QToolBar(self)
        toolbar.setMovable(False)
        toolbar.setToolButtonStyle(QtCore.Qt.ToolButtonTextBesideIcon)
        self.encoding_selector = EncodingMenuSelector(self.encoding,
            gettext("Encoding"), self.encoding_changed)
        show_view_menu = QtGui.QAction(get_icon("document-properties"), gettext("&View Options"), self)
        view_menu = QtGui.QMenu(gettext('View Options'), self)
        show_view_menu.setMenu(view_menu)
        view_menu.addMenu(self.encoding_selector)
        toolbar.addAction(show_view_menu)

        self.hunk_view = HunkView()

        vbox.addWidget(toolbar)
        vbox.addWidget(self.hunk_view)

        splitter.setStretchFactor(0, 1)
        splitter.setStretchFactor(1, 4)

        layout = QtGui.QVBoxLayout(self.centralwidget)
        layout.addWidget(self.throbber)
        layout.addWidget(splitter)

        # build buttonbox
        buttonbox = self.create_button_box(BTN_OK, BTN_CLOSE)
        layout.addWidget(buttonbox)

        self.connect(self.file_view, QtCore.SIGNAL("itemSelectionChanged()"),
                self.selected_file_changed)

        self.connect(self.file_view, QtCore.SIGNAL("itemChanged(QTreeWidgetItem *, int)"),
                self.file_checked)

        self.connect(self.hunk_view, QtCore.SIGNAL("selectionChanged()"),
                self.selected_hunk_changed)

    def show(self):
        QBzrWindow.show(self)
        QtCore.QTimer.singleShot(1, self.load)
        
    @runs_in_loading_queue
    @ui_current_widget
    @reports_exception()
    def load(self):
        cleanup = []
        try:
            self.throbber.show()
            cleanup.append(self.throbber.hide)
            shelver = Shelver.from_args(DummyDiffWriter(), self.revision,
                    False, self.file_list, None, directory = self.directory)
            cleanup.append(shelver.finalize)
            creator = ShelfCreator(
                    shelver.work_tree, shelver.target_tree, self.file_list)
            cleanup.append(creator.finalize)
            trees = (shelver.target_tree, shelver.work_tree)
            for tree in trees:
                cleanup.append(tree.lock_read().unlock)
                
            for change in creator.iter_shelvable():
                item = self._create_item(change, shelver, trees)
                self.file_view.addTopLevelItem(item)
            
        finally:
            for func in cleanup:
                func()

    def update(self):
        QtGui.QTextBrowser.update(self)
        self.viewport().update()

    def _create_item(self, change, shelver, trees):
        status = change[0]
        file_id = change[1]
        if status == 'delete file':
            path = trees[0].id2path(file_id)
        elif status == 'rename':
            path = u'%s => %s' % (trees[0].id2path(file_id), trees[1].id2path(file_id))
        else:
            path = trees[1].id2path(file_id)
        item = QtGui.QTreeWidgetItem()
        if status == 'modify text':
            try:
                for tree in trees:
                    lines = tree.get_file_lines(file_id)
                    textfile.check_text_lines(lines)

                parsed = shelver.get_parsed_patch(file_id, False)
                item.setText(2, u'0/%d' % len(parsed.hunks))
                for hunk in parsed.hunks:
                    hunk.selected = False
                item.parsed_patch = parsed
            except errors.BinaryFile:
                status = 'modify binary'

        item.setIcon(0, get_icon("file", 16))
        item.change = change
        item.file_id = file_id
        item.status = status
        item.setText(0, path)
        item.setText(1, status)
        item.setCheckState(0, QtCore.Qt.Unchecked)
        return item

    def selected_file_changed(self):
        items = self.file_view.selectedItems()
        if len(items) != 1 or items[0].status != 'modify text':
            self.hunk_view.clear()
        else:
            item = items[0]
            self.hunk_view.set_parsed_patch(item.parsed_patch, None)

    def selected_hunk_changed(self):
        for item in self.file_view.selectedItems():
            if item.status != 'modify text':
                continue
            hunks = item.parsed_patch.hunks
            hunk_num = len(hunks)
            selected_hunk_num = 0
            for hunk in hunks:
                if hunk.selected:
                    selected_hunk_num += 1
            item.setText(2, "%d/%d" % (selected_hunk_num, hunk_num))
            if selected_hunk_num == 0:
                item.setCheckState(0, QtCore.Qt.Unchecked)
            elif selected_hunk_num == hunk_num:
                item.setCheckState(0, QtCore.Qt.Checked)
            else:
                item.setCheckState(0, QtCore.Qt.PartiallyChecked)

    def file_checked(self, item, column):
        if column != 0:
            return

        checked = item.checkState(0)
        if checked == QtCore.Qt.Checked:
            selected = True
        elif checked == QtCore.Qt.Unchecked:
            selected = False
        else:
            return

        if item.status == 'modify text':
            for hunk in item.parsed_patch.hunks:
                hunk.selected = selected
            self.hunk_view.update()

    def encoding_changed(self, encoding):
        pass

    def do_accept(self):
        pass


class HunkView(QtGui.QTextBrowser):

    def __init__(self, parent=None):
        # XXX: This code should be merged with QSimpleDiffView
        QtGui.QTextBrowser.__init__(self, parent)
        self.hunk_list = []
        self.doc = QtGui.QTextDocument(parent)
        self.doc.setUndoRedoEnabled(False)
        self.setDocument(self.doc)

        option = self.doc.defaultTextOption()
        option.setWrapMode(QtGui.QTextOption.NoWrap)
        self.doc.setDefaultTextOption(option)
        self.rewinded = False
        self.cursor = QtGui.QTextCursor(self.doc)
        format = QtGui.QTextCharFormat()
        format.setAnchorNames(["top"])
        self.cursor.insertText("", format)
        
        monospacedFont = get_monospace_font()
        self.monospacedFormat = QtGui.QTextCharFormat()
        self.monospacedFormat.setFont(monospacedFont)
        self.monospacedInsertFormat = QtGui.QTextCharFormat(self.monospacedFormat)
        self.monospacedInsertFormat.setForeground(QtGui.QColor(0, 136, 11))
        self.monospacedDeleteFormat = QtGui.QTextCharFormat(self.monospacedFormat)
        self.monospacedDeleteFormat.setForeground(QtGui.QColor(204, 0, 0))
    
        titleFont = QtGui.QFont(monospacedFont)
        titleFont.setPointSize(titleFont.pointSize() * 140 / 100)
        titleFont.setBold(True)
        titleFont.setItalic(True)
    
        self.monospacedHunkFormat = QtGui.QTextCharFormat()
        self.monospacedHunkFormat.setFont(titleFont)
        self.monospacedHunkFormat.setForeground(QtCore.Qt.black)

        self.normal_pen = QtGui.QPen(QtCore.Qt.black)
        self.bold_pen = QtGui.QPen(QtCore.Qt.black)
        self.bold_pen.setWidth(2)

    def rewind(self):
        if not self.rewinded:
            self.rewinded = True
            self.scrollToAnchor("top")

    def set_parsed_patch(self, patch, encoding):
        self.clear()
        del(self.hunk_list[:])
        cursor = self.cursor

        for hunk in patch.hunks:
            cursor.beginEditBlock()
            y = cursor.block().layout().position().y()
            self.hunk_list.append((hunk, y))
            cursor.insertText('  ' + str(hunk.get_header()),
                    self.monospacedHunkFormat)
            cursor.insertText("\n")
            for line in hunk.lines:
                if isinstance(line, InsertLine):
                    fmt = self.monospacedInsertFormat
                elif isinstance(line, RemoveLine):
                    fmt = self.monospacedDeleteFormat
                else:
                    fmt = self.monospacedFormat
                cursor.insertText(str(line), fmt)
            cursor.insertText("\n", self.monospacedFormat)
            cursor.endEditBlock()

        self.update()

    def paintEvent(self, event):
        QtGui.QTextBrowser.paintEvent(self, event) 
        if not self.hunk_list:
            return
        scroll_x = self.horizontalScrollBar().value()
        scroll_y = self.verticalScrollBar().value()
        width = self.width()
        rect = event.rect()
        top, bottom = rect.top(), rect.bottom()

        painter = QtGui.QPainter(self.viewport())
        painter.setClipRect(rect)
        for hunk, y in self.hunk_list:
            y -= scroll_y
            if bottom < y or y + 21 < top:
                continue

            # draw checkbox
            painter.setPen(self.normal_pen)
            painter.fillRect(2 - scroll_x, y, 16, 16, QtCore.Qt.white)
            painter.drawRect(2 - scroll_x, y, 16, 16)

            painter.setPen(self.bold_pen)
            if hunk.selected:
                painter.drawLine(6 - scroll_x, y + 8, 10 - scroll_x, y + 12)
                painter.drawLine(14 - scroll_x, y + 4, 10 - scroll_x, y + 12)

            # draw bottom line
            painter.drawLine(0, y + 20, width, y + 20)

        del painter

    def mousePressEvent(self, event):
        if event.button() == QtCore.Qt.LeftButton:
            x, y = event.x(), event.y()
            scroll_x = self.horizontalScrollBar().value()
            scroll_y = self.verticalScrollBar().value()
            left = 2 - scroll_x
            for hunk, top in self.hunk_list:
                top -= scroll_y
                if left <= x <= left + 16 and top <= y <= top + 16:
                    hunk.selected = not hunk.selected
                    self.viewport().repaint(left, top, 16, 16)
                    self.emit(QtCore.SIGNAL("selectionChanged()"))
                    return
        QtGui.QTextBrowser.mousePressEvent(self, event)
        

