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

from bzrlib.plugins.qbzr.lib.i18n import gettext, ngettext, N_
from bzrlib.plugins.qbzr.lib.util import (
    get_global_config,
    get_set_encoding,
    runs_in_loading_queue,
    get_icon,
    ToolBarThrobberWidget,
    get_monospace_font,
    get_tab_width_pixels,
    get_set_tab_width_chars,
    get_qbzr_config,
    file_extension,
    )
from bzrlib.plugins.qbzr.lib.widgets.toolbars import (
    FindToolbar, ToolbarPanel, LayoutSelector
    )
from bzrlib.plugins.qbzr.lib.widgets.tab_width_selector import TabWidthMenuSelector
from bzrlib.plugins.qbzr.lib.widgets.texteditaccessory import (
    GuideBar, setup_guidebar_for_find
    )
from bzrlib.plugins.qbzr.lib.decorators import lazy_call
from bzrlib import errors
from bzrlib.plugins.qbzr.lib.uifactory import ui_current_widget
from bzrlib.plugins.qbzr.lib.trace import reports_exception
from bzrlib.patches import HunkLine, ContextLine, InsertLine, RemoveLine
from bzrlib.lazy_import import lazy_import
lazy_import(globals(), '''
from bzrlib import transform, textfile, patches
from bzrlib.workingtree import WorkingTree
from bzrlib.plugins.qbzr.lib.encoding_selector import EncodingMenuSelector
from bzrlib.plugins.qbzr.lib.commit import TextEdit
from bzrlib.plugins.qbzr.lib.spellcheck import SpellCheckHighlighter, SpellChecker
from bzrlib.plugins.qbzr.lib.autocomplete import get_wordlist_builder
from bzrlib.shelf import ShelfCreator
from bzrlib.shelf_ui import Shelver
from bzrlib.osutils import split_lines
from cStringIO import StringIO
import os
''')


"""
TODO::
  Wordwrap mode
  Side by side view
  External diff (ShelveListWindow)
  Select hunk by Find.
"""

# For i18n
change_status = (
        N_("delete file"), N_("rename"), N_("add file"), 
        N_("modify text"), N_("modify target"), N_("modify binary")
        )

MAX_AUTOCOMPLETE_FILES = 20
class WorkingTreeHasChanged(errors.BzrError):
    pass

class WorkingTreeHasPendingMarge(errors.BzrError):
    pass

class DummyDiffWriter(object):
    def __init__(self):
        pass
    def write(self, *args, **kwargs):
        pass

class Change(object):
    def __init__(self, change, shelver, trees):
        status = change[0]
        file_id = change[1]
        def get_kind(tree, id):
            try:
                return tree.kind(id)
            except errors.NoSuchFile:
                return 'file'
        if status == 'delete file':
            self.path = trees[0].id2path(file_id)
            self.kind = get_kind(trees[0], file_id)
            self.disp_text = self.path
        elif status == 'rename':
            self.path = [tree.id2path(file_id) for tree in trees] 
            self.disp_text = u'%s => %s' % (self.path[0], self.path[1])
            self.kind = get_kind(trees[1], file_id)
        else:
            self.path = trees[1].id2path(file_id)
            self.disp_text = self.path
            self.kind = get_kind(trees[1], file_id)
        if status == 'modify text':
            try:
                self.sha1 = trees[1].get_file_sha1(file_id)
                target_lines = trees[0].get_file_lines(file_id)
                textfile.check_text_lines(target_lines)
                work_lines = trees[1].get_file_lines(file_id)
                textfile.check_text_lines(work_lines)
                
                self._target_lines = [None, target_lines, None]
                self._work_lines = [None, work_lines, None]
                self._edited_lines = [None, None, None]

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
        self._words = None

    def is_same_change(self, other):
        # NOTE: I does not use __cmp__ because this method does not compare entire data.
        if self.data != other.data:
            return False
        if self.status in ('modify text', 'modify binary'):
            if self.sha1 != other.sha1:
                return False
        return True

    @property
    def target_lines(self):
        """Original file lines"""
        return self._target_lines[1]

    @property
    def work_lines(self):
        """Working file lines"""
        return self._work_lines[1]

    def get_edited_lines(self):
        return self._edited_lines[1]

    def set_edited_lines(self, lines):
        self._edited_lines = [None, lines, None]

    edited_lines = property(get_edited_lines, set_edited_lines)

    def encode_hunk_texts(self, encoding):
        """
        Return encoded hunk texts.
        hunk texts is nested list. Outer is per hunks, inner is per lines.
        """
        if self.hunk_texts[0] == encoding:
            return self.hunk_texts[2]
        patch = self.parsed_patch
        try:
            texts = [[str(l).decode(encoding) for l in hunk.lines]
                     for hunk in patch.hunks]
        except UnicodeError:
            if self.hunk_texts[1] is None:
                texts = [[str(l) for l in hunk.lines] for hunk in patch.hunks]
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
        """Return encoded working file lines. """
        return self.encode(self._work_lines, encoding)

    def encode_target_lines(self, encoding):
        """Return encoded original file lines."""
        return self.encode(self._target_lines, encoding)

    def encode_edited_lines(self, encoding):
        """Return encoded edited lines by editor."""
        if self._edited_lines[1] is None:
            return None
        return self.encode(self._edited_lines, encoding)
    
    def get_words(self):
        if self._words is not None:
            return self._words, False

        # Add path
        self._words = set() 
        if self.status == 'rename':
            for path in self.path:
                self._words.add(path)
                self._words.add(os.path.split(path)[-1])
        else:
            self._words.add(self.path)
            self._words.add(os.path.split(self.path)[-1])

        if self.status == 'modify text':
            ext = file_extension(self.path)
            builder = get_wordlist_builder(ext)
            if builder is not None:
                try:
                    self._words.update(builder.iter_words(StringIO("".join(self.work_lines))))
                    return self._words, True
                except EnvironmentError:
                    pass

        return self._words, False


class ShelveWidget(ToolbarPanel):

    def __init__(self, file_list=None, directory=None, complete=False, encoding=None, 
                splitters=None, parent=None, select_all=False, init_msg=None):
        ToolbarPanel.__init__(self, slender=False, icon_size=22, parent=parent)

        self.revision = None
        self.file_list = file_list
        self.directory = directory
        self.message = None

        self.initial_encoding = encoding
        self.select_all = select_all

        self.current_layout = -1
        self.load_settings()

        self.splitter = QtGui.QSplitter(QtCore.Qt.Vertical, self)
        pal = QtGui.QPalette()
        pal.setColor(QtGui.QPalette.Window, QtGui.QColor(0,0,0,0))
        self.splitter.setPalette(pal)

        self.splitter1 = QtGui.QSplitter(QtCore.Qt.Horizontal, self)
        self.splitter2 = QtGui.QSplitter(QtCore.Qt.Horizontal, self)
        self.splitter.addWidget(self.splitter1)
        self.splitter.addWidget(self.splitter2)
        
        message_groupbox = QtGui.QGroupBox(gettext("Message"), self)
        message_layout = QtGui.QVBoxLayout(message_groupbox)
        self.splitter1.addWidget(message_groupbox)

        language = get_global_config().get_user_option('spellcheck_language') or 'en'
        spell_checker = SpellChecker(language)
        
        self.message = TextEdit(spell_checker, message_groupbox, main_window=self)
        self.message.setToolTip(gettext("Enter the shelve message"))
        self.connect(self.message, QtCore.SIGNAL("messageEntered()"),
                     self.do_shelve)
        self.completer = QtGui.QCompleter()
        self.completer_model = QtGui.QStringListModel(self.completer)
        self.completer.setModel(self.completer_model)
        self.message.setCompleter(self.completer)
        self.message.setAcceptRichText(False)
        if init_msg is not None:
            self.message.setText(init_msg)
        SpellCheckHighlighter(self.message.document(), spell_checker)

        message_layout.addWidget(self.message)

        self.file_view = QtGui.QTreeWidget(self)
        self.file_view.setHeaderLabels(
                [gettext("File Name"), gettext("Status"), gettext("Hunks")])
        header = self.file_view.header()
        header.setStretchLastSection(False)
        header.setResizeMode(0, QtGui.QHeaderView.Stretch)
        header.setResizeMode(1, QtGui.QHeaderView.ResizeToContents)
        header.setResizeMode(2, QtGui.QHeaderView.ResizeToContents)

        self.splitter1.addWidget(self.file_view)

        hunk_panel = ToolbarPanel(parent=self)
        self.hunk_view = HunkView(complete=complete)

        self.splitter2.addWidget(hunk_panel)

        # Build hunk panel toolbar
        show_find = hunk_panel.add_toolbar_button(
                        N_("Find"), icon_name="edit-find", checkable=True,
                        shortcut=QtGui.QKeySequence.Find)
        hunk_panel.add_separator()

        view_menu = QtGui.QMenu(gettext('View Options'), self)
        view_menu.addAction(
                hunk_panel.create_button(N_("Complete"), icon_name="complete", 
                    onclick=self.hunk_view.set_complete,
                    checkable=True, checked=complete)
                )
        self.tabwidth_selector = \
                TabWidthMenuSelector(label_text=gettext("Tab width"),
                    onChanged=self.on_tabwidth_changed)
        view_menu.addMenu(self.tabwidth_selector)
                
        self.encoding_selector = EncodingMenuSelector(encoding,
                                    gettext("Encoding"), self.encoding_changed)
        self.encoding_selector.setIcon(get_icon("format-text-bold", 16))
        view_menu.addMenu(self.encoding_selector)
        hunk_panel.add_toolbar_menu(
                N_("&View Options"), view_menu, icon_name="document-properties",
                shortcut="Alt+V")

        hunk_panel.add_separator()
        hunk_panel.add_toolbar_button(N_("Previous hunk"), icon_name="go-up",
                          onclick=self.hunk_view.move_previous, shortcut="Alt+Up")
        hunk_panel.add_toolbar_button(N_("Next hunk"), icon_name="go-down",
                          onclick=self.hunk_view.move_next, shortcut="Alt+Down")

        self.editor_button = hunk_panel.add_toolbar_button(N_("Use editor"), 
                                icon_name="accessories-text-editor", enabled=False,
                                onclick=self.use_editor, shortcut="Ctrl+E")
        find_toolbar = FindToolbar(self, self.hunk_view.browser, show_find)
        hunk_panel.add_widget(find_toolbar)
        hunk_panel.add_widget(self.hunk_view)
        find_toolbar.hide()

        setup_guidebar_for_find(self.hunk_view.guidebar, find_toolbar, index=1)
        self.find_toolbar = find_toolbar

        layout = QtGui.QVBoxLayout()
        layout.setMargin(10)
        layout.addWidget(self.splitter)
        self.add_layout(layout)

        shelve_menu = QtGui.QMenu(gettext("Shelve"), self)
        shelve_menu.addAction(self.create_button(N_("Destroy"),
                                    onclick=lambda:self.do_shelve(destroy=True)))

        self.add_toolbar_button(N_('Shelve'), icon_name='shelve', 
                shortcut=QtGui.QKeySequence.Save, onclick=self.do_shelve,
                menu = shelve_menu)

        self.add_separator()

        self.add_toolbar_button(N_('Select all'), icon_name='select-all', 
                onclick=lambda:self.check_all(True))

        self.add_toolbar_button(N_('Unselect all'), icon_name='unselect-all', 
                onclick=lambda:self.check_all(False))

        layout_selector = \
                LayoutSelector(num=3, onchanged=self.set_layout, parent=self,
                                initial_no=self.current_layout)

        self.add_toolbar_menu(N_("&Layout"), layout_selector, 
                icon_name="internet-news-reader", shortcut="Alt+L")
        
        self.add_toolbar_button(N_('&Refresh'), icon_name='view-refresh', 
                shortcut="Ctrl+R", onclick=self.refresh)

        self.connect(self.file_view, QtCore.SIGNAL("itemSelectionChanged()"),
                self.selected_file_changed)

        self.connect(self.file_view, QtCore.SIGNAL("itemChanged(QTreeWidgetItem *, int)"),
                self.file_checked)

        self.connect(self.hunk_view, QtCore.SIGNAL("selectionChanged()"),
                self.selected_hunk_changed)

        self.set_layout()

        if splitters:
            splitters.add("shelve_splitter", self.splitter)
            splitters.add("shelve_splitter1", self.splitter1)
            splitters.add("shelve_splitter2", self.splitter2)
        for sp in (self.splitter, self.splitter1, self.splitter2):
            sp.setChildrenCollapsible(False)
            sp.setStretchFactor(0, 3)
            sp.setStretchFactor(1, 7)

        self.brushes = {
            'add file' : QtGui.QBrush(QtCore.Qt.blue),
            'delete file' : QtGui.QBrush(QtCore.Qt.red),
            'rename' : QtGui.QBrush(QtGui.QColor(160, 32, 240)), # purple
        }

        self.loaded = False

    def set_layout(self, type=None):
        if type:
            self.current_layout = type

        self.file_view.setParent(None)
        if self.current_layout == 1:
            self.splitter.setOrientation(QtCore.Qt.Vertical)
            self.splitter1.setOrientation(QtCore.Qt.Horizontal)
            self.splitter1.insertWidget(1, self.file_view)
        elif self.current_layout == 2:
            self.splitter.setOrientation(QtCore.Qt.Horizontal)
            self.splitter1.setOrientation(QtCore.Qt.Vertical)
            self.splitter1.insertWidget(1, self.file_view)
        else:
            self.splitter.setOrientation(QtCore.Qt.Vertical)
            self.splitter2.setOrientation(QtCore.Qt.Horizontal)
            self.splitter2.insertWidget(0, self.file_view)

        for sp in (self.splitter, self.splitter1, self.splitter2):
            if sp.count() != 2:
                continue
            size = sum(sp.sizes())
            if size > 0:
                size1 = int(size * 0.3)
                sp.setSizes((size1, size - size1))

    def _create_shelver_and_creator(self, destroy=False):
        shelver = Shelver.from_args(DummyDiffWriter(), None,
                    False, self.file_list, None, directory=self.directory,
                    destroy=destroy)
        try:
            creator = ShelfCreator(
                    shelver.work_tree, shelver.target_tree, shelver.file_list)
        except:
            shelver.finalize()
            raise

        return shelver, creator

    def on_tabwidth_changed(self, width):
        get_set_tab_width_chars(self.trees[1].branch, tab_width_chars=width)
        self._on_tabwidth_changed(width)

    def _on_tabwidth_changed(self, width):
        pixels = get_tab_width_pixels(tab_width_chars=width)
        self.hunk_view.set_tab_width(pixels)

    def refresh(self):
        cleanup = []
        try:
            old_rev = self.revision
            old_changes = self._get_change_dictionary()
            self.clear(clear_message = False)

            shelver, creator = self._create_shelver_and_creator()
            cleanup.append(shelver.finalize)
            cleanup.append(creator.finalize)

            file_list = shelver.file_list
            if file_list:
                nfiles = len(file_list)
                if nfiles > 2:
                    self.files_str = ngettext("%d file", "%d files", nfiles) % nfiles
                else:
                    self.files_str = ", ".join(file_list)

            self.trees = (shelver.target_tree, shelver.work_tree)
            branch = shelver.work_tree.branch       # current branch corresponding to working tree
            if self.initial_encoding is None:
                encoding = get_set_encoding(None, branch)
                self.initial_encoding = encoding            # save real encoding for the next time
                self.encoding_selector.encoding = encoding  # set encoding selector
            self.editor_available = (shelver.change_editor is not None)
            self.editor_button.setVisible(self.editor_available)
            tabwidth = get_set_tab_width_chars(branch)
            self.tabwidth_selector.setTabWidth(tabwidth)
            self._on_tabwidth_changed(tabwidth)
            self.revision = self.trees[0].get_revision_id()
            if self.revision != old_rev:
                old_changes = None
            for change in creator.iter_shelvable():
                item = self._create_item(change, shelver, self.trees, old_changes)
                self.file_view.addTopLevelItem(item)

        finally:
            for func in cleanup:
                func()

        if self.select_all:
            self.check_all(True)
            self.select_all = False

        self.loaded = True

    def _create_item(self, change, shelver, trees, old_changes):
        """Create QTreeWidgetItem for file list from Change instance."""
        ch = Change(change, shelver, trees)
        item = QtGui.QTreeWidgetItem()

        if ch.kind == 'directory':
            item.setIcon(0, get_icon("folder", 16))
        else:
            item.setIcon(0, get_icon("file", 16))
        item.change = ch
        item.setText(0, ch.disp_text)
        item.setText(1, gettext(ch.status))
        if ch.status == 'modify text':
            item.setText(2, u'0/%d' % len(ch.parsed_patch.hunks))
        brush = self.brushes.get(ch.status)
        if brush:
            for i in range(3):
                item.setForeground(i, brush)
        item.setCheckState(0, QtCore.Qt.Unchecked)

        if old_changes:
            old_change = old_changes.get((ch.file_id, ch.status))
            if old_change and old_change.is_same_change(ch):
                # Keep selection when reloading
                if ch.status == 'modify text':
                    item.change = old_change
                    self.update_item(item)
                else:
                    item.setCheckState(0, QtCore.Qt.Checked)
        return item

    def selected_file_changed(self):
        items = self.file_view.selectedItems()
        if len(items) != 1 or items[0].change.status != 'modify text':
            self.hunk_view.clear()
            self.editor_button.setEnabled(False)
        else:
            item = items[0]
            encoding = self.encoding_selector.encoding
            self.hunk_view.set_parsed_patch(item.change, encoding)
            self.editor_button.setEnabled(self.editor_available)

    def selected_hunk_changed(self):
        for item in self.file_view.selectedItems():
            self.update_item(item)
    
    def update_item(self, item):
        change = item.change
        if change.status != 'modify text':
            return

        if change.edited_lines:
            state = QtCore.Qt.PartiallyChecked
            item.setText(2, "???")
        else:
            hunks = change.parsed_patch.hunks
            hunk_num = len(hunks)
            selected_hunk_num = 0
            for hunk in hunks:
                if hunk.selected:
                    selected_hunk_num += 1
            item.setText(2, "%d/%d" % (selected_hunk_num, hunk_num))
            if selected_hunk_num == 0:
                state = QtCore.Qt.Unchecked
            elif selected_hunk_num == hunk_num:
                state = QtCore.Qt.Checked
            else:
                state = QtCore.Qt.PartiallyChecked

        if item.checkState(0) != state:
            item.setCheckState(0, state)
            self.update_compleater_words()

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
            if item.change.edited_lines:
                item.change.edited_lines = None
                self.selected_file_changed()
            else:
                self.hunk_view.update()
            item.setText(2, u'%d/%d' % (hunk_num if selected else 0, hunk_num))

        self.update_compleater_words()

    def encoding_changed(self, encoding):
        self.selected_file_changed()

    def complete_toggled(self, checked):
        self.hunk_view.set_complete(checked)

    def check_all(self, checked):
        if checked:
            state = QtCore.Qt.Checked
        else:
            state = QtCore.Qt.Unchecked

        view = self.file_view
        for i in range(view.topLevelItemCount()):
            item = view.topLevelItem(i)
            if item.checkState(0) != state:
                item.setCheckState(0, state)

    def clear(self, clear_message = True):
        if clear_message:
            self.message.clear()
        self.file_view.clear()
        self.file_view.viewport().update()
        self.hunk_view.clear()
        self.revision = None
        self.loaded = False

    def use_editor(self):
        cleanup = []
        items = self.file_view.selectedItems()
        if len(items) != 1 or items[0].change.status != 'modify text':
            return
        else:
            change = items[0].change
        try:
            target_tree, work_tree = self.trees
            cleanup.append(work_tree.lock_read().unlock)
            cleanup.append(target_tree.lock_read().unlock)
            config = work_tree.branch.get_config()
            change_editor = config.get_change_editor(target_tree, work_tree)
            if change_editor is None:
                QtGui.QMessageBox.information(self, gettext('Shelve'),
                        gettext('Change editor is not defined.'), gettext('&OK'))
                self.editor_available = False
                self.editor_button.setEnabled(False)
                return

            cleanup.append(change_editor.finish)
            lines = split_lines(change_editor.edit_file(change.file_id))
            change_count = Shelver._count_changed_regions(change.work_lines, lines)
            if change_count > 0:
                change.edited_lines = lines
                self.update_item(items[0])
                self.selected_file_changed()
        finally:
            while cleanup:
                cleanup.pop()()

    def _get_change_dictionary(self):
        change_dict = {}
        for i in range(0, self.file_view.topLevelItemCount()):
            item = self.file_view.topLevelItem(i)
            change = item.change
            if item.checkState(0) == QtCore.Qt.Unchecked:
                continue
            change_dict[(change.file_id, change.status)] = change
        return change_dict

    def do_shelve(self, destroy=False):
        change_dict = self._get_change_dictionary()
        if change_dict:
            nfiles = len(change_dict)
            if destroy:
                prompt = ngettext('Delete changes of %d file without shelving',
                                  'Delete changes of %d files without shelving', nfiles) % nfiles 
                func = QtGui.QMessageBox.warning
            else:
                prompt = ngettext('Shelve changes of %d file',
                                  'Shelve changes of %d files', nfiles) % nfiles 
                func = QtGui.QMessageBox.question
            ret = func(self, gettext('Shelve'), prompt,
                    QtGui.QMessageBox.Ok | QtGui.QMessageBox.Cancel)
            if ret != QtGui.QMessageBox.Ok:
                return
        else:
            QtGui.QMessageBox.information(self, gettext('Shelve'),
                    gettext('No changes selected.'), gettext('&OK'))
            return

        cleanup = []
        try:
            shelver, creator = self._create_shelver_and_creator(destroy=destroy)
            cleanup.append(shelver.finalize)
            cleanup.append(creator.finalize)
            trees = (shelver.target_tree, shelver.work_tree)
            if len(trees[1].get_parent_ids()) > 1:
                raise WorkingTreeHasPendingMarge
            if self.revision != trees[0].get_revision_id():
                raise WorkingTreeHasChanged

            changes = []
            for ch in creator.iter_shelvable():
                change = Change(ch, shelver, trees)
                key = (change.file_id, change.status)
                org_change = change_dict.get(key)
                if org_change is None:
                    continue
                if not change.is_same_change(org_change):
                    raise WorkingTreeHasChanged
                del(change_dict[key])
                changes.append(org_change)

            if change_dict:
                raise WorkingTreeHasChanged

            for change in changes:
                if change.status == 'modify text':
                    self.handle_modify_text(creator, change)
                elif change.status == 'modify binary':
                    creator.shelve_content_change(change.data[1])
                else:
                    creator.shelve_change(change.data)
            manager = shelver.work_tree.get_shelf_manager()
            message = unicode(self.message.toPlainText()).strip() or gettext(u'<no message>')
            if destroy:
                creator.transform()
                shelf_id = -1
            else:
                shelf_id = manager.shelve_changes(creator, message)

        except WorkingTreeHasPendingMarge:
            QtGui.QMessageBox.warning(self, gettext('Shelve'),
                    gettext('Operation aborted because working tree has pending merges.'),
                    gettext('&OK'))
            return
        except WorkingTreeHasChanged:
            QtGui.QMessageBox.warning(self, gettext('Shelve'),
                    gettext('Operation aborted because target files has been changed.'), gettext('&OK'))
            return

        finally:
            while cleanup:
                cleanup.pop()()
        self.emit(QtCore.SIGNAL("shelfCreated(int)"), shelf_id)
        self.clear()

    def handle_modify_text(self, creator, change):
        final_hunks = []
        offset = 0
        change_count = 0
        if change.edited_lines:
            creator.shelve_lines(change.file_id, change.edited_lines)
        else:
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
            creator.shelve_lines(change.file_id, list(patched))

    def load_settings(self):
        config = get_qbzr_config()
        layout = config.get_option("shelve_layout")
        if layout not in ("1", "3"):
            layout = "2"
        self.current_layout = int(layout)

    def save_settings(self):
        config = get_qbzr_config()
        config.set_option("shelve_layout", str(self.current_layout))
        config.save()

    def hideEvent(self, event):
        self.save_settings()

    def update_compleater_words(self):
        words = set()
        num_files_loaded = 0
        for i in range(0, self.file_view.topLevelItemCount()):
            item = self.file_view.topLevelItem(i)
            if item.checkState(0) == QtCore.Qt.Unchecked:
                continue
            ch = item.change

            if num_files_loaded < MAX_AUTOCOMPLETE_FILES:
                file_words, load_texts_first = ch.get_words()
                words.update(file_words)
                if load_texts_first:
                    num_files_loaded += 1
                    self.window().processEvents()

        words = list(words)
        words.sort(key=lambda x: x.lower())
        self.completer_model.setStringList(words)
    
class HunkView(QtGui.QWidget):
    def __init__(self, complete=False, parent=None):
        QtGui.QWidget.__init__(self, parent)
        layout = QtGui.QHBoxLayout(self)
        layout.setSpacing(0)
        layout.setMargin(0)
        self.browser = HunkTextBrowser(complete, self)
        self.guidebar = GuideBar(self.browser, parent=self)
        self.guidebar.add_entry('hunk', self.browser.focus_color)
        self.selector = HunkSelector(self.browser, self)
        layout.addWidget(self.selector)
        layout.addWidget(self.browser)
        layout.addWidget(self.guidebar)
        self.connect(self.browser, QtCore.SIGNAL("focusedHunkChanged()"),
                     self.update)

        def selected_hunk_changed():
            self.update()
            self.emit(QtCore.SIGNAL("selectionChanged()"))
        self.connect(self.browser, QtCore.SIGNAL("selectedHunkChanged()"), 
                     selected_hunk_changed)

        self.change = None
        self.encoding = None

    def set_tab_width(self, pixels):
        self.browser.setTabStopWidth(pixels)

    def set_complete(self, value):
        self.browser.complete = value
        if self.change is not None:
            self.set_parsed_patch(self.change, self.encoding)

    def move_previous(self):
        self.browser.move_previous()

    def move_next(self):
        self.browser.move_next()

    def rewind(self):
        self.browser.rewind()

    def set_parsed_patch(self, change, encoding):
        self.change = change
        self.encoding = encoding
        self.browser.set_parsed_patch(change, encoding)
        self.guidebar.update_data(hunk=self.browser.guidebar_deta)
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
        self.setStyleSheet("border:1px solid lightgray;")
        self.connect(browser.verticalScrollBar(), QtCore.SIGNAL("valueChanged(int)"), self.scrolled)
        self.frame_width = QtGui.QApplication.style().pixelMetric(QtGui.QStyle.PM_DefaultFrameWidth)

        self.checkbox_pen = QtGui.QPen(QtCore.Qt.black)
        self.checkbox_pen.setWidth(2)

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
        painter.setClipRect(rect)
        browser.draw_background(
                QtCore.QRect(1, rect.top(), self.width() - 2, rect.height()), 
                painter, scroll_y)

        # draw checkbox
        top, bottom = rect.top(), rect.bottom()
        painter.setRenderHint(QtGui.QPainter.Antialiasing, True)
        painter.setPen(self.checkbox_pen)
        for hunk, y1, y2 in browser.hunk_list:
            y1 -= scroll_y
            y1 += 4
            if y1 + 13 < top:
                continue
            if bottom < y1:
                break
            painter.fillRect(6, y1, 13, 13, QtCore.Qt.white)

            painter.drawRect(6, y1, 13, 13)
            if hunk.selected:
                painter.drawLine(9, y1 + 7, 12, y1 + 10)
                painter.drawLine(16, y1 + 3, 12, y1 + 10)

        del painter

    def mousePressEvent(self, event):
        if event.button() == QtCore.Qt.LeftButton:
            browser = self.browser
            scroll_y = browser.verticalScrollBar().value()

            y = event.y() + scroll_y - self.frame_width
            for i, (hunk, top, bottom) in enumerate(browser.hunk_list):
                if top <= y <= bottom:
                    browser.toggle_selection(i)
                    break
                elif y < top:
                    break
            browser.focus_hunk_by_pos(event.y() - self.frame_width)
        QtGui.QFrame.mousePressEvent(self, event)

class HunkTextBrowser(QtGui.QTextBrowser):

    def __init__(self, complete=False, parent=None):
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
        
        from bzrlib.plugins.qbzr.lib.diffview import colors
        self.header_color = colors['blank'][0]
        self.border_pen = QtGui.QPen(QtCore.Qt.gray)
        self.focus_color = QtGui.QColor(0x87, 0xCE, 0xEB, 0x48) # lightBlue
        self.focus_color_inactive = QtGui.QColor(0x87, 0xCE, 0xEB, 0x20) # lightBlue

        self.complete = complete
        self._focused_index = -1
        self.guidebar_deta = []

    def rewind(self):
        if not self.rewinded:
            self.rewinded = True
            self.verticalScrollBar().setValue(0)

    def set_parsed_patch(self, change, encoding):
        self.clear()
        cursor = self.cursor

        if change.edited_lines:
            cursor.insertText(
                    gettext("Edited by change editor.\n"), self.monospacedHunkFormat)
            lines = "".join(change.encode_edited_lines(encoding))
            if lines:
                cursor.insertText(lines, self.monospacedInactiveFormat)
            return

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
                lines = "".join([' ' + l for l in work_lines[start:hunk.mod_pos - 1]])
                if lines:
                    cursor.insertText(lines, self.monospacedInactiveFormat)
                start = hunk.mod_pos + hunk.mod_range - 1
                y1 = cursor.block().layout().position().y()
                l1 = cursor.block().blockNumber()
                print_hunk(hunk, hunk_texts)
                y2 = cursor.block().layout().position().y()
                l2 = cursor.block().blockNumber()
                self.guidebar_deta.append((l1, l2 - l1))
            else:
                y1 = cursor.block().layout().position().y()
                cursor.insertText(str(hunk.get_header()), self.monospacedHunkFormat)
                print_hunk(hunk, hunk_texts)
                cursor.insertText("\n", self.monospacedFormat)
                y2 = cursor.block().layout().position().y()

            self.hunk_list.append((hunk, y1, y2))

        if self.complete:
            lines = "".join([' ' + l for l in work_lines[start:]])
            if lines:
                cursor.insertText(lines, self.monospacedInactiveFormat)

        if self.hunk_list:
            self._set_focused_hunk(0)

        self.emit(QtCore.SIGNAL("documentChangeFinished()"))
        self.update()

    def update(self):
        QtGui.QTextBrowser.update(self)
        self.viewport().update()

    def clear(self):
        QtGui.QTextBrowser.clear(self)
        del(self.hunk_list[:])
        self._set_focused_hunk(-1)
        self.guidebar_deta = []
        self.emit(QtCore.SIGNAL("documentChangeFinished()"))

    def paintEvent(self, event):
        if not self.hunk_list:
            QtGui.QTextBrowser.paintEvent(self, event) 
            return
        scroll_y = self.verticalScrollBar().value()

        painter = QtGui.QPainter(self.viewport())
        rect = event.rect()
        painter.setClipRect(rect)

        self.draw_background(rect, painter, scroll_y)

        del painter
        QtGui.QTextBrowser.paintEvent(self, event) 

    def draw_background(self, rect, painter, offset):
        left, right, width = rect.left(), rect.right(), rect.width()
        top, bottom = rect.top(), rect.bottom()
        painter.setPen(self.border_pen)
        for i, (hunk, y1, y2) in enumerate(self.hunk_list):
            y1 -= offset
            y2 -= offset
            if bottom < y1 or y2 < top:
                continue
            if not self.complete:
                # Fill header rect.
                painter.fillRect(left, y1, width, 20, self.header_color)
            # Overlay focus rect.
            if i == self._focused_index:
                if self.hasFocus():
                    color = self.focus_color
                else:
                    color = self.focus_color_inactive
                painter.fillRect(left, y1, width, y2 - y1, color)
            # Draw border.
            painter.drawLine(left, y1, right, y1)
            painter.drawLine(left, y2, right, y2)
        
    def move_next(self):
        index = int(self._focused_index + 1)
        if index == len(self.hunk_list):
            index -= 1
        self._set_focused_hunk(index)
        self.setFocus(QtCore.Qt.OtherFocusReason)

    def move_previous(self):
        index = int(self._focused_index)
        if 1 <= index and index == self._focused_index:
            index -= 1
        self._set_focused_hunk(index)
        self.setFocus(QtCore.Qt.OtherFocusReason)

    def toggle_selection(self, index):
        if 0 <= index < len(self.hunk_list) and int(index) == index:
            self.hunk_list[index][0].selected = \
                    not self.hunk_list[index][0].selected
            self.emit(QtCore.SIGNAL("selectedHunkChanged()"))

    def focus_hunk_by_pos(self, y):
        index = self.hittest(y)
        self._set_focused_hunk(index, scroll=False)

    def _set_focused_hunk(self, index, scroll=True):
        self._focused_index = index
        self.update()
        self.emit(QtCore.SIGNAL("focusedHunkChanged()"))
        if scroll and int(index) == index:
            self.scroll_to_hunk(index)

    def hittest(self, y):
        # NOTE : Value of y is client coordinate.
        # If y is between (N)th and (N+1)th hunks, return (N + 0.5)
        if not self.hunk_list:
            return -1
        y += self.verticalScrollBar().value()
        for i, (hunk, y1, y2) in enumerate(self.hunk_list):
            if y1 <= y <= y2:
                return i
            elif y < y1:
                return i - 0.5
        return i + 0.5

    def scroll_to_hunk(self, index):
        sbar = self.verticalScrollBar()
        if index < 0:
            sbar.setValue(0)
        elif len(self.hunk_list) <= index:
            sbar.setValue(sbar.maximum())
        else:
            MARGIN = 24
            height = self.viewport().height()
            cur_pos = sbar.value()
            max_pos = self.hunk_list[index][1] - MARGIN
            min_pos = self.hunk_list[index][2] - height + MARGIN
            if max_pos <= min_pos or max_pos < cur_pos:
                sbar.setValue(max_pos)
            elif cur_pos < min_pos:
                sbar.setValue(min_pos)
                
    def mousePressEvent(self, event):
        if event.button() == QtCore.Qt.LeftButton:
            self.focus_hunk_by_pos(event.y())

        QtGui.QTextBrowser.mousePressEvent(self, event)

    def focusInEvent(self, event):
        self.parent().update()
        QtGui.QTextBrowser.focusInEvent(self, event)

    def focusOutEvent(self, event):
        self.parent().update()
        QtGui.QTextBrowser.focusOutEvent(self, event)

    def keyPressEvent(self, event):
        mod, key = int(event.modifiers()), event.key()
        if mod == QtCore.Qt.NoModifier:
            if key == QtCore.Qt.Key_Space:
                self.toggle_selection(self._focused_index)
                return
        QtGui.QTextBrowser.keyPressEvent(self, event)
