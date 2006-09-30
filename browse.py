# -*- coding: utf-8 -*-
#
# QBzr - Qt frontend to Bazaar commands
# Copyright (C) 2006 Lukáš Lalinský <lalinsky@gmail.com>
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
from bzrlib.branch import Branch
from bzrlib.commands import Command, register_command
from bzrlib.urlutils import local_path_from_url


class FileTreeWidget(QtGui.QTreeWidget):

    def __init__(self, window, *args):
        QtGui.QTreeWidget.__init__(self, *args)
        self.window = window
    
    def contextMenuEvent(self, event):
        self.window.context_menu.popup(event.globalPos())
        event.accept()


class BrowseWindow(QtGui.QMainWindow):

    def __init__(self, branch=None, parent=None):
        QtGui.QMainWindow.__init__(self, parent)
        self.branch = branch

        title = u"QBzr - Browse - " + local_path_from_url(branch.base)
        self.setWindowTitle(title)

        icon = QtGui.QIcon()
        icon.addFile(":/bzr-16.png", QtCore.QSize(16, 16))
        icon.addFile(":/bzr-48.png", QtCore.QSize(48, 48))
        self.setWindowIcon(icon)
        self.resize(QtCore.QSize(780, 580).expandedTo(self.minimumSizeHint()))

        self.centralWidget = QtGui.QWidget(self)
        self.setCentralWidget(self.centralWidget)
        vbox = QtGui.QVBoxLayout(self.centralWidget)

        self.file_tree = FileTreeWidget(self, self.centralWidget)
        self.file_tree.setHeaderLabels([u"Name", u"Date", u"Author", u"Message"])

        self.context_menu = QtGui.QMenu(self.file_tree)
        self.context_menu.addAction("Show log...")

        self.dir_icon = QtGui.QIcon(":/folder.png")
        self.file_icon = QtGui.QIcon(":/text-x-generic.png")

        self.items = []

        tree = self.branch.basis_tree()
        file_id = tree.inventory.path2id('.')
        revs = self.load_file_tree(tree.inventory[file_id], self.file_tree)
        revs = dict(zip(revs, self.branch.repository.get_revisions(list(revs))))
        
        date = QtCore.QDateTime()
        for item, rev_id in self.items:
            rev = revs[rev_id]
            date.setTime_t(int(rev.timestamp))
            item.setText(1, date.toString(QtCore.Qt.LocalDate))
            item.setText(2, rev.committer)
            item.setText(3, rev.message.split("\n")[0])

        vbox.addWidget(self.file_tree)
        
        hbox = QtGui.QHBoxLayout()
        hbox.addStretch()
        self.closeButton = QtGui.QPushButton(u"&Close", self)
        self.connect(self.closeButton, QtCore.SIGNAL("clicked()"), self.close)
        hbox.addWidget(self.closeButton)
        vbox.addLayout(hbox)

    def load_file_tree(self, entry, parent_item):
        files, dirs = [], []
        revs = set()
        for name, child in entry.sorted_children():
            revs.add(child.revision)
            if child.kind == "directory":
                dirs.append(child)
            else:
                files.append(child)
        for child in dirs:
            item = QtGui.QTreeWidgetItem(parent_item)
            item.setIcon(0, self.dir_icon)
            item.setText(0, child.name)
            revs.update(self.load_file_tree(child, item))
            self.items.append((item, child.revision))
        for child in files:
            item = QtGui.QTreeWidgetItem(parent_item)
            item.setIcon(0, self.file_icon)
            item.setText(0, child.name)
            self.items.append((item, child.revision))
        return revs


def get_diff_trees(tree1, tree2, **kwargs):
    """Return unified diff between two trees as a string."""
    from bzrlib.diff import show_diff_trees
    output = StringIO()
    show_diff_trees(tree1, tree2, output, **kwargs)
    return output.getvalue().decode("UTF-8", "replace")


class cmd_qbrowse(Command):
    """Show differences in working tree in a Qt window.
    
    Otherwise, all changes for the tree are listed.
    """
    takes_args = ['location?']
    takes_options = ['revision']

    def run(self, revision=None, location=None):
        branch, path = Branch.open_containing(location)
        app = QtGui.QApplication(sys.argv)
        win = BrowseWindow(branch)
        win.show()
        app.exec_()


register_command(cmd_qbrowse)

