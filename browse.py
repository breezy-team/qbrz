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
from bzrlib.urlutils import local_path_from_url
from bzrlib.plugins.qbzr.i18n import _
from bzrlib.plugins.qbzr.util import QBzrWindow


class FileTreeWidget(QtGui.QTreeWidget):

    def __init__(self, window, *args):
        QtGui.QTreeWidget.__init__(self, *args)
        self.window = window

    def contextMenuEvent(self, event):
        self.window.context_menu.popup(event.globalPos())
        event.accept()


class BrowseWindow(QBzrWindow):

    def __init__(self, branch=None, parent=None):
        self.branch = branch
        self.location = local_path_from_url(branch.base)
        QBzrWindow.__init__(self,
            [_("Browse"), self.location], (780, 580), parent)

        vbox = QtGui.QVBoxLayout(self.centralwidget)

        hbox = QtGui.QHBoxLayout()
        hbox.addWidget(QtGui.QLabel(_("Location:")))
        self.location_edit = QtGui.QLineEdit()
        self.location_edit.setText(self.location)
        hbox.addWidget(self.location_edit, 7)
        hbox.addWidget(QtGui.QLabel(_("Revision:")))
        self.revision_edit = QtGui.QLineEdit()
        self.revision_edit.setText(str(self.branch.revno()))
        hbox.addWidget(self.revision_edit, 1)
        self.show_button = QtGui.QPushButton(_("Show"))
        self.show_button.setEnabled(False)
        hbox.addWidget(self.show_button, 0)
        vbox.addLayout(hbox)

        self.file_tree = FileTreeWidget(self)
        self.file_tree.setHeaderLabels(
            [_("Name"), _("Date"), _("Author"), _("Message")])

        self.context_menu = QtGui.QMenu(self.file_tree)
        self.context_menu.addAction(_("Show log..."))

        self.dir_icon = self.style().standardIcon(QtGui.QStyle.SP_DirIcon)
        self.file_icon = self.style().standardIcon(QtGui.QStyle.SP_FileIcon)

        self.items = []

        tree = self.branch.basis_tree()
        file_id = tree.path2id('.')
        if file_id is not None:
            revs = self.load_file_tree(tree.inventory[file_id], self.file_tree)
            revs = dict(zip(revs, self.branch.repository.get_revisions(list(revs))))
        else:
            revs = {}

        date = QtCore.QDateTime()
        for item, rev_id in self.items:
            rev = revs[rev_id]
            date.setTime_t(int(rev.timestamp))
            item.setText(1, date.toString(QtCore.Qt.LocalDate))
            item.setText(2, rev.committer)
            item.setText(3, rev.message.split("\n")[0])

        vbox.addWidget(self.file_tree)

        buttonbox = QtGui.QDialogButtonBox(
            QtGui.QDialogButtonBox.StandardButtons(
                QtGui.QDialogButtonBox.Close),
            QtCore.Qt.Horizontal,
            self.centralwidget)
        self.connect(buttonbox, QtCore.SIGNAL("rejected()"), self.close)
        vbox.addWidget(buttonbox)

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
    # XXX more complicated encoding support needed
    return output.getvalue().decode("UTF-8", "replace")
