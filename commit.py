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
from bzrlib.errors import NotVersionedError, BzrCommandError, NoSuchFile
from bzrlib.workingtree import WorkingTree
from bzrlib.plugins.qbzr.diff import get_diff_trees, DiffWindow

class CommitDialog(QtGui.QDialog):

    def __init__(self, tree, path, parent=None):
        QtGui.QDialog.__init__(self, parent)

        self.tree = tree
        self.basis_tree = self.tree.basis_tree()

        title = "QBzr - Commit"
        if path:
            title += " - " + path 
        self.setWindowTitle(title)
        icon = QtGui.QIcon()
        icon.addFile(":/bzr-16.png", QtCore.QSize(16, 16))
        icon.addFile(":/bzr-48.png", QtCore.QSize(48, 48))
        self.setWindowIcon(icon)
        self.resize(QtCore.QSize(501, 364).expandedTo(self.minimumSizeHint()))

        self.vboxlayout = QtGui.QVBoxLayout(self)

        splitter = QtGui.QSplitter(QtCore.Qt.Vertical, self)

        groupBox = QtGui.QGroupBox(u"Message", splitter)
        splitter.addWidget(groupBox)

        self.messageEdit = QtGui.QTextEdit(groupBox)

        vbox1 = QtGui.QVBoxLayout(groupBox)
        vbox1.addWidget(self.messageEdit)

        groupBox = QtGui.QGroupBox(u"Changes made", splitter)
        splitter.addWidget(groupBox)

        self.changed_filesList = QtGui.QTreeWidget(groupBox)
        self.changed_filesList.setHeaderLabels([u"File", u"Extension",
                                                u"Status"])
        self.changed_filesList.setRootIsDecorated(False)
        self.connect(self.changed_filesList,
                     QtCore.SIGNAL("itemDoubleClicked(QTreeWidgetItem *, int)"),
                     self.show_differences)
        
        vbox1 = QtGui.QVBoxLayout(groupBox)
        vbox1.addWidget(self.changed_filesList)

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
            item = QtGui.QTreeWidgetItem(self.changed_filesList)
            item.setText(0, entry[1])
            item.setText(1, os.path.splitext(entry[2])[1])
            item.setText(2, entry[0])
            if entry[3]:
                item.setCheckState(0, QtCore.Qt.Checked)
            else:
                item.setCheckState(0, QtCore.Qt.Unchecked)
            self.item_to_file[item] = entry

        self.vboxlayout.addWidget(splitter)

        self.hboxlayout = QtGui.QHBoxLayout()
        self.hboxlayout.addStretch()

        self.okButton = QtGui.QPushButton(u"&OK", self)
        self.hboxlayout.addWidget(self.okButton)

        self.cancelButton = QtGui.QPushButton(u"&Cancel", self)
        self.hboxlayout.addWidget(self.cancelButton)
        
        self.vboxlayout.addLayout(self.hboxlayout)
        
        self.connect(self.okButton, QtCore.SIGNAL("clicked()"), self.accept)
        self.connect(self.cancelButton, QtCore.SIGNAL("clicked()"), self.reject)
        self.windows = []

    def closeEvent(self, event):
        for window in self.windows:
            window.close()
        event.accept()
        
    def accept(self):
        self.message = unicode(self.messageEdit.toPlainText())
        self.specific_files = [] 
        for i in range(self.changed_filesList.topLevelItemCount()):
            item = self.changed_filesList.topLevelItem(i)
            if item.checkState(0) == QtCore.Qt.Checked:
                entry = self.item_to_file[item]
                if not entry[3]:
                    self.tree.add(entry[2])
                self.specific_files.append(entry[2])
        QtGui.QDialog.accept(self)

    def show_differences(self, item, column):
        """Show differences between the working copy and the last revision."""
        entry = self.item_to_file[item]
        if entry[3]:
            window = DiffWindow(self.basis_tree, self.tree,
                                specific_files=(entry[2],))
            window.show()
            self.windows.append(window)

class cmd_qcommit(Command):
    """Qt commit dialog

    Graphical user interface for committing revisions"""

    takes_args = ['filename?']
    takes_options = [
                     Option('unchanged',
                            help='commit even if nothing has changed'), 
                    ]

    def run(self, filename=None, unchanged=False):
        from bzrlib.commit import ReportCommitToLog
        from bzrlib.errors import BzrCommandError, PointlessCommit, \
            ConflictsInTree, StrictCommitFailed

        tree, filename = WorkingTree.open_containing(filename)

        app = QtGui.QApplication(sys.argv)
        dialog = CommitDialog(tree, filename)
        if dialog.exec_():
            tree.commit(message=dialog.message,
                        specific_files=dialog.specific_files,
                        allow_pointless=unchanged,
                        reporter=ReportCommitToLog())

register_command(cmd_qcommit)
