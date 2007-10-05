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
from bzrlib.plugins.qbzr.diff import DiffWindow
from bzrlib.plugins.qbzr.util import QBzrWindow, get_apparent_author


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

        if not isShortcut and (hasModifier or e.text().isEmpty() or completionPrefix.length() < 2 or self.eow.contains(e.text().right(1))):
            c.popup().hide()
            return

        if completionPrefix != c.completionPrefix():
            c.setCompletionPrefix(completionPrefix)
            c.popup().setCurrentIndex(c.completionModel().index(0, 0))

        cr = self.cursorRect()
        cr.setWidth(c.popup().sizeHintForColumn(0) + c.popup().verticalScrollBar().sizeHint().width())
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

    def __init__(self, tree, path, parent=None):
        title = ["Commit"]
        if path:
            title.append(path)
        QBzrWindow.__init__(self, title, (540, 540), parent)
        self.setWindowFlags(QtCore.Qt.WindowContextHelpButtonHint)

        self.tree = tree
        self.basis_tree = self.tree.basis_tree()
        self.windows = []

        # Get information about modified files
        files = []
        delta = self.tree.changes_from(self.basis_tree)
        for path, _, kind in delta.added:       # here and below _ is file id
            marker = osutils.kind_marker(kind)
            ext = os.path.splitext(path)[1]
            files.append(("added", path+marker, ext, path, True))
        for path, _, kind in delta.removed:
            marker = osutils.kind_marker(kind)
            ext = os.path.splitext(path)[1]
            files.append(("removed", path+marker, ext, path, True))
        for (oldpath, newpath, _, kind,
            text_modified, meta_modified) in delta.renamed:
            marker = osutils.kind_marker(kind)
            ext = os.path.splitext(newpath)[1]
            if text_modified or meta_modified:
                changes = "renamed and modified"
            else:
                changes = "renamed"
            files.append((changes,
                          "%s%s => %s%s" % (oldpath, marker, newpath, marker),
                          ext, newpath, True))
        for path, _, kind, text_modified, meta_modified in delta.modified:
            marker = osutils.kind_marker(kind)
            ext = os.path.splitext(path)[1]
            files.append(("modified", path+marker, ext, path, True))
        for entry in tree.unknowns():
            ext = os.path.splitext(entry)[1]
            files.append(("non-versioned", entry, ext, entry, False))

        branch = tree.branch
        parents = tree.get_parent_ids()
        pending_merges = None
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
            pending_merges = branch.repository.get_revisions(parents[1:])
            for i, merge in enumerate(pending_merges):
                ignore.add(merge.revision_id)
                inner_merges = branch.repository.get_ancestry(merge.revision_id)
                inner_merges.pop(0)
                for inner_merge in inner_merges:
                    if inner_merge in ignore:
                        continue
                    ignore.add(inner_merge)
                    inner_merge = branch.repository.get_revision(inner_merge)
                    pending_merges.insert(i + 1, inner_merge)
            #for rev in pending_merges:
            #    print rev.committer, rev.get_summary()
        self.has_pending_merges = bool(pending_merges)

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

        splitter = QtGui.QSplitter(QtCore.Qt.Vertical, self.centralwidget)

        groupbox = QtGui.QGroupBox("Message", splitter)
        splitter.addWidget(groupbox)
        grid = QtGui.QGridLayout(groupbox)

        # Equivalent for 'bzr commit --message'
        self.message = TextEdit(groupbox)
        self.message.setToolTip("Enter the commit message")
        completer = QtGui.QCompleter()
        completer.setModel(QtGui.QStringListModel(words, completer))
        self.message.setCompleter(completer)
        self.message.setAcceptRichText(False)
        grid.addWidget(self.message, 0, 0, 1, 2)

        # Equivalent for 'bzr commit --fixes'
        self.bugsCheckBox = QtGui.QCheckBox("&Fixed bugs:")
        self.bugsCheckBox.setToolTip("Set the IDs of bugs fixed by "
                                     "this commit")
        self.bugs = QtGui.QLineEdit()
        self.bugs.setToolTip("Enter the list of bug IDs in format "
                             "<i>tag:id</i> separated by a space, "
                             "e.g. <i>project:123 project:765</i>")
        self.bugs.setEnabled(False)
        self.connect(self.bugsCheckBox, QtCore.SIGNAL("stateChanged(int)"),
                     self.enableBugs)
        grid.addWidget(self.bugsCheckBox, 1, 0)
        grid.addWidget(self.bugs, 1, 1)

        # Equivalent for 'bzr commit --author'
        self.authorCheckBox = QtGui.QCheckBox("&Author:")
        self.authorCheckBox.setToolTip("Set the author of this change, if"
                                       " it's different from the committer")
        self.author = QtGui.QLineEdit()
        self.author.setToolTip("Enter the author's name, e.g. <i>John Doe "
                               "&lt;jdoe@example.com&gt;</i>")
        self.author.setEnabled(False)
        self.connect(self.authorCheckBox, QtCore.SIGNAL("stateChanged(int)"),
                     self.enableAuthor)
        grid.addWidget(self.authorCheckBox, 2, 0)
        grid.addWidget(self.author, 2, 1)

        # Display a list of pending merges
        if pending_merges:
            groupbox = QtGui.QGroupBox("Pending Merges", splitter)
            splitter.addWidget(groupbox)

            pendingMergesWidget = QtGui.QTreeWidget(groupbox)
            pendingMergesWidget.setHeaderLabels(
                ["Date", "Author", "Message"])
            header = pendingMergesWidget.header()
            header.resizeSection(0, 120)
            header.resizeSection(1, 190)

            date = QtCore.QDateTime()
            for merge in pending_merges:
                item = QtGui.QTreeWidgetItem(pendingMergesWidget)
                date.setTime_t(int(merge.timestamp))
                item.setText(0, date.toString(QtCore.Qt.LocalDate))
                item.setText(1, get_apparent_author(merge))
                item.setText(2, merge.get_summary())

            vbox = QtGui.QVBoxLayout(groupbox)
            vbox.addWidget(pendingMergesWidget)

        # Display the list of changed files
        groupbox = QtGui.QGroupBox("Changes", splitter)
        splitter.addWidget(groupbox)

        self.filelist = QtGui.QTreeWidget(groupbox)
        self.filelist.setSelectionMode(QtGui.QAbstractItemView.ExtendedSelection);
        self.filelist.setSortingEnabled(True)
        self.filelist.setHeaderLabels(["File", "Extension", "Status"])
        self.filelist.header().resizeSection(0, 250)
        self.filelist.header().resizeSection(1, 70)
        self.filelist.setRootIsDecorated(False)
        self.connect(self.filelist,
                     QtCore.SIGNAL("itemDoubleClicked(QTreeWidgetItem *, int)"),
                     self.show_differences)

        self.filelist.setContextMenuPolicy(QtCore.Qt.ActionsContextMenu)

        self.revert_action = QtGui.QAction("&Revert...", self)
        self.connect(self.revert_action, QtCore.SIGNAL("triggered()"), self.revert_selected)
        self.filelist.addAction(self.revert_action)

        self.show_diff_action = QtGui.QAction("Show &Differences...", self)
        self.connect(self.show_diff_action, QtCore.SIGNAL("triggered()"), self.show_differences)
        self.filelist.addAction(self.show_diff_action)

        vbox = QtGui.QVBoxLayout(groupbox)
        vbox.addWidget(self.filelist)

        hbox = QtGui.QVBoxLayout()
        self.show_nonversioned_checkbox = QtGui.QCheckBox("Show non-versioned files")
        self.connect(self.show_nonversioned_checkbox, QtCore.SIGNAL("toggled(bool)"), self.show_nonversioned)
        hbox.addWidget(self.show_nonversioned_checkbox)
        vbox.addLayout(hbox)

        self.unknowns = []
        self.item_to_file = {}
        for entry in files:
            status, name, ext, path, versioned = entry
            item = QtGui.QTreeWidgetItem(self.filelist)
            item.setText(0, name)
            item.setText(1, ext)
            item.setText(2, status)
            if not self.has_pending_merges:
                if versioned and (path.startswith(path) or not path):
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

        buttonbox = QtGui.QDialogButtonBox(
            QtGui.QDialogButtonBox.StandardButtons(
                QtGui.QDialogButtonBox.Ok |
                QtGui.QDialogButtonBox.Cancel),
            QtCore.Qt.Horizontal,
            self.centralwidget)
        self.connect(buttonbox, QtCore.SIGNAL("accepted()"), self.accept)
        self.connect(buttonbox, QtCore.SIGNAL("rejected()"), self.reject)

        vbox = QtGui.QVBoxLayout(self.centralwidget)
        vbox.addWidget(splitter)
        vbox.addWidget(buttonbox)

    def closeEvent(self, event):
        for window in self.windows:
            window.close()
        event.accept()

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

    def accept(self):
        """Commit the changes."""

        properties = {}

        if self.bugsCheckBox.checkState() == QtCore.Qt.Checked:
            try:
                bugs = self.parseBugs()
            except Exception, e:
                QtGui.QMessageBox.warning(self,
                    "QBzr - Commit", str(e), QtGui.QMessageBox.Ok)
                return
            else:
                if bugs:
                    properties['bugs'] = bugs

        if self.authorCheckBox.checkState() == QtCore.Qt.Checked:
            author = unicode(self.author.text())
            if author:
                properties['author'] = author

        if not self.has_pending_merges:
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

        try:
            self.tree.commit(message=unicode(self.message.toPlainText()),
                             specific_files=specific_files,
                             reporter=ReportCommitToLog(),
                             allow_pointless=False,
                             revprops=properties)
        except BzrError, e:
            QtGui.QMessageBox.warning(self, "QBzr - Commit", str(e), QtGui.QMessageBox.Ok)

        self.close()

    def reject(self):
        """Reject the commit."""
        self.close()

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
        button = QtGui.QMessageBox.question(self, "QBzr - Commit", "Do you really want to revert the selected file(s)?", QtGui.QMessageBox.StandardButtons(QtGui.QMessageBox.Ok | QtGui.QMessageBox.Cancel))
        if button == QtGui.QMessageBox.Ok:
            paths = [self.item_to_file[item][3] for item in items]
            try:
                self.tree.revert(paths, self.tree.branch.repository.revision_tree(self.tree.last_revision()))
            except BzrError, e:
                QtGui.QMessageBox.warning(self, "QBzr - Revert", str(e), QtGui.QMessageBox.Ok)
            else:
                for item in items:
                    index = self.filelist.indexOfTopLevelItem(item)
                    self.filelist.takeTopLevelItem(index)

