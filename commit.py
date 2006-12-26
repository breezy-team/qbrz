# -*- coding: utf-8 -*-
#
# QBzr - Qt frontend to Bazaar commands
# Copyright (C) 2006 Lukáš Lalinský <lalinsky@gmail.com>
# Portions Copyright (C) 2006 Jelmer Vernooij <jelmer@samba.org> 
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

import sys
import os.path
from PyQt4 import QtCore, QtGui

from bzrlib.option import Option 
from bzrlib.commands import Command, register_command
from bzrlib.commit import ReportCommitToLog
from bzrlib.workingtree import WorkingTree
from bzrlib.plugins.qbzr.diff import get_diff_trees, DiffWindow
from bzrlib.plugins.qbzr.util import QBzrWindow

class CommitWindow(QBzrWindow):

    def __init__(self, tree, path, parent=None):
        title = ["Commit"]
        if path:
            title.append(path)
        QBzrWindow.__init__(self, title, (540, 500), parent)

        self.tree = tree
        self.basis_tree = self.tree.basis_tree()
        self.windows = []

        splitter = QtGui.QSplitter(QtCore.Qt.Vertical, self.centralwidget)

        groupbox = QtGui.QGroupBox("Message", splitter)
        splitter.addWidget(groupbox)

        self.message = QtGui.QTextEdit(groupbox)

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

        vbox = QtGui.QVBoxLayout(groupbox)
        vbox.addWidget(self.filelist)

        basis_tree = self.tree.basis_tree()
        delta = self.tree.changes_from(basis_tree)

        files = []
        for entry in delta.added:
            files.append(("added", entry[0], entry[0], True))
        for entry in delta.removed:
            files.append(("removed", entry[0], entry[0], True))
        for entry in delta.renamed:
            files.append(("renamed", "%s => %s" % (entry[0], entry[1]),
                          entry[1], True))
        for entry in delta.modified:
            files.append(("modified", entry[0], entry[0], True))
        for entry in tree.unknowns():
            files.append(("non-versioned", entry, entry, False))

        self.item_to_file = {}
        for entry in files:
            item = QtGui.QTreeWidgetItem(self.filelist)
            item.setText(0, entry[1])
            item.setText(1, os.path.splitext(entry[2])[1])
            item.setText(2, entry[0])
            if (entry[3] and not path) or (path == entry[1]):
                item.setCheckState(0, QtCore.Qt.Checked)
            else:
                item.setCheckState(0, QtCore.Qt.Unchecked)
            self.item_to_file[item] = entry

        splitter.setStretchFactor(0, 2)
        splitter.setStretchFactor(1, 3)

        buttonbox = QtGui.QDialogButtonBox(
            QtGui.QDialogButtonBox.StandardButtons(
                QtGui.QDialogButtonBox.Ok |
                QtGui.QDialogButtonBox.Cancel),
            QtCore.Qt.Horizontal,
            self)
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
        """Accept the commit."""
        specific_files = [] 
        for i in range(self.filelist.topLevelItemCount()):
            item = self.filelist.topLevelItem(i)
            if item.checkState(0) == QtCore.Qt.Checked:
                entry = self.item_to_file[item]
                if not entry[3]:
                    self.tree.add(entry[2])
                specific_files.append(entry[2])
        self.tree.commit(message=unicode(self.message.toPlainText()),
                         specific_files=specific_files,
                         reporter=ReportCommitToLog())
        self.close()

    def reject(self):
        """Reject the commit."""
        self.close()

    def show_differences(self, item, column):
        """Show differences between the working copy and the last revision."""
        entry = self.item_to_file[item]
        if entry[3]:
            window = DiffWindow(self.basis_tree, self.tree,
                                specific_files=(entry[2],), parent=self)
            window.show()
            self.windows.append(window)
