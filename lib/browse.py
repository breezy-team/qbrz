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

from time import (strftime, localtime)
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
from bzrlib.plugins.qbzr.lib.revtreeview import RevisionTreeView
from bzrlib.plugins.qbzr.lib.lazycachedrevloader import cached_revisions
from bzrlib.plugins.qbzr.lib.util import (
    BTN_CLOSE,
    QBzrWindow,
    ThrobberWidget,
    format_timestamp,
    get_set_encoding,
    runs_in_loading_queue,
    url_for_display,
    get_summary,
    get_apparent_author_name,
    )
from bzrlib.plugins.qbzr.lib.uifactory import ui_current_widget
from bzrlib.plugins.qbzr.lib.trace import reports_exception


class TreeModel(QtCore.QAbstractItemModel):
    
    HEADER_LABELS = [gettext("File Name"),
                     gettext("Date"),
                     gettext("Rev"),
                     gettext("Message"),
                     gettext("Author"),]
    NAME, DATE, REVNO, MESSAGE, AUTHOR = range(len(HEADER_LABELS))

    REVID = QtCore.Qt.UserRole + 1
    FILEID = QtCore.Qt.UserRole + 2
    PATH = QtCore.Qt.UserRole + 3
    
    def __init__(self, file_icon, dir_icon, parent=None):
        QtCore.QAbstractTableModel.__init__(self, parent)

        self.file_icon = file_icon
        self.dir_icon = dir_icon
        self.tree = None
    
    def set_tree(self, tree, branch):
        self.emit(QtCore.SIGNAL("layoutAboutToBeChanged()"))
        self.tree = tree
        self.branch = branch
        self.revno_map = None
        self.id2fileid = []
        self.fileid2id = {}
        self.dir_children_ids = {}
        self.parent_ids = []
        
        # Create internal ids for all items in the tree for use in
        # ModelIndex's.
        root_fileid = tree.path2id('.')
        self.append_fileid(root_fileid, None)
        remaining_dirs = [root_fileid,]        
        while remaining_dirs:
            dir_fileid = remaining_dirs.pop(0)
            dir_id = self.fileid2id[dir_fileid]
            dir_children_ids = []
            
            children = sorted(tree.inventory[dir_fileid].children.itervalues(),
                              self.inventory_dirs_first_cmp)
            for child in children:
                id = self.append_fileid(child.file_id, dir_id)
                dir_children_ids.append(id)
                if child.kind == "directory":
                    remaining_dirs.append(child.file_id)
                
                if len(self.id2fileid) % 100 == 0:
                    QtCore.QCoreApplication.processEvents()
            self.dir_children_ids[dir_id] = dir_children_ids
        
        self.emit(QtCore.SIGNAL("layoutChanged()"))
    
    def inventory_dirs_first_cmp(self, x, y):
        x_is_dir = x.kind =="directory"
        y_is_dir = y.kind =="directory"
        if x_is_dir and not y_is_dir:
            return -1
        if y_is_dir and not x_is_dir:
            return 1
        return cmp(x.name, y.name)
    
    def set_revno_map(self, revno_map):
        self.revno_map = revno_map
        inventory = self.tree.inventory
        for fileid in inventory:
            id = self.fileid2id[fileid]
            if id > 0:
                parent_id = self.parent_ids[id]
                row = self.dir_children_ids[parent_id].index(id)
                index = self.createIndex (row, self.REVNO, id)
                self.emit(QtCore.SIGNAL("dataChanged(QModelIndex, QModelIndex)"),
                          index,index)        
    
    def append_fileid(self, fileid, parent_id):
        ix = len(self.id2fileid)
        self.id2fileid.append(fileid)
        self.parent_ids.append(parent_id)
        self.fileid2id[fileid] = ix
        return ix
    
    def columnCount(self, parent):
         return len(self.HEADER_LABELS)

    def rowCount(self, parent):
        if self.tree is None:
            return 0
        parent_id = parent.internalId()
        if parent_id not in self.dir_children_ids:
            return 0
        return len(self.dir_children_ids[parent_id])

    def _index(self, row, column, parent_id):
        item_id = self.dir_children_ids[parent_id][row]
        return self.createIndex(row, column, item_id)
    
    def index(self, row, column, parent = QtCore.QModelIndex()):
        if self.tree is None:
            return self.createIndex(row, column, 0)
        parent_id = parent.internalId()
        return self._index(row, column, parent_id)
    
    def sibling(self, row, column, index):
        sibling_id = index.internalId()
        if sibling_id == 0:
            return QtCore.QModelIndex()
        parent_id = self.parent_ids[sibling_id]
        return self._index(row, column, parent_id)
    
    def parent(self, child):
        child_id = child.internalId()
        if child_id == 0:
            return QtCore.QModelIndex()
        item_id = self.parent_ids[child_id]
        if item_id == 0 :
            return QtCore.QModelIndex()
        
        parent_id = self.parent_ids[item_id]
        row = self.dir_children_ids[parent_id].index(item_id)
        return self.createIndex(row, 0, item_id)

    def hasChildren(self, parent):
        if self.tree is None:
            return False
        
        parent_id = parent.internalId()
        return parent_id in self.dir_children_ids
    
    def data(self, index, role):
        if not index.isValid():
            return QtCore.QVariant()
        
        fileid = self.id2fileid[index.internalId()]
        
        if role == self.FILEID:
            return QtCore.QVariant(fileid)
        
        item = self.tree.inventory[fileid]
        
        revid = item.revision
        if role == self.REVID:
            return QtCore.QVariant(revid)

        column = index.column()
        if column == self.NAME:
            if role == QtCore.Qt.DisplayRole:
                return QtCore.QVariant(item.name)
            if role == QtCore.Qt.DecorationRole:
                if item.kind == "file":
                    return QtCore.QVariant(self.file_icon)
                if item.kind == "directory":
                    return QtCore.QVariant(self.dir_icon)
                # XXX Simlink
                return QtCore.QVariant()
        
        if column == self.REVNO:
            if role == QtCore.Qt.DisplayRole:
                if self.revno_map is not None:
                    revno_sequence = self.revno_map[revid]
                    return QtCore.QVariant(
                        ".".join(["%d" % (revno) for revno in revno_sequence]))
                else:
                    return QtCore.QVariant()
            if role == QtCore.Qt.TextAlignmentRole:
                return QtCore.QVariant(QtCore.Qt.AlignRight)

        if role == QtCore.Qt.DisplayRole:
            if revid in cached_revisions:
                rev = cached_revisions[revid]
                
                if column == self.AUTHOR:
                    return QtCore.QVariant(get_apparent_author_name(rev))

                if column == self.MESSAGE:
                    return QtCore.QVariant(get_summary(rev))
        
                if column == self.DATE:
                    return QtCore.QVariant(strftime("%Y-%m-%d %H:%M",   
                                                    localtime(rev.timestamp)))
        
        if role == self.PATH:
            return QtCore.QVariant(self.tree.inventory.id2path(fileid))
        
        return QtCore.QVariant()
    
    def flags(self, index):
        if not index.isValid():
            return QtCore.Qt.ItemIsEnabled

        return QtCore.Qt.ItemIsEnabled | QtCore.Qt.ItemIsSelectable

    def headerData(self, section, orientation, role):
        if orientation == QtCore.Qt.Horizontal and role == QtCore.Qt.DisplayRole:
            return QtCore.QVariant(self.HEADER_LABELS[section])
        return QtCore.QVariant()
    
    def on_revisions_loaded(self, revisions, last_call):
        inventory = self.tree.inventory
        for fileid in inventory:
            revid = inventory[fileid].revision
            if revid in revisions:
                id = self.fileid2id[fileid]
                if id > 0:
                    parent_id = self.parent_ids[id]
                    row = self.dir_children_ids[parent_id].index(id)
                    self.emit(QtCore.SIGNAL("dataChanged(QModelIndex, QModelIndex)"),
                              self.createIndex (row, self.DATE, id),
                              self.createIndex (row, self.AUTHOR,id))

    def get_repo(self):
        return self.branch.repository

class FileTreeWidget(RevisionTreeView):

    def __init__(self, window, *args):
        RevisionTreeView.__init__(self, *args)
        self.window = window

    def contextMenuEvent(self, event):
        self.window.context_menu.popup(event.globalPos())
        event.accept()


class BrowseWindow(QBzrWindow):

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
        self.root_file_id = None

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
        
        file_icon = self.style().standardIcon(QtGui.QStyle.SP_FileIcon)
        dir_icon = self.style().standardIcon(QtGui.QStyle.SP_DirIcon)

        self.file_tree = FileTreeWidget(self)
        self.file_tree.throbber = self.throbber

        self.file_tree_model = TreeModel(file_icon, dir_icon)
        self.file_tree.setModel(self.file_tree_model)
        
        header = self.file_tree.header()
        header.setStretchLastSection(False)
        header.setResizeMode(self.file_tree_model.NAME, QtGui.QHeaderView.ResizeToContents)
        header.setResizeMode(self.file_tree_model.DATE, QtGui.QHeaderView.Interactive)
        header.setResizeMode(self.file_tree_model.REVNO, QtGui.QHeaderView.Interactive)
        header.setResizeMode(self.file_tree_model.MESSAGE, QtGui.QHeaderView.Stretch)
        header.setResizeMode(self.file_tree_model.AUTHOR, QtGui.QHeaderView.Interactive)
        fm = self.fontMetrics()
        # XXX Make this dynamic.
        col_margin = 6
        header.resizeSection(self.file_tree_model.REVNO,
                             fm.width("8888.8.888") + col_margin)
        header.resizeSection(self.file_tree_model.DATE,
                             fm.width("88-88-8888 88:88") + col_margin)
        header.resizeSection(self.file_tree_model.AUTHOR,
                             fm.width("Joe I have a Long Name") + col_margin)

        self.context_menu = QtGui.QMenu(self.file_tree)
        self.context_menu.addAction(gettext("Show log..."), self.show_file_log)
        self.context_menu.addAction(gettext("Annotate"), self.show_file_annotate)
        self.context_menu.setDefaultAction(
            self.context_menu.addAction(gettext("View file"),
                                        self.show_file_content))

        self.connect(self.file_tree,
                     QtCore.SIGNAL("doubleClicked(QModelIndex)"),
                     self.show_file_content)

        vbox.addWidget(self.file_tree)

        buttonbox = self.create_button_box(BTN_CLOSE)
        vbox.addWidget(buttonbox)

        self.windows = []

    def show(self):
        # we show the bare form as soon as possible.
        QBzrWindow.show(self)
        QtCore.QTimer.singleShot(1, self.load)
   
    @runs_in_loading_queue
    @ui_current_widget
    @reports_exception()
    def load(self):
        self.throbber.show()
        self.processEvents()
        try:
            self.revno_map = None
            if not self.branch:
                self.branch, path = Branch.open_containing(self.location) 
            
            if self.revision is None:
                if self.revision_id is None:
                    revno, self.revision_id = self.branch.last_revision_info()
                    self.revision_spec = str(revno)
                self.set_revision(revision_id=self.revision_id, text=self.revision_spec)
            else:
                self.set_revision(self.revision)
            
            self.processEvents()
            # XXX make this operation lazy? how?
            self.revno_map = self.branch.get_revision_id_to_revno_map()
            self.file_tree_model.set_revno_map(self.revno_map)
            
        finally:
            self.throbber.hide()

    
    @ui_current_widget
    def set_revision(self, revspec=None, revision_id=None, text=None):
        branch = self.branch
        branch.lock_read()
        self.processEvents()
        self.processEvents()
        try:
            if revision_id is None:
                text = revspec.spec or ''
                if revspec.in_branch == revspec.in_history:
                    args = [branch]
                else:
                    args = [branch, False]
                
                revision_id = revspec.in_branch(*args).rev_id

            self.revision_id = revision_id
            self.tree = branch.repository.revision_tree(revision_id)
            self.processEvents()
            self.file_tree_model.set_tree(self.tree, self.branch)
            if self.revno_map is not None:
                self.file_tree_model.set_revno_map(self.revno_map)
        finally:
            branch.unlock()
        self.revision_edit.setText(text)


    @ui_current_widget
    def show_file_content(self, index=None):
        """Launch qcat for one selected file."""
        
        if index is None:
            index = self.file_tree.currentIndex()
        path = unicode(index.data(self.file_tree_model.PATH).toString())

        encoding = get_set_encoding(None, self.branch)
        window = QBzrCatWindow(filename = path,
                               tree = self.tree,
                               parent=self,
                               encoding=encoding)
        window.show()
        self.windows.append(window)

    @ui_current_widget
    def show_file_log(self):
        """Show qlog for one selected file."""
        
        index = self.file_tree.currentIndex()
        file_id = unicode(index.data(self.file_tree_model.FILEID).toString())

        window = LogWindow(None, self.branch, file_id)
        window.show()
        self.windows.append(window)
    
    @ui_current_widget
    def show_file_annotate(self):
        """Show qannotate for selected file."""
        index = self.file_tree.currentIndex()
        file_id = unicode(index.data(self.file_tree_model.FILEID).toString())
        path = unicode(index.data(self.file_tree_model.PATH).toString())

        window = AnnotateWindow(self.branch, self.tree, path, file_id)
        window.show()
        self.windows.append(window)

    @ui_current_widget
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

