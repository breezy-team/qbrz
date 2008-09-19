# -*- coding: utf-8 -*-
#
# QBzr - Qt frontend to Bazaar commands
# Copyright (C) 2006-2007 Lukáš Lalinský <lalinsky@gmail.com>
# Copyright (C) 2006 Trolltech ASA
# Copyright (C) 2006 Jelmer Vernooij <jelmer@samba.org>
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

import os.path
import re
import sys
from PyQt4 import QtCore, QtGui

from bzrlib import (
    bugtracker,
    errors,
    osutils,
    )
from bzrlib.errors import BzrError, NoSuchRevision
from bzrlib.option import Option
from bzrlib.commands import Command, register_command
from bzrlib.commit import ReportCommitToLog
from bzrlib.workingtree import WorkingTree

from bzrlib.plugins.qbzr.lib.spellcheck import SpellCheckHighlighter, SpellChecker
from bzrlib.plugins.qbzr.lib.autocomplete import get_wordlist_builder
from bzrlib.plugins.qbzr.lib.diff import DiffWindow
from bzrlib.plugins.qbzr.lib.wtlist import WorkingTreeFileList
from bzrlib.plugins.qbzr.lib.i18n import gettext
from bzrlib.plugins.qbzr.lib.subprocess import SubProcessWindow
from bzrlib.plugins.qbzr.lib.util import (
    BTN_CANCEL,
    BTN_OK,
    QBzrWindow,
    file_extension,
    format_timestamp,
    get_apparent_author,
    get_global_config,
    )


MAX_AUTOCOMPLETE_FILES = 20


class TextEdit(QtGui.QTextEdit):

    def __init__(self, parent=None, main_window=None):
        QtGui.QTextEdit.__init__(self, parent)
        self.completer = None
        self.eow = QtCore.QString("~!@#$%^&*()_+{}|:\"<>?,./;'[]\\-=")
        self.main_window = main_window

    def keyPressEvent(self, e):
        c = self.completer
        e_key = e.key()
        if (e_key in (QtCore.Qt.Key_Tab, QtCore.Qt.Key_Backtab)
            or (c.popup().isVisible() and e_key in (QtCore.Qt.Key_Enter,
                QtCore.Qt.Key_Return, QtCore.Qt.Key_Escape))):
            e.ignore()
            return
        if (self.main_window
            and e_key in (QtCore.Qt.Key_Enter, QtCore.Qt.Key_Return)
            and (int(e.modifiers()) & QtCore.Qt.ControlModifier)):
                e.ignore()
                # FIXME probably this is ugly hack and main qcommit window
                # should explicitly catch Ctrl+Enter by self
                self.main_window.accept()
                return

        isShortcut = e.modifiers() & QtCore.Qt.ControlModifier and e.key() == QtCore.Qt.Key_E
        if not isShortcut:
            QtGui.QTextEdit.keyPressEvent(self, e)

        ctrlOrShift = e.modifiers() & (QtCore.Qt.ControlModifier | QtCore.Qt.ShiftModifier)
        if ctrlOrShift and e.text().isEmpty():
            return

        hasModifier = (e.modifiers() != QtCore.Qt.NoModifier) and not ctrlOrShift
        completionPrefix = self.textUnderCursor()

        if not isShortcut and (hasModifier or e.text().isEmpty()
                               or completionPrefix.length() < 2
                               or self.eow.contains(e.text().right(1))):
            c.popup().hide()
            return

        if completionPrefix != c.completionPrefix():
            c.setCompletionPrefix(completionPrefix)
            c.popup().setCurrentIndex(c.completionModel().index(0, 0))

        cr = self.cursorRect()
        cr.setWidth(c.popup().sizeHintForColumn(0) +
                    c.popup().verticalScrollBar().sizeHint().width())
        c.complete(cr);

    def textUnderCursor(self):
        tc = self.textCursor()
        tc.select(QtGui.QTextCursor.WordUnderCursor)
        return tc.selectedText()

    def insertCompletion(self, completion):
        tc = self.textCursor()
        extra = completion.length() - self.completer.completionPrefix().length()
        tc.movePosition(QtGui.QTextCursor.Left)
        tc.movePosition(QtGui.QTextCursor.EndOfWord)
        tc.insertText(completion.right(extra))
        self.setTextCursor(tc)

    def setCompleter(self, completer):
        self.completer = completer
        completer.setWidget(self)
        completer.setCaseSensitivity(QtCore.Qt.CaseSensitive)
        self.connect(completer, QtCore.SIGNAL("activated(QString)"), self.insertCompletion)


class CommitWindow(SubProcessWindow):

    RevisionIdRole = QtCore.Qt.UserRole + 1
    ParentIdRole = QtCore.Qt.UserRole + 2

    def collect_info(self):
        tree = self.tree
        branch = tree.branch
        repo = branch.repository
        parents = tree.get_parent_ids()
        pending_merges = []
        if len(parents) > 1:
            last_revision = parents[0]
            if last_revision is not None:
                try:
                    ignore = set(branch.repository.get_ancestry(last_revision,
                                                                topo_sorted=False))
                except NoSuchRevision:
                    ignore = set([None, last_revision])
            else:
                ignore = set([None])
            for merge in parents[1:]:
                ignore.add(merge)
                pending_merges.append(merge)
                inner_merges = repo.get_ancestry(merge)
                inner_merges.pop(0)
                for inner_merge in reversed(inner_merges):
                    if inner_merge in ignore:
                        continue
                    ignore.add(inner_merge)
                    pending_merges.append(inner_merge)
        self.pending_merges = repo.get_revisions(pending_merges)
        self.is_bound = bool(branch.get_bound_location())

    def iter_changes_and_state(self):
        """An iterator for the WorkingTreeFileList widget"""
        # a word list for message completer
        words = set()
        show_nonversioned = self.show_nonversioned_checkbox.isChecked()

        def in_selected_list(path):
            if not self.initial_selected_list:
                return True
            if path in self.initial_selected_list:
                return True
            for p in self.initial_selected_list:
                if path.startswith(p):
                    return True
            return False

        num_versioned_files = 0
        for desc in self.tree.iter_changes(self.tree.basis_tree(),
                                           want_unversioned=True):
            # desc[0]: file_id         -> ascii string
            # desc[1]: paths           -> 2-tuple (old, new) fullpaths unicode/None
            # desc[2]: changed_content -> bool
            # desc[3]: versioned       -> 2-tuple (bool, bool)
            # desc[4]: parent          -> 2-tuple
            # desc[5]: name            -> 2-tuple (old_name, new_name) utf-8?/None
            # desc[6]: kind            -> 2-tuple (string/None, string/None)
            # desc[7]: executable      -> 2-tuple (bool/None, bool/None)
            # NOTE: None value used for non-existing entry in corresponding
            #       tree, e.g. for added/deleted file

            if desc[0] is not None and desc[4] == (None, None):     # skip TREE_ROOT
                # TREE_ROOT has not parents (desc[4]).
                # But because we want to see unversioned files we need to check
                # for file_id too (desc[0])
                continue

            is_versioned = self.filelist.is_changedesc_versioned(desc)
            path = self.filelist.get_changedesc_path(desc)

            if not is_versioned and self.tree.is_ignored(path):
                continue

            visible = is_versioned or show_nonversioned
            check_state = None
            if not self.pending_merges:
                check_state = visible and is_versioned and in_selected_list(path)
            yield desc, visible, check_state

            if is_versioned:
                num_versioned_files += 1

                words.update(os.path.split(path))
                if num_versioned_files < MAX_AUTOCOMPLETE_FILES:
                    ext = file_extension(path)
                    builder = get_wordlist_builder(ext)
                    if builder is not None:
                        try:
                            file = open(path, 'rt')
                            words.update(builder.iter_words(file))
                        except EnvironmentError:
                            pass
        words = list(words)
        words.sort(lambda a, b: cmp(a.lower(), b.lower()))
        self.completion_words = words

    def __init__(self, tree, selected_list, dialog=True, parent=None,
                 local=None, message=None, ui_mode=True):
        super(CommitWindow, self).__init__(
                                  gettext("Commit"),
                                  name = "commit",
                                  default_size = (540, 540),
                                  ui_mode = ui_mode,
                                  dialog = dialog,
                                  parent = parent)
        self.tree = tree
        self.basis_tree = self.tree.basis_tree()
        self.windows = []
        self.initial_selected_list = selected_list

        self.connect(self.process_widget,
            QtCore.SIGNAL("failed()"),
            self.failed)

        splitter = QtGui.QSplitter(QtCore.Qt.Vertical, self)

        message_groupbox = QtGui.QGroupBox(gettext("Message"), splitter)
        splitter.addWidget(message_groupbox)
        self.tabWidget = QtGui.QTabWidget()
        splitter.addWidget(self.tabWidget)
        
        grid = QtGui.QGridLayout(message_groupbox)

        self.show_nonversioned_checkbox = QtGui.QCheckBox(
            gettext("Show non-versioned files"))

        self.filelist = WorkingTreeFileList(message_groupbox, self.tree)
        selectall_checkbox = QtGui.QCheckBox(
                                gettext(self.filelist.SELECTALL_MESSAGE))
        selectall_checkbox.setCheckState(QtCore.Qt.Checked)
        self.filelist.set_selectall_checkbox(selectall_checkbox)

        tree.lock_read()
        try:
            self.collect_info()
            self.filelist.fill(self.iter_changes_and_state())
        finally:
            tree.unlock()

        self.filelist.setup_actions()

        # Equivalent for 'bzr commit --message'
        self.message = TextEdit(message_groupbox, main_window=self)
        self.message.setToolTip(gettext("Enter the commit message"))
        completer = QtGui.QCompleter()
        completer.setModel(QtGui.QStringListModel(self.completion_words, completer))
        self.message.setCompleter(completer)
        self.message.setAcceptRichText(False)

        language = get_global_config().get_user_option('spellcheck_language') or 'en'
        spell_checker = SpellChecker(language)
        spell_highlighter = SpellCheckHighlighter(self.message.document(), spell_checker)

        self.restore_message()
        if message:
            self.message.setText(message)
        grid.addWidget(self.message, 0, 0, 1, 2)

        # Equivalent for 'bzr commit --fixes'
        self.bugsCheckBox = QtGui.QCheckBox(gettext("&Fixed bugs:"))
        self.bugsCheckBox.setToolTip(gettext("Set the IDs of bugs fixed by "
                                     "this commit"))
        self.bugs = QtGui.QLineEdit()
        self.bugs.setToolTip(gettext("Enter the list of bug IDs in format "
                             "<i>tag:id</i> separated by a space, "
                             "e.g. <i>project:123 project:765</i>"))
        self.bugs.setEnabled(False)
        self.connect(self.bugsCheckBox, QtCore.SIGNAL("stateChanged(int)"),
                     self.enableBugs)
        grid.addWidget(self.bugsCheckBox, 1, 0)
        grid.addWidget(self.bugs, 1, 1)

        # Equivalent for 'bzr commit --author'
        self.authorCheckBox = QtGui.QCheckBox(gettext("&Author:"))
        self.authorCheckBox.setToolTip(gettext("Set the author of this change,"
            " if it's different from the committer"))
        self.author = QtGui.QLineEdit()
        self.author.setToolTip(gettext("Enter the author's name, "
            "e.g. <i>John Doe &lt;jdoe@example.com&gt;</i>"))
        self.author.setEnabled(False)
        self.connect(self.authorCheckBox, QtCore.SIGNAL("stateChanged(int)"),
                     self.enableAuthor)
        grid.addWidget(self.authorCheckBox, 2, 0)
        grid.addWidget(self.author, 2, 1)
        # default author from config
        config = self.tree.branch.get_config()
        self.default_author = config.username()
        self.custom_author = ''
        self.author.setText(self.default_author)

        if self.is_bound:
            self.local_checkbox = QtGui.QCheckBox(gettext(
                "&Local commit in a bound branch"))
            self.local_checkbox.setToolTip(gettext(
                "Local commits are not pushed to the master branch "
                "until a normal commit is performed"))
            grid.addWidget(self.local_checkbox, 3, 0, 1, 2)
            if local:
                self.local_checkbox.setChecked(True)

        # Display the list of changed files
        files_tab = QtGui.QWidget()
        self.tabWidget.addTab(files_tab, gettext("Changes"))

        vbox = QtGui.QVBoxLayout(files_tab)
        vbox.addWidget(self.filelist)
        self.connect(self.show_nonversioned_checkbox, QtCore.SIGNAL("toggled(bool)"), self.show_nonversioned)
        vbox.addWidget(self.show_nonversioned_checkbox)
    
        vbox.addWidget(selectall_checkbox)

        self.filelist.sortItems(0, QtCore.Qt.AscendingOrder)

        # Display a list of pending merges
        if self.pending_merges:
            selectall_checkbox.setEnabled(False)
            pendingMergesWidget = QtGui.QTreeWidget()
            self.tabWidget.addTab(pendingMergesWidget, gettext("Pending Merges"))
            
            pendingMergesWidget.setRootIsDecorated(False)
            pendingMergesWidget.setHeaderLabels(
                [gettext("Date"), gettext("Author"), gettext("Message")])
            header = pendingMergesWidget.header()
            header.resizeSection(0, 120)
            header.resizeSection(1, 190)
            self.connect(pendingMergesWidget,
                QtCore.SIGNAL("itemDoubleClicked(QTreeWidgetItem *, int)"),
                self.show_changeset)
            # Pending-merge widget gets disabled as we are executing.
            QtCore.QObject.connect(self,
                                   QtCore.SIGNAL("subprocessStarted(bool)"),
                                   pendingMergesWidget,
                                   QtCore.SLOT("setDisabled(bool)"))

            items = []
            for merge in self.pending_merges:
                item = QtGui.QTreeWidgetItem()
                item.setText(0, format_timestamp(merge.timestamp))
                item.setText(1, get_apparent_author(merge))
                item.setText(2, merge.get_summary())
                item.setData(0, self.RevisionIdRole,
                             QtCore.QVariant(merge.revision_id))
                if merge.parent_ids:
                    item.setData(0, self.ParentIdRole,
                                 QtCore.QVariant(merge.parent_ids[0]))
                items.append(item)
            pendingMergesWidget.insertTopLevelItems(0, items)

        self.tabWidget.addTab(self.process_widget, gettext("Status"))
        
        splitter.setStretchFactor(0, 3)

        vbox = QtGui.QVBoxLayout(self.centralwidget)
        vbox.addWidget(splitter)
        vbox.addWidget(self.buttonbox)

        # groupbox and tabbox get disabled as we are executing.
        QtCore.QObject.connect(self,
                               QtCore.SIGNAL("subprocessStarted(bool)"),
                               message_groupbox,
                               QtCore.SLOT("setDisabled(bool)"))
        QtCore.QObject.connect(self,
                               QtCore.SIGNAL("subprocessStarted(bool)"),
                               files_tab,
                               QtCore.SLOT("setDisabled(bool)"))
        
        # Try to be smart: if there is no saved message
        # then set focus on Edit Area; otherwise on OK button.
        if self.get_saved_message():
            self.buttonbox.setFocus()
        else:
            self.message.setFocus()

    def enableBugs(self, state):
        if state == QtCore.Qt.Checked:
            self.bugs.setEnabled(True)
            self.bugs.setFocus(QtCore.Qt.OtherFocusReason)
        else:
            self.bugs.setEnabled(False)

    def enableAuthor(self, state):
        if state == QtCore.Qt.Checked:
            self.author.setEnabled(True)
            self.author.setText(self.custom_author)
            self.author.setFocus(QtCore.Qt.OtherFocusReason)
        else:
            self.author.setEnabled(False)
            self.custom_author = self.author.text()
            self.author.setText(self.default_author)


    def get_saved_message(self):
        config = self.tree.branch.get_config()._get_branch_data_config()
        return config.get_user_option('qbzr_commit_message')

    def restore_message(self):
        message = self.get_saved_message()
        if message:
            self.message.setText(message)

    def save_message(self):
        message = unicode(self.message.toPlainText())
        config = self.tree.branch.get_config()
        if message.strip():
            config.set_user_option('qbzr_commit_message', message)
        else:
            if config.get_user_option('qbzr_commit_message'):
                # FIXME this should delete the config entry, not just set it to ''
                config.set_user_option('qbzr_commit_message', '')

    def clear_saved_message(self):
        config = self.tree.branch.get_config()
        # FIXME this should delete the config entry, not just set it to ''
        config.set_user_option('qbzr_commit_message', '')


    def start(self):
        args = ["commit"]
        files_to_add = ["add"]
        
        message = unicode(self.message.toPlainText()).strip() 
        if not message: 
            button = QtGui.QMessageBox.warning(self, 
                "QBzr - " + gettext("Commit"), 
                gettext("Empty commit message. Do you really want to commit?"), 
                QtGui.QMessageBox.Yes | QtGui.QMessageBox.No) 
            if button == QtGui.QMessageBox.No: 
                # don't commit, but don't close the window either
                self.failed()
                return
        args.append(('-m %s' % message))
        
        if not self.pending_merges:
            for desc in self.filelist.iter_checked():
                is_ver = self.filelist.is_changedesc_versioned(desc)
                path = self.filelist.get_changedesc_path(desc)
                if not is_ver:
                    files_to_add.append(path)
                args.append(path)
        
        if self.bugsCheckBox.isChecked():
            for s in unicode(self.bugs.text()).split():
                args.append(("--fixes=%s" % s))
        
        if self.authorCheckBox.isChecked():
            args.append(("--author=%s" % unicode(self.author.text())))
        
        if self.is_bound and self.local_checkbox.isChecked():
            args.append("--local")
        
        dir = self.tree.basedir
        commands = []
        if len(files_to_add)>1:
            commands.append((dir, files_to_add))
        commands.append((dir, args))

        self.tabWidget.setCurrentWidget(self.process_widget)
        self.process_widget.start_multi(commands)
    
    def show_changeset(self, item=None, column=None):
        repo = self.tree.branch.repository
        rev_id = str(item.data(0, self.RevisionIdRole).toString())
        rev_parent_id = str(item.data(0, self.ParentIdRole).toString())
        revs = [rev_parent_id, rev_id]
        repo.lock_read()
        try:
            tree1, tree2 = repo.revision_trees(revs)
        finally:
            repo.unlock()
        window = DiffWindow(tree1, tree2,
                            self.tree.branch, self.tree.branch,
                            parent=self)
        window.show()
        self.windows.append(window)

    def show_nonversioned(self, state):
        """Show/hide non-versioned files."""
        state = not state
        for (tree_item, change_desc) in self.filelist.iter_treeitem_and_desc(True):
            if change_desc[3] == (False, False):
                tree_item.setHidden(state)
        self.filelist.update_selectall_state(None, None)

    def closeEvent(self, event):
        if not self.process_widget.is_running():
            if self.process_widget.finished:
                self.clear_saved_message()
            else:
                self.save_message()
        return SubProcessWindow.closeEvent(self, event)
