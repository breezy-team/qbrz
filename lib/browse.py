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
from time import clock
from PyQt4 import QtCore, QtGui
from bzrlib import (
    osutils,
    errors,
    )
from bzrlib.branch import Branch
from bzrlib.osutils import pathjoin
from bzrlib.revisionspec import RevisionSpec

from bzrlib.plugins.qbzr.lib.cat import QBzrCatWindow
from bzrlib.plugins.qbzr.lib.annotate import AnnotateWindow
from bzrlib.plugins.qbzr.lib.i18n import gettext
from bzrlib.plugins.qbzr.lib.log import LogWindow
from bzrlib.plugins.qbzr.lib.util import (
    BTN_CLOSE,
    QBzrWindow,
    ThrobberWidget,
    extract_name,
    format_timestamp,
    get_set_encoding,
    url_for_display,
    )


class FileTreeWidget(QtGui.QTreeWidget):

    def __init__(self, window, *args):
        QtGui.QTreeWidget.__init__(self, *args)
        self.window = window

    def contextMenuEvent(self, event):
        self.window.context_menu.popup(event.globalPos())
        event.accept()


class BrowseWindow(QBzrWindow):

    NAME, DATE, AUTHOR, REV, MESSAGE = range(5)     # indices of columns in the window

    def __init__(self, branch=None, location=None, revision=None,
                 revision_id=None, revision_spec=None, parent=None):
        if branch:
            self.branch = branch
            self.location = url_for_display(branch.base)
        else:
            self.branch = None
            if location is None:
                location = osutils.getcwd()
            self.location = location
        
        self.revision_id = revision_id
        self.revision_spec = revision_spec
        self.revision = revision
        
        QBzrWindow.__init__(self,
            [gettext("Browse"), self.location], parent)
        self.restoreSize("browse", (780, 580))

        vbox = QtGui.QVBoxLayout(self.centralwidget)
        
        self.throbber = ThrobberWidget(self)
        vbox.addWidget(self.throbber)

        hbox = QtGui.QHBoxLayout()
        hbox.addWidget(QtGui.QLabel(gettext("Location:")))
        self.location_edit = QtGui.QLineEdit()
        self.location_edit.setReadOnly(True)
        self.location_edit.setText(self.location)
        hbox.addWidget(self.location_edit, 7)
        hbox.addWidget(QtGui.QLabel(gettext("Revision:")))
        self.revision_edit = QtGui.QLineEdit()
        hbox.addWidget(self.revision_edit, 1)
        self.show_button = QtGui.QPushButton(gettext("Show"))
        self.connect(self.show_button, QtCore.SIGNAL("clicked()"), self.reload_tree)
        hbox.addWidget(self.show_button, 0)
        vbox.addLayout(hbox)

        self.file_tree = FileTreeWidget(self)
        self.file_tree.setHeaderLabels([
            gettext("Name"),
            gettext("Date"),
            gettext("Author"),
            gettext("Rev"),
            gettext("Message"),
            ])
        header = self.file_tree.header()
        header.setResizeMode(self.NAME, QtGui.QHeaderView.ResizeToContents)
        header.setResizeMode(self.REV, QtGui.QHeaderView.ResizeToContents)

        self.context_menu = QtGui.QMenu(self.file_tree)
        self.context_menu.addAction(gettext("Show log..."), self.show_file_log)
        self.context_menu.addAction(gettext("Annotate"), self.show_file_annotate)
        self.context_menu.setDefaultAction(
            self.context_menu.addAction(gettext("View file"),
                                        self.show_file_content))

        self.connect(self.file_tree,
                     QtCore.SIGNAL("doubleClicked(QModelIndex)"),
                     self.show_file_content)

        self.dir_icon = self.style().standardIcon(QtGui.QStyle.SP_DirIcon)
        self.file_icon = self.style().standardIcon(QtGui.QStyle.SP_FileIcon)

        vbox.addWidget(self.file_tree)

        buttonbox = self.create_button_box(BTN_CLOSE)
        vbox.addWidget(buttonbox)

        self.windows = []

    def show(self):
        # we show the bare form as soon as possible.
        QBzrWindow.show(self)
        QtCore.QTimer.singleShot(1, self.load)
   
    def load(self):
        try:
            self.throbber.show()
            self.processEvents()
            try:
                if not self.branch:
                    self.branch, path = Branch.open_containing(self.location) 
                
                if self.revision is None:
                    if self.revision_id is None:
                        revno, self.revision_id = self.branch.last_revision_info()
                        self.revision_spec = str(revno)
                    self.set_revision(revision_id=self.revision_id, text=self.revision_spec)
                else:
                    self.set_revision(self.revision)
            finally:
                self.throbber.hide()
        except:
            self.report_exception()
    
    def load_file_tree(self, entry, parent_item):
        files, dirs = [], []
        revs = set()
        for name, child in entry.sorted_children():
            revs.add(child.revision)
            if child.kind == "directory":
                dirs.append(child)
            else:
                files.append(child)
            
            current_time = clock()
            if 0.1 < current_time - self.start_time:
                self.processEvents()
                self.start_time = clock()
            
        for child in dirs:
            item = QtGui.QTreeWidgetItem(parent_item)
            item.setIcon(self.NAME, self.dir_icon)
            item.setText(self.NAME, child.name)
            revs.update(self.load_file_tree(child, item))
            self.items.append((item, child.revision))
        for child in files:
            item = QtGui.QTreeWidgetItem(parent_item)
            item.setIcon(self.NAME, self.file_icon)
            item.setText(self.NAME, child.name)
            self.items.append((item, child.revision))
        return revs

    def get_current_path(self):
        # Get selected item.
        item = self.file_tree.currentItem()
        if item == None: return

        # Build full item path.
        path_parts = [unicode(item.text(0))]
        parent = item.parent()
        while parent is not None:
            path_parts.append(unicode(parent.text(0)))
            parent = parent.parent()
        #path_parts.append('.')      # IMO with leading ./ path looks better
        path_parts.reverse()
        return pathjoin(*path_parts)
    
    def show_file_content(self):
        """Launch qcat for one selected file."""
        path = self.get_current_path()

        tree = self.branch.repository.revision_tree(self.revision_id)
        encoding = get_set_encoding(None, self.branch)
        window = QBzrCatWindow(filename = path, tree = tree, parent=self,
            encoding=encoding)
        window.show()
        self.windows.append(window)

    def show_file_log(self):
        """Show qlog for one selected file."""
        path = self.get_current_path()

        branch = self.branch
        file_id = branch.basis_tree().path2id(path)

        window = LogWindow(None, branch, [file_id])
        window.show()
        self.windows.append(window)
    
    def show_file_annotate(self):
        """Show qannotate for selected file."""
        path = self.get_current_path()

        branch = self.branch
        tree = self.branch.repository.revision_tree(self.revision_id)
        file_id = tree.path2id(path)
        window = AnnotateWindow(branch, tree, path, file_id)
        window.show()
        self.windows.append(window)
    
    def set_revision(self, revspec=None, revision_id=None, text=None):
        branch = self.branch
        branch.lock_read()
        self.processEvents()
        revno_map = branch.get_revision_id_to_revno_map()   # XXX make this operation lazy? how?
        self.processEvents()
        try:
            if revision_id is None:
                text = revspec.spec or ''
                if revspec.in_branch == revspec.in_history:
                    args = [branch]
                else:
                    args = [branch, False]
                try:
                    revision_id = revspec.in_branch(*args).rev_id
                except errors.InvalidRevisionSpec, e:
                    QtGui.QMessageBox.warning(self,
                        "QBzr - " + gettext("Browse"), str(e),
                        QtGui.QMessageBox.Ok)
                    return
            self.items = []
            self.file_tree.invisibleRootItem().takeChildren()
            self.revision_id = revision_id
            tree = branch.repository.revision_tree(revision_id)
            self.processEvents()
            root_file_id = tree.path2id('.')
            if root_file_id is not None:
                self.start_time = clock()
                revs = self.load_file_tree(tree.inventory[root_file_id],
                                           self.file_tree)
                revs = dict(zip(revs, branch.repository.get_revisions(list(revs))))
            else:
                revs = {}
        finally:
            branch.unlock()
        self.revision_edit.setText(text)
        for item, revision_id in self.items:
            rev = revs[revision_id]
            revno = ''
            rt = revno_map.get(revision_id)
            if rt:
                revno = '.'.join(map(str, rt))
            item.setText(self.REV, revno)
            item.setText(self.DATE, format_timestamp(rev.timestamp))
            author = rev.properties.get('author', rev.committer)
            item.setText(self.AUTHOR, extract_name(author))
            item.setText(self.MESSAGE, rev.get_summary())

    def reload_tree(self):
        revstr = unicode(self.revision_edit.text())
        if not revstr:
            revno, revision_id = self.branch.last_revision_info()
            revision_spec = str(revno)
            self.set_revision(revision_id=revision_id, text=revision_spec)
        else:
            try:
                revspec = RevisionSpec.from_string(revstr)
            except errors.NoSuchRevisionSpec, e:
                QtGui.QMessageBox.warning(self,
                    "QBzr - " + gettext("Browse"), str(e),
                    QtGui.QMessageBox.Ok)
                return
            self.set_revision(revspec)


def get_diff_trees(tree1, tree2, **kwargs):
    """Return unified diff between two trees as a string."""
    from bzrlib.diff import show_diff_trees
    output = StringIO()
    show_diff_trees(tree1, tree2, output, **kwargs)
    # XXX more complicated encoding support needed
    return output.getvalue().decode("UTF-8", "replace")
