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
from bzrlib.plugins.qbzr.lib.i18n import gettext, N_
from bzrlib.plugins.qbzr.lib.util import (
    BTN_OK, BTN_CLOSE, BTN_REFRESH,
    get_apparent_author_name,
    get_global_config,
    get_set_encoding,
    runs_in_loading_queue,
    get_icon,
    QBzrDialog,
    ToolBarThrobberWidget,
    get_monospace_font,
    StandardButton,
    )
from bzrlib import errors
from bzrlib.plugins.qbzr.lib.uifactory import ui_current_widget
from bzrlib.plugins.qbzr.lib.trace import reports_exception
from bzrlib.plugins.qbzr.lib.logwidget import LogList
from bzrlib.patches import HunkLine, ContextLine, InsertLine, RemoveLine
from bzrlib.lazy_import import lazy_import
lazy_import(globals(), '''
from bzrlib import transform, textfile, patches
from bzrlib.workingtree import WorkingTree
from bzrlib.revisiontree import RevisionTree
from bzrlib.plugins.qbzr.lib.encoding_selector import EncodingMenuSelector
from bzrlib.plugins.qbzr.lib.commit import TextEdit
from bzrlib.plugins.qbzr.lib.spellcheck import SpellCheckHighlighter, SpellChecker
from bzrlib.patiencediff import PatienceSequenceMatcher as SequenceMatcher
from bzrlib.shelf import ShelfCreator
from bzrlib.shelf_ui import Shelver
''')

"""
TODO::
  Auto complete of commit message.
  Wordwrap
  Tab width
  Prev hunk / Next hunk
  Complete view
"""
class DummyDiffWriter(object):
    def __init__(self):
        pass
    def write(self, *args, **kwargs):
        pass

class ToolbarPanel(QtGui.QWidget):
    def __init__(self, parent = None):
        QtGui.QWidget.__init__(self, parent)
        vbox = QtGui.QVBoxLayout(self)
        vbox.setSpacing(0)

        toolbar = QtGui.QToolBar(self)
        toolbar.setMovable(False)
        toolbar.setIconSize(QtCore.QSize(16,16))
        toolbar.setStyleSheet('QToolBar { margin:1px; padding:0px; border:none; }')
        toolbar.setToolButtonStyle(QtCore.Qt.ToolButtonTextBesideIcon)

        vbox.addWidget(toolbar)
        self.vbox = vbox
        self.toolbar = toolbar

    def add_toolbar_button(self, text, icon_name=None, enabled=True, 
            checkable=False, checked=False, shortcut=None, onclick=None):
        button = self.create_button(text, icon_name=icon_name, enabled=enabled,
                        checkable=checkable, checked=checked, 
                        shortcut=shortcut, onclick=onclick)
        self.toolbar.addAction(button)
        return button

    def add_menu(self, text, menu, icon_name=None, enabled=True, shortcut=None):
        button = self.create_button(text, icon_name=icon_name, enabled=enabled, 
                                    shortcut=shortcut, 
                                    onclick=lambda:menu.exec_(QtGui.QCursor.pos()))
        button.setMenu(menu)
        self.toolbar.addAction(button)
        return button

    def create_button(self, text, icon_name=None, enabled=True, 
            checkable=False, checked=False, shortcut=None, onclick=None):
        if icon_name:
            button = QtGui.QAction(get_icon(icon_name, size=16), gettext(text), self)
        else:
            button = QtGui.QAction(gettext(text), self)
        if checkable:
            button.setCheckable(True)
            button.setChecked(checked)
            signal = "toggled(bool)"
        else:
            signal = "triggered()"
        if not enabled:
            button.setEnabled(False)
        if shortcut:
            button.setShortcuts(shortcut)
        if onclick:
            self.connect(button, QtCore.SIGNAL(signal), onclick)
        return button

    def add_separator(self):
        self.toolbar.addSeparator()

    def add_widget(self, widget):
        self.vbox.addWidget(widget)

class Change(object):
    def __init__(self, change, shelver, trees):
        status = change[0]
        file_id = change[1]
        if status == 'delete file':
            self.disp_text = trees[0].id2path(file_id)
        elif status == 'rename':
            self.disp_text = u'%s => %s' % (trees[0].id2path(file_id), trees[1].id2path(file_id))
        else:
            self.disp_text = trees[1].id2path(file_id)
        if status == 'modify text':
            try:
                target_lines = trees[0].get_file_lines(file_id)
                textfile.check_text_lines(target_lines)
                work_lines = trees[1].get_file_lines(file_id)
                textfile.check_text_lines(work_lines)
                
                self.target_lines = [None, target_lines, None]
                self.work_lines = [None, work_lines, None]

                parsed = shelver.get_parsed_patch(file_id, False)
                for hunk in parsed.hunks:
                    hunk.selected = False
                self.parsed_patch = parsed
                self.hunk_texts = [None, None, None]
            except errors.BinaryFile:
                status = 'modify binary'

        self.data = change
        self.file_id = file_id
        self.status = status

    def encode_hunk_texts(self, encoding):
        if self.hunk_texts[0] == encoding:
            return self.hunk_texts[2]
        patch = self.parsed_patch
        try:
            texts = [[str(l).decode(encoding) for l in hunk.lines]
                     for hunk in patch.hunks]
        except UnicodeError:
            if self.hunk_texts[1] is None:
                texts = [[l for l in hunk.lines] for hunk in patch.hunks]
                self.hunk_texts[1] = texts
            else:
                texts = self.hunk_texts[1]
        self.hunk_texts[0] = encoding
        self.hunk_texts[2] = texts

        return texts

    def encode(self, lines, encoding):
        if lines[0] == encoding:
            return lines[2]
        try:
            encoded_lines = [l.decode(encoding) for l in lines[1]]
        except UnicodeError:
            encoded_lines = lines[1]
        lines[2] = encoded_lines
        return encoded_lines

    def encode_work_lines(self, encoding):
        return self.encode(self.work_lines, encoding)

    def encode_target_lines(self, encoding):
        return self.encode(self.target_lines, encoding)


class SelectAllCheckBox(QtGui.QCheckBox):
    def __init__(self, view, parent):
        QtGui.QCheckBox.__init__(self, 
                                 gettext("Select / deselect all"), 
                                 parent)
        self.changed_by_code = False
        self.view = view
        self.connect(self, QtCore.SIGNAL("clicked(bool)"),
                self.clicked)
        self.connect(self.view, QtCore.SIGNAL("itemChanged(QTreeWidgetItem *, int)"),
                self.view_itemchecked)

    def view_itemchecked(self, item, column):
        if self.changed_by_code:
            return
        if column != 0:
            return
        view = self.view
        state = None
        for i in range(view.topLevelItemCount()):
            item = view.topLevelItem(i)
            if state is None:
                state = item.checkState(0)
                if state == QtCore.Qt.PartiallyChecked:
                    break
            elif state != item.checkState(0):
                state = QtCore.Qt.PartiallyChecked
                break
        try:
            self.changed_by_code = True
            self.setCheckState(state)
        finally:
            self.changed_by_code = False

    def clicked(self, state):
        if self.changed_by_code:
            return
        if state:
            state = QtCore.Qt.Checked
        else:
            state = QtCore.Qt.Unchecked

        view = self.view
        self.changed_by_code = True
        try:
            for i in range(view.topLevelItemCount()):
                item = view.topLevelItem(i)
                if item.checkState(0) != state:
                    item.setCheckState(0, state)
        finally:
            self.changed_by_code = False

class ShelveWindow(QBzrDialog):

    def __init__(self, file_list=None, encoding=None, dialog=True, parent=None, ui_mode=True):
        QBzrDialog.__init__(self,
                            gettext("Shelve"),
                            parent, ui_mode=ui_mode)
        self.restoreSize("shelve", (780, 680))
        self._cleanup_funcs = []

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

        selectall_checkbox = SelectAllCheckBox(
                                view=self.file_view, parent=fileview_panel)
        vbox.addWidget(selectall_checkbox)

        hunk_panel = ToolbarPanel(self)
        hsplitter.addWidget(hunk_panel)

        hunk_panel.add_toolbar_button(N_("Complete"), icon_name="complete", 
                                  onclick=self.complete_toggled, checkable=True)
        hunk_panel.add_separator()
        hunk_panel.add_toolbar_button(N_("Previous"), icon_name="go-up")
        hunk_panel.add_toolbar_button(N_("Next"), icon_name="go-down")
        hunk_panel.add_separator()
        
        self.encoding_selector = EncodingMenuSelector(self.encoding,
            gettext("Encoding"), self.encoding_changed)
        hunk_panel.add_menu(N_("Encoding"), self.encoding_selector, icon_name="format-text-bold")

        self.hunk_view = HunkView()
        hunk_panel.add_widget(self.hunk_view)

        splitter.setStretchFactor(0, 1)
        splitter.setStretchFactor(1, 6)

        layout = QtGui.QVBoxLayout(self)
        layout.addWidget(self.throbber)
        layout.addWidget(splitter)

        # build buttonbox
        buttonbox = self.create_button_box(BTN_OK, BTN_CLOSE)
        layout.addWidget(buttonbox)

        self.connect(self, QtCore.SIGNAL("finished(int)"),
                self.finished)

        self.connect(self.file_view, QtCore.SIGNAL("itemSelectionChanged()"),
                self.selected_file_changed)

        self.connect(self.file_view, QtCore.SIGNAL("itemChanged(QTreeWidgetItem *, int)"),
                self.file_checked)

        self.connect(self.hunk_view, QtCore.SIGNAL("selectionChanged()"),
                self.selected_hunk_changed)

    def show(self):
        QtCore.QTimer.singleShot(1, self.load)
        QBzrDialog.show(self)

    def exec_(self):
        QtCore.QTimer.singleShot(1, self.load)
        return QBzrDialog.exec_(self)

        
    @runs_in_loading_queue
    @ui_current_widget
    @reports_exception()
    def load(self):
        cleanup = []
        try:
            self.throbber.show()
            cleanup.append(self.throbber.hide)
            self.shelver = Shelver.from_args(DummyDiffWriter(), self.revision,
                    False, self.file_list, None, directory = self.directory)
            self.add_cleanup(self.shelver.finalize)
            
            self.creator = ShelfCreator(
                    self.shelver.work_tree, self.shelver.target_tree, self.file_list)
            self.add_cleanup(self.creator.finalize)

            trees = (self.shelver.target_tree, self.shelver.work_tree)
            for tree in trees:
                cleanup.append(tree.lock_read().unlock)
                
            for change in self.creator.iter_shelvable():
                item = self._create_item(change, self.shelver, trees)
                self.file_view.addTopLevelItem(item)
            
        finally:
            for func in cleanup:
                func()

    def _create_item(self, change, shelver, trees):
        ch = Change(change, shelver, trees)
        item = QtGui.QTreeWidgetItem()

        item.setIcon(0, get_icon("file", 16))
        item.change = ch
        item.setText(0, ch.disp_text)
        item.setText(1, ch.status)
        if ch.status == 'modify text':
            item.setText(2, u'0/%d' % len(ch.parsed_patch.hunks))
        item.setCheckState(0, QtCore.Qt.Unchecked)
        return item

    def selected_file_changed(self):
        items = self.file_view.selectedItems()
        if len(items) != 1 or items[0].change.status != 'modify text':
            self.hunk_view.clear()
        else:
            item = items[0]
            encoding = self.encoding_selector.encoding
            self.hunk_view.set_parsed_patch(item.change, encoding)

    def selected_hunk_changed(self):
        for item in self.file_view.selectedItems():
            change = item.change
            if change.status != 'modify text':
                continue
            hunks = change.parsed_patch.hunks
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

        if item.change.status == 'modify text':
            hunk_num = len(item.change.parsed_patch.hunks)
            for hunk in item.change.parsed_patch.hunks:
                hunk.selected = selected
            self.hunk_view.update()
            item.setText(2, u'%d/%d' % (hunk_num if selected else 0, hunk_num))

    def encoding_changed(self, encoding):
        # refresh hunk view
        self.selected_file_changed()

    def complete_toggled(self, checked):
        self.hunk_view.set_complete(checked)
    
    def do_accept(self):
        shelved = False
        for i in range(0, self.file_view.topLevelItemCount()):
            item = self.file_view.topLevelItem(i)
            if item.checkState(0) == QtCore.Qt.Unchecked:
                continue
            shelved = True
            change = item.change
            if change.status == 'modify text':
                self.handle_modify_text(change)
            elif change.status == 'modify binary':
                self.creator.shelve_content_change(change.data[1])
            else:
                self.creator.shelve_change(change.data)
        if shelved:
            manager = self.shelver.work_tree.get_shelf_manager()
            message = unicode(self.message.toPlainText()).strip()
            shelf_id = manager.shelve_changes(self.creator, message)
            QBzrDialog.do_accept(self)
        else:
            QBzrDialog.do_reject(self)

    def handle_modify_text(self, change):
        final_hunks = []
        offset = 0
        change_count = 0
        for hunk in change.parsed_patch.hunks:
            if hunk.selected:
                offset -= (hunk.mod_range - hunk.orig_range)
                change_count += 1
            else:
                hunk.mod_pos += offset
                final_hunks.append(hunk)

        if change_count == 0:
            return
        patched = patches.iter_patched_from_hunks(change.target_lines, final_hunks)
        self.creator.shelve_lines(change.file_id, list(patched))

    def add_cleanup(self, func):
        self._cleanup_funcs.append(func)
        
    def cleanup(self):
        while len(self._cleanup_funcs) > 0:
            try:
                self._cleanup_funcs.pop()()
            except:
                pass

    def finished(self, ret):
        self.cleanup()
        self.saveSize()

class HunkView(QtGui.QWidget):
    def __init__(self, parent=None):
        QtGui.QWidget.__init__(self, parent)
        layout = QtGui.QHBoxLayout(self)
        layout.setSpacing(0)
        layout.setMargin(0)
        self.browser = HunkTextBrowser(self)
        self.selector = HunkSelector(self.browser, self)
        layout.addWidget(self.selector)
        layout.addWidget(self.browser)

        self.change = None
        self.encoding = None

    def set_complete(self, value):
        self.browser.complete = value
        if self.change is not None:
            self.set_parsed_patch(self.change, self.encoding)

    def rewind(self):
        self.browser.rewind()

    def set_parsed_patch(self, change, encoding):
        self.change = change
        self.encoding = encoding
        self.browser.set_parsed_patch(change, encoding)
        self.update()

    def update(self):
        self.selector.update()
        self.browser.update()

    def clear(self):
        self.browser.clear()

class HunkSelector(QtGui.QFrame):
    def __init__(self, browser, parent):
        QtGui.QFrame.__init__(self, parent)
        self.browser = browser
        self.setFixedWidth(25)
        self.setStyleSheet("border:1px solid lightgray; background-color:white;")
        self.connect(browser.verticalScrollBar(), QtCore.SIGNAL("valueChanged(int)"), self.scrolled)
        self.frame_width = QtGui.QApplication.style().pixelMetric(QtGui.QStyle.PM_DefaultFrameWidth)

    def scrolled(self, value):
        self.update()

    def paintEvent(self, event):
        QtGui.QFrame.paintEvent(self, event) 
        browser = self.browser
        if not browser.hunk_list:
            return
        scroll_y = browser.verticalScrollBar().value() - self.frame_width
        painter = QtGui.QPainter(self)
        rect = event.rect()
        top, bottom = rect.top(), rect.bottom()
        painter.setClipRect(rect)
        browser.paint_background(self.width(), rect.top(), rect.bottom(), painter, scroll_y)

        # draw checkbox
        painter.setRenderHint(QtGui.QPainter.Antialiasing, True)
        painter.setPen(browser.bold_pen)
        for hunk, y1, y2 in browser.hunk_list:
            y1 -= scroll_y
            y1 += 4
            if bottom < y1 or y1 + 13 < top:
                continue

            painter.fillRect(6, y1, 13, 13, QtCore.Qt.white)

            painter.drawRect(6, y1, 13, 13)
            if hunk.selected:
                painter.drawLine(9, y1 + 7, 12, y1 + 10)
                painter.drawLine(16, y1 + 3, 12, y1 + 10)

        del painter

    def mousePressEvent(self, event):
        if event.button() == QtCore.Qt.LeftButton:
            x, y = event.x(), event.y()
            scroll_y = self.browser.verticalScrollBar().value()
            for hunk, top, bottom in self.browser.hunk_list:
                top -= scroll_y
                if top <= y <= bottom:
                    hunk.selected = not hunk.selected
                    self.repaint(6, top + 3, 13, 13)
                    self.parent().emit(QtCore.SIGNAL("selectionChanged()"))
                    return
        QtGui.QFrame.mousePressEvent(self, event)

class HunkTextBrowser(QtGui.QTextBrowser):

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
        
        self.monospacedInactiveFormat = QtGui.QTextCharFormat(self.monospacedFormat)
        self.monospacedInactiveFormat.setForeground(QtGui.QColor(128, 128, 128))
    
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
        
        from bzrlib.plugins.qbzr.lib.diffview import colors
        self.header_color = colors['blank'][0]

        self.complete = False 

    def rewind(self):
        if not self.rewinded:
            self.rewinded = True
            self.scrollToAnchor("top")

    def set_parsed_patch(self, change, encoding):
        self.clear()
        cursor = self.cursor

        patch = change.parsed_patch
        texts = change.encode_hunk_texts(encoding)
        if self.complete:
            work_lines = change.encode_work_lines(encoding)

        def print_hunk(hunk, hunk_texts):
            for line, text in zip(hunk.lines, hunk_texts):
                if isinstance(line, InsertLine):
                    fmt = self.monospacedInsertFormat
                elif isinstance(line, RemoveLine):
                    fmt = self.monospacedDeleteFormat
                else:
                    fmt = self.monospacedFormat
                cursor.insertText(text, fmt)
        
        start = 0
        for hunk, hunk_texts in zip(patch.hunks, texts):
            # NOTE: hunk.mod_pos is 1 based value, not 0 based.
            if self.complete:
                for i in range(start, hunk.mod_pos - 1):
                    cursor.insertText(' ' + work_lines[i], self.monospacedInactiveFormat)
                start = hunk.mod_pos + hunk.mod_range - 1
                cursor.beginEditBlock()
                y1 = cursor.block().layout().position().y()
                print_hunk(hunk, hunk_texts)
                cursor.endEditBlock()
                y2 = cursor.block().layout().position().y()

            else:
                cursor.beginEditBlock()
                y1 = cursor.block().layout().position().y()
                cursor.insertText(str(hunk.get_header()), self.monospacedHunkFormat)
                print_hunk(hunk, hunk_texts)
                cursor.insertText("\n", self.monospacedFormat)
                cursor.endEditBlock()
                y2 = cursor.block().layout().position().y()

            self.hunk_list.append((hunk, y1, y2))

        self.update()

    def update(self):
        QtGui.QTextBrowser.update(self)
        self.viewport().update()

    def clear(self):
        QtGui.QTextBrowser.clear(self)
        del(self.hunk_list[:])

    def paintEvent(self, event):
        if not self.hunk_list:
            QtGui.QTextBrowser.paintEvent(self, event) 
            return
        scroll_y = self.verticalScrollBar().value()

        painter = QtGui.QPainter(self.viewport())
        rect = event.rect()
        painter.setClipRect(rect)

        self.paint_background(self.width(), rect.top(), rect.bottom(), painter, scroll_y)

        QtGui.QTextBrowser.paintEvent(self, event) 
        del painter

    def paint_background(self, width, top, bottom, painter, offset):
        painter.setPen(self.normal_pen)
        for hunk, y1, y2 in self.hunk_list:
            y1 -= offset
            y2 -= offset
            if self.complete:
                if bottom < y1 or y2 < top:
                    continue
                painter.drawLine(0, y1, width, y1)
                painter.drawLine(0, y2, width, y2)
            else:
                if bottom < y1 or y1 + 20 < top:
                    continue
                painter.fillRect(0, y1, width, 20, self.header_color)
                painter.drawLine(0, y1, width, y1)

