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
from PyQt5 import QtCore, QtGui, QtWidgets

from breezy.plugins.qbrz.lib.i18n import gettext

from breezy.plugins.qbrz.lib.revtreeview import (
    RevisionTreeView,
    RevNoItemDelegate,
    )
from breezy.plugins.qbrz.lib.uifactory import ui_current_widget
from breezy.lazy_import import lazy_import
from breezy.plugins.qbrz.lib.lazycachedrevloader import cached_revisions
from breezy.plugins.qbrz.lib.trace import report_exception, SUB_LOAD_METHOD

lazy_import(globals(), '''
import posixpath  # to use '/' path sep in path.join().
from time import (strftime, localtime)

from breezy import errors
from breezy.workingtree import WorkingTree
from breezy.revisiontree import RevisionTree
from breezy.osutils import file_kind, minimum_path_selection
from breezy.conflicts import TextConflict, resolve
from breezy.tree import TreeChange

from breezy.plugins.qbrz.lib.cat import QBzrCatWindow, QBzrViewWindow, cat_to_native_app
from breezy.plugins.qbrz.lib.annotate import AnnotateWindow
from breezy.plugins.qbrz.lib.log import LogWindow
from breezy.plugins.qbrz.lib.util import (
    get_set_encoding,
    get_summary,
    get_apparent_author_name,
    )
from breezy.plugins.qbrz.lib.subprocess import SimpleSubProcessDialog
from breezy.plugins.qbrz.lib.diff import (
    show_diff,
    has_ext_diff,
    ExtDiffMenu,
    InternalWTDiffArgProvider,
    )

''')


def dict_set_add(dict, key, value):
    if key in dict:
        dict[key].add(value)
    else:
        dict[key] = set((value,))


def group_large_dirs(paths):
    # XXX - check the performance of this method with lots of paths, and
    # deep paths.

    all_paths_expanded = {'':('', 0, set([]))}
    """Dict of all paths expanded, and their depth, and a set of decendents
    they contain.

    The key is the path
    The value is a tuple of (path, depths, decendents)
    """
    if not paths:
        paths = frozenset(('',))

    # print('group_large_dirs...all_paths', all_paths_expanded, paths)
    for path in paths:
        # print('\t--:path:', path)
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
            depth = lp - i - 1
            if dir_path in all_paths_expanded:
                all_paths_expanded[dir_path][2].add(path)
            else:
                all_paths_expanded[dir_path] = [dir_path, depth, set((path,))]

    container_dirs = {}
    """Dict of a container dir path, with a set of its decendents"""

    paths_deep_first = sorted(iter(all_paths_expanded.values()), key=lambda x: -x[1])

    def set_dir_as_container(path):
        decendents = all_paths_expanded[path][2]
        container_dirs[path] = decendents
        dir_path = path
        while dir_path:
            dir_path, name = os.path.split(dir_path)
            ans_decendents = all_paths_expanded[dir_path][2]
            old_len = len(ans_decendents)
            ans_decendents.difference_update(decendents)
            if len(ans_decendents) < old_len:
                ans_decendents.add(path)

    # directories included in the original paths container.
    for path, depth, decendents in paths_deep_first:
        if len(decendents)>0 and (path in paths):
            set_dir_as_container(path)

    for path, depth, decendents in paths_deep_first:
        len_decendents = len(decendents)
        # Config?
        if len_decendents >= 4 and path not in container_dirs:
            has_ansestor_with_others = False
            dir_path = path
            while dir_path:
                dir_path, name = os.path.split(dir_path)
                if len_decendents < len(all_paths_expanded[dir_path][2]):
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
    """This is use to stores a reference to a item that is persisted when we refresh the model."""
    __slots__ = ["file_id", "path"]

    def __init__(self, file_id, path):
        self.file_id = file_id
        self.path = path

    def __repr__(self):
        return "<%s %s %s>" % (self.__class__.__name__, self.path, self.file_id)


class ChangeDesc:
    """Helper class that "knows" about internals of iter_changes' changed entry
    description tuple, and provides additional helper methods.

    iter_changes return tuple with info about changed entry:
    [0]: file_id         -> ascii string <-- RJL this is actually now a b'yte string
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

    ALSO: 3.1 returns:
    [8] copied           -> bool
    [9] ?
    """
    # RJLRJL TreeChange (which is returned from breezy, uses the following to
    # supply a tuple
    # def _as_tuple(self):
    #     return (self.file_id, self.path, self.changed_content, self.versioned,
    #             self.parent_id, self.name, self.kind, self.executable, self.copied)
    # 0 self.file_id
    # 1 self.path
    # 2 self.changed_content,
    # 3 self.versioned,
    # 4 self.parent_id,
    # 5 self.name,
    # 6 self.kind,
    # 7 self.executable,
    # 8 self.copied

    # XXX We should may be try get this into breezy.
    # XXX We should use this in qdiff.

    def __init__(self, tree_change_object, ignored_flag=None):
        self.change = tree_change_object
        # self.is_ignored = None
        self._is_ignored = ignored_flag

    def fileid(self):
        return self.change.file_id

    def old_or_new_path(self):  # was path()
        """Return a suitable entry for a 'specific_files' param to bzr functions."""
        oldpath, newpath = self.change.path
        return newpath or oldpath

    def oldpath(self):
        """Return oldpath for renames."""
        return self.change.path[0]

    def old_or_new_kind(self):  # was kind
        oldkind, newkind = self.change.kind
        return newkind or oldkind

    def is_versioned(self):
        return self.change.versioned != (False, False)
        # return desc[3] != (False, False)

    def is_modified(self):
        return self.is_versioned() and self.change.changed_content
        # return (desc[3] != (False, False) and desc[2])

    def is_renamed(self):
        old_tuple = (self.change.parent_id[0], self.change.name[0])
        new_tuple = (self.change.parent_id[1], self.change.name[1])
        return (self.change.versioned == (True, True) and old_tuple != new_tuple)
        # return (desc[3] == (True, True)
        #         and (desc[4][0], desc[5][0]) != (desc[4][1], desc[5][1]))

    def is_tree_root(self):
        """Check if entry actually tree root."""
        if self.is_versioned() and self.change.parent_id == (None, None):
            return True
            # if desc[3] != (False, False) and desc[4] == (None, None):
            # TREE_ROOT has no parents (desc[4]).
            # But because we could want to see unversioned files
            # we need to check for versioned flag (desc[3])
            # return True
        return False

    def is_missing(self):
        """Check if file was present in previous revision but now it's gone
        (i.e. deleted manually, without invoking `bzr remove` command)
        """
        return self.change.versioned == (True, True) and self.change.kind[1] is None
        # return (desc[3] == (True, True) and desc[6][1] is None)

    def is_on_disk(self):
        """Is the file or folder actualy on the disk"""
        return self.change.kind[1] is not None
        # return desc[6][1] is not None

    def is_misadded(self):
        """Check if file was added to the working tree but then gone
        (i.e. deleted manually, without invoking `bzr remove` command)
        """
        return self.change.versioned == (False, True) and self.change.kind[1] is None
        # return (desc[3] == (False, True) and desc[6][1] is None)

    def is_ignored(self):
        """Returns ignore pattern if file is ignored;
        None if none pattern match;
        False is there is pattern but file actually versioned.
        """
        if len(self.change._as_tuple()) > 8:
            # ignored is when file match ignore pattern and not versioned
            # HOWEVER, the old [8] position is now occupied by 'copied'
            #return self.change.copied and self.change.versioned == (False, False)
            return self._is_ignored and self.change.versioned == (False, False)
            # return desc[8] and desc[3] == (False, False)
        else:
            return None

    def dump(self):
        c = self.change
        s = "Change: file_id {0} (Path: old [{1}], new [{2}])\n".format(self.fileid(), c.path[0], c.path[1])
        s += "\tchanged? {0}, (Versioned? old {1}, new {2})\n".format(c.changed_content, c.versioned[0], c.versioned[1])
        s += "\t(parent_id old[{0}], new[{1}]), (name: old[{2}], new[{3}])\n".format(c.parent_id[0], c.parent_id[1], c.name[0], c.name[1])
        s += "\t(kind: old {0}, new {1})".format(c.kind[0], c.kind[1])
        s += " (exec old {0}, new {1}), ?? copied / ignore?? {2}\n".format(c.executable[0], c.executable[1], c.copied)
        return s

    def status(self):
        # Although _as_tuple is supposed to return 8 fields and apparently
        # sometimes 9, Breezy gives us 10, and we don't know what the last one is
        # Also, 'ignored' is called 'copied'
        desc = self.change._as_tuple()
        if len(desc) == 8:
            (file_id,
            (path_in_source, path_in_target),
             changed_content, versioned, parent, name, kind,
             executable) = desc
            is_ignored = None
        elif len(desc) == 9:
            (file_id, (path_in_source, path_in_target),
             changed_content, versioned, parent, name, kind,
             executable, is_ignored) = desc
        elif len(desc) == 10:
            (file_id, (path_in_source, path_in_target),
             changed_content, versioned, parent, name, kind,
             executable, is_ignored, unknown) = desc
        else:
            raise RuntimeError("Unkown number of items to unpack.")

        versioned = self.change.versioned
        if versioned == (False, False):
            if is_ignored:
                return gettext("ignored")
            else:
                return gettext("non-versioned")
        elif versioned == (False, True):
            # if kind[1] is None:
            if self.change.kind[1] is None:
                return gettext("added, missing")
            else:
                return gettext("added")
        elif versioned == (True, False):
            return gettext("removed")
        elif self.change.kind[0] is not None and self.change.kind[1] is None:
            return gettext("missing")
        else:
            # versioned = True, True - so either renamed or modified
            # or properties changed (x-bit).
            mod_strs = []

            if self.change.parent_id[0] != self.change.parent_id[1]:
                mod_strs.append(gettext("moved"))
            if self.change.name[0] != self.change.name[1]:
                mod_strs.append(gettext("renamed"))
            if self.change.changed_content:
                mod_strs.append(gettext("modified"))
            if self.change.executable[0] != self.change.executable[1]:
                mod_strs.append(gettext("x-bit"))
            return ", ".join(mod_strs)


class TreeModel(QtCore.QAbstractItemModel):
    layoutAboutToBeChanged = QtCore.pyqtSignal()
    layoutChanged = QtCore.pyqtSignal()
    dataChanged = QtCore.pyqtSignal(QtCore.QModelIndex, QtCore.QModelIndex)

    HEADER_LABELS = [gettext("File Name"),
                     gettext("Date"),
                     gettext("Rev"),
                     gettext("Message"),
                     gettext("Author"),
                     gettext("Status")]
    # Once again, this bizarre construct. Just... why?
    # NAME, DATE, REVNO, MESSAGE, AUTHOR, STATUS = list(range(len(HEADER_LABELS)))
    # These are the 'columns' (sic)
    NAME = 0
    DATE = 1
    REVNO = 2
    MESSAGE = 3
    AUTHOR = 4
    STATUS = 5

    def __init__(self, parent=None):
        # XXX parent object: instance of what class it supposed to be?
        QtCore.QAbstractTableModel.__init__(self, parent)

        self.missing_icon = QtGui.QIcon()
        if parent is not None:
            # TreeModel is subclass of QtCore.QAbstractItemModel,
            # the latter can have parent in constructor
            # as instance of QtCore.QModelIndex and the latter does not have style()
            style = parent.style()
            self.file_icon = style.standardIcon(QtWidgets.QStyle.SP_FileIcon)
            self.dir_icon = style.standardIcon(QtWidgets.QStyle.SP_DirIcon)
            self.symlink_icon = style.standardIcon(QtWidgets.QStyle.SP_FileLinkIcon)
            self.missing_icon.addFile(':/16x16/missing.png')
        else:
            self.file_icon = QtGui.QIcon()
            self.dir_icon = QtGui.QIcon()
            self.symlink_icon = QtGui.QIcon()

        self.tree = None
        self.inventory_data = []
        self.inventory_data_by_path = {}
        self.inventory_data_by_id = {}  # Will not contain unversioned items.
        self.checkable = False
        self.icon_provider = QtWidgets.QFileIconProvider()
        self.parent_view = parent
        self._index_cache = {}
        self.set_select_all_kind()


    def set_tree(self, tree, branch=None, changes_mode=False, want_unversioned=True,
                 initial_checked_paths=None, change_load_filter=None, load_dirs=None):
        self.tree = tree
        self.branch = branch
        self.revno_map = None
        self.changes_mode = changes_mode
        self.change_load_filter = change_load_filter

        self.layoutAboutToBeChanged.emit()

        # print('::: TreeMODEL.set_tree called :::', tree, 'branch', branch, 'initial', initial_checked_paths, 'change',
        #     change_load_filter, 'isinstance', isinstance(tree, WorkingTree), 'changes mode', changes_mode,
        #     'want unversioned?', want_unversioned)
        is_refresh = len(self.inventory_data) > 0
        if is_refresh:
            self.beginRemoveRows(QtCore.QModelIndex(), 0, len(self.inventory_data[0].children_ids) - 1)
        self.inventory_data = []
        self._index_cache = {}
        self.unver_by_parent = {}
        self.inventory_data_by_path = {}
        self.inventory_data_by_id = {}
        if is_refresh:
            self.endRemoveRows()

        if isinstance(self.tree, WorkingTree):
            # print(':::-> tree.lock_read (try) about to execute')
            tree.lock_read()
            try:
                # RJL Breezy release notes state that:
                #
                #  The ``Tree.get_root_id`` method has been removed. Use``Tree.path2id('')`` instead. (Jelmer Vernooĳ)
                #
                root_id = self.tree.path2id('')
                basis_tree = self.tree.basis_tree()
                basis_tree.lock_read()
                try:
                    # print(':::->>second try block')
                    for the_change in self.tree.iter_changes(basis_tree, want_unversioned=want_unversioned):
                        # iter_changes now seems to appear to return a TreeChange type See Jelmer's 7390.
                        # Handily, it has an as_tuple() function, so we'll cheat for now
                        change = ChangeDesc(the_change)
                        # print('\n\nthe_change', change.dump())
                        path = change.old_or_new_path()
                        fileid = change.fileid()
                        # RJLRJL
                        # print('*** WARNING OLD_OR_NEW_PATH ***', path)

                        # print('::::change was', change, 'with path and file id of', path, fileid)
                        # if change.old_or_new_path() == 'wibble.txt':
                        #     print("*** found wibble.txt ***")
                        # RJLRJL Removed
                        # if fileid is None: # HOGEHOGE WORKAROUND
                        #     continue       # HOGEHOGE
                        # print('root_id, file_id', root_id, fileid,'same?', fileid == root_id)
                        if fileid == root_id:
                            # print('====>> CONTINUING! <<=====')
                            continue
                        is_ignored = self.tree.is_ignored(path)
                        # change = ChangeDesc(change + (is_ignored,))
                        change._is_ignored = is_ignored
                        # print('Change: is_ignored is ', is_ignored, 'filter:', self.change_load_filter, self.tree)

                        if (self.change_load_filter is not None and not self.change_load_filter(change)):
                            # print('^^^^ Continuing! ^^^^')
                            continue

                        item = InternalItem("", change.old_or_new_kind(), fileid)
                        item_data = ModelItemData(path, change=change, item=item)
                        # print('item', item, 'item_data', item_data)

                        self.inventory_data_by_path[path] = item_data
                        if fileid:
                            self.inventory_data_by_id[fileid] = item_data

                    # print('\n::: CHANGE LOOP FINISHED: ...conflicts')
                    for conflict in self.tree.conflicts():
                        path = conflict.path
                        if path in self.inventory_data_by_path:
                            self.inventory_data_by_path[path].conflicts.append(conflict)
                        else:
                            item_data = ModelItemData(path, conflicts=[conflict])
                            fileid = conflict.file_id
                            try:
                                kind = file_kind(self.tree.abspath(path))
                            except errors.NoSuchFile:
                                kind = ''

                            item_data.item = InternalItem("", kind, fileid)
                            self.inventory_data_by_path[path] = item_data
                            if fileid:
                                self.inventory_data_by_id[fileid] = item_data

                    # print('\nCONFLICTS FINISHED: initial_checked_paths', initial_checked_paths)
                    if initial_checked_paths:
                        # Add versioned directories so that we can easily check them.
                        for path in initial_checked_paths:
                            fileid = self.tree.path2id(path)
                            if fileid:
                                kind = self.tree.kind(path)
                                if kind == "directory":
                                    item_data = self.inventory_data_by_path.get(path)
                                    if item_data is None:
                                        item = InternalItem("", kind, fileid)
                                        item_data = ModelItemData(path, item=item)
                                        self.inventory_data_by_path[path] = item_data
                                        self.inventory_data_by_id[fileid] = item_data

                    # print('\nInventory: by path', self.inventory_data_by_path, 'by id', self.inventory_data_by_id)

                    def get_name(dir_fileid, dir_path, path, change):
                        # print('\n --> get_name', dir_fileid, '#', dir_path, '#', path, '#', change, '\n-----\n')
                        # If we've a name like 'somedir/thisname' then dirpath will be non-empty ('somedir')
                        # remove it from the name
                        if dir_path:
                            # print('It had a dirpath so we are removing it', path, path[len(dir_path) + 1:])
                            name = path[len(dir_path) + 1:]
                        else:
                            name = path
                            # print('No path, so name = ', path)
                        if change and change.is_renamed():
                            # print('\n\tRenamed Change Detected:', change, '\n\t\tbasis', basis_tree,
                            #     '\n\t\tchange_fileid', change.fileid(), '\n\t\tNAME:', name)
                            old_inventory_item = self._get_entry(basis_tree, change.fileid())
                            old_names = [old_inventory_item.name]
                            # print('\n\t\t old_inv, old_name', old_inventory_item, old_names)
                            while old_inventory_item.parent_id:
                                if old_inventory_item.parent_id == dir_fileid:
                                    break
                                old_inventory_item = self._get_entry(basis_tree, old_inventory_item.parent_id)
                                old_names.append(old_inventory_item.name)
                                # print('old_names in loop', old_names)
                            old_names.reverse()
                            old_path = "/".join(old_names)
                            name = "%s => %s" % (old_path, name)
                        return name

                    if changes_mode:
                        # print('CHANGES MODE -- COULD BE HERE: iter')
                        self.unver_by_parent = group_large_dirs(frozenset(iter(self.inventory_data_by_path.keys())))
                        # print('unver:', self.unver_by_parent)

                        # Add items for directories added
                        for path in self.unver_by_parent.keys():
                            # print('\tstepping: ={0}='.format(path))
                            if path not in self.inventory_data_by_path:
                                # print('\t', path,'not in inventory_data_by_path')
                                kind = "directory"
                                file_id = self.tree.path2id(path)
                                item = InternalItem("", kind, file_id)
                                item_data = ModelItemData(path, item=item)
                                self.inventory_data_by_path[path] = item_data
                                if file_id:
                                    self.inventory_data_by_id[file_id] = item_data

                        # Name setting
                        for dir_path, decendents in self.unver_by_parent.items():
                            dir_fileid = self.tree.path2id(dir_path)
                            for path in decendents:
                                item_data = self.inventory_data_by_path[path]
                                item_data.item.name = get_name(dir_fileid, dir_path, path, item_data.change)
                    else:
                        # record the unversioned items
                        # print('NOT in changes_mode')
                        for item_data in self.inventory_data_by_path.values():
                            # print('\titem_data', item_data, '\tchange', item_data.change, '\tis_versioned', item_data.change.is_versioned())
                            if (item_data.change and not item_data.change.is_versioned() or not item_data.change):
                                parent_path, name = os.path.split(item_data.path)
                                # print('\t\tadding ', parent_path, item_data.path, ' to unver_by_partent but name is ={0}='.format(name))
                                dict_set_add(self.unver_by_parent, parent_path, item_data.path)
                        # print('unver_by_parent', self.unver_by_parent)

                        # Name setting
                        # print('\nNAME SETTING')
                        for item_data in self.inventory_data_by_path.values():
                            # print('\titem_data', item_data, '\tchange', item_data.change, '\tis_versioned', item_data.change.is_versioned())
                            dir_path, name = os.path.split(item_data.path)
                            dir_fileid = self.tree.path2id(dir_path)
                            # print('\tname setting gave ', item_data, item_data.path, dir_path, name, dir_fileid)
                            item_data.item.name = get_name(dir_fileid, dir_path, item_data.path, item_data.change)
                finally:
                    basis_tree.unlock()
                # print('\n\t\t FIRST process_tree...', initial_checked_paths, load_dirs)
                self.process_tree(self.working_tree_get_children, initial_checked_paths, load_dirs)
            finally:
                tree.unlock()
        else:
            # print('\n\t\t SECOND process_tree...', initial_checked_paths, load_dirs)
            self.process_tree(self.revision_tree_get_children, initial_checked_paths, load_dirs)

        self.layoutChanged.emit()

    def revision_tree_get_children(self, item_data):
        path = self.tree.id2path(item_data.item.file_id)
        # print('\n\t\trevision_tree_get_children path:[{0}]'.format(path), item_data)
        path_was = path
        for child in self.tree.iter_child_entries(path):
            path = self.tree.id2path(child.file_id)
            # print('\n\t\t\t----> child', child, 'childpath', path, 'old path [{0}]'.format(path_was))
            yield ModelItemData(path, item=child)

    def working_tree_get_children(self, item_data):
        # print('\n\t!! working_tree_get_children, item_data', item_data, 'file_id', item_data.item.file_id)
        item = item_data.item
        # RJLRJL temp bypass
        if item.file_id is None:
            abspath = self.tree.abspath(item_data.path)
            # print('\n\t!!abspath is ', abspath)

            for name in os.listdir(abspath):
                path = item_data.path + "/" + name
                (kind, executable, stat_value) = self.tree._comparison_data(None, path)
                child = InternalItem(name, kind, None)
                is_ignored = self.tree.is_ignored(path)
                t = TreeChange(None,(None, path), False, (False, False), (None, None), (None, name), (None, kind), (None, executable))
                change = ChangeDesc(t, is_ignored)

                # change = ChangeDesc((None,(None, path), False, (False, False), (None, None), (None, name), (None, kind),
                #                      (None, executable),
                #                      is_ignored))

                if (self.change_load_filter is not None and not self.change_load_filter(change)):
                    continue

                yield ModelItemData(path, item=child, change=change)

        # print('\n\t!!type(item)', type(item), '[instance?]',isinstance(item, InternalItem), 'kind', item.kind, 'changes_mode', self.changes_mode)
        if (not isinstance(item, InternalItem) and item.kind == 'directory' and not self.changes_mode):
            # Because we create copies, we have to get the real item.
            item = self._get_entry(self.tree, item.file_id)
            path = self.tree.id2path(item.file_id)
            for child in self.tree.iter_child_entries(path):

                if child.file_id in self.inventory_data_by_id:
                    child_item_data = self.inventory_data_by_id[child.file_id]
                else:
                    path = self.tree.id2path(child.file_id)
                    child_item_data = ModelItemData(path)

                # Create a copy so that we don't have to hold a lock of the wt.
                child = self._get_entry(self.tree, child.file_id).copy()
                child_item_data.item = child
                yield child_item_data

        # print('\t\t\t AT third if...[{0}] [{1}]'.format(item_data.path, self.unver_by_parent))
        if item_data.path in self.unver_by_parent:
            for path in self.unver_by_parent[item_data.path]:
                yield self.inventory_data_by_path[path]

    _many_loaddirs_started = False
    _many_loaddirs_should_start = False
    def start_maybe_many_loaddirs(self):
        self._many_loaddirs_should_start = True

    def end_maybe_many_loaddirs(self):
        self._many_loaddirs_should_start = False
        if self._many_loaddirs_started:
            self._many_loaddirs_started = False
            self.tree.unlock()

    def load_dir(self, dir_id):
        if dir_id >= len(self.inventory_data):
            # print('\n\tLOAD_DIR RETURNING EARLY: dir_id >= len(self.inventory_data)')
            return
        dir_item = self.inventory_data[dir_id]
        if dir_item.children_ids is not None:
            # print('\n\tLOAD_DIR RETURNING EARLY: dir already loaded)')
            return  # This dir has already been loaded.
        if not dir_item.item.kind == 'directory':
            # print('\n\tLOAD_DIR RETURNING EARLY: not a directory')
            return

        if not self._many_loaddirs_started:
            self.tree.lock_read()
            if self._many_loaddirs_should_start:
                self._many_loaddirs_started = True

        # RJL: the strange construction with self.get_children pointing to
        # revision_tree_get_children seems to be a hangover from
        # python 2.4 days when one could not have yield in a try / finally block
        # nor had context managers.
        # print('\n\tSTARTING LOAD_DIR dir_id, type:', dir_id, type(dir_id))
        try:
            dir_item.children_ids = []
            child_list = list(self.get_children(dir_item))
            # print('\t\t\t We have', child_list, 'as the child_list. get_children is', self.get_children)
            children = sorted(child_list, key=ModelItemData.dirs_first_sort_key)
            parent_model_index = self._index_from_id(dir_id, 0)
            # print('\n\t\t~~~ load_dir, parent_model_index', parent_model_index, 'children', children)
            self.beginInsertRows(parent_model_index, 0, len(children) - 1)
            try:
                for child in children:
                    # print('\n\t\t\t>>>>>>>>>>>> child: ', child)
                    child_id = self.append_item(child, dir_id)
                    dir_item.children_ids.append(child_id)
            finally:
                self.endInsertRows()
        finally:
            if not self._many_loaddirs_started:
                self.tree.unlock()
        # print('\n\t FINISHED load_dir\n')

    def _get_entry(self, tree, file_id):
        # RJLRJL BUGBUG it looks like requesting specific_files must NOT pass any
        # actual paths (e.g. dir/movedandrenamed should be stripped to movedandrenamed)
        # print('\n^^^ _get_entry', tree, file_id, type(file_id))
        # print('\n\tid2path of ={0}='.format(file_id), 'gives: --> ', self.tree.id2path(file_id))
        # for _, entry in tree.iter_entries_by_dir(recurse_nested=True):
        #     print('\n\t -> ', _, 'entry:', entry)

        for _, entry in tree.iter_entries_by_dir(specific_files=[self.tree.id2path(file_id),], recurse_nested=True):
            return entry
        raise errors.NoSuchId(tree, file_id)

    def process_tree(self, get_children, initial_checked_paths, load_dirs):
        # RJL get_children seems to be a pass function and looks like it is used by
        # load_dir
        # print('\n\t process_tree with get_children as ', get_children)
        self.get_children = get_children

        root_item = ModelItemData('', item=self._get_entry(self.tree, self.tree.path2id('')))

        root_id = self.append_item(root_item, None)
        self.load_dir(root_id)

        if load_dirs:
            # refs2indexes will load the parents if nesseary.
            for index in self.refs2indexes(load_dirs, ignore_no_file_error=True):
                self.load_dir(index.internalId())

        if self.checkable:
            # print('\ncheckable!')
            if initial_checked_paths is not None:
                self.set_checked_paths(initial_checked_paths)
            else:
                # RJL initial_checked_paths will be None (I think) if EVERYTHING is to be checked
                # that is, 'select all'
                # print('\n\t ::: select all', root_id, self.NAME, 'index is ', self._index_from_id(root_id, self.NAME))
                self.setData(self._index_from_id(root_id, self.NAME), QtCore.Qt.Checked, QtCore.Qt.CheckStateRole)

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
            self.dataChanged.emit(index, index)

    def columnCount(self, parent):
        return len(self.HEADER_LABELS)

    def rowCount(self, parent):
        #if 0: parent = QtCore.QModelIndex()
        # Note, internalID() is part of pyQt4
        # print('\n\t^^^ rowCount called with parent=', parent)
        if parent.column() > 0 or parent.internalId() >= len(self.inventory_data):
            # print('\n\t:: first fail return')
            return 0
        parent_data = self.inventory_data[parent.internalId()]
        # print('\n\t:: parent_data was ', parent_data, 'ID', parent.internalId())
        if parent_data.children_ids is None:
            # print('\n\t:: second fail return')
            return 0
        # print('\n\t::Returning at end:', parent_data.children_ids, len(parent_data.children_ids))
        return len(parent_data.children_ids)

    def canFetchMore(self, parent):
        if parent.internalId()>=len(self.inventory_data):
            return False
        parent_data = self.inventory_data[parent.internalId()]
        return (parent_data.children_ids is None and parent_data.item.kind == "directory")

    def fetchMore(self, parent):
        self.load_dir(parent.internalId())

    def _index(self, row, column, parent_id):
        if parent_id >= len(self.inventory_data):
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
        if parent.column()>0:
            return QtCore.QModelIndex()
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

    def set_select_all_kind(self, kind='all'):
        """Set checker function for 'select all' checkbox.
        Possible kind values: all, versioned.
        """
        def _is_item_in_select_all_all(item):
            """Returns whether an item is changed when select all is clicked,
            and whether it's children are looked at."""
            return True, True

        def _is_item_in_select_all_versioned(item):
            return (item.change is None or item.change.is_versioned(), True)

        if kind == 'all':
            self.is_item_in_select_all = _is_item_in_select_all_all
        elif kind == 'versioned':
            self.is_item_in_select_all = _is_item_in_select_all_versioned

    def setData(self, index, value, role):
        # This appears to be used when clicking select / deselec all (at least in qAdd
        # print('***setData, index.column is ', index.column(), 'and ', type(role), 'value is', value, type(value), self.NAME)
        if index.column() == self.NAME and role == QtCore.Qt.CheckStateRole:

            def set_checked(item_data, checked, emit=True):
                old_checked = item_data.checked
                item_data.checked = checked
                return not old_checked == checked

            # RJLRJL: patch undo
            # value = int(value)
            if index.internalId() >= len(self.inventory_data):
                return False

            item_data = self.inventory_data[index.internalId()]
            first_index = self._index_from_id(item_data.id, self.NAME)
            # print('\n\t** got first_index of ', first_index)
            set_checked(item_data, value)

            # this is an array so that it is a poormans nonlocal
            # http://www.python.org/dev/peps/pep-3104/
            last_item_data = [None]
            # Recursively set all children to checked.
            def set_child_checked_recurse(item_data):
                # print('\n\t\t<<<>> set_child_checked_recurse', item_data)
                if (item_data.children_ids is None and item_data.item.kind == "directory"):
                    self.load_dir(item_data.id)

                if not item_data.children_ids:
                    # print('\n\t\t<<<>> returning FALSE', item_data.children_ids)
                    return False
                have_changed_item = False

                for child_id in item_data.children_ids:
                    child = self.inventory_data[child_id]

                    # If unchecking, uncheck everything, but if checking,
                    # only check those in "select_all" get checked.
                    # print('\n\t ---> child lock')
                    if value == QtCore.Qt.Unchecked:
                        # print('\n\t\t ~~ unlocking')
                        change = True
                        lookat_children = True
                    else:
                        # print('\n\t\t ~~ locking')
                        (change, lookat_children) = self.is_item_in_select_all(child)

                    last_item_data[0] = child

                    if lookat_children:
                        has_children_changed = set_child_checked_recurse(child)
                    else:
                        has_children_changed = False

                    if (change or has_children_changed):
                        have_changed_item = True
                        set_checked(child, value, False)
                return have_changed_item

            self.start_maybe_many_loaddirs()
            try:
                set_child_checked_recurse(item_data)
            finally:
                self.end_maybe_many_loaddirs()

            if last_item_data[0]:
                last_index = self._index_from_id(last_item_data[0].id, self.NAME)
            else:
                last_index = first_index
            self.dataChanged.emit(first_index, last_index)

            # Walk up the tree, and update every dir
            parent_data = item_data
            while parent_data.parent_id is not None:
                (in_select_all, look_at_children) = self.is_item_in_select_all(parent_data)
                if (not in_select_all and value == QtCore.Qt.Unchecked):
                    # Don't uncheck parents if not in "select_all".
                    break
                parent_data = self.inventory_data[parent_data.parent_id]
                has_checked = False
                has_unchecked = False
                for child_id in parent_data.children_ids:
                    child = self.inventory_data[child_id]
                    (child_in_select_all, child_look_at_children) = self.is_item_in_select_all(parent_data)

                    if child.checked == QtCore.Qt.Checked:
                        has_checked = True
                    elif (child.checked == QtCore.Qt.Unchecked and child_in_select_all):
                        has_unchecked = True
                    elif child.checked == QtCore.Qt.PartiallyChecked:
                        has_checked = True
                        if child_in_select_all:
                            has_unchecked = True

                    if has_checked and has_unchecked:
                        break

                if has_checked and has_unchecked:
                    checked = QtCore.Qt.PartiallyChecked
                elif has_checked:
                    checked = QtCore.Qt.Checked
                else:
                    checked = QtCore.Qt.Unchecked

                if set_checked(parent_data, checked):
                    index = self._index_from_id(parent_data.id, self.NAME)
                    self.dataChanged.emit(index, index)

            return True

        if index.column() == self.NAME and role == QtCore.Qt.EditRole:
            if not isinstance(self.tree, WorkingTree):
                return False
            # Rename
            value = str(value)
            item_data = self.inventory_data[index.internalId()]
            parent = self.inventory_data[item_data.parent_id]
            new_path = posixpath.join(parent.path, value)
            if item_data.path == new_path:
                return False
            try:
                if item_data.item.file_id:
                    # Versioned file
                    self.tree.rename_one(item_data.path, new_path)
                else:
                    old_path_abs=self.tree.abspath(item_data.path)
                    new_path_abs=self.tree.abspath(new_path)
                    os.rename(old_path_abs, new_path_abs)
            except Exception:
                report_exception(type=SUB_LOAD_METHOD, window=self.parent_view.window())
            # We do this so that the ref has the new_path, and hence refresh
            # restores it's state correctly.
            item_data.path = new_path
            ref = self.index2ref(index)
            self.parent_view.refresh()
            try:
                new_index = self.ref2index(ref)
                new_index = self.parent_view.tree_filter_model.mapFromSource(new_index)
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
            return None

        if role >= QtCore.Qt.FontRole and role <= QtCore.Qt.TextColorRole:
            return None

        item_data = self.inventory_data[index.internalId()]
        item = item_data.item

        if role == self.FILEID:
            return QtCore.QByteArray(item.file_id)

        column = index.column()
        if column == self.NAME:
            if role == QtCore.Qt.DisplayRole:
                return item.name
            if role == QtCore.Qt.EditRole:
                path = item_data.path
                if item_data.parent_id:
                    parent = self.inventory_data[item_data.parent_id]
                    path = path[len(parent.path) + 1:]
                return path
            if role == QtCore.Qt.DecorationRole:
                if item_data.icon is None:
                    if (item_data.change and not item_data.change.is_on_disk() or item.kind == ''):
                        item_data.icon = self.missing_icon
                    elif isinstance(self.tree, WorkingTree):
                        abspath = self.tree.abspath(item_data.path)
                        info = QtCore.QFileInfo(abspath)
                        item_data.icon = self.icon_provider.icon(info)
                    else:
                        if item.kind == "file":
                            item_data.icon = self.file_icon
                        if item.kind == "directory":
                            item_data.icon = self.dir_icon
                        if item.kind == "symlink":
                            item_data.icon = self.symlink_icon
                if item_data.icon is None:
                    item_data.icon = None
                return item_data.icon

            if role == QtCore.Qt.CheckStateRole:
                if not self.checkable:
                    return None
                else:
                    return item_data.checked

        if column == self.STATUS:
            if role == QtCore.Qt.DisplayRole:
                status = []
                if item_data.change is not None:
                    status.append(item_data.change.status())
                for conflict in item_data.conflicts:
                    status.append(conflict.typestring)
                return ", ".join(status)


        # RJLRJL check this before patch changes (patch line ~= 1897)
        try:
            revid = item_data.item.revision
        except AttributeError:
            # GitTreeDirectory object has no attribute 'repository'
            return None

        if role == self.REVID:
            return revid

        if column == self.REVNO:
            if role == QtCore.Qt.DisplayRole:
                if self.revno_map is not None and revid in self.revno_map:
                    revno_sequence = self.revno_map[revid]
                    return ".".join(["%d" % (revno) for revno in revno_sequence])
                else:
                    return ""

        if role == QtCore.Qt.DisplayRole:
            if revid in cached_revisions:
                rev = cached_revisions[revid]

                if column == self.AUTHOR:
                    return get_apparent_author_name(rev)

                if column == self.MESSAGE:
                    return get_summary(rev)

                if column == self.DATE:
                    return strftime("%Y-%m-%d %H:%M", localtime(rev.timestamp))

        if role == self.PATH:
            return item_data.path

        if role == QtCore.Qt.DisplayRole:
            return ""
        return None

    def flags(self, index):
        if not index.isValid():
            return QtCore.Qt.NoItemFlags

        flags = (QtCore.Qt.ItemIsEnabled | QtCore.Qt.ItemIsSelectable)

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
            return self.HEADER_LABELS[section]
        return None

    def on_revisions_loaded(self, revisions, last_call):
        for item_data in self.inventory_data:
            if item_data.id == 0:
                continue

            if item_data.item.revision in revisions:
                self.dataChanged.emit(self.createIndex (item_data.row, self.DATE, item_data.id), self.createIndex (item_data.row, self.AUTHOR, item_data.id))

    def get_repo(self):
        # RJLRJL Check this patch line ~= 1966
        if self.branch is not None:
            return self.branch.repository
        else:
            return None

    def item2ref(self, item_data):
        return PersistantItemReference(item_data.item.file_id, item_data.path)

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
                parent_id = self._get_entry(self.tree, ref.file_id).parent_id
                parent_ids = []
                while parent_id is not None:
                    parent_ids.append(parent_id)
                    parent_id = self._get_entry(self.tree, parent_id).parent_id
                return reversed(parent_ids)
        else:
            key = ref.path
            dict = self.inventory_data_by_path
            def iter_parents():
                path_split = ref.path.split("/")
                parent_dir_path = None
                for parent_name in path_split[:-1]:
                    if parent_dir_path is None:\
                        parent_dir_path = parent_name
                    else:
                        parent_dir_path += "/" + parent_name
                    yield parent_dir_path

        if key not in dict or dict[key].id is None:
            # Try loading the parents
            for parent_key in iter_parents():
                if parent_key in dict:
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

    def iter_checked(self, include_unchanged_dirs=True):
        """
        Iterate over the list of checked items and emit the entires.

        @param include_unchanged_dirs: should we include unchanged directories
            or skip them.
        """
        # We have to recurse and load all dirs, because we use --no-recurse
        # for add, and commit and revert don't recurse.
        i = 0
        # print('iter_checked', len(self.inventory_data), self.inventory_data)
        while i < len(self.inventory_data):
            item_data = self.inventory_data[i]
            # print('\n\t---> itemd_data is ', item_data, 'for', i, 'children_ids, kind, checked',
            #     item_data.children_ids, item_data.item.kind, item_data.checked)
            if (item_data.children_ids is None and item_data.item.kind == "directory" and item_data.checked):
                # print('\n\t...loading...')
                self.load_dir(item_data.id)
            i += 1

        for item_data in self.inventory_data[1:]:
            # print('\n\tsecond loop: ', item_data)
            if item_data.checked == QtCore.Qt.Checked:
                if (item_data.change is None and item_data.item.kind == 'directory' and not include_unchanged_dirs):
                    continue
                # print('\n\t *** YIELDING *** ')
                yield self.item2ref(item_data)

    def set_checked_items(self, refs, ignore_no_file_error=True):
        # set every thing off
        root_index = self._index_from_id(0, self.NAME)
        self.setData(root_index, QtCore.Qt.Unchecked, QtCore.Qt.CheckStateRole)

        for index in self.refs2indexes(refs, ignore_no_file_error):
            self.setData(index, QtCore.Qt.Checked, QtCore.Qt.CheckStateRole)

    def set_checked_paths(self, paths):
        return self.set_checked_items([PersistantItemReference(None, path) for path in paths])

    def supportedDropActions(self):
        return QtCore.Qt.MoveAction


class TreeFilterProxyModel(QtCore.QSortFilterProxyModel):
    source_model = None

    filters = [True, True, True, False]
    # This just sets 0, 1, 2, 3. Dunno why you'd do the list nonsense
    # (UNCHANGED, CHANGED, UNVERSIONED, IGNORED) = list(range(4))
    UNCHANGED =0
    CHANGED = 1
    UNVERSIONED =2
    IGNORED = 3

    filter_cache = {}

    def setSourceModel (self, source_model):
        self.source_model = source_model
        QtCore.QSortFilterProxyModel.setSourceModel(self, source_model)

    def invalidateFilter(self):
        self.filter_cache = {}
        self.source_model.start_maybe_many_loaddirs()
        try:
            QtCore.QSortFilterProxyModel.invalidateFilter(self)
        finally:
            self.source_model.end_maybe_many_loaddirs()

    def setFilter(self, filter, value):
        self.filters[filter] = value
        # This is slow. It causes TreeModel.index, and TreeModel.data thousands of times.
        self.invalidateFilter()

    def setFilters(self, filters):
        def iff(b, x, y):
            if b:
                return x
            else:
                return y

        self.filters = [iff(f is not None, f, old_f) for f, old_f in zip(filters, self.filters)]
        self.invalidateFilter()

    def filterAcceptsRow(self, source_row, source_parent):
        #if all(self.filters):
        #    return True

        model = self.source_model
        parent_id = source_parent.internalId()
        children_ids = model.inventory_data[parent_id].children_ids
        if len(children_ids)<=source_row:
            return False
        id = children_ids[source_row]
        if (model.checkable and not model.inventory_data[id].checked == QtCore.Qt.Unchecked):
            return True
        return self.filter_id_cached(id)

    def filter_id_cached(self, id):
        if id in self.filter_cache:
            return self.filter_cache[id]
        else:
            result = self.filter_id_recurse(id)
            self.filter_cache[id] = result
            return result

    def filter_id_recurse(self, id):
        item_data = self.source_model.inventory_data[id]

        filter = self.filter_id(id, item_data)
        if filter is not None:
            return filter

        if item_data.item.kind == "directory":
            if item_data.children_ids is None:
                self.source_model.load_dir(id)

            for child_id in item_data.children_ids:
                if self.filter_id_cached(child_id):
                    return True
        return False

    def filter_id(self, id, item_data):
        """Determines whether a item should be displayed.
        Returns :
            * True: Show the item
            * False: Do not show the item
            * None: Show the item if there are any children that are visible.
        """

        (unchanged, changed, unversioned, ignored) = self.filters
        # print('$$$ filter_id', unchanged, changed, unversioned, ignored)
        # print('$$$ item_data is ', type(item_data), item_data)
        is_changed = item_data.change is not None
        is_versioned = item_data.item.file_id is not None

        if is_versioned and not is_changed and unchanged:
            return True

        if is_versioned and is_changed and changed:
            return True

        if not is_versioned:
            if is_changed and (unversioned or ignored):
                is_ignored = item_data.change.is_ignored()
                if not is_ignored and unversioned: return True
                if is_ignored: return ignored
            else:
                return False

        return None

    def on_revisions_loaded(self, revisions, last_call):
        self.source_model.on_revisions_loaded(revisions, last_call)

    def get_repo(self):
        return self.source_model.get_repo()

    def hasChildren(self, parent):
        return self.source_model.hasChildren(self.mapToSource(parent))


class TreeFilterMenu(QtWidgets.QMenu):
    triggered = QtCore.pyqtSignal(int, bool)

    def __init__ (self, parent=None):
        QtWidgets.QMenu.__init__(self, gettext("&Filter"), parent)

        filters = (gettext("Unchanged"),
                   gettext("Changed"),
                   gettext("Unversioned"),
                   gettext("Ignored"))

        self.actions = []
        for i, text in enumerate(filters):
            action = QtWidgets.QAction(text, self)
            action.setData(i)
            action.setCheckable(True)
            self.addAction(action)
            self.actions.append(action)

        # self.triggered[QtWidgets.QAction].connect(self._triggered)
        self.triggered.connect(self._triggered)

    def _triggered(self, action):
        # filter = action.data().toInt()[0]
        filter = int(action.data())
        checked = action.isChecked()
        self.triggered.emit(filter, checked)

    def set_filters(self, filters):
        for checked, action in zip(filters, self.actions):
            action.setChecked(checked)


class TreeWidget(RevisionTreeView):
    dataChanged = QtCore.pyqtSignal(QtCore.QModelIndex, QtCore.QModelIndex)

    def __init__(self, *args):
        RevisionTreeView.__init__(self, *args)

        self.setSelectionMode(QtWidgets.QAbstractItemView.ExtendedSelection)
        self.setUniformRowHeights(True)
        self.setEditTriggers(QtWidgets.QAbstractItemView.SelectedClicked | QtWidgets.QAbstractItemView.EditKeyPressed)
        self.viewport().setAcceptDrops(True)
        self.setDropIndicatorShown(True)
        self.setDragDropMode(QtWidgets.QAbstractItemView.InternalMove);

        self.tree = None
        self.branch = None

        self.tree_model = TreeModel(self)
        self.tree_filter_model = TreeFilterProxyModel()
        self.tree_filter_model.setSourceModel(self.tree_model)
        self.setModel(self.tree_filter_model)
        # self.setModel(self.tree_model)

        self.revno_item_delegate = RevNoItemDelegate(parent=self)
        self.set_header_width_settings()
        self.setItemDelegateForColumn(self.tree_model.REVNO, self.revno_item_delegate)
        self.create_context_menu()
        self.doubleClicked[QtCore.QModelIndex].connect(self.do_default_action)

    def set_header_width_settings(self):
        header = self.header()
        header.setStretchLastSection(False)
        header.setSectionResizeMode(self.tree_model.NAME, QtWidgets.QHeaderView.ResizeToContents)
        header.setSectionResizeMode(self.tree_model.DATE, QtWidgets.QHeaderView.Interactive)
        header.setSectionResizeMode(self.tree_model.REVNO, QtWidgets.QHeaderView.Interactive)
        header.setSectionResizeMode(self.tree_model.MESSAGE, QtWidgets.QHeaderView.Stretch)
        header.setSectionResizeMode(self.tree_model.AUTHOR, QtWidgets.QHeaderView.Interactive)
        header.setSectionResizeMode(self.tree_model.STATUS, QtWidgets.QHeaderView.Stretch)
        fm = self.fontMetrics()
        # XXX Make this dynamic.
        col_margin = (self.style().pixelMetric(QtWidgets.QStyle.PM_FocusFrameHMargin, None, self) + 1) * 2

        header.resizeSection(self.tree_model.REVNO, fm.width("8" * self.revno_item_delegate.max_mainline_digits + ".8.888") + col_margin)
        header.resizeSection(self.tree_model.DATE, fm.width("88-88-8888 88:88") + col_margin)
        header.resizeSection(self.tree_model.AUTHOR, fm.width("Joe I have a Long Name") + col_margin)
        if self.tree and isinstance(self.tree, WorkingTree):
            header.setSectionResizeMode(self.tree_model.NAME, QtWidgets.QHeaderView.Stretch)
            header.setSectionResizeMode(self.tree_model.STATUS, QtWidgets.QHeaderView.ResizeToContents)

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
            header.setSectionResizeMode(self.tree_model.NAME, QtWidgets.QHeaderView.Stretch)
            header.setSectionResizeMode(self.tree_model.STATUS, QtWidgets.QHeaderView.ResizeToContents)

            self.context_menu.setDefaultAction(self.action_open_file)
        else:
            header.showSection(self.tree_model.DATE)
            header.showSection(self.tree_model.REVNO)
            header.showSection(self.tree_model.MESSAGE)
            header.showSection(self.tree_model.AUTHOR)
            header.hideSection(self.tree_model.STATUS)
            header.setSectionResizeMode(self.tree_model.NAME, QtWidgets.QHeaderView.ResizeToContents)
            header.setSectionResizeMode(self.tree_model.STATUS, QtWidgets.QHeaderView.Stretch)

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
        # print('TreeWidget.set_tree', tree, 'branch', branch, 'initial', initial_checked_paths, 'change',
        #     change_load_filter, 'isinstance', isinstance(tree, WorkingTree), 'changes mode', changes_mode,
        #     'want unversioned?', want_unversioned)
        self.tree = tree
        if isinstance(tree, RevisionTree) and branch is None:
            raise AttributeError("A branch must be provided if the tree is a RevisionTree")

        self.revision_loading_disabled = isinstance(tree, WorkingTree)
        self.branch = branch
        self.changes_mode = changes_mode
        self.want_unversioned = want_unversioned
        self.change_load_filter = change_load_filter

        if branch:
            branch.lock_read()
            try:
                last_revno = branch.last_revision_info()[0]
            finally:
                branch.unlock()
            self.revno_item_delegate.set_max_revno(last_revno)
        # update width uncoditionally because we may change the revno column
        self.set_header_width_settings()
        self.set_visible_headers()
        QtCore.QCoreApplication.processEvents()

        if initial_checked_paths and not self.tree_model.checkable:
            raise AttributeError("You can't have a initial_selection if tree_model.checkable is not True.")

        # print('Treewidget calling its model set_tree with', self.tree, self.branch,
        #                          changes_mode, want_unversioned, change_load_filter, initial_checked_paths)
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
            # (https://bugs.launchpad.net/qbrz/+bug/402276)
            # I think that this is a bug with qt, and so this is just a work-
            # arround. We should check when we bump the min qt version to 4.5 if
            # we can take this out. I think it only happens on windows. This may
            # need to be checked.
            for row in range(len(self.tree_model.inventory_data[0].children_ids)):
                index = self.tree_model.createIndex(row, self.tree_model.NAME, 0)
                self.tree_model.dataChanged.emit(index, index)

    def iter_expanded_indexes(self):
        parents_to_check = [QtCore.QModelIndex()]
        while parents_to_check:
            parent = parents_to_check.pop(0)
            for row in range(self.tree_filter_model.rowCount(parent)):
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
            checked = [(self.tree_model.item2ref(item_data), item_data.checked) for item_data in self.tree_model.inventory_data[1:]]
        else:
            checked = None
        expanded = self.tree_model.indexes2refs(self.iter_expanded_indexes())
        selected = self.tree_model.indexes2refs(self.get_selection_indexes())
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
                            self.tree_model.setData(index, state, QtCore.Qt.CheckStateRole)
                        except (errors.NoSuchId, errors.NoSuchFile):
                            pass

            self.set_expanded_indexes(
                self.tree_model.refs2indexes(expanded, ignore_no_file_error=True))

            for index in self.tree_model.refs2indexes(selected, ignore_no_file_error=True):
                # XXX This does not work for sub items. I can't figure out why.
                # GaryvdM - 14/07/2009
                # RJLRJL that would be nice (2021)
                self.selectionModel().select(
                    self.tree_filter_model.mapFromSource(index),
                    QtCore.QItemSelectionModel.SelectCurrent |
                    QtCore.QItemSelectionModel.Rows)
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
            for path in minimum_path_selection(list(item_by_path.keys())):
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

        QtWidgets.QTreeView.mousePressEvent(self, event)

    def dropEvent(self, event):
        if not isinstance(self.tree, WorkingTree):
            return

        # we should encode the paths list, give it an aproite mime type, etc.
        # Eaiser to just get the selection.
        drop_index = self.tree_filter_model.mapToSource(self.indexAt(event.pos()))
        drop_item = self.tree_model.inventory_data[drop_index.internalId()]
        if drop_item.item.kind == "directory":
            drop_path = drop_item.path
        else:
            drop_path, name = os.path.split(drop_item.path)
        paths = [item.path for item in self.get_selection_items()]
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
            if not self.state() & QtWidgets.QAbstractItemView.EditingState:
                event.accept()
                indexes = self.selectionModel().selectedRows(0)
                if (len(indexes) == 1 and
                        self.get_selection_items(indexes)[0].item.kind == 'directory'):
                    self.setExpanded(indexes[0], not self.isExpanded(indexes[0]))
                else:
                    self.do_default_action(None)
                return
        QtWidgets.QTreeView.keyPressEvent(self, event)

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
        self.context_menu = QtWidgets.QMenu(self)
        self.action_open_file = self.context_menu.addAction(gettext("&Open"), self.open_file)
        self.action_show_file = self.context_menu.addAction(gettext("&View file"), self.show_file_content)
        self.action_show_annotate = self.context_menu.addAction(gettext("Show &annotate"), self.show_file_annotate)
        self.action_show_log = self.context_menu.addAction(gettext("Show &log"), self.show_file_log)
        if has_ext_diff():
            diff_menu = ExtDiffMenu(self)
            self.action_show_diff = self.context_menu.addMenu(diff_menu)
            diff_menu.triggered['QString'].connect(self.show_differences)
        else:
            self.action_show_diff = self.context_menu.addAction(gettext("Show &differences"), self.show_differences)

        self.context_menu.addSeparator()
        self.action_merge = self.context_menu.addAction(gettext("&Merge conflict"), self.merge)
        self.action_resolve = self.context_menu.addAction(gettext("Mark conflict &resolved"), self.resolve)

        self.context_menu.addSeparator()
        self.action_add = self.context_menu.addAction(gettext("&Add"), self.add)
        self.action_revert = self.context_menu.addAction(gettext("&Revert"), self.revert)
        self.action_rename = self.context_menu.addAction(gettext("Re&name"), self.rename)
        self.action_remove = self.context_menu.addAction(gettext("Remove"), self.remove)
        # The text for this is set per selection, depending on move or rename.
        self.action_mark_move = self.context_menu.addAction("mv --after", self.mark_move)

    def filter_context_menu(self):
        is_working_tree = isinstance(self.tree, WorkingTree)
        items = self.get_selection_items()
        versioned = [item.item.file_id is not None for item in items]
        changed = [item.change is not None for item in items]
        versioned_changed = [ver and ch for ver,ch in zip(versioned, changed)]
        conflicts = [len(item.conflicts) > 0 for item in items]
        text_conflicts = [len([conflicts for conflict in item.conflicts if isinstance(conflict, TextConflict)]) > 0 for item in items]
        on_disk = [item.change is None or item.change.is_on_disk() for item in items]
        selection_len = len(items)

        single_item_in_tree = (selection_len == 1 and (items[0].change is None or items[0].change[6][1] is not None))
        single_file = (single_item_in_tree and items[0].item.kind == "file")
        single_versioned_file = (single_file and versioned[0])

        self.action_open_file.setEnabled(single_item_in_tree)
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
        # XXX This should be made to handle selections of multiple items.
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
            window = QBzrCatWindow(filename = item.path, tree = self.tree, parent=self, encoding=encoding)
        else:
            abspath = os.path.join(self.tree.basedir, item.path)
            window = QBzrViewWindow(filename=abspath, encoding=encoding, parent=self)
        window.show()
        self.window().windows.append(window)

    @ui_current_widget
    def open_file(self, index=None):
        """Open the file in the os specified editor."""

        items = self.get_selection_items([index])
        if not len(items) == 1:
            return
        item = items[0]

        if isinstance(self.tree, WorkingTree):
            self.tree.lock_read()
            try:
                abspath = self.tree.abspath(item.path)
            finally:
                self.tree.unlock()
            url = QtCore.QUrl.fromLocalFile(abspath)
            QtGui.QDesktopServices.openUrl(url)
        else:
            cat_to_native_app(self.tree, item.path)

    @ui_current_widget
    def show_file_log(self):
        """Show qlog for one selected file(s)."""

        items = self.get_selection_items()
        fileids = [item.item.file_id for item in items if item.item.file_id is not None]
        window = LogWindow(branch=self.branch,  specific_file_ids=fileids)
        window.show()
        self.window().windows.append(window)

    @ui_current_widget
    def show_file_annotate(self):
        """Show qannotate for selected file."""
        index = self.currentIndex()
        file_id = bytes(index.data(self.tree_model.FILEID))
        path = str(index.data(self.tree_model.PATH))

        if isinstance(file_id, str):
            raise errors.InternalBzrError('file_id should be plain string, not unicode')

        window = AnnotateWindow(self.branch, None, self.tree, path, file_id)
        window.show()
        self.window().windows.append(window)

    @ui_current_widget
    def show_differences(self, ext_diff=None, index=None):
        """Show differences for selected file(s)."""

        items = self.get_selection_items([index])
        if len(items) > 0:
            # Only paths that have changes.
            paths = [item.path for item in items if item.change is not None]
        else:
            # Show all.
            paths = None

        arg_provider = InternalWTDiffArgProvider(None, self.tree, self.tree.branch, self.tree.branch, specific_files=paths)
        show_diff(arg_provider, ext_diff=ext_diff, parent_window=self.window(), context=self.diff_context)

    def unversioned_parents_paths(self, item, include_item=True):
        paths = []
        first = True
        while item.item.file_id is None:
            if first:
                if include_item:
                    paths.append(item.path)
                first = False
            else:
                paths.append(item.path)

            if item.parent_id:
                item = self.tree_model.inventory_data[item.parent_id]
            else:
                break
        paths.reverse()
        return paths

    @ui_current_widget
    def add(self):
        """Add selected file(s)."""

        items = self.get_selection_items()

        # Only paths that are not versioned.
        paths = []
        for item in items:
            paths.extend(self.unversioned_parents_paths(item))
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
        paths = [item.path for item in items if item.change is not None and item.item.file_id is not None]
        if len(paths) == 0:
            return

        res = QtWidgets.QMessageBox.question(self,
            gettext("Revert"),
            gettext("Do you really want to revert the selected file(s)?"),
            QtWidgets.QMessageBox.Yes | QtWidgets.QMessageBox.No)
        if res == QtWidgets.QMessageBox.Yes:
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
                 if len([conflict for conflict in item.conflicts if isinstance(conflict, TextConflict)]) >0 ]
        if len(paths) == 0:
            return

        args = ["extmerge"]
        args.extend(paths)
        desc = " ".join(args)
        SimpleSubProcessDialog(gettext("External Merge"),
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
        paths = [item.path for item in items if len(item.conflicts)>0]
        if len(paths) == 0:
            return
        try:
            resolve(self.tree, paths)
        except Exception:
            report_exception(type=SUB_LOAD_METHOD, window=self.window())
        self.refresh()

    def mark_move(self):
        items = self.get_selection_items()
        if len(items) != 2:
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
            # add the new parent
            self.tree.add(self.unversioned_parents_paths(new, False))
            self.tree.rename_one(old.path, new.path, after=True)
        except Exception:
            report_exception(type=SUB_LOAD_METHOD, window=self.window())
        self.refresh()

    @ui_current_widget
    def rename(self):
        """Rename the selected file."""

        indexes = self.get_selection_indexes()
        if len(indexes) != 1:
            return
        index = indexes[0]
        index = self.tree_filter_model.mapFromSource (index)
        self.edit(index)

    @ui_current_widget
    def remove(self):
        """Remove selected file(s)."""

        items = self.get_selection_items()
        # Only paths that are not missing
        paths = [item.path for item in items if item.change is None or item.change.is_on_disk()]
        if len(paths) == 0:
            return
        try:
            try:
                self.tree.remove(paths, keep_files=False)
            except errors.BzrRemoveChangedFilesError:
                res = QtWidgets.QMessageBox.question(
                    self, gettext("Remove"),
                    gettext("Some of the files selected cannot be recovered if "
                            "removed. Are you sure you want to remove these "
                            "files?"),
                    QtWidgets.QMessageBox.Yes | QtWidgets.QMessageBox.No)
                if res == QtWidgets.QMessageBox.Yes:
                    self.tree.remove(paths, keep_files=False, force=True)
        except Exception:
            report_exception(type=SUB_LOAD_METHOD, window=self.window())

        self.refresh()


class SelectAllCheckBox(QtWidgets.QCheckBox):

    clicked = QtCore.pyqtSignal(bool)

    def __init__(self, tree_widget, parent=None):
        QtWidgets.QCheckBox.__init__(self, gettext("Select / deselect all"), parent)
        self.tree_widget = tree_widget
        #self.setTristate(True)
        tree_widget.tree_model.dataChanged[QtCore.QModelIndex, QtCore.QModelIndex].connect(self.on_data_changed)
        self.clicked[bool].connect(self._clicked)

    def on_data_changed(self, start_index, end_index):
        self.update_state()

    def update_state(self):
        model = self.tree_widget.tree_model
        root_index = model._index_from_id(0, model.NAME)
        state = model.data(root_index, QtCore.Qt.CheckStateRole)
        self.setCheckState(QtCore.Qt.CheckState(state))

    def _clicked(self, state):
        model = self.tree_widget.tree_model
        root_index = model._index_from_id(0, model.NAME)
        if state:
            state = QtCore.Qt.Checked
        else:
            state = QtCore.Qt.Unchecked
        model.setData(root_index, state, QtCore.Qt.CheckStateRole)
