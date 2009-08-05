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

import os, sys
from time import (strftime, localtime)
from PyQt4 import QtCore, QtGui
from bzrlib import errors
from bzrlib.workingtree import WorkingTree
from bzrlib.revisiontree import RevisionTree

from bzrlib.plugins.qbzr.lib.cat import QBzrCatWindow, QBzrViewWindow
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
from bzrlib.plugins.qbzr.lib.subprocess import SimpleSubProcessDialog
from bzrlib.plugins.qbzr.lib.diff import (
    show_diff,
    has_ext_diff,
    ExtDiffMenu,
    InternalWTDiffArgProvider,
    )


class InternalItem(object):
    __slots__  = ["name", "kind", "file_id"]
    def __init__(self, name, kind, file_id):
        self.name = name
        self.kind = kind
        self.file_id = file_id
    
    revision = property(lambda self:None)


class UnversionedItem(InternalItem):
    def __init__(self, name, kind):
        InternalItem.__init__(self, name, kind, None)


class ModelItemData(object):
    __slots__ = ["id", "item", "change", "checked", "children_ids",
                 "parent_id", "row", "path", "icon"]
    
    def __init__(self, item, change, path):
        self.item = item
        self.change = change
        self.path = path
        if change is not None and change.is_ignored() is None:
            self.checked = QtCore.Qt.Checked
        else:
            self.checked = QtCore.Qt.Unchecked
            
        self.children_ids = None
        self.parent_id = None
        self.id = None
        self.row = None
        self.icon = None


class PersistantItemReference(object):
    """This is use to stores a reference to a item that is persisted when we
    refresh the model."""
    __slots__ = ["file_id", "path"]
    
    def __init__(self, file_id, path):
        self.file_id = file_id
        self.path = path


class ChangeDesc(tuple):
    """Helper class that "knows" about internals of iter_changes' changed entry
    description tuple, and provides additional helper methods.

    iter_changes return tuple with info about changed entry:
    [0]: file_id         -> ascii string
    [1]: paths           -> 2-tuple (old, new) fullpaths unicode/None
    [2]: changed_content -> bool
    [3]: versioned       -> 2-tuple (bool, bool)
    [4]: parent          -> 2-tuple
    [5]: name            -> 2-tuple (old_name, new_name) utf-8?/None
    [6]: kind            -> 2-tuple (string/None, string/None)
    [7]: executable      -> 2-tuple (bool/None, bool/None)
    
    --optional--
    [8]: is_ignored      -> If the file is ignored, pattern which caused it to
                            be ignored, otherwise None.
    
    NOTE: None value used for non-existing entry in corresponding
          tree, e.g. for added/deleted/ignored/unversioned
    """
    
    # XXX We should may be try get this into bzrlib.
    # XXX We should use this in qdiff.
    
    def fileid(desc):
        return desc[0]

    def path(desc):
        """Return a suitable entry for a 'specific_files' param to bzr functions."""
        oldpath, newpath = desc[1]
        return newpath or oldpath

    def oldpath(desc):
        """Return oldpath for renames."""
        return desc[1][0]

    def kind(desc):
        oldkind, newkind = desc[6]
        return newkind or oldkind        

    def is_versioned(desc):
        return desc[3] != (False, False)

    def is_modified(desc):
        return (desc[3] != (False, False) and desc[2])

    def is_renamed(desc):
        return (desc[3] == (True, True)
                and (desc[4][0], desc[5][0]) != (desc[4][1], desc[5][1]))

    def is_tree_root(desc):
        """Check if entry actually tree root."""
        if desc[3] != (False, False) and desc[4] == (None, None):
            # TREE_ROOT has not parents (desc[4]).
            # But because we could want to see unversioned files
            # we need to check for versioned flag (desc[3])
            return True
        return False

    def is_missing(desc):
        """Check if file was present in previous revision but now it's gone
        (i.e. deleted manually, without invoking `bzr remove` command)
        """
        return (desc[3] == (True, True) and desc[6][1] is None)

    def is_misadded(desc):
        """Check if file was added to the working tree but then gone
        (i.e. deleted manually, without invoking `bzr remove` command)
        """
        return (desc[3] == (False, True) and desc[6][1] is None)
    
    def is_ignored(desc):
        if len(desc) >= 8: 
            return desc[8]
        else:
            return None
    
    def status(desc):
        if len(desc) == 8:
            (file_id, (path_in_source, path_in_target),
             changed_content, versioned, parent, name, kind,
             executable) = desc
            is_ignored = None
        elif len(desc) == 9:
            (file_id, (path_in_source, path_in_target),
             changed_content, versioned, parent, name, kind,
             executable, is_ignored) = desc
        else:
            raise RuntimeError, "Unkown number of items to unpack."
            
        if versioned == (False, False):
            if is_ignored:
                return gettext("ignored")
            else:
                return gettext("non-versioned")
        elif versioned == (False, True):
            return gettext("added")
        elif versioned == (True, False):
            return gettext("removed")
        elif kind[0] is not None and kind[1] is None:
            return gettext("missing")
        else:
            # versioned = True, True - so either renamed or modified
            # or properties changed (x-bit).
            renamed = (parent[0], name[0]) != (parent[1], name[1])
            if renamed:
                if changed_content:
                    return gettext("renamed and modified")
                else:
                    return gettext("renamed")
            elif changed_content:
                return gettext("modified")
            elif executable[0] != executable[1]:
                return gettext("modified (x-bit)")
            else:
                raise RuntimeError, "what status am I missing??"


class TreeModel(QtCore.QAbstractItemModel):
    
    HEADER_LABELS = [gettext("File Name"),
                     gettext("Date"),
                     gettext("Rev"),
                     gettext("Message"),
                     gettext("Author"),
                     gettext("Status")]
    NAME, DATE, REVNO, MESSAGE, AUTHOR, STATUS = range(len(HEADER_LABELS))

    def __init__(self, parent=None):
        # XXX parent object: instance of what class it supposed to be?
        QtCore.QAbstractTableModel.__init__(self, parent)

        if parent is not None:
            # TreeModel is subclass of QtCore.QAbstractItemModel,
            # the latter can have parent in constructor
            # as instance of QModelIndex and the latter does not have style()
            style = parent.style()
            self.file_icon = style.standardIcon(QtGui.QStyle.SP_FileIcon)
            self.dir_icon = style.standardIcon(QtGui.QStyle.SP_DirIcon)
            self.symlink_icon = style.standardIcon(QtGui.QStyle.SP_FileLinkIcon)
        else:
            self.file_icon = QtGui.QIcon()
            self.dir_icon = QtGui.QIcon()
            self.symlink_icon = QtGui.QIcon()
        self.tree = None
        self.inventory_data = []
        self.inventory_data_by_path = {}
        self.inventory_data_by_id = {} # Will not contain unversioned items.
        self.checkable = False
        self.icon_provider = QtGui.QFileIconProvider()
    
    def set_tree(self, tree, branch=None, 
                 changes_mode=False, want_unversioned=True,
                 initial_selected_paths=None):
        self.tree = tree
        self.branch = branch
        self.revno_map = None
        self.changes_mode = changes_mode
        
        self.changes = {}
        self.unver_by_parent = {}
        self.inventory_data_by_path = {}
        self.inventory_data_by_id = {}
        
        if isinstance(self.tree, WorkingTree):
            tree.lock_read()
            try:
                root_id = self.tree.get_root_id()
                basis_tree = self.tree.basis_tree()
                basis_tree.lock_read()
                try:
                    for change in self.tree.iter_changes(basis_tree,
                                                want_unversioned=want_unversioned):
                        change = ChangeDesc(change)
                        path = change.path()
                        fileid = change.fileid()
                        if fileid == root_id:
                            continue
                        is_ignored = self.tree.is_ignored(path)
                        change = ChangeDesc(change+(is_ignored,))
                        
                        if fileid is not None and not changes_mode:
                            self.changes[change.fileid()] = change
                        else:
                            if changes_mode:
                                dir_path = path
                                dir_fileid = None
                                relpath = ""
                                while dir_path:
                                    (dir_path, slash, name) = dir_path.rpartition('/')
                                    relpath = slash + name + relpath
                                    if dir_path in self.inventory_data_by_path:
                                        dir_item = self.inventory_data_by_path[
                                                                         dir_path]
                                        dir_fileid = dir_item.item.file_id
                                        break
                                if dir_fileid is None:
                                    dir_fileid = root_id
                                    dir_path = ""
                                
                                name = relpath.lstrip("/")
                                if change.is_renamed():
                                    old_inventory_item = basis_tree.inventory[fileid]
                                    old_names = [old_inventory_item.name]
                                    while old_inventory_item.parent_id:
                                        old_inventory_item = basis_tree.inventory[old_inventory_item.parent_id]
                                        if old_inventory_item.parent_id == dir_fileid:
                                            break
                                        old_names.append(old_inventory_item.name)
                                    old_names.reverse()
                                    old_path = "/".join(old_names)
                                    name = "%s => %s" % (old_path, name)
                            else:
                                (dir_path, slash, name) = path.rpartition('/')
                                dir_fileid = self.tree.path2id(dir_path)
                            
                            if change.is_versioned():
                                if changes_mode:
                                    item = InternalItem(name, change.kind(),
                                                        change.fileid())
                                else:
                                    item = self.tree.inventory[change.fileid()]
                            else:
                                item = UnversionedItem(name, change.kind())
                            
                            item_data = ModelItemData(item, change, path)
                            
                            if dir_fileid not in self.unver_by_parent:
                                self.unver_by_parent[dir_fileid] = []
                            self.unver_by_parent[dir_fileid].append(item_data)
                            self.inventory_data_by_path[path] = item_data
                finally:
                    basis_tree.unlock()
                self.process_inventory(self.working_tree_get_children)
            finally:
                tree.unlock()
        else:
            self.process_inventory(self.revision_tree_get_children)
    
    def revision_tree_get_children(self, item_data):
        for child in item_data.item.children.itervalues():
            path = self.tree.id2path(child.file_id)
            yield ModelItemData(child, None, path)
    
    def working_tree_get_children(self, item_data):
        item = item_data.item
        if isinstance(item, UnversionedItem):
            abspath = self.tree.abspath(item_data.path)
            
            for name in os.listdir(abspath):
                path = item_data.path+"/"+name
                (kind,
                 executable,
                 stat_value) = self.tree._comparison_data(None, path)
                child = UnversionedItem(name, kind)
                is_ignored = self.tree.is_ignored(path)
                change = ChangeDesc((None,
                                     (None, path),
                                     False,
                                     (False, False),
                                     (None, None),
                                     (None, name),
                                     (None, kind),
                                     (None, executable),
                                     is_ignored))
                yield ModelItemData(child, change, path)
        
        if (not isinstance(item, InternalItem) and
            item.children is not None and not self.changes_mode):
            #Because we create copies, we have to get the real item.
            item = self.tree.inventory[item.file_id]
            for child in item.children.itervalues():
                # Create a copy so that we don't have to hold a lock of the wt.
                child = child.copy()
                if child.file_id in self.changes:
                    change = self.changes[child.file_id]
                else:
                    change = None
                path = self.tree.id2path(child.file_id)
                yield ModelItemData(child, change, path)
        if item.file_id in self.unver_by_parent:
            for item_data in self.unver_by_parent[item.file_id]:
                yield item_data
    
    def load_dir(self, dir_id):
        if dir_id>=len(self.inventory_data):
            return
        dir_item = self.inventory_data[dir_id]
        if dir_item.children_ids is not None:
            return 
        
        if isinstance(self.tree, WorkingTree):
            self.tree.lock_read()
        try:
            dir_item.children_ids = []
            children = sorted(self.get_children(dir_item),
                              self.inventory_dirs_first_cmp,
                              lambda x: (x.item.name, x.item.kind))
            
            parent_model_index = self._index_from_id(dir_id, 0)
            self.beginInsertRows(parent_model_index, 0, len(children)-1)
            try:
                for child in children:
                    child_id = self.append_item(child, dir_id)
                    dir_item.children_ids.append(child_id)
                    
                    if len(dir_item.children_ids) % 100 == 0:
                        QtCore.QCoreApplication.processEvents()
            finally:
                self.endInsertRows();
        finally:
            if isinstance(self.tree, WorkingTree):
                self.tree.unlock()
    
    def process_inventory(self, get_children):
        self.get_children = get_children
        
        self.emit(QtCore.SIGNAL("layoutAboutToBeChanged()"))
        
        is_refresh = len(self.inventory_data)>0
        if is_refresh:
            self.beginRemoveRows(QtCore.QModelIndex(), 0,
                                 len(self.inventory_data[0].children_ids)-1)
        self.inventory_data = []
        if is_refresh:
            self.endRemoveRows()
            
        root_item = ModelItemData(self.tree.inventory[self.tree.get_root_id()],
                                  None, '')
        root_id = self.append_item(root_item, None)
        self.load_dir(root_id)
        self.emit(QtCore.SIGNAL("layoutChanged()"))
    
    def append_item(self, item_data, parent_id):
        item_data.id = len(self.inventory_data)
        if parent_id is not None:
            parent_data = self.inventory_data[parent_id]
            if self.is_item_in_select_all(item_data):
                item_data.checked = parent_data.checked
            else:
                item_data.checked = False
            item_data.row = len(parent_data.children_ids)
        else:
            item_data.checked = QtCore.Qt.Checked
            item_data.row = 0
        item_data.parent_id = parent_id
        self.inventory_data.append(item_data)
        self.inventory_data_by_path[item_data.path] = item_data
        if not isinstance(item_data.item, UnversionedItem):
            self.inventory_data_by_id[item_data.item.file_id] = item_data
        return item_data.id
    
    def inventory_dirs_first_cmp(self, x, y):
        (x_name, x_kind) = x
        (y_name, y_kind) = y
        x_a = x_name
        y_a = y_name
        x_is_dir = x_kind =="directory"
        y_is_dir = y_kind =="directory"
        while True:
            x_b, sep, x_a_t = x_a.partition("/")
            y_b, sep, y_a_t = y_a.partition("/")
            if x_a_t == "" and y_a_t == "":
                break
            if (x_is_dir or not x_a_t == "") and not (y_is_dir or not y_a_t == ""):
                return -1
            if (y_is_dir or not y_a_t == "") and not (x_is_dir or not x_a_t == ""):
                return 1
            cmp_r = cmp(x_b, y_b)
            if not cmp_r == 0:
                return cmp_r
            x_a = x_a_t
            y_a = y_a_t
        if x_is_dir and not y_is_dir:
            return -1
        if y_is_dir and not x_is_dir:
            return 1
        return cmp(x_name, y_name)
    
    def set_revno_map(self, revno_map):
        self.revno_map = revno_map
        for item_data in self.inventory_data[1:0]:
            index = self.createIndex (item_data.row, self.REVNO, item_data.id)
            self.emit(QtCore.SIGNAL("dataChanged(QModelIndex, QModelIndex)"),
                      index,index)        
    
    def columnCount(self, parent):
         return len(self.HEADER_LABELS)

    def rowCount(self, parent):
        if parent.internalId()>=len(self.inventory_data):
            return 0
        parent_data = self.inventory_data[parent.internalId()]
        if parent_data.children_ids is None:
            return 0
        return len(parent_data.children_ids)
    
    def canFetchMore(self, parent):
        if parent.internalId()>=len(self.inventory_data):
            return False
        parent_data = self.inventory_data[parent.internalId()]
        return (parent_data.children_ids is None and
                parent_data.item.kind == "directory")
    
    def fetchMore(self, parent):
        self.load_dir(parent.internalId())

    def _index(self, row, column, parent_id):
        if parent_id>=len(self.inventory_data):
            return QtCore.QModelIndex()
        
        parent_data = self.inventory_data[parent_id]
        if parent_data.children_ids is None:
            return QtCore.QModelIndex()
        
        if (row < 0 or
            row >= len(parent_data.children_ids) or
            column < 0 or
            column >= len(self.HEADER_LABELS)):
            return QtCore.QModelIndex()
        item_id = parent_data.children_ids[row]
        return self.createIndex(row, column, item_id)
    
    def _index_from_id(self, item_id, column):
        if item_id >= len(self.inventory_data):
            return QtCore.QModelIndex()
        
        item_data = self.inventory_data[item_id]
        return self.createIndex(item_data.row, column, item_id) 
    
    def index(self, row, column, parent = QtCore.QModelIndex()):
        return self._index(row, column, parent.internalId())
    
    def sibling(self, row, column, index):
        sibling_id = index.internalId()
        if sibling_id == 0:
            return QtCore.QModelIndex()
        item_data = self.inventory_data[sibling_id]
        return self._index(row, column, item_data.parent_id)
    
    def parent(self, child):
        child_id = child.internalId()
        if child_id == 0:
            return QtCore.QModelIndex()
        item_data = self.inventory_data[child_id]
        if item_data.parent_id == 0 :
            return QtCore.QModelIndex()
        
        return self._index_from_id(item_data.parent_id, 0)

    def hasChildren(self, parent):
        if self.tree is None:
            return False
        if parent.internalId() == 0:
            return True
        item_data = self.inventory_data[parent.internalId()]
        return item_data.item.kind == "directory"
    
    is_item_in_select_all = lambda self, item: True
    """Returns wether an item is changed when select all is clicked."""
    
    def setData(self, index, value, role):
        
        def set_checked(item_data, checked):
            old_checked = item_data.checked
            item_data.checked = checked
            if not old_checked == checked:
                index = self.createIndex (item_data.row, self.NAME, item_data.id)
                self.emit(QtCore.SIGNAL("dataChanged(QModelIndex, QModelIndex)"),
                          index,index)        
            
        if index.column() == self.NAME and role == QtCore.Qt.CheckStateRole:
            value = value.toInt()[0]
            if index.internalId() >= len(self.inventory_data):
                return False
            
            item_data = self.inventory_data[index.internalId()]
            set_checked(item_data, value)
            
            # Recursively set all children to checked.
            if item_data.children_ids is not None:
                children_ids = list(item_data.children_ids)
                while children_ids:
                    child = self.inventory_data[children_ids.pop(0)]
                    
                    # If unchecking, uncheck everything, but if checking,
                    # only check those in "select_all" get checked.
                    if (self.is_item_in_select_all(child) or
                        value == QtCore.Qt.Unchecked):
                        
                        set_checked(child, value)
                        if child.children_ids is not None:
                            children_ids.extend(child.children_ids)
            
            # Walk up the tree, and update every dir
            parent_data = item_data
            while parent_data.parent_id is not None:
                if (not self.is_item_in_select_all(parent_data) and
                        value == QtCore.Qt.Unchecked):
                    # Don't uncheck parents if not in "select_all".
                    break
                parent_data = self.inventory_data[parent_data.parent_id]
                has_checked = False
                has_unchecked = False
                for child_id in parent_data.children_ids:
                    child = self.inventory_data[child_id]
                    
                    if child.checked == QtCore.Qt.Checked:
                        has_checked = True
                    elif (child.checked == QtCore.Qt.Unchecked and
                          self.is_item_in_select_all(child)):
                        has_unchecked = True
                    elif child.checked == QtCore.Qt.PartiallyChecked:
                        has_checked = True
                        if self.is_item_in_select_all(child):
                            has_unchecked = True
                    
                    if has_checked and has_unchecked:
                        break
                
                if has_checked and has_unchecked:
                    set_checked(parent_data, QtCore.Qt.PartiallyChecked)
                elif has_checked:
                    set_checked(parent_data, QtCore.Qt.Checked)
                else:
                    set_checked(parent_data, QtCore.Qt.Unchecked)
            
            return True
        
        return False
    
    REVID = QtCore.Qt.UserRole + 1
    FILEID = QtCore.Qt.UserRole + 2
    PATH = QtCore.Qt.UserRole + 3
    
    def data(self, index, role):
        if not index.isValid():
            return QtCore.QVariant()
        
        item_data = self.inventory_data[index.internalId()]
        item = item_data.item
        
        if role == self.FILEID:
            return QtCore.QVariant(item.file_id)
        
        revid = item_data.item.revision
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
                if isinstance(self.tree, WorkingTree):
                    if item_data.icon is None:
                        abspath = self.tree.abspath(item_data.path)
                        info = QtCore.QFileInfo(abspath)
                        item_data.icon = self.icon_provider.icon(info)
                    return QtCore.QVariant(item_data.icon)
                else:
                    if item.kind == "file":
                        return QtCore.QVariant(self.file_icon)
                    if item.kind == "directory":
                        return QtCore.QVariant(self.dir_icon)
                    if item.kind == "symlink":
                        return QtCore.QVariant(self.symlink_icon)
                    return QtCore.QVariant()
            
            if role ==  QtCore.Qt.CheckStateRole:
                if not self.checkable:
                    return QtCore.QVariant()
                else:
                    return QtCore.QVariant(item_data.checked)
        
        if column == self.STATUS:
            if role == QtCore.Qt.DisplayRole:
                if item_data.change is not None:
                    return QtCore.QVariant(item_data.change.status())
                else:
                    return QtCore.QVariant("")
        
        if column == self.REVNO:
            if role == QtCore.Qt.DisplayRole:
                if self.revno_map is not None and revid in self.revno_map:
                    revno_sequence = self.revno_map[revid]
                    return QtCore.QVariant(
                        ".".join(["%d" % (revno) for revno in revno_sequence]))
                else:
                    return QtCore.QVariant("")

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
            return QtCore.QVariant(item_data.path)
        
        if role == QtCore.Qt.DisplayRole:
            return QtCore.QVariant("")
        return QtCore.QVariant()
    
    def flags(self, index):
        #if not index.isValid():
        #    return QtCore.Qt.ItemIsEnabled

        if self.checkable and index.column() == self.NAME:
            return (QtCore.Qt.ItemIsEnabled |
                    QtCore.Qt.ItemIsSelectable |
                    QtCore.Qt.ItemIsUserCheckable)
        else:
            return (QtCore.Qt.ItemIsEnabled |
                    QtCore.Qt.ItemIsSelectable)

    def headerData(self, section, orientation, role):
        if orientation == QtCore.Qt.Horizontal and role == QtCore.Qt.DisplayRole:
            return QtCore.QVariant(self.HEADER_LABELS[section])
        return QtCore.QVariant()
    
    def on_revisions_loaded(self, revisions, last_call):
        inventory = self.tree.inventory
        for item_data in self.inventory_data:
            if item_data.id == 0:
                continue
            
            if item_data.item.revision in revisions:
                self.emit(QtCore.SIGNAL("dataChanged(QModelIndex, QModelIndex)"),
                          self.createIndex (item_data.row, self.DATE, item_data.id),
                          self.createIndex (item_data.row, self.AUTHOR, item_data.id))

    def get_repo(self):
        return self.branch.repository
    
    def item2ref(self, item_data):
        if isinstance(item_data.item, UnversionedItem):
            file_id = None
        else:
            file_id = item_data.item.file_id
        return PersistantItemReference(file_id, item_data.path)
    
    def index2ref(self, index):
        item_data = self.inventory_data[index.internalId()]
        return self.item2ref(item_data)
    
    def indexes2refs(self, indexes):
        refs = []
        for index in indexes:
            refs.append(self.index2ref(index))
        return refs
    
    def ref2index(self, ref):
        if ref.file_id is not None:
            key = ref.file_id
            dict = self.inventory_data_by_id
            def iter_parents():
                parent_id = ref.file_id
                parent_ids = []
                while parent_id is not None:
                    parent_id = self.tree.inventory[parent_id].parent_id
                    parent_ids.append(parent_id)
                return reversed(parent_ids)
        else:
            key = ref.path
            dict = self.inventory_data_by_path
            def iter_parents():
                path_split = ref.path.split("/")
                parent_dir_path = None
                for parent_name in ref.path.split("/")[:-1]:
                    if parent_dir_path is None:\
                        parent_dir_path = parent_name
                    else:
                        parent_dir_path += "/" + parent_name
                    yield parent_dir_path
        
        if key not in dict or dict[key].id is None:
            # Try loading the parents
            for parent_key in iter_parents():
                if parent_key not in dict:
                    break
                self.load_dir(dict[parent_key].id)
        
        if key not in dict:
            raise errors.NoSuchFile(ref.path)
        
        return self._index_from_id(dict[key].id, self.NAME)
    
    def refs2indexes(self, refs, ignore_no_file_error=False):
        indexes = []
        for ref in refs:
            try:
                indexes.append(self.ref2index(ref))
            except (errors.NoSuchId, errors.NoSuchFile):
                if not ignore_no_file_error:
                    raise
        return indexes
    
    def iter_checked(self):
        # We have to recurse and load all dirs, because we use --no-recurse
        # for add, and commit and revert don't recurse.
        i = 0
        while i<len(self.inventory_data):
            item_data = self.inventory_data[i]
            if (item_data.children_ids is None and
                item_data.item.kind == "directory" and
                item_data.checked):
                self.load_dir(item_data.id)
            i += 1
        
        return [self.item2ref(item_data)
                for item_data in sorted(
                    [item_data for item_data in self.inventory_data[1:]
                     if item_data.checked == QtCore.Qt.Checked],
                    self.inventory_dirs_first_cmp,
                    lambda x: (x.change.path(), x.item.kind))]

    def set_checked_items(self, refs, ignore_no_file_error=True):
        # set every thing off
        root_index = self._index_from_id(0, self.NAME)
        self.setData(root_index, QtCore.QVariant(QtCore.Qt.Unchecked),
                     QtCore.Qt.CheckStateRole)
        
        for index in self.refs2indexes(refs, ignore_no_file_error):
            self.setData(index, QtCore.QVariant(QtCore.Qt.Checked),
                         QtCore.Qt.CheckStateRole)

    def set_checked_paths(self, paths):
        return self.set_checked_items([PersistantItemReference(None, path)
                                       for path in paths])


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
                return y
        self.filters = [iff(f is not None, f, old_f)
                        for f, old_f in zip(filters, self.filters)]
        self.invalidateFilter()

    def filterAcceptsRow(self, source_row, source_parent):
        if all(self.filters):
            return True
        
        model = self.source_model
        parent_id = source_parent.internalId()
        children_ids = model.inventory_data[parent_id].children_ids
        if len(children_ids)<=source_row:
            return False
        id = children_ids[source_row]
        if (model.checkable and
            not model.inventory_data[id].checked == QtCore.Qt.Unchecked):
            return True
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
        item_data = model.inventory_data[id]
        
        if item_data.change is None and unchanged: return True
        
        is_versioned = not isinstance(item_data.item, UnversionedItem)
        
        if is_versioned and item_data.change is not None and changed:
            return True
        
        if not is_versioned and unversioned:
            is_ignored = item_data.change.is_ignored()
            if not is_ignored: return True
            if is_ignored and ignored: return True
            if is_ignored and not ignored: return False
        
        if item_data.item.kind == "directory":
            if item_data.children_ids is None:
                model.load_dir(id)
            
            for child_id in item_data.children_ids:
                if self.filter_id_cached(child_id):
                    return True
        
        return False
    
    def on_revisions_loaded(self, revisions, last_call):
        self.source_model.on_revisions_loaded(revisions, last_call)
    
    def get_repo(self):
        return self.source_model.get_repo()
    
    def hasChildren(self, parent):
        return self.source_model.hasChildren(self.mapToSource(parent))


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
        
        self.setSelectionMode(QtGui.QAbstractItemView.ExtendedSelection)
        
        self.tree = None
        self.branch = None
        
        self.tree_model = TreeModel(self)
        self.tree_filter_model = TreeFilterProxyModel()
        self.tree_filter_model.setSourceModel(self.tree_model)
        self.setModel(self.tree_filter_model)
        #self.setModel(self.tree_model)
        
        self.set_header_width_settings()

        self.setItemDelegateForColumn(self.tree_model.REVNO,
                                      RevNoItemDelegate(parent=self))

        self.create_context_menu()
        
        self.connect(self,
                     QtCore.SIGNAL("doubleClicked(QModelIndex)"),
                     self.do_default_action)
    
    def set_header_width_settings(self):
        header = self.header()
        header.setStretchLastSection(False)
        header.setResizeMode(self.tree_model.NAME, QtGui.QHeaderView.ResizeToContents)
        header.setResizeMode(self.tree_model.DATE, QtGui.QHeaderView.Interactive)
        header.setResizeMode(self.tree_model.REVNO, QtGui.QHeaderView.Interactive)
        header.setResizeMode(self.tree_model.MESSAGE, QtGui.QHeaderView.Stretch)
        header.setResizeMode(self.tree_model.AUTHOR, QtGui.QHeaderView.Interactive)        
        header.setResizeMode(self.tree_model.STATUS, QtGui.QHeaderView.Stretch)        
        fm = self.fontMetrics()
        # XXX Make this dynamic.
        col_margin = 6
        header.resizeSection(self.tree_model.REVNO,
                             fm.width("8888.8.888") + col_margin)
        header.resizeSection(self.tree_model.DATE,
                             fm.width("88-88-8888 88:88") + col_margin)
        header.resizeSection(self.tree_model.AUTHOR,
                             fm.width("Joe I have a Long Name") + col_margin)        
        if self.tree and isinstance(self.tree, WorkingTree):
            header.setResizeMode(self.tree_model.NAME, QtGui.QHeaderView.Stretch)
            header.setResizeMode(self.tree_model.STATUS, QtGui.QHeaderView.ResizeToContents)        
            
    
    def create_context_menu(self):
        self.context_menu = QtGui.QMenu(self)
        self.action_open_file = self.context_menu.addAction(
                                    gettext("&Open"),
                                    self.open_file)
        self.action_show_file = self.context_menu.addAction(
                                    gettext("&View"),
                                    self.show_file_content)
        self.action_show_annotate = self.context_menu.addAction(
                                    gettext("Show &annotate"), 
                                    self.show_file_annotate)
        self.action_show_log = self.context_menu.addAction(
                                    gettext("Show &log"),
                                    self.show_file_log)
        if has_ext_diff():
            diff_menu = ExtDiffMenu(self)
            self.action_show_diff = self.context_menu.addMenu(diff_menu)
            self.connect(diff_menu,
                         QtCore.SIGNAL("triggered(QString)"),
                         self.show_differences)
        else:
            self.action_show_diff = self.context_menu.addAction(
                                    gettext("Show &differences"),
                                    self.show_differences)
        
        self.context_menu.addSeparator()
        self.action_add = self.context_menu.addAction(
                                    gettext("&Add"),
                                    self.add)
        self.action_revert = self.context_menu.addAction(
                                    gettext("&Revert"),
                                    self.revert)
    
    def set_tree(self, tree, branch=None,
                 changes_mode=False, want_unversioned=True,
                 initial_checked_paths=None):
        """Causes a tree to be loaded, and displayed in the widget.

        @param changes_mode: If in changes mode, a list of changes, and
                             unversioned items, rather than a tree, is diplayed.
                             e.g., when not in changes mode, one will get:
                             
                             dir1
                                file1              changed
                             file2                 changed
                             
                             but when in changes mode, one will get:
                             
                             dir1/file1             changed
                             file2                  changed
                             
                             When in changes mode, no unchanged items are shown.
        """
        self.tree = tree
        if isinstance(tree, RevisionTree) and branch is None:
            raise AttributeError("A branch must be provided if the tree is a "
                                 "RevisionTree")
        self.branch = branch
        self.changes_mode = changes_mode
        self.want_unversioned = want_unversioned
        self.tree_model.set_tree(self.tree, self.branch,
                                 changes_mode, want_unversioned)
        if initial_checked_paths is not None and not self.tree_model.checkable:
            raise AttributeError("You can't have a initial_selection if "
                                 "tree_model.checkable is not True.")
        if initial_checked_paths is not None:
            self.tree_model.set_checked_paths(initial_checked_paths)
        
        self.tree_filter_model.invalidateFilter()
        
        if str(QtCore.QT_VERSION_STR).startswith("4.4"):
            # 4.4.x have a bug where if you do a layoutChanged when using
            # a QSortFilterProxyModel, it loses all header width settings.
            # So if you are using 4.4, we have to reset the width settings
            # after every time we do a layout changed. The issue is similar to 
            # http://www.qtsoftware.com/developer/task-tracker/index_html?method=entry&id=236755
            self.set_header_width_settings()
        
        header = self.header()
        if isinstance(self.tree, WorkingTree):
            # We currently have to hide the revision columns, because the
            # revision property is not availible from the WorkingTree.inventory.
            # We may be able to get this by looking at the revision tree for
            # the revision of the basis tree.
            header.hideSection(self.tree_model.DATE)
            header.hideSection(self.tree_model.REVNO)
            header.hideSection(self.tree_model.MESSAGE)
            header.hideSection(self.tree_model.AUTHOR)
            header.showSection(self.tree_model.STATUS)
            header.setResizeMode(self.tree_model.NAME, QtGui.QHeaderView.Stretch)
            header.setResizeMode(self.tree_model.STATUS, QtGui.QHeaderView.ResizeToContents)        
            
            self.context_menu.setDefaultAction(self.action_open_file)
        else:
            header.showSection(self.tree_model.DATE)
            header.showSection(self.tree_model.REVNO)
            header.showSection(self.tree_model.MESSAGE)
            header.showSection(self.tree_model.AUTHOR)
            header.hideSection(self.tree_model.STATUS)
            header.setResizeMode(self.tree_model.NAME, QtGui.QHeaderView.ResizeToContents)
            header.setResizeMode(self.tree_model.STATUS, QtGui.QHeaderView.Stretch)        
            
            self.context_menu.setDefaultAction(self.action_show_file)
        
        if sys.platform.startswith("win"):
            # This is to fix Bug 402276, where the treewidget does not get
            # repainted when you scroll.
            # (https://bugs.launchpad.net/qbzr/+bug/402276)
            # I think that this is a bug with qt, and so this is just a work-
            # arround. We should check when we bump the min qt version to 4.5 if
            # we can take this out. I think it only happens on windows. This may
            # need to be checked.
            for row in range(len(
                            self.tree_model.inventory_data[0].children_ids)):
                index = self.tree_model.createIndex(row, self.tree_model.NAME,
                                                    0)
                self.tree_model.emit(
                    QtCore.SIGNAL("dataChanged(QModelIndex, QModelIndex)"),
                    index, index)
    
    def iter_expanded_indexes(self):
        parents_to_check = [QtCore.QModelIndex()]
        while parents_to_check:
            parent = parents_to_check.pop(0)
            for row in xrange(self.tree_filter_model.rowCount(parent)):
                child = self.tree_filter_model.index(row, 0, parent)
                if self.isExpanded(child):
                    parents_to_check.append(child)
                    yield self.tree_filter_model.mapToSource(child)
    
    def set_expanded_indexes(self, indexes):
        for index in indexes:
            self.expand(self.tree_filter_model.mapFromSource(index))
    
    def get_state(self):
        if self.tree_model.checkable:
            checked = [(self.tree_model.item2ref(item_data), item_data.checked)
                       for item_data in self.tree_model.inventory_data[1:]]
        else:
            checked = None
        expanded = self.tree_model.indexes2refs(
                                            self.iter_expanded_indexes())
        selected = self.tree_model.indexes2refs(
            self.get_selection_indexes())
        return (checked, expanded, selected)
    
    def restore_state(self, state):
        (checked, expanded, selected) = state
        self.tree.lock_read()
        try:
            if self.tree_model.checkable and checked is not None:
                for (ref, state) in checked:
                    if not state == QtCore.Qt.PartiallyChecked:
                        try:
                            index = self.tree_model.ref2index(ref)
                            self.tree_model.setData(index,
                                                    QtCore.QVariant(state),
                                                    QtCore.Qt.CheckStateRole)
                        except (errors.NoSuchId, errors.NoSuchFile):
                            pass
            
            self.set_expanded_indexes(
                self.tree_model.refs2indexes(expanded,
                                             ignore_no_file_error=True))
            
            for index in self.tree_model.refs2indexes(selected,
                                                    ignore_no_file_error=True):
                # XXX This does not work for sub items. I can't figure out why.
                # GaryvdM - 14/07/2009
                self.selectionModel().select(
                    self.tree_filter_model.mapFromSource(index),
                    QtGui.QItemSelectionModel.SelectCurrent |
                    QtGui.QItemSelectionModel.Rows)
        finally:
            self.tree.unlock()

    def refresh(self):
        self.tree.lock_read()
        try:
            state = self.get_state()
            self.tree_model.set_tree(self.tree, self.branch,
                                     self.changes_mode, self.want_unversioned)
            self.restore_state(state)
            self.tree_filter_model.invalidateFilter()
            if str(QtCore.QT_VERSION_STR).startswith("4.4"):
                # 4.4.x have a bug where if you do a layoutChanged when using
                # a QSortFilterProxyModel, it loses all header width settings.
                # So if you are using 4.4, we have to reset the width settings
                # after every time we do a layout changed. The issue is similar to 
                # http://www.qtsoftware.com/developer/task-tracker/index_html?method=entry&id=236755
                self.set_header_width_settings()
        finally:
            self.tree.unlock()

    def contextMenuEvent(self, event):
        self.filter_context_menu()
        self.context_menu.popup(event.globalPos())
        event.accept()
    
    def get_selection_indexes(self, indexes=None):
        if indexes is None or (len(indexes) == 1 and indexes[0] is None):
            indexes = self.selectionModel().selectedRows(0)
        return [self.tree_filter_model.mapToSource(index) for index in indexes]
    
    def get_selection_items(self, indexes=None):
        items = []
        indexes = self.get_selection_indexes(indexes) 
        for index in indexes:
            items.append(self.tree_model.inventory_data[index.internalId()])
        return items

    def filter_context_menu(self):
        is_working_tree = isinstance(self.tree, WorkingTree)
        items = self.get_selection_items()
        versioned = [not isinstance(item.item, UnversionedItem)
                     for item in items]
        changed = [item.change is not None
                   for item in items]
        versioned_changed = [ver and ch for ver,ch in zip(versioned, changed)]
        
        selection_len = len(items)
        
        single_item_in_tree = (selection_len == 1 and
            (items[0].change is None or items[0].change[6][1] is not None))
        single_file = (single_item_in_tree and items[0].item.kind == "file")
        single_versioned_file = (single_file and versioned[0])
        
        self.action_open_file.setEnabled(single_item_in_tree)
        self.action_open_file.setVisible(is_working_tree)
        self.action_show_file.setEnabled(single_file)
        self.action_show_annotate.setEnabled(single_versioned_file)
        self.action_show_log.setEnabled(any(versioned))
        self.action_show_diff.setVisible(is_working_tree)
        self.action_show_diff.setEnabled(any(versioned_changed))
        
        self.action_add.setVisible(is_working_tree)
        self.action_add.setDisabled(all(versioned))
        self.action_revert.setVisible(is_working_tree)
        self.action_revert.setEnabled(any(versioned_changed))
        
        if is_working_tree:
            if any(versioned_changed):
                self.context_menu.setDefaultAction(self.action_show_diff)
            else:
                self.context_menu.setDefaultAction(self.action_open_file)
            
    
    def do_default_action(self, index):
        item_data = self.get_selection_items([index])[0]
        if item_data.item.kind == "directory":
            # Don't do anything, so that the directory can be expanded.
            return
        
        if isinstance(self.tree, WorkingTree):
            if item_data.change is not None and item_data.change.is_versioned():
                self.show_differences(index=index)
            else:
                self.open_file(index)
        else:
            self.show_file_content(index)

    @ui_current_widget
    def show_file_content(self, index=None):
        """Launch qcat for one selected file."""
        items = self.get_selection_items([index])
        if not len(items) == 1:
            return
        item = items[0]
        
        encoding = get_set_encoding(None, self.branch)
        if not isinstance(item.item, UnversionedItem):
            window = QBzrCatWindow(filename = item.path,
                                   tree = self.tree,
                                   parent=self,
                                   encoding=encoding)
        else:
            window = QBzrViewWindow(filename=item.path,
                                    encoding=encoding,
                                    parent=self)
        window.show()
        self.window().windows.append(window)

    @ui_current_widget
    def open_file(self, index=None):
        """Open the file in the os specified editor."""
        
        if not isinstance(self.tree, WorkingTree):
            raise RuntimeException("Tree must be a working tree to open a file.")
            
        items = self.get_selection_items([index])
        if not len(items) == 1:
            return
        item = items[0]
        
        self.tree.lock_read()
        abspath = self.tree.abspath(item.path)
        
        url = QtCore.QUrl.fromLocalFile(abspath)
        result = QtGui.QDesktopServices.openUrl(url)

    @ui_current_widget
    def show_file_log(self):
        """Show qlog for one selected file(s)."""
        
        items = self.get_selection_items()
        fileids = [item.item.file_id for item in items
                   if item.item.file_id is not None]
        
        window = LogWindow(None, self.branch, fileids)
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

    @ui_current_widget
    def show_differences(self, ext_diff=None, index=None):
        """Show differences for selected file(s)."""
        
        items = self.get_selection_items([index])
        if len(items) > 0:
            # Only paths that have changes.
            paths = [item.path
                     for item in items
                     if item.change is not None]
        else:
            # Show all.
            paths = None
        
        arg_provider = InternalWTDiffArgProvider(
            None, self.tree,
            self.tree.branch, self.tree.branch,
            specific_files=paths)
        
        show_diff(arg_provider, ext_diff=ext_diff,
                  parent_window=self.window())


    @ui_current_widget
    def add(self):
        """Add selected file(s)."""
        
        items = self.get_selection_items()
        
        # Only paths that are not versioned.
        paths = [item.path
                 for item in items
                 if isinstance(item.item, UnversionedItem)]
        
        if len(paths) == 0:
            return
        
        args = ["add"]
        args.extend(paths)
        desc = (gettext("Add %s to the tree.") % ", ".join(paths))
        revert_dialog = SimpleSubProcessDialog(gettext("Add"),
                                               desc=desc,
                                               args=args,
                                               dir=self.tree.basedir,
                                               parent=self,
                                               hide_progress=True,)
        res = revert_dialog.exec_()
        if res == QtGui.QDialog.Accepted:
            self.refresh()

    @ui_current_widget
    def revert(self):
        """Revert selected file(s)."""
        
        items = self.get_selection_items()
        
        # Only paths that have changes.
        paths = [item.path
                 for item in items
                 if item.change is not None and
                    not isinstance(item.item, UnversionedItem)]
        
        if len(paths) == 0:
            return
        
        args = ["revert"]
        args.extend(paths)
        desc = (gettext("Revert %s to latest revision.") % ", ".join(paths))
        revert_dialog = SimpleSubProcessDialog(gettext("Revert"),
                                         desc=desc,
                                         args=args,
                                         dir=self.tree.basedir,
                                         parent=self,
                                         hide_progress=True,)
        res = revert_dialog.exec_()
        if res == QtGui.QDialog.Accepted:
            self.refresh()

class SelectAllCheckBox(QtGui.QCheckBox):
    
    def __init__(self, tree_widget, parent=None):
        QtGui.QCheckBox.__init__(self, gettext("Select / deselect all"), parent)
        
        self.tree_widget = tree_widget
        #self.setTristate(True)
        
        self.connect(tree_widget.tree_model,
                     QtCore.SIGNAL("dataChanged(QModelIndex, QModelIndex)"),
                     self.on_data_changed)
        
        self.connect(self, QtCore.SIGNAL("clicked(bool)"),
                     self.clicked)
    
    def on_data_changed(self, start_index, end_index):
        self.update_state()
    
    def update_state(self):
        model = self.tree_widget.tree_model
        root_index = model._index_from_id(0, model.NAME)
        
        state = model.data(root_index, QtCore.Qt.CheckStateRole)
        self.setCheckState(QtCore.Qt.CheckState(state.toInt()[0]))
    
    def clicked(self, state):
        model = self.tree_widget.tree_model
        root_index = model._index_from_id(0, model.NAME)
        if state:
            state = QtCore.QVariant(QtCore.Qt.Checked)
        else:
            state = QtCore.QVariant(QtCore.Qt.Unchecked)
        
        model.setData(root_index, QtCore.QVariant(state),
                      QtCore.Qt.CheckStateRole)
