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
from bzrlib.osutils import file_kind, minimum_path_selection
from bzrlib.conflicts import TextConflict, resolve

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
from bzrlib.plugins.qbzr.lib.trace import report_exception, SUB_LOAD_METHOD

def dict_set_add(dict, key, value):
    if key in dict:
        dict[key].add(value)
    else:
        dict[key] = set((value,))

def group_large_dirs(paths):
    
    # XXX - check the performance of this method with lots of paths, and
    # deep paths.
    
    all_paths_expanded = {'':('', 0, set([]))}
    """Dict of all paths expaned, and thier depth, and a set of decendents
    they contain.
    
    The key is the path
    The value is a tuple of (path, depths, decendents)
    """
    if not paths:
        paths = frozenset(('',))
    
    for path in paths:
        if path == '':
            continue
        
        parent_paths = []
        dir_path = path
        while True:
            dir_path, name = os.path.split(dir_path)
            parent_paths.append(dir_path)
            if not dir_path:
                break
        
        lp = len(parent_paths)
        for i, dir_path in enumerate(parent_paths):
            depth = lp - i
            if dir_path in all_paths_expanded:
                all_paths_expanded[dir_path][2].add(path)
            else:
                all_paths_expanded[dir_path] = [dir_path, depth, set((path,))]
    
    container_dirs = {}
    """Dict of a container dir path, with a set of it's decendents"""
    
    def set_dir_as_container(path):
        decendents = all_paths_expanded[path][2]
        container_dirs[path] = decendents
        dir_path = path
        while dir_path:
            dir_path, name = os.path.split(dir_path)
            ans_decendents = all_paths_expanded[dir_path][2]
            ans_decendents.difference_update(decendents)
            ans_decendents.add(path)
    
    # directories included in the original paths container.
    for path, depth, decendents in all_paths_expanded.itervalues():
        if len(decendents)>0 and (path in paths):
            set_dir_as_container(path)
    
    for path, depth, decendents in sorted(all_paths_expanded.itervalues(),
                                          key=lambda x: -x[1]):
        len_decendents = len(decendents)
        # Config?
        if len_decendents>=4:
            has_ansestor_with_others = False
            dir_path = path
            while dir_path:
                dir_path, name = os.path.split(dir_path)
                if len_decendents<len(all_paths_expanded[dir_path][2]):
                    has_ansestor_with_others = True
                    break
            if has_ansestor_with_others:
                set_dir_as_container(path)
    
    set_dir_as_container('')
    return container_dirs

def missing_unversioned(missing, unversioned): 
    return (missing.change is not None and
            missing.change.is_missing() and
            unversioned.change is not None and
            unversioned.change[3][1] == False)

def move_or_rename(old_path, new_path):
    old_split = os.path.split(old_path)
    new_split = os.path.split(new_path)
    return (old_split[0] != new_split[0],
            old_split[1] != new_split[1])
    
class InternalItem(object):
    __slots__  = ["name", "kind", "file_id"]
    def __init__(self, name, kind, file_id):
        self.name = name
        self.kind = kind
        self.file_id = file_id
    
    def __repr__(self):
        return "<%s %r %s>" % (self.__class__.__name__, self.name, self.kind)
    
    revision = property(lambda self:None)


class ModelItemData(object):
    __slots__ = ["id", "item", "change", "checked", "children_ids",
                 "parent_id", "row", "path", "icon", "conflicts"]
    
    def __init__(self, path, item=None, change=None, conflicts=None):
        self.path = path
        self.item = item
        self.change = change
        if conflicts is None:
            self.conflicts = []
        else:
            self.conflicts = conflicts
        self.checked = QtCore.Qt.Unchecked
            
        self.children_ids = None
        self.parent_id = None
        self.id = None
        self.row = None
        self.icon = None

    def dirs_first_sort_key(self):
        """
        Gives a string key that will sort directories before files
        
        This works by annotating each path segment with either 'D' or 'F', so
        that directories compare smaller than files on the same level.
        """
        item = self.item
        if item.kind == "directory":
            return "D" + item.name.replace("/", "/D")
        if "/" not in item.name:
            return "F" + item.name
        path, f = item.name.rsplit("/", 1)
        return "D" + path.replace("/", "/D") + "/F" + f

    def __repr__(self):
        return "<ModelItemData %s, %r>" % (self.path, self.item,)


class PersistantItemReference(object):
    """This is use to stores a reference to a item that is persisted when we
    refresh the model."""
    __slots__ = ["file_id", "path"]
    
    def __init__(self, file_id, path):
        self.file_id = file_id
        self.path = path

    def __repr__(self):
        return "<%s %s %s>" % (self.__class__.__name__, self.path, self.file_id)

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
    [8]: ignore_pattern  -> If the file name matches ignore pattern then
                            this value holds corresponding pattern,
                            otherwise None.
    
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
    
    def is_on_disk(desc):
        """Is the file or folder actualy on the disk"""
        return desc[6][1] is not None

    def is_misadded(desc):
        """Check if file was added to the working tree but then gone
        (i.e. deleted manually, without invoking `bzr remove` command)
        """
        return (desc[3] == (False, True) and desc[6][1] is None)
    
    def is_ignored(desc):
        """Returns ignore pattern if file is ignored;
        None if none pattern match;
        False is there is pattern but file actually versioned.
        """
        if len(desc) > 8:
            # ignored is when file match ignore pattern and not versioned
            return desc[8] and desc[3] == (False, False)
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
            if kind[1] is None:
                return gettext("added, missing")
            else:
                return gettext("added")
        elif versioned == (True, False):
            return gettext("removed")
        elif kind[0] is not None and kind[1] is None:
            return gettext("missing")
        else:
            # versioned = True, True - so either renamed or modified
            # or properties changed (x-bit).
            mod_strs = []
            
            if parent[0] != parent[1]:
                mod_strs.append(gettext("moved"))
            if name[0] != name[1]:
                mod_strs.append(gettext("renamed"))
            if changed_content:
                mod_strs.append(gettext("modified"))
            if executable[0] != executable[1]:
                mod_strs.append(gettext("x-bit"))
            return ", ".join(mod_strs)


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

        self.missing_icon = QtGui.QIcon()
        if parent is not None:
            # TreeModel is subclass of QtCore.QAbstractItemModel,
            # the latter can have parent in constructor
            # as instance of QModelIndex and the latter does not have style()
            style = parent.style()
            self.file_icon = style.standardIcon(QtGui.QStyle.SP_FileIcon)
            self.dir_icon = style.standardIcon(QtGui.QStyle.SP_DirIcon)
            self.symlink_icon = style.standardIcon(QtGui.QStyle.SP_FileLinkIcon)
            self.missing_icon.addFile(':/16x16/missing.png')
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
        self.parent_view = parent
        self._index_cache = {}
    
    def set_tree(self, tree, branch=None, 
                 changes_mode=False, want_unversioned=True,
                 initial_checked_paths=None,
                 change_load_filter=None,
                 load_dirs=None):
        self.tree = tree
        self.branch = branch
        self.revno_map = None
        self.changes_mode = changes_mode
        
        self.unver_by_parent = {}
        self.inventory_data_by_path = {}
        self.inventory_data_by_id = {}
        self._index_cache = {}
        
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
                        
                        if (change_load_filter is not None and
                            not change_load_filter(change)):
                            continue
                        
                        item = InternalItem("", change.kind(), fileid)
                        item_data = ModelItemData(path, change=change, item=item)
                        
                        self.inventory_data_by_path[path] = item_data
                        if fileid:
                            self.inventory_data_by_id[fileid] = item_data
                    
                    for conflict in self.tree.conflicts():
                        path = conflict.path
                        if path in self.inventory_data_by_path:
                            self.inventory_data_by_path[path].\
                                conflicts.append(conflict)
                        else:
                            item_data = ModelItemData(path,
                                                      conflicts=[conflict])
                            fileid = conflict.file_id
                            kind = file_kind(self.tree.abspath(path))
                            item_data.item = InternalItem("", kind, fileid)
                            self.inventory_data_by_path[path] = item_data
                            if fileid:
                                self.inventory_data_by_id[fileid] \
                                    = item_data
                    
                    if initial_checked_paths:
                        # Add versioned directories so that we can easily check
                        # them.
                        for path in initial_checked_paths:
                            fileid = self.tree.path2id(path)
                            if fileid:
                                kind = self.tree.kind(fileid)
                                if kind == "directory":
                                    item = InternalItem("", kind, fileid)
                                    item_data = ModelItemData(path, change=change, item=item)
                                    self.inventory_data_by_path[path] = item_data
                                    self.inventory_data_by_id[fileid] = item_data
                    
                    def get_name(dir_fileid, dir_path, path, change):
                        if dir_path:
                            name = path[len(dir_path)+1:]
                        else:
                            name = path
                        if change and change.is_renamed():
                            root_id = basis_tree.get_root_id()
                            old_inventory_item = basis_tree.inventory[change.fileid()]
                            old_names = [old_inventory_item.name]
                            while old_inventory_item.parent_id:
                                if old_inventory_item.parent_id == dir_fileid:
                                    break
                                old_inventory_item = basis_tree.inventory[old_inventory_item.parent_id]
                                old_names.append(old_inventory_item.name)
                            old_names.reverse()
                            old_path = "/".join(old_names)
                            name = "%s => %s" % (old_path, name)
                        return name
                    
                    if changes_mode:
                        self.unver_by_parent = group_large_dirs(
                            frozenset(self.inventory_data_by_path.iterkeys()))
                        
                        # Add items for directories added
                        for path in self.unver_by_parent.iterkeys():
                            if path not in self.inventory_data_by_path:
                                kind = "directory"
                                file_id = self.tree.path2id(path)
                                item = InternalItem("", kind, file_id)
                                item_data = ModelItemData(path, item=item)
                                self.inventory_data_by_path[path] = item_data
                                if file_id: 
                                    self.inventory_data_by_id[file_id] = item_data
                        
                        # Name setting
                        for dir_path, decendents in \
                                self.unver_by_parent.iteritems():
                            dir_fileid = self.tree.path2id(dir_path)
                            for path in decendents:
                                item_data = self.inventory_data_by_path[path]
                                item_data.item.name = get_name(
                                    dir_fileid, dir_path, path,
                                    item_data.change)
                    else:
                        # record the unversioned items
                        for item_data in self.inventory_data_by_path.itervalues():
                            if item_data.change and not item_data.change.is_versioned():
                                parent_path, name = os.path.split(item_data.path)
                                dict_set_add(self.unver_by_parent, parent_path,
                                             item_data.path)
                        
                        # Name setting
                        for item_data in self.inventory_data_by_path.itervalues():
                            dir_path, name = os.path.split(item_data.path)
                            dir_fileid = self.tree.path2id(dir_path)
                            item_data.item.name = get_name(
                                dir_fileid, dir_path, item_data.path,
                                item_data.change)
                finally:
                    basis_tree.unlock()
                self.process_inventory(self.working_tree_get_children,
                                       initial_checked_paths, load_dirs)
            finally:
                tree.unlock()
        else:
            self.process_inventory(self.revision_tree_get_children,
                                   initial_checked_paths, load_dirs)
    
    def revision_tree_get_children(self, item_data):
        for child in item_data.item.children.itervalues():
            path = self.tree.id2path(child.file_id)
            yield ModelItemData(path, item=child)
    
    def working_tree_get_children(self, item_data):
        item = item_data.item
        if item.file_id is None:
            abspath = self.tree.abspath(item_data.path)
            
            for name in os.listdir(abspath):
                path = item_data.path+"/"+name
                (kind,
                 executable,
                 stat_value) = self.tree._comparison_data(None, path)
                child = InternalItem(name, kind, None)
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
                yield ModelItemData(path, item=child, change=change)
        
        if (not isinstance(item, InternalItem) and
            item.children is not None and not self.changes_mode):
            #Because we create copies, we have to get the real item.
            item = self.tree.inventory[item.file_id]
            for child in item.children.itervalues():
                # Create a copy so that we don't have to hold a lock of the wt.
                child = child.copy()
                if child.file_id in self.inventory_data_by_id:
                    child_item_data = self.inventory_data_by_id[child.file_id]
                else:
                    path = self.tree.id2path(child.file_id)
                    child_item_data = ModelItemData(path)
                
                child_item_data.item = child
                yield child_item_data
        
        if item_data.path in self.unver_by_parent:
            for path in self.unver_by_parent[item_data.path]:
                yield self.inventory_data_by_path[path]
    
    def load_dir(self, dir_id):
        if dir_id>=len(self.inventory_data):
            return
        dir_item = self.inventory_data[dir_id]
        if dir_item.children_ids is not None:
            return 
        
        self.tree.lock_read()
        try:
            dir_item.children_ids = []
            children = sorted(self.get_children(dir_item),
                              key=ModelItemData.dirs_first_sort_key)
            parent_model_index = self._index_from_id(dir_id, 0)
            self.beginInsertRows(parent_model_index, 0, len(children)-1)
            try:
                for child in children:
                    child_id = self.append_item(child, dir_id)
                    dir_item.children_ids.append(child_id)
            finally:
                self.endInsertRows();
        finally:
            self.tree.unlock()
    
    def process_inventory(self, get_children, initial_checked_paths, load_dirs):
        self.get_children = get_children
        
        self.emit(QtCore.SIGNAL("layoutAboutToBeChanged()"))
        
        is_refresh = len(self.inventory_data)>0
        if is_refresh:
            self.beginRemoveRows(QtCore.QModelIndex(), 0,
                                 len(self.inventory_data[0].children_ids)-1)
        self.inventory_data = []
        if is_refresh:
            self.endRemoveRows()
            
        root_item = ModelItemData(
            '', item=self.tree.inventory[self.tree.get_root_id()])
        
        root_id = self.append_item(root_item, None)
        self.load_dir(root_id)
        
        if load_dirs:
            # refs2indexes will load the parents if nesseary.
            for index in self.refs2indexes(load_dirs,
                                           ignore_no_file_error=True):
                self.load_dir(index.internalId())
        
        if self.checkable:
            if initial_checked_paths is not None:
                self.set_checked_paths(initial_checked_paths)
            else:
                self.setData(self._index_from_id(root_id,self.NAME), 
                             QtCore.QVariant(QtCore.Qt.Checked),
                             QtCore.Qt.CheckStateRole)
        self.emit(QtCore.SIGNAL("layoutChanged()"))
    
    def append_item(self, item_data, parent_id):
        item_data.id = len(self.inventory_data)
        if parent_id is not None:
            parent_data = self.inventory_data[parent_id]
            item_data.row = len(parent_data.children_ids)
        else:
            # Root Item
            item_data.row = 0
        item_data.parent_id = parent_id
        self.inventory_data.append(item_data)
        self.inventory_data_by_path[item_data.path] = item_data
        if item_data.item.file_id is not None:
            self.inventory_data_by_id[item_data.item.file_id] = item_data
        return item_data.id
    
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
        
        cache_key = (parent_id, row, column)
        if cache_key in self._index_cache:
            return self._index_cache[cache_key]
        else:
            parent_data = self.inventory_data[parent_id]
            if parent_data.children_ids is None:
                return QtCore.QModelIndex()
            
            if (row < 0 or
                row >= len(parent_data.children_ids) or
                column < 0 or
                column >= len(self.HEADER_LABELS)):
                return QtCore.QModelIndex()
            item_id = parent_data.children_ids[row]
            index = self.createIndex(row, column, item_id)
            self._index_cache[cache_key] = index
            return index
    
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
            def set_child_checked_recurse(item_data):
                if (item_data.children_ids is None and
                    item_data.item.kind == "directory"):
                    self.load_dir(item_data.id)
                
                if not item_data.children_ids:
                    return False
                have_changed_item = False
                
                for child_id in item_data.children_ids:
                    child = self.inventory_data[child_id]
                    
                    has_children_changed = set_child_checked_recurse(child)

                    # If unchecking, uncheck everything, but if checking,
                    # only check those in "select_all" get checked.
                    if (self.is_item_in_select_all(child) or
                        value == QtCore.Qt.Unchecked or
                        has_children_changed):
                        have_changed_item = True
                        set_checked(child, value)
                return have_changed_item
            set_child_checked_recurse(item_data)
            
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
        
        if index.column() == self.NAME and role == QtCore.Qt.EditRole:
            if not isinstance(self.tree, WorkingTree):
                return False
            # Rename
            value = unicode(value.toString())
            item_data = self.inventory_data[index.internalId()]
            parent = self.inventory_data[item_data.parent_id]
            new_path = os.path.join(parent.path, value)
            try:
                if item_data.item.file_id:
                    # Versioned file
                    self.tree.rename_one(item_data.path, new_path)
                else:
                    old_path_abs=self.tree.abspath(item_data.path)
                    new_path_abs=self.tree.abspath(new_path)
                    os.rename(old_path_abs, new_path_abs)
            except Exception:
                report_exception(type=SUB_LOAD_METHOD,
                                 window=self.parent_view.window())
            # We do this so that the ref has the new_path, and hence refresh
            # restores it's state correctly.
            item_data.path = new_path
            ref = self.index2ref(index)
            self.parent_view.refresh()
            try:
                new_index = self.ref2index(ref)
                new_index = self.parent_view.tree_filter_model.mapFromSource(
                                                                        new_index)
                self.parent_view.scrollTo(new_index)
            except (errors.NoSuchId, errors.NoSuchFile):
                pass
            return True
            
        return False
    
    REVID = QtCore.Qt.UserRole + 1
    FILEID = QtCore.Qt.UserRole + 2
    PATH = QtCore.Qt.UserRole + 3
    
    def data(self, index, role):
        if not index.isValid():
            return QtCore.QVariant()
        
        if role >= QtCore.Qt.FontRole and role <= QtCore.Qt.TextColorRole:
            return QtCore.QVariant()
        
        item_data = self.inventory_data[index.internalId()]
        item = item_data.item
        
        if role == self.FILEID:
            return QtCore.QVariant(item.file_id)
        
        column = index.column()
        if column == self.NAME:
            if role == QtCore.Qt.DisplayRole:
                return QtCore.QVariant(item.name)
            if role == QtCore.Qt.EditRole:
                parent = self.inventory_data[item_data.parent_id]
                return QtCore.QVariant(item_data.path[len(parent.path):])
            if role == QtCore.Qt.DecorationRole:
                if item_data.icon is None:
                    if item_data.change and not item_data.change.is_on_disk():
                        item_data.icon = QtCore.QVariant(self.missing_icon)
                    elif isinstance(self.tree, WorkingTree):
                        abspath = self.tree.abspath(item_data.path)
                        info = QtCore.QFileInfo(abspath)
                        item_data.icon = \
                                QtCore.QVariant(self.icon_provider.icon(info))
                    else:
                        if item.kind == "file":
                            item_data.icon = QtCore.QVariant(self.file_icon)
                        if item.kind == "directory":
                            item_data.icon = QtCore.QVariant(self.dir_icon)
                        if item.kind == "symlink":
                            item_data.icon = QtCore.QVariant(self.symlink_icon)
                if item_data.icon is None:
                    item_data.icon = QtCore.QVariant()
                return item_data.icon
            
            if role ==  QtCore.Qt.CheckStateRole:
                if not self.checkable:
                    return QtCore.QVariant()
                else:
                    return QtCore.QVariant(item_data.checked)
        
        if column == self.STATUS:
            if role == QtCore.Qt.DisplayRole:
                status = []
                if item_data.change is not None:
                    status.append(item_data.change.status())
                for conflict in item_data.conflicts:
                    status.append(conflict.typestring)
                return QtCore.QVariant(", ".join(status))
        
        revid = item_data.item.revision
        if role == self.REVID:
            if revid is None:
                return QtCore.QVariant()
            else:
                return QtCore.QVariant(revid)
        
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
        
        flags = (QtCore.Qt.ItemIsEnabled |
                 QtCore.Qt.ItemIsSelectable)
        
        if isinstance(self.tree, WorkingTree):
            flags = flags | QtCore.Qt.ItemIsDragEnabled
        
        if index.column() == self.NAME:
            flags = flags | QtCore.Qt.ItemIsEditable
            if self.checkable:
                flags = flags | QtCore.Qt.ItemIsUserCheckable
        
        id = index.internalId()
        if id < len(self.inventory_data):
            item_data = self.inventory_data[index.internalId()]
            if item_data.item.kind == "directory":
                flags = flags | QtCore.Qt.ItemIsDropEnabled
        
        return flags

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
        return PersistantItemReference(item_data.item.file_id,
                                       item_data.path)
    
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
                parent_id = self.tree.inventory[ref.file_id].parent_id
                parent_ids = []
                while parent_id is not None:
                    parent_ids.append(parent_id)
                    parent_id = self.tree.inventory[parent_id].parent_id
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
        
        for item_data in self.inventory_data[1:]:
            if item_data.checked == QtCore.Qt.Checked:
                yield self.item2ref(item_data)

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
    
    def supportedDropActions(self):
        return QtCore.Qt.MoveAction


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
        # This is slow. It causes TreeModel.index, and TreeModel.data thousands
        # of times. 
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
        
        is_versioned = item_data.item.file_id is not None
        
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
        self.setUniformRowHeights(True)
        self.setEditTriggers(QtGui.QAbstractItemView.NoEditTriggers)
        self.viewport().setAcceptDrops(True)
        self.setDropIndicatorShown(True)
        self.setDragDropMode(QtGui.QAbstractItemView.InternalMove);
        
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
        col_margin = (self.style().pixelMetric(QtGui.QStyle.PM_FocusFrameHMargin,
                                               None, self) + 1) *2
        
        header.resizeSection(self.tree_model.REVNO,
                             fm.width("8888.8.888") + col_margin)
        header.resizeSection(self.tree_model.DATE,
                             fm.width("88-88-8888 88:88") + col_margin)
        header.resizeSection(self.tree_model.AUTHOR,
                             fm.width("Joe I have a Long Name") + col_margin)        
        if self.tree and isinstance(self.tree, WorkingTree):
            header.setResizeMode(self.tree_model.NAME, QtGui.QHeaderView.Stretch)
            header.setResizeMode(self.tree_model.STATUS, QtGui.QHeaderView.ResizeToContents)
    
    def set_visible_headers(self):
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

    def set_tree(self, tree, branch=None,
                 changes_mode=False, want_unversioned=True,
                 initial_checked_paths=None,
                 change_load_filter=None):
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

        @param initial_checked_paths: list of specific filenames
            which should be selected in the widget. By default all items
            selected. Value None or empty list means: all selected.
        """
        self.tree = tree
        if isinstance(tree, RevisionTree) and branch is None:
            raise AttributeError("A branch must be provided if the tree is a "
                                 "RevisionTree")
        self.branch = branch
        self.changes_mode = changes_mode
        self.want_unversioned = want_unversioned
        self.change_load_filter = change_load_filter
        
        if str(QtCore.QT_VERSION_STR).startswith("4.4"):
            # 4.4.x have a bug where if you do a layoutChanged when using
            # a QSortFilterProxyModel, it loses all header width settings.
            # So if you are using 4.4, we have to reset the width settings
            # after every time we do a layout changed. The issue is similar to 
            # http://www.qtsoftware.com/developer/task-tracker/index_html?method=entry&id=236755
            self.set_header_width_settings()
        self.set_visible_headers()
        QtCore.QCoreApplication.processEvents()
        
        if initial_checked_paths and not self.tree_model.checkable:
            raise AttributeError("You can't have a initial_selection if "
                                 "tree_model.checkable is not True.")
        
        self.tree_model.set_tree(self.tree, self.branch,
                                 changes_mode, want_unversioned,
                                 change_load_filter=self.change_load_filter,
                                 initial_checked_paths=initial_checked_paths)
        
        if self.tree_model.checkable:
            refs = self.tree_model.iter_checked()
            indexes = self.tree_model.refs2indexes(refs)
            self.expanded_to_indexes(indexes)        
        
        if str(QtCore.QT_VERSION_STR).startswith("4.4"):
            # 4.4.x have a bug where if you do a layoutChanged when using
            # a QSortFilterProxyModel, it loses all header width settings.
            # So if you are using 4.4, we have to reset the width settings
            # after every time we do a layout changed. The issue is similar to 
            # http://www.qtsoftware.com/developer/task-tracker/index_html?method=entry&id=236755
            self.set_header_width_settings()
            self.set_visible_headers()
        
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

    def expanded_to_indexes(self, indexes):
        for index in indexes:
            while index.internalId():
                self.expand(self.tree_filter_model.mapFromSource(index))
                index = self.tree_model.parent(index)
    
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
        v_scroll = self.verticalScrollBar().value()
        return (checked, expanded, selected, v_scroll)
    
    def restore_state(self, state):
        (checked, expanded, selected, v_scroll) = state
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
            self.verticalScrollBar().setValue(v_scroll)
        finally:
            self.tree.unlock()

    def refresh(self):
        self.tree.lock_read()
        try:
            state = self.get_state()
            self.tree_model.set_tree(self.tree, self.branch,
                                     self.changes_mode, self.want_unversioned,
                                     change_load_filter=self.change_load_filter,
                                     load_dirs=state[1])
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
    
    def mousePressEvent(self, event):
        index = self.indexAt(event.pos())
        if not isinstance(self.tree, WorkingTree):
            self.setDragEnabled(False)
        if not self.selectionModel().isSelected(index):
            # Don't drag if we are not over the selection.
            self.setDragEnabled(False)
        else:
            # Don't allow draging a selection that goes across dirs.
            ok_selection = True
            item_by_path = {}
            item_ids = set()
            for item in self.get_selection_items():
                item_by_path[item.path] = item
                item_ids.add(item.id)
            root_dir = None
            for path in minimum_path_selection(item_by_path.keys()):
                dir_path, name = os.path.split(path)
                if root_dir is None:
                    root_dir = dir_path
                if dir_path != root_dir:
                    ok_selection = False
                    break
                item = item_by_path[path]
                if item.item.kind == "directory" and item.children_ids:
                    # Either all, or none of the children must be selected.
                    first = None
                    for child_id in item.children_ids:
                        this = child_id in item_ids
                        if first is None:
                            first = this
                        if first != this:
                            ok_selection = False
                            break
                    if not ok_selection:
                        break
            self.setDragEnabled(ok_selection)
            
        QtGui.QTreeView.mousePressEvent(self, event)
    
    def dropEvent(self, event):
        if not isinstance(self.tree, WorkingTree):
            return
        
        # we should encode the paths list, give it an aproite mime type, etc.
        # Eaiser to just get the selection.
        drop_index = self.tree_filter_model.mapToSource(
                                                    self.indexAt(event.pos()))
        drop_item = self.tree_model.inventory_data[drop_index.internalId()]
        if drop_item.item.kind == "directory":
            drop_path = drop_item.path
        else:
            drop_path, name = os.path.split(drop_item.path)
        paths = [item.path for item in self.get_selection_items()]
        min_paths = minimum_path_selection(paths)
        try:
            self.tree.move(paths, drop_path)
        except Exception:
            report_exception(type=SUB_LOAD_METHOD, window=self.window())        
        self.refresh()

    def contextMenuEvent(self, event):
        self.filter_context_menu()
        self.context_menu.popup(event.globalPos())
        event.accept()

    def keyPressEvent(self, event):
        """Processing Enter key to launch default action for files and
        expand/collapse directories.
        """
        e_key = event.key()
        if e_key in (QtCore.Qt.Key_Enter, QtCore.Qt.Key_Return):
            items = self.get_selection_items()
            if len(items) == 1:
                kind = items[0].item.kind
                event.accept()
                index = self.selectedIndexes()[0]
                if kind == 'directory':
                    self.setExpanded(index, not self.isExpanded(index))
                else:
                    self.do_default_action(index)
                return
        QtGui.QTreeView.keyPressEvent(self, event)

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
    
    def create_context_menu(self):
        self.context_menu = QtGui.QMenu(self)
        self.action_open_file = self.context_menu.addAction(
                                    gettext("&Open"),
                                    self.open_file)
        self.action_show_file = self.context_menu.addAction(
                                    gettext("&View file"),
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
        self.action_merge = self.context_menu.addAction(
                                    gettext("&Merge conflict"),
                                    self.merge)
        self.action_resolve = self.context_menu.addAction(
                                    gettext("Mark conflict &resolved"),
                                    self.resolve)
        
        self.context_menu.addSeparator()
        self.action_add = self.context_menu.addAction(
                                    gettext("&Add"),
                                    self.add)
        self.action_revert = self.context_menu.addAction(
                                    gettext("&Revert"),
                                    self.revert)
        self.action_rename = self.context_menu.addAction(
                                    gettext("Re&name"),
                                    self.rename)
        self.action_remove = self.context_menu.addAction(
                                    gettext("Remove"),
                                    self.remove)
        # The text for this is set per selection, depending on move or rename.
        self.action_mark_move = self.context_menu.addAction(
                                    "mv --after", 
                                    self.mark_move)
    
    def filter_context_menu(self):
        is_working_tree = isinstance(self.tree, WorkingTree)
        items = self.get_selection_items()
        versioned = [item.item.file_id is not None
                     for item in items]
        changed = [item.change is not None
                   for item in items]
        versioned_changed = [ver and ch for ver,ch in zip(versioned, changed)]
        conflicts = [len(item.conflicts)>0
                     for item in items]
        text_conflicts = [len([conflicts
                               for conflict in item.conflicts
                               if isinstance(conflict, TextConflict)])>0
                          for item in items]
        on_disk = [item.change is None or item.change.is_on_disk()
                   for item in items]
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
        
        self.action_merge.setVisible(is_working_tree)
        self.action_merge.setEnabled(any(text_conflicts))
        self.action_resolve.setVisible(is_working_tree)
        self.action_resolve.setEnabled(any(conflicts))
        
        self.action_add.setVisible(is_working_tree)
        self.action_add.setDisabled(all(versioned))
        self.action_revert.setVisible(is_working_tree)
        self.action_revert.setEnabled(any(versioned_changed))
        self.action_rename.setVisible(is_working_tree)
        self.action_rename.setEnabled(single_item_in_tree)
        self.action_remove.setVisible(is_working_tree)
        self.action_remove.setEnabled(any(on_disk))

        can_mark_move = (selection_len == 2 and
                         (missing_unversioned(items[0], items[1]) or
                          missing_unversioned(items[1], items[0])))
        self.action_mark_move.setVisible(can_mark_move)
        if can_mark_move:
            move, rename = move_or_rename(items[0].path, items[1].path)
            if move and rename:
                self.action_mark_move.setText(gettext("&Mark as moved and renamed"))
            elif move:
                self.action_mark_move.setText(gettext("&Mark as moved"))
            elif rename:
                self.action_mark_move.setText(gettext("&Mark as renamed"))
        
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
        if item.item.file_id is not None:
            window = QBzrCatWindow(filename = item.path,
                                   tree = self.tree,
                                   parent=self,
                                   encoding=encoding)
        else:
            abspath = os.path.join(self.tree.basedir, item.path)
            window = QBzrViewWindow(filename=abspath,
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
        try:
            abspath = self.tree.abspath(item.path)
        finally:
            self.tree.unlock()
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
                 if item.item.file_id is None]
        
        if len(paths) == 0:
            return
        try:
            self.tree.add(paths)
        except Exception:
            report_exception(type=SUB_LOAD_METHOD, window=self.window())
        
        # XXX - it would be good it we could just refresh the selected items
        self.refresh()

    @ui_current_widget
    def revert(self):
        """Revert selected file(s)."""
        
        items = self.get_selection_items()
        
        # Only paths that have changes.
        paths = [item.path
                 for item in items
                 if item.change is not None and
                    item.item.file_id is not None]
        
        if len(paths) == 0:
            return
        
        res = QtGui.QMessageBox.question(self,
            gettext("Revert"),
            gettext("Do you really want to revert the selected file(s)?"),
            QtGui.QMessageBox.Yes | QtGui.QMessageBox.No)
        if res == QtGui.QMessageBox.Yes:
            try:
                self.tree.lock_write()
                try:
                    self.tree.revert(paths, self.tree.basis_tree())
                finally:
                    self.tree.unlock()
            except Exception:
                report_exception(type=SUB_LOAD_METHOD, window=self.window())
            # XXX - it would be good it we could just refresh the selected items
            self.refresh()
    
    @ui_current_widget
    def merge(self):
        """Merge conflicting file in external merge app"""
        
        items = self.get_selection_items()
        
        # Only paths that have text conflicts.
        paths = [item.path
                 for item in items
                 if len([conflict
                         for conflict in item.conflicts
                         if isinstance(conflict, TextConflict)])>0]
        
        if len(paths) == 0:
            return
        
        args = ["extmerge"]
        args.extend(paths)
        desc = " ".join(args)
        window = SimpleSubProcessDialog(gettext("External Merge"),
                                         desc=desc,
                                         args=args,
                                         dir=self.tree.basedir,
                                         parent=self,
                                         auto_start_show_on_failed=True,
                                         hide_progress=True,)
        # We don't refesh the tree, because it is very unlikley to have
        # changed.

    def resolve(self):
        """Mark selected file(s) as resolved."""
        
        items = self.get_selection_items()
        
        # Only paths that have changes.
        paths = [item.path
                 for item in items
                 if len(item.conflicts)>0]
        
        if len(paths) == 0:
            return
        
        try:
            resolve(self.tree, paths)
        except Exception:
            report_exception(type=SUB_LOAD_METHOD, window=self.window())
        self.refresh()
    
    def mark_move(self):
        items = self.get_selection_items()
        if len(items) <> 2:
            return
        
        if missing_unversioned(items[0], items[1]):
            old = items[0]
            new = items[1]
        elif missing_unversioned(items[1], items[0]):
            old = items[1]
            new = items[0]
        else:
            return
        try:
            self.tree.rename_one(old.path, new.path, after=True)
        except Exception:
            report_exception(type=SUB_LOAD_METHOD, window=self.window())
        self.refresh()

    @ui_current_widget
    def rename(self):
        """Rename the selected file."""
        
        indexes = self.get_selection_indexes()
        if len(indexes) <> 1:
            return
        index = indexes[0]
        index = self.tree_filter_model.mapFromSource (index)
        self.edit(index)
    
    @ui_current_widget
    def remove(self):
        """Remove selected file(s)."""
        
        items = self.get_selection_items()
        
        # Only paths that are not missing
        paths = [item.path
                 for item in items
                 if item.change is None or 
                    item.change.is_on_disk()]
        if len(paths) == 0:
            return
        try:
            try:
                self.tree.remove(paths, keep_files=False)
            except errors.BzrRemoveChangedFilesError:
                res = QtGui.QMessageBox.question(
                    self, gettext("Remove"),
                    gettext("Some of the files selected cannot be recoverd if "
                            "removed. Are you sure you want to remove these "
                            "files?"),
                    QtGui.QMessageBox.Yes | QtGui.QMessageBox.No)
                if res == QtGui.QMessageBox.Yes:
                    self.tree.remove(paths, keep_files=False, force=True)
        except Exception:
            report_exception(type=SUB_LOAD_METHOD, window=self.window())
        
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
