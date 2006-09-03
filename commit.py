# -*- coding: utf-8 -*-
#
# QBzr - Qt frontend to Bazaar commands
# Copyright (C) 2006 Lukáš Lalinský <lalinsky@gmail.com>
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

import sys
from PyQt4 import QtCore, QtGui
from bzrlib.commands import Command, register_command
from bzrlib.errors import NotVersionedError, BzrCommandError, NoSuchFile
from bzrlib.workingtree import WorkingTree 

class CommitDialog(QtGui.QDialog):

    def __init__(self, changes, path, parent=None):
        QtGui.QDialog.__init__(self, parent)

        self.setWindowTitle(u"Bazaar - Commit - %s" % (path,))
        icon = QtGui.QIcon()
        icon.addFile(":/bzr-16.png", QtCore.QSize(16, 16))
        icon.addFile(":/bzr-48.png", QtCore.QSize(48, 48))
        self.setWindowIcon(icon)
        self.resize(QtCore.QSize(501, 364).expandedTo(self.minimumSizeHint()))

        self.vboxlayout = QtGui.QVBoxLayout(self)

        splitter = QtGui.QSplitter(QtCore.Qt.Vertical, self)

        groupBox = QtGui.QGroupBox(u"Message", splitter)
        splitter.addWidget(groupBox)

        self.commitMessageEdit = QtGui.QTextEdit(groupBox)

        vbox1 = QtGui.QVBoxLayout(groupBox)
        vbox1.addWidget(self.commitMessageEdit)

        groupBox = QtGui.QGroupBox(u"Changes made", splitter)
        splitter.addWidget(groupBox)

        self.changesList = QtGui.QTreeWidget(groupBox)
        self.changesList.setHeaderLabels([u"File", u"Extension", u"Status"])
        self.changesList.setRootIsDecorated(False)
        
        vbox1 = QtGui.QVBoxLayout(groupBox)
        vbox1.addWidget(self.changesList)

        for change in changes:
            item = QtGui.QTreeWidgetItem(self.changesList)
            item.setText(0, change[1])
            item.setText(1, change[1][change[1].rfind(u"."):])
            item.setText(2, change[2])
            item.setCheckState(0, QtCore.Qt.Checked)
        
        self.vboxlayout.addWidget(splitter)
        
        self.hboxlayout = QtGui.QHBoxLayout()
        self.hboxlayout.addStretch()

        self.okButton = QtGui.QPushButton(u"OK", self)
        self.hboxlayout.addWidget(self.okButton)

        self.cancelButton = QtGui.QPushButton(u"Cancel", self)
        self.hboxlayout.addWidget(self.cancelButton)
        
        self.vboxlayout.addLayout(self.hboxlayout)
        
        self.connect(self.okButton, QtCore.SIGNAL("clicked()"), self.accept)
        self.connect(self.cancelButton, QtCore.SIGNAL("clicked()"), self.reject)

    def accept(self):
        self.commitMessage = unicode(self.commitMessageEdit.toPlainText())
        self.specificFiles = [] 
        for i in range(self.changesList.topLevelItemCount()):
            item = self.changesList.topLevelItem(i)
            if item.checkState(0) == QtCore.Qt.Checked:
                self.specificFiles.append(unicode(item.text(0)))
        QtGui.QDialog.accept(self)
        
class cmd_qcommit(Command):
    """Qt commit dialog

    Graphical user interface for committing revisions"""
    
    takes_args = []
    takes_options = []

    def run(self, filename=None):
        from bzrlib.commit import Commit
        from bzrlib.errors import (BzrCommandError, PointlessCommit, ConflictsInTree, 
           StrictCommitFailed)

        (wt, path) = WorkingTree.open_containing(filename)
        branch = wt.branch

        file_id = wt.path2id(path)

        if file_id is None:
            raise NotVersionedError(filename)

        tree = wt
        self.old_tree = tree.branch.repository.revision_tree(tree.branch.last_revision())
        self.delta = tree.changes_from(self.old_tree) 

        self.file_store = []

        for path, _, _ in self.delta.added:
            self.file_store.append((True, path, u"Added"))

        for path, _, _ in self.delta.removed:
            self.file_store.append((True, path, u"Removed"))

        for oldpath, _, _, _, _, _ in self.delta.renamed:
            self.file_store.append((True, oldpath, u"Renamed"))

        for path, _, _, _, _ in self.delta.modified:
            self.file_store.append((True, path, u"Modified"))

        app = QtGui.QApplication(sys.argv)
        dialog = CommitDialog(self.file_store, path)
        if dialog.exec_():
            Commit().commit(working_tree=wt,message=dialog.commitMessage,
                specific_files=dialog.specificFiles)

register_command(cmd_qcommit)
