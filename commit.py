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

from bzrlib.errors import BzrError
from bzrlib.option import Option
from bzrlib.commands import Command, register_command
from bzrlib.commit import ReportCommitToLog
from bzrlib.workingtree import WorkingTree
from bzrlib.plugins.qbzr.diff import get_diff_trees, DiffWindow
from bzrlib.plugins.qbzr.util import QBzrWindow


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
        QBzrWindow.__init__(self, title, (540, 500), parent)

        self.tree = tree
        self.basis_tree = self.tree.basis_tree()
        self.windows = []

        # Get information about modified files
        files = []
        delta = self.tree.changes_from(self.basis_tree)
        for entry in delta.added:
            ext = os.path.splitext(entry[0])[1]
            files.append(("added", entry[0], ext, entry[0], True))
        for entry in delta.removed:
            ext = os.path.splitext(entry[0])[1]
            files.append(("removed", entry[0], ext, entry[0], True))
        for entry in delta.renamed:
            ext = os.path.splitext(entry[1])[1]
            files.append(("renamed", "%s => %s" % (entry[0], entry[1]), ext, entry[1], True))
        for entry in delta.modified:
            ext = os.path.splitext(entry[0])[1]
            files.append(("modified", entry[0], ext, entry[0], True))
        for entry in tree.unknowns():
            ext = os.path.splitext(entry)[1]
            files.append(("non-versioned", entry, ext, entry, False))

        # Build a word list for message completer
        words = []
        for status, name, ext, path, versioned in files:
            words.extend(os.path.split(path))
            if versioned and ext in _word_list_builders:
                try:
                    file = open(path, 'rt')
                except EnvironmentError:
                    pass
                words.extend(_word_list_builders[ext](file))
        words = list(set(words))
        words.sort(lambda a, b: cmp(a.lower(), b.lower()))

        splitter = QtGui.QSplitter(QtCore.Qt.Vertical, self.centralwidget)

        groupbox = QtGui.QGroupBox("Message", splitter)
        splitter.addWidget(groupbox)

        completer = QtGui.QCompleter()
        completer.setModel(QtGui.QStringListModel(words, completer))

        self.message = TextEdit(groupbox)
        self.message.setCompleter(completer)
        self.message.setAcceptRichText(False)

        vbox = QtGui.QVBoxLayout(groupbox)
        vbox.addWidget(self.message)

        groupbox = QtGui.QGroupBox("Changes made", splitter)
        splitter.addWidget(groupbox)

        self.filelist = QtGui.QTreeWidget(groupbox)
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
        self.connect(self.revert_action, QtCore.SIGNAL("activated()"), self.revert_selected)
        self.filelist.addAction(self.revert_action)

        self.show_diff_action = QtGui.QAction("Show &Differences...", self)
        self.connect(self.show_diff_action, QtCore.SIGNAL("activated()"), self.show_differences)
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
            if versioned and (path.startswith(path) or not path):
                item.setCheckState(0, QtCore.Qt.Checked)
            else:
                item.setCheckState(0, QtCore.Qt.Unchecked)
            self.item_to_file[item] = entry
            if not versioned:
                item.setHidden(not self.show_nonversioned_checkbox.isChecked())
                self.unknowns.append(item)

        splitter.setStretchFactor(0, 2)
        splitter.setStretchFactor(1, 3)

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

    def accept(self):
        """Commit the changes."""
        specific_files = []
        for i in range(self.filelist.topLevelItemCount()):
            item = self.filelist.topLevelItem(i)
            if item.checkState(0) == QtCore.Qt.Checked:
                entry = self.item_to_file[item]
                if not entry[4]:
                    self.tree.add(entry[3])
                specific_files.append(entry[3])
        try:
            self.tree.commit(message=unicode(self.message.toPlainText()),
                             specific_files=specific_files,
                             reporter=ReportCommitToLog(),
                             allow_pointless=False)
        except BzrError, e:
            QtGui.QMessageBox.warning(self, "QBzr - Commit", str(e), QtGui.QMessageBox.Ok)
        self.close()

    def reject(self):
        """Reject the commit."""
        self.close()

    def show_differences(self, item=None, column=None):
        """Show differences between the working copy and the last revision."""
        if item is None:
            items = self.filelist.selectedItems()
            if not items:
                return
            item = items[0]
        entry = self.item_to_file[item]
        if entry[4]:
            window = DiffWindow(self.basis_tree, self.tree, specific_files=(entry[3],), parent=self)
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
        item = items[0]
        path = self.item_to_file[item][3]
        button = QtGui.QMessageBox.question(self, "QBzr - Commit", "Do you really want to revert the selected file(s)?", QtGui.QMessageBox.StandardButtons(QtGui.QMessageBox.Ok | QtGui.QMessageBox.Cancel))
        if button == QtGui.QMessageBox.Ok:
            try:
                self.tree.revert([path], self.tree.branch.repository.revision_tree(self.tree.last_revision()))
            except BzrError, e:
                QtGui.QMessageBox.warning(self, "QBzr - Revert", str(e), QtGui.QMessageBox.Ok)
            else:
                index = self.filelist.indexOfTopLevelItem(item)
                self.filelist.takeTopLevelItem(index)

