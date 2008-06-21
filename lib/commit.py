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

from bzrlib.plugins.qbzr.lib.diff import DiffWindow
from bzrlib.plugins.qbzr.lib.i18n import gettext
from bzrlib.plugins.qbzr.lib.util import (
    BTN_CANCEL,
    BTN_OK,
    QBzrWindow,
    file_extension,
    format_timestamp,
    get_apparent_author,
    )


_python_identifier_re = re.compile(r"(?:def|class)\s+(\w+)")
_python_variable_re = re.compile(r"(\w+)\s*=\s*")

def python_word_list_builder(file):
    for line in file:
        match = _python_identifier_re.search(line)
        if match:
            yield match.group(1)
        match = _python_variable_re.search(line)
        if match:
            yield match.group(1)


_cpp_identifier_re = re.compile(r"(?:class|typedef|struct|union|namespace)\s+(\w+)")
_cpp_member_re = re.compile(r"::\s*(\w+)\s*\(")

def cpp_header_word_list_builder(file):
    for line in file:
        match = _cpp_identifier_re.search(line)
        if match:
            yield match.group(1)

def cpp_source_word_list_builder(file):
    for line in file:
        match = _cpp_member_re.search(line)
        if match:
            yield match.group(1)


_word_list_builders = {
    ".py": python_word_list_builder,
    ".cpp": cpp_source_word_list_builder,
    ".h": cpp_header_word_list_builder,
}


class TextEdit(QtGui.QTextEdit):

    def __init__(self, parent=None):
        QtGui.QTextEdit.__init__(self, parent)
        self.completer = None
        self.eow = QtCore.QString("~!@#$%^&*()_+{}|:\"<>?,./;'[]\\-=")

    def keyPressEvent(self, e):
        c = self.completer
        if c.popup().isVisible():
            if (e.key() == QtCore.Qt.Key_Enter or
                e.key() == QtCore.Qt.Key_Return or
                e.key() == QtCore.Qt.Key_Escape or
                e.key() == QtCore.Qt.Key_Tab or
                e.key() == QtCore.Qt.Key_Backtab):
                e.ignore()
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


class CommitWindow(QBzrWindow):

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

    def __init__(self, tree, selected_list, dialog=True, parent=None):
        title = [gettext("Commit")]
        QBzrWindow.__init__(self, title, parent)
        self.restoreSize("commit", (540, 540))
        if dialog:
            flags = QtCore.Qt.Dialog | QtCore.Qt.WindowContextHelpButtonHint
        else:
            flags = QtCore.Qt.Window | QtCore.Qt.WindowContextHelpButtonHint
        self.setWindowFlags(flags)

        self.tree = tree
        self.basis_tree = self.tree.basis_tree()
        self.windows = []

        tree.lock_read()
        try:
            self.collect_info()
        finally:
            tree.unlock()

        # Get information about modified files
        files = []
        delta = self.tree.changes_from(self.basis_tree)
        for path, id_, kind in delta.added:
            marker = osutils.kind_marker(kind)
            ext = file_extension(path)
            files.append((gettext("added"), path+marker, ext, path, True))
        for path, id_, kind in delta.removed:
            marker = osutils.kind_marker(kind)
            ext = file_extension(path)
            files.append((gettext("removed"), path+marker, ext, path, True))
        for (oldpath, newpath, id_, kind,
            text_modified, meta_modified) in delta.renamed:
            marker = osutils.kind_marker(kind)
            ext = file_extension(newpath)
            if text_modified or meta_modified:
                changes = gettext("renamed and modified")
            else:
                changes = gettext("renamed")
            files.append((changes,
                          "%s%s => %s%s" % (oldpath, marker, newpath, marker),
                          ext, newpath, True))
        for path, id_, kind, text_modified, meta_modified in delta.modified:
            marker = osutils.kind_marker(kind)
            ext = file_extension(path)
            files.append((gettext("modified"), path+marker, ext, path, True))
        for entry in tree.unknowns():
            ext = file_extension(entry)
            files.append((gettext("non-versioned"), entry, ext, entry, False))

        # Build a word list for message completer
        words = []
        for status, name, ext, path, versioned in files:
            if not versioned:
                continue
            words.extend(os.path.split(path))
            if ext in _word_list_builders:
                try:
                    file = open(path, 'rt')
                    words.extend(_word_list_builders[ext](file))
                except EnvironmentError:
                    pass
        words = list(set(words))
        words.sort(lambda a, b: cmp(a.lower(), b.lower()))

        # To set focus on splitter below one need to pass
        # second argument to constructor: self.centralwidget
        # Try to be smart: if there is no saved message
        # then set focus on Edit Area; otherwise on OK button.
        if self.get_saved_message():
            splitter = QtGui.QSplitter(QtCore.Qt.Vertical)
        else:
            splitter = QtGui.QSplitter(QtCore.Qt.Vertical, self.centralwidget)

        groupbox = QtGui.QGroupBox(gettext("Message"), splitter)
        splitter.addWidget(groupbox)
        grid = QtGui.QGridLayout(groupbox)

        # Equivalent for 'bzr commit --message'
        self.message = TextEdit(groupbox)
        self.message.setToolTip(gettext("Enter the commit message"))
        completer = QtGui.QCompleter()
        completer.setModel(QtGui.QStringListModel(words, completer))
        self.message.setCompleter(completer)
        self.message.setAcceptRichText(False)
        self.restore_message()
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

        if self.is_bound:
            self.local_checkbox = QtGui.QCheckBox(gettext(
                "&Local commit in a bound branch"))
            self.local_checkbox.setToolTip(gettext(
                "Local commits are not pushed to the master branch "
                "until a normal commit is performed"))
            grid.addWidget(self.local_checkbox, 3, 0, 1, 2)

        # Display a list of pending merges
        if self.pending_merges:
            groupbox = QtGui.QGroupBox(gettext("Pending Merges"), splitter)
            splitter.addWidget(groupbox)

            pendingMergesWidget = QtGui.QTreeWidget(groupbox)
            pendingMergesWidget.setHeaderLabels(
                [gettext("Date"), gettext("Author"), gettext("Message")])
            header = pendingMergesWidget.header()
            header.resizeSection(0, 120)
            header.resizeSection(1, 190)
            self.connect(pendingMergesWidget,
                QtCore.SIGNAL("itemDoubleClicked(QTreeWidgetItem *, int)"),
                self.show_changeset)

            for merge in self.pending_merges:
                item = QtGui.QTreeWidgetItem(pendingMergesWidget)
                item.setText(0, format_timestamp(merge.timestamp))
                item.setText(1, get_apparent_author(merge))
                item.setText(2, merge.get_summary())
                item.setData(0, QtCore.Qt.UserRole + 1,
                             QtCore.QVariant(merge.revision_id))

            vbox = QtGui.QVBoxLayout(groupbox)
            vbox.addWidget(pendingMergesWidget)

        # Display the list of changed files
        groupbox = QtGui.QGroupBox(gettext("Changes"), splitter)
        splitter.addWidget(groupbox)

        self.filelist = QtGui.QTreeWidget(groupbox)
        self.filelist.setSelectionMode(QtGui.QAbstractItemView.ExtendedSelection)
        self.filelist.setSortingEnabled(True)
        self.filelist.setHeaderLabels(
            [gettext("File"), gettext("Extension"), gettext("Status")])
        self.filelist.header().resizeSection(0, 250)
        self.filelist.header().resizeSection(1, 70)
        self.filelist.setRootIsDecorated(False)
        self.connect(self.filelist,
                     QtCore.SIGNAL("itemDoubleClicked(QTreeWidgetItem *, int)"),
                     self.show_differences)

        self.filelist.setContextMenuPolicy(QtCore.Qt.ActionsContextMenu)
        self.connect(self.filelist,
                     QtCore.SIGNAL("itemSelectionChanged()"),
                     self.update_context_menu_actions)

        self.revert_action = QtGui.QAction(gettext("&Revert..."), self)
        self.connect(self.revert_action, QtCore.SIGNAL("triggered()"), self.revert_selected)
        self.filelist.addAction(self.revert_action)

        self.show_diff_action = QtGui.QAction(gettext("Show &Differences..."),
                                              self)
        self.connect(self.show_diff_action, QtCore.SIGNAL("triggered()"), self.show_differences)
        self.filelist.addAction(self.show_diff_action)

        vbox = QtGui.QVBoxLayout(groupbox)
        vbox.addWidget(self.filelist)

        hbox = QtGui.QVBoxLayout()
        self.show_nonversioned_checkbox = QtGui.QCheckBox(
            gettext("Show non-versioned files"))
        self.connect(self.show_nonversioned_checkbox, QtCore.SIGNAL("toggled(bool)"), self.show_nonversioned)
        hbox.addWidget(self.show_nonversioned_checkbox)
        vbox.addLayout(hbox)

        def in_selected_list(path):
            if not selected_list:
                return True
            if path in selected_list:
                return True
            for p in selected_list:
                if path.startswith(p):
                    return True
            return False

        self.unknowns = []
        self.item_to_file = {}
        for entry in files:
            status, name, ext, path, versioned = entry
            item = QtGui.QTreeWidgetItem(self.filelist)
            item.setText(0, name)
            item.setText(1, ext)
            item.setText(2, status)
            if not self.pending_merges:
                if versioned and in_selected_list(path):
                    item.setCheckState(0, QtCore.Qt.Checked)
                else:
                    item.setCheckState(0, QtCore.Qt.Unchecked)
            self.item_to_file[item] = entry
            if not versioned:
                self.unknowns.append(item)

        self.filelist.sortItems(0, QtCore.Qt.AscendingOrder)
        self.show_nonversioned(self.show_nonversioned_checkbox.isChecked())

        splitter.setStretchFactor(0, 3)
        splitter.setStretchFactor(1, 4)

        buttonbox = self.create_button_box(BTN_OK, BTN_CANCEL)

        vbox = QtGui.QVBoxLayout(self.centralwidget)
        vbox.addWidget(splitter)
        vbox.addWidget(buttonbox)

    def enableBugs(self, state):
        if state == QtCore.Qt.Checked:
            self.bugs.setEnabled(True)
            self.bugs.setFocus(QtCore.Qt.OtherFocusReason)
        else:
            self.bugs.setEnabled(False)

    def enableAuthor(self, state):
        if state == QtCore.Qt.Checked:
            self.author.setEnabled(True)
            self.author.setFocus(QtCore.Qt.OtherFocusReason)
        else:
            self.author.setEnabled(False)

    def parseBugs(self):
        fixes = unicode(self.bugs.text()).split()
        properties = []
        for fixed_bug in fixes:
            tokens = fixed_bug.split(':')
            if len(tokens) != 2:
                raise errors.BzrCommandError(
                    "Invalid bug '%s'. Must be in the form of 'tag:id'."
                    % fixed_bug)
            tag, bug_id = tokens
            try:
                bug_url = bugtracker.get_bug_url(tag, self.tree.branch, bug_id)
            except errors.UnknownBugTrackerAbbreviation:
                raise errors.BzrCommandError(
                    "Unrecognized bug '%s'." % fixed_bug)
            except errors.MalformedBugIdentifier:
                raise errors.BzrCommandError(
                    "Invalid bug identifier for '%s'." % fixed_bug)
            properties.append('%s fixed' % bug_url)
        return '\n'.join(properties)

    def get_saved_message(self):
        config = self.tree.branch.get_config()._get_branch_data_config()
        return config.get_user_option('qbzr_commit_message')

    def restore_message(self):
        message = self.get_saved_message()
        if message:
            self.message.setText(message)

    def save_message(self):
        message = unicode(self.message.toPlainText())
        if message:
            config = self.tree.branch.get_config()
            config.set_user_option('qbzr_commit_message', message)

    def clear_saved_message(self):
        config = self.tree.branch.get_config()
        # FIXME this should delete the config entry, not just set it to ''
        config.set_user_option('qbzr_commit_message', '')

    def accept(self):
        """Commit the changes."""

        message = unicode(self.message.toPlainText()).strip()
        if not message:
            button = QtGui.QMessageBox.warning(self,
                "QBzr - " + gettext("Commit"),
                gettext("Empty commit message. Do you really want to commit?"),
                QtGui.QMessageBox.Yes | QtGui.QMessageBox.No)
            if button == QtGui.QMessageBox.No:
                # don't commit, but don't close the window either
                return

        properties = {}

        if self.bugsCheckBox.checkState() == QtCore.Qt.Checked:
            try:
                bugs = self.parseBugs()
            except Exception, e:
                QtGui.QMessageBox.warning(self,
                    "QBzr - "+gettext("Commit"), str(e), QtGui.QMessageBox.Ok)
                return
            else:
                if bugs:
                    properties['bugs'] = bugs

        if self.authorCheckBox.checkState() == QtCore.Qt.Checked:
            author = unicode(self.author.text())
            author = re.sub('\s+', ' ', author).strip()
            if author:
                properties['author'] = author

        if not self.pending_merges:
            specific_files = []
            for i in range(self.filelist.topLevelItemCount()):
                item = self.filelist.topLevelItem(i)
                if item.checkState(0) == QtCore.Qt.Checked:
                    entry = self.item_to_file[item]
                    if not entry[4]:
                        self.tree.add(entry[3])
                    specific_files.append(entry[3])
        else:
            specific_files = None

        local = None
        if self.is_bound:
            local = self.local_checkbox.isChecked()

        try:
            self.tree.commit(message=message,
                             specific_files=specific_files,
                             reporter=ReportCommitToLog(),
                             allow_pointless=False,
                             revprops=properties,
                             local=local)
        except BzrError, e:
            self.save_message()
            QtGui.QMessageBox.warning(self,
                "QBzr - " + gettext("Commit"), str(e), QtGui.QMessageBox.Ok)
        else:
            self.clear_saved_message()

        self.close()

    def reject(self):
        """Reject the commit."""
        self.save_message()
        self.close()

    def show_changeset(self, item=None, column=None):
        repo = self.tree.branch.repository
        rev_id = str(item.data(0, QtCore.Qt.UserRole + 1).toString())
        rev_parent_id = repo.revision_parents(rev_id)[0]
        revs = [rev_parent_id, rev_id]
        tree1, tree2 = repo.revision_trees(revs)
        window = DiffWindow(tree1, tree2, custom_title="..".join(revs),
                            branch=self.tree.branch, parent=self)
        window.show()
        self.windows.append(window)

    def show_differences(self, items=None, column=None):
        """Show differences between the working copy and the last revision."""
        if items is None:
            items = self.filelist.selectedItems()
            if not items:
                return
            #item = items[0]

        if not isinstance(items, list):
            items = (items,)

        entries = [self.item_to_file[item][3] for item in items]
        if entries:
            window = DiffWindow(self.basis_tree,
                                self.tree,
                                specific_files=entries,
                                parent=self,
                                branch=self.tree.branch)
            window.show()
            self.windows.append(window)

    def show_nonversioned(self, state):
        """Show/hide non-versioned files."""
        state = not state
        for item in self.unknowns:
            item.setHidden(state)

    def revert_selected(self):
        """Revert the selected file."""
        items = self.filelist.selectedItems()
        if not items:
            return
        res = QtGui.QMessageBox.question(self,
            gettext("Revert"),
            gettext("Do you really want to revert the selected file(s)?"),
            QtGui.QMessageBox.Yes | QtGui.QMessageBox.No)
        if res == QtGui.QMessageBox.Yes:
            paths = [self.item_to_file[item][3] for item in items]
            try:
                self.tree.revert(paths, self.tree.branch.repository.revision_tree(self.tree.last_revision()))
            except BzrError, e:
                QtGui.QMessageBox.warning(self,
                    gettext("Revert"), str(e), QtGui.QMessageBox.Ok)
            else:
                for item in items:
                    index = self.filelist.indexOfTopLevelItem(item)
                    self.filelist.takeTopLevelItem(index)

    def update_context_menu_actions(self):
        contains_non_versioned = False
        files = (self.item_to_file[i] for i in self.filelist.selectedItems())
        for file in files:
            if not file[4]:
                contains_non_versioned = True
                break
        self.revert_action.setEnabled(not contains_non_versioned)
        self.show_diff_action.setEnabled(not contains_non_versioned)
