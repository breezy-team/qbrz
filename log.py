# -*- coding: utf-8 -*-
#
# QBzr - Qt frontend to Bazaar commands
# Copyright (C) 2006 Lukáš Lalinský <lalinsky@gmail.com>
# Porions Copyright (C) 2004, 2005, 2006 by Canonical Ltd 
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
from PyQt4 import QtCore, QtGui
from bzrlib.bzrdir import BzrDir
from bzrlib.commands import Command, register_command
from bzrlib.errors import NotVersionedError, BzrCommandError, NoSuchFile
from bzrlib.plugins.qbzr.diff import DiffWindow

class LogWindow(QtGui.QMainWindow):

    def __init__(self, branch, location, parent=None):
        QtGui.QMainWindow.__init__(self, parent)

        if location:
            self.setWindowTitle(u"QBzr - Log - %s" % location)
        else:
            self.setWindowTitle(u"QBzr - Log")
        icon = QtGui.QIcon()
        icon.addFile(":/bzr-16.png", QtCore.QSize(16, 16))
        icon.addFile(":/bzr-48.png", QtCore.QSize(48, 48))
        self.setWindowIcon(icon)
        self.resize(QtCore.QSize(710, 580).expandedTo(self.minimumSizeHint()))

        self.centralWidget = QtGui.QWidget(self)
        self.setCentralWidget(self.centralWidget)
        self.vboxlayout = QtGui.QVBoxLayout(self.centralWidget)

        splitter = QtGui.QSplitter(QtCore.Qt.Vertical)

        groupBox = QtGui.QGroupBox(u"Log", splitter)
        splitter.addWidget(groupBox)

        self.changesList = QtGui.QTreeWidget(groupBox)
        self.changesList.setHeaderLabels([u"Rev", u"Date", u"Author", u"Message"])
        self.changesList.setRootIsDecorated(False)
        header = self.changesList.header()
        header.resizeSection(0, 30)
        header.resizeSection(1, 110)
        header.resizeSection(2, 190)
        self.connect(self.changesList, QtCore.SIGNAL("itemSelectionChanged()"), self.update_selection)
        
        self.connect(self.changesList,
                     QtCore.SIGNAL("itemDoubleClicked(QTreeWidgetItem *, int)"),
                     self.show_differences)
        
        vbox1 = QtGui.QVBoxLayout(groupBox)
        vbox1.addWidget(self.changesList)

        self.item_to_rev = {}
        revno = 1
        revs = branch.repository.get_revisions(branch.revision_history())
        for rev in reversed(revs):
            item = QtGui.QTreeWidgetItem(self.changesList)
            item.setText(0, str(revno))
            date = QtCore.QDateTime()
            date.setTime_t(int(rev.timestamp))
            item.setText(1, date.toString(QtCore.Qt.LocalDate))
            item.setText(2, rev.committer)
            item.setText(3, rev.message.split("\n")[0])
            self.item_to_rev[item] = rev
            rev.revno = revno
            revno += 1

        self.branch = branch
        self.revs = revs

        groupBox = QtGui.QGroupBox(u"Details", splitter)
        splitter.addWidget(groupBox)

        splitter.setStretchFactor(0, 5)
        splitter.setStretchFactor(1, 1)

        gridLayout = QtGui.QGridLayout(groupBox)
        gridLayout.setColumnStretch(0, 0)
        gridLayout.setColumnStretch(1, 3)
        gridLayout.setColumnStretch(2, 1)

        gridLayout.addWidget(QtGui.QLabel(u"Revision:", groupBox), 0, 0)
        self.revisionEdit = QtGui.QLineEdit(u"", groupBox)
        self.revisionEdit.setReadOnly(True)
        gridLayout.addWidget(self.revisionEdit, 0, 1)

        gridLayout.addWidget(QtGui.QLabel(u"Parents:", groupBox), 1, 0)
        self.parentsEdit = QtGui.QLineEdit(u"", groupBox)
        self.parentsEdit.setReadOnly(True)
        gridLayout.addWidget(self.parentsEdit, 1, 1)

        gridLayout.addWidget(QtGui.QLabel(u"Message:", groupBox), 2, 0)
        self.messageEdit = QtGui.QTextEdit(u"", groupBox)
        self.messageEdit.setReadOnly(True)
        self.messageDocument = QtGui.QTextDocument()
        self.messageEdit.setDocument(self.messageDocument)
        gridLayout.addWidget(self.messageEdit, 2, 1)

        self.fileList = QtGui.QListWidget(groupBox)
        gridLayout.addWidget(self.fileList, 0, 2, 3, 1)
        
        self.vboxlayout.addWidget(splitter)
        
        self.hboxlayout = QtGui.QHBoxLayout()
        self.hboxlayout.addStretch()

        self.closeButton = QtGui.QPushButton(u"&Close", self)
        self.hboxlayout.addWidget(self.closeButton)

        self.vboxlayout.addLayout(self.hboxlayout)
        
        self.connect(self.closeButton, QtCore.SIGNAL("clicked()"), self.close)
        self.windows = []

    def closeEvent(self, event):
        for window in self.windows:
            window.close()
        event.accept()
        
    def anchorClicked(self, url):
        print url

    def update_selection(self):
        item = self.changesList.selectedItems()[0]
        rev = self.item_to_rev[item]

        self.revisionEdit.setText(rev.revision_id)
        self.parentsEdit.setText(u", ".join(rev.parent_ids))
        self.messageDocument.setPlainText(rev.message)

        self.fileList.clear()

        tree1 = self.branch.repository.revision_tree(rev.revision_id)
        index = self.revs.index(rev)
        if not index:
            revision_id = None
        else:
            revision_id = self.revs[index-1].revision_id
        tree2 = self.branch.repository.revision_tree(revision_id)
        delta = tree1.changes_from(tree2)

        for path, _, _ in delta.added:
            item = QtGui.QListWidgetItem(path, self.fileList)
            item.setTextColor(QtGui.QColor("blue"))
            
        for path, _, _, _, _ in delta.modified:
            item = QtGui.QListWidgetItem(path, self.fileList)
            
        for path, _, _ in delta.removed:
            item = QtGui.QListWidgetItem(path, self.fileList)
            item.setTextColor(QtGui.QColor("red"))
            
        for oldpath, newpath, _, _, _, _ in delta.renamed:
            item = QtGui.QListWidgetItem("%s => %s" % (oldpath, newpath), self.fileList)
            item.setTextColor(QtGui.QColor("purple"))
        
    def show_differences(self, item, column):
        """Show differences between the working copy and the last revision."""
        rev = self.item_to_rev[item]
        tree1 = self.branch.repository.revision_tree(rev.revision_id)
        index = self.revs.index(rev)
        if not index:
            revision_id = None
        else:
            revision_id = self.revs[index-1].revision_id
        tree2 = self.branch.repository.revision_tree(revision_id)
        window = DiffWindow(tree2, tree1, custom_title="#%d" % rev.revno)
        window.show()
        self.windows.append(window)

class cmd_qlog(Command):
    """Show log of a branch, file, or directory in a Qt window.

    By default show the log of the branch containing the working directory."""

    takes_args = ['location?']
    takes_options = []

    def run(self, location=None):
        file_id = None
        if location:
            dir, path = BzrDir.open_containing(location)
            branch = dir.open_branch()
            if path:
                try:
                    inv = dir.open_workingtree().inventory
                except (errors.NotBranchError, errors.NotLocalUrl):
                    inv = branch.basis_tree().inventory
                file_id = inv.path2id(path)
        else:
            dir, path = BzrDir.open_containing('.')
            branch = dir.open_branch()

        app = QtGui.QApplication(sys.argv)
        window = LogWindow(branch, location)
        window.show()
        app.exec_()

register_command(cmd_qlog)
