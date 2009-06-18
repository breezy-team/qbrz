# -*- coding: utf-8 -*-
#
# QBzr - Qt frontend to Bazaar commands
# Copyright (C) 2009 Gary van der Merwe <garyvdm@gmail.com>
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
from bzrlib.workingtree import WorkingTree

from bzrlib.plugins.qbzr.lib.cat import QBzrCatWindow
from bzrlib.plugins.qbzr.lib.annotate import AnnotateWindow
from bzrlib.plugins.qbzr.lib.i18n import gettext
from bzrlib.plugins.qbzr.lib.log import LogWindow
from bzrlib.plugins.qbzr.lib.revtreeview import (
    RevisionTreeView,
    RevNoItemDelegate,
    )
from bzrlib.plugins.qbzr.lib.lazycachedrevloader import cached_revisions
from bzrlib.plugins.qbzr.lib.util import (
    get_set_encoding,
    get_summary,
    get_apparent_author_name,
    )
from bzrlib.plugins.qbzr.lib.uifactory import ui_current_widget
from bzrlib.plugins.qbzr.lib.wtlist import ChangeDesc


class UnversionedItem():
    __slots__  = ["name", "path", "kind", "children"]
    def __init__(self, name, path, kind):
        self.name = name
        self.path = path
        self.kind = kind
        self.children = None
    
    revision = property(lambda self:None)
    file_id = property(lambda self:None)

class TreeModel(QtCore.QAbstractItemModel):
    
    HEADER_LABELS = [gettext("File Name"),
                     gettext("Date"),
                     gettext("Rev"),
                     gettext("Message"),
                     gettext("Author"),
                     gettext("Status")]
    NAME, DATE, REVNO, MESSAGE, AUTHOR, STATUS = range(len(HEADER_LABELS))

    REVID = QtCore.Qt.UserRole + 1
    FILEID = QtCore.Qt.UserRole + 2
    PATH = QtCore.Qt.UserRole + 3
    
    def __init__(self, file_icon, dir_icon, parent=None):
        QtCore.QAbstractTableModel.__init__(self, parent)

        self.file_icon = file_icon
        self.dir_icon = dir_icon
        self.tree = None
        self.dir_children_ids = {}
    
    def set_tree(self, tree, branch):
        self.tree = tree
        self.branch = branch
        self.revno_map = None
        
        self.changes = {}
        self.unver_by_parent = {}

        if isinstance(self.tree, WorkingTree):
            tree.lock_read()
            try:
                for change in self.tree.iter_changes(self.tree.basis_tree(),
                                                   want_unversioned=True):
                    change = ChangeDesc(change)
                    path = change.path()
                    is_ignored = self.tree.is_ignored(path)
                    change = ChangeDesc(change+(is_ignored,))
                    
                    if change.fileid() is not None:
                        self.changes[change.fileid()] = change
                    else:
                        (dir_path, slash, name) = path.rpartition('/')
                        dir_fileid = self.tree.path2id(dir_path)
                        
                        if dir_fileid not in self.unver_by_parent:
                            self.unver_by_parent[dir_fileid] = []
                        self.unver_by_parent[dir_fileid].append((
                                        UnversionedItem(name, path, change.kind()),
                                        change))
                
                self.process_inventory(self.working_tree_get_children)
            finally:
                tree.unlock()
        else:
            self.process_inventory(self.get_children)
    
    def get_children(self, item):
        for child in item.children.itervalues():
            yield (child, None)
    
    def working_tree_get_children(self, item):
        if item.children is not None:
            #Because we create copies, we have to get the real item.
            item = self.tree.inventory[item.file_id]
            for child in item.children.itervalues():
                # Create a copy so that we don't have to hold a lock of the wt.
                child = child.copy()
                if child.file_id in self.changes:
                    change = self.changes[child.file_id]
                else:
                    change = None
                yield (child, change)
        if item.file_id in self.unver_by_parent:
            for (child, change) in self.unver_by_parent[item.file_id]:
                yield (child, change)
    
    def process_inventory(self, get_children):
        self.emit(QtCore.SIGNAL("layoutAboutToBeChanged()"))
        try:
            self.inventory_items = []
            self.dir_children_ids = {}
            self.parent_ids = []
            
            # Create internal ids for all items in the tree for use in
            # ModelIndex's.
            root_item = self.tree.inventory[self.tree.get_root_id()]
            root_id = self.append_item(root_item, None, None)
            remaining_dirs = [(root_item, root_id)]
            while remaining_dirs:
                (dir_item, dir_id) = remaining_dirs.pop(0)
                dir_children_ids = []
                
                children = sorted(get_children(dir_item),
                                  self.inventory_dirs_first_cmp,
                                  lambda x: x[0])
                for (child, change) in children:
                    child_id = self.append_item(child, change, dir_id)
                    dir_children_ids.append(child_id)
                    if child.kind == "directory":
                        remaining_dirs.append((child, child_id))
                    
                    if len(self.inventory_items) % 100 == 0:
                        QtCore.QCoreApplication.processEvents()
                self.dir_children_ids[dir_id] = dir_children_ids
        finally:
            self.emit(QtCore.SIGNAL("layoutChanged()"))
    
    def append_item(self, item, change, parent_id):
        id = len(self.inventory_items)
        self.inventory_items.append((item, change))
        self.parent_ids.append(parent_id)
        return id
    
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
        for id in xrange(1, len(self.inventory_items)):
            parent_id = self.parent_ids[id]
            row = self.dir_children_ids[parent_id].index(id)
            index = self.createIndex (row, self.REVNO, id)
            self.emit(QtCore.SIGNAL("dataChanged(QModelIndex, QModelIndex)"),
                      index,index)        
    
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
        dir_children_ids = self.dir_children_ids[parent_id]
        if row >= len(dir_children_ids):
            return QtCore.QModelIndex()
        item_id = dir_children_ids[row]
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
        
        (item, change) = self.inventory_items[index.internalId()]
        
        if role == self.FILEID:
            return QtCore.QVariant(item.fileid)
        
        revid = item.revision
        if role == self.REVID:
            if revid is None:
                return QtCore.QVariant()
            else:
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
        
        if column == self.STATUS:
            if role == QtCore.Qt.DisplayRole:
                if change is not None:
                    return QtCore.QVariant(change.status())
                else:
                    return QtCore.QVariant()
        
        if column == self.REVNO:
            if role == QtCore.Qt.DisplayRole:
                if self.revno_map is not None and revid in self.revno_map:
                    revno_sequence = self.revno_map[revid]
                    return QtCore.QVariant(
                        ".".join(["%d" % (revno) for revno in revno_sequence]))
                else:
                    return QtCore.QVariant()

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
        for id, (item, change) in enumerate(self.inventory_items):
            if id == 0:
                continue
            
            if item.revision in revisions:
                parent_id = self.parent_ids[id]
                row = self.dir_children_ids[parent_id].index(id)
                self.emit(QtCore.SIGNAL("dataChanged(QModelIndex, QModelIndex)"),
                          self.createIndex (row, self.DATE, id),
                          self.createIndex (row, self.AUTHOR,id))

    def get_repo(self):
        return self.branch.repository

class TreeFilterProxyModel(QtGui.QSortFilterProxyModel):
    source_model = None
    
    filters = [True, True, True, False]
    (UNCHANGED, CHANGED, UNVERSIONED, IGNORED) = range(4)
    
    filter_cache = {}
    
    def setSourceModel (self, source_model):
        self.source_model = source_model
        QtGui.QSortFilterProxyModel.setSourceModel(self, source_model)
    
    def invalidateFilter(self):
        self.filter_cache = {}
        QtGui.QSortFilterProxyModel.invalidateFilter(self)
    
    def setFilter(self, filter, value):
        self.filters[filter] = value
        self.invalidateFilter()
    
    def setFilters(self, filters):
        def iff(b, x, y):
            if b:
                return x
            else:
                return Y
        self.filters = [iff(f is not None, f, old_f)
                        for f, old_f in zip(filters, self.filters)]
        self.invalidateFilter()

    def filterAcceptsRow(self, source_row, source_parent):
        if all(self.filters):
            return True
        
        model = self.source_model
        parent_id = source_parent.internalId()
        id = model.dir_children_ids[parent_id][source_row]
        return self.filter_id_cached(id)
    
    def filter_id_cached(self, id):
        if id in self.filter_cache:
            return self.filter_cache[id]
        else:
            result = self.filter_id(id)
            self.filter_cache[id] = result
            return result
    
    def filter_id(self, id):
        (unchanged, changed, unversioned, ignored) = self.filters

        model = self.source_model
        item, change = model.inventory_items[id]
        
        if change is None and unchanged: return True
        
        is_versioned = not isinstance(item, UnversionedItem)
        
        if is_versioned and change is not None and changed: return True
        
        if not is_versioned and unversioned:
            is_ignored = change.is_ignored()
            if not is_ignored: return True
            if is_ignored and ignored: return True
        
        if id in model.dir_children_ids:
            for child_id in model.dir_children_ids[id]:
                if self.filter_id_cached(child_id):
                    return True
        
        return False
    
    
    
    def on_revisions_loaded(self, revisions, last_call):
        self.source_model.on_revisions_loaded(revisions, last_call)
    
    def get_repo(self):
        return self.source_model.get_repo()

class TreeFilterMenu(QtGui.QMenu):
    
    def __init__ (self, parent=None):
        QtGui.QMenu.__init__(self, gettext("&Filter"), parent)
        
        filters = (gettext("Unchanged"),
                   gettext("Changed"),
                   gettext("Unversioned"),
                   gettext("Ignored"))
        
        self.actions = []
        for i, text in enumerate(filters):
            action = QtGui.QAction(text, self)
            action.setData(QtCore.QVariant (i))
            action.setCheckable(True)
            self.addAction(action)
            self.actions.append(action)
        
        self.connect(self, QtCore.SIGNAL("triggered(QAction *)"),
                     self.triggered)
    
    def triggered(self, action):
        filter = action.data().toInt()[0]
        checked = action.isChecked()
        self.emit(QtCore.SIGNAL("triggered(int, bool)"), filter, checked)
    
    def set_filters(self, filters):
        for checked, action in zip(filters, self.actions):
            action.setChecked(checked)


class TreeWidget(RevisionTreeView):

    def __init__(self, *args):
        RevisionTreeView.__init__(self, *args)
        
        file_icon = self.style().standardIcon(QtGui.QStyle.SP_FileIcon)
        dir_icon = self.style().standardIcon(QtGui.QStyle.SP_DirIcon)
        
        self.tree_model = TreeModel(file_icon, dir_icon)
        self.tree_filter_model = TreeFilterProxyModel()
        self.tree_filter_model.setSourceModel(self.tree_model)
        self.setModel(self.tree_filter_model)

        self.setItemDelegateForColumn(self.tree_model.REVNO,
                                      RevNoItemDelegate(parent=self))

        header = self.header()
        header.setStretchLastSection(False)
        header.setResizeMode(self.tree_model.NAME, QtGui.QHeaderView.ResizeToContents)
        header.setResizeMode(self.tree_model.DATE, QtGui.QHeaderView.Interactive)
        header.setResizeMode(self.tree_model.REVNO, QtGui.QHeaderView.Interactive)
        header.setResizeMode(self.tree_model.MESSAGE, QtGui.QHeaderView.Stretch)
        header.setResizeMode(self.tree_model.AUTHOR, QtGui.QHeaderView.Interactive)        
        fm = self.fontMetrics()
        # XXX Make this dynamic.
        col_margin = 6
        header.resizeSection(self.tree_model.REVNO,
                             fm.width("8888.8.888") + col_margin)
        header.resizeSection(self.tree_model.DATE,
                             fm.width("88-88-8888 88:88") + col_margin)
        header.resizeSection(self.tree_model.AUTHOR,
                             fm.width("Joe I have a Long Name") + col_margin)

        self.context_menu = QtGui.QMenu(self)
        self.context_menu.addAction(gettext("Show log..."), self.show_file_log)
        self.context_menu.addAction(gettext("Annotate"), self.show_file_annotate)
        self.context_menu.setDefaultAction(
            self.context_menu.addAction(gettext("View file"),
                                        self.show_file_content))
        
        self.connect(self,
                     QtCore.SIGNAL("doubleClicked(QModelIndex)"),
                     self.show_file_content)
        self.tree = None
        self.branch = None        
    
    def set_tree(self, tree, branch):
        self.tree = tree
        self.branch = branch
        self.tree_model.set_tree(self.tree, self.branch)

    def contextMenuEvent(self, event):
        self.context_menu.popup(event.globalPos())
        event.accept()
    
    @ui_current_widget
    def show_file_content(self, index=None):
        """Launch qcat for one selected file."""
        
        if index is None:
            index = self.currentIndex()
        path = unicode(index.data(self.tree_model.PATH).toString())

        encoding = get_set_encoding(None, self.branch)
        window = QBzrCatWindow(filename = path,
                               tree = self.tree,
                               parent=self,
                               encoding=encoding)
        window.show()
        self.window().windows.append(window)

    @ui_current_widget
    def show_file_log(self):
        """Show qlog for one selected file."""
        
        index = self.currentIndex()
        file_id = unicode(index.data(self.tree_model.FILEID).toString())

        window = LogWindow(None, self.branch, file_id)
        window.show()
        self.window().windows.append(window)
    
    @ui_current_widget
    def show_file_annotate(self):
        """Show qannotate for selected file."""
        index = self.currentIndex()
        file_id = unicode(index.data(self.tree_model.FILEID).toString())
        path = unicode(index.data(self.tree_model.PATH).toString())

        window = AnnotateWindow(self.branch, self.tree, path, file_id)
        window.show()
        self.window().windows.append(window)
