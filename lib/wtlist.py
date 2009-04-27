# -*- coding: utf-8 -*-
#
# QBzr - Qt frontend to Bazaar commands
# Copyright (C) 2006-2007 Lukáš Lalinský <lalinsky@gmail.com>
# Copyright (C) 2006 Trolltech ASA
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

"""A QTreeWidget that shows the items in a working tree, and includes a common
context menu."""

from PyQt4 import QtCore, QtGui

from bzrlib.errors import BzrError
from bzrlib import (
    osutils,
    )

from bzrlib.plugins.qbzr.lib.diff import (
    show_diff,
    has_ext_diff,
    ExtDiffMenu,
    InternalWTDiffArgProvider,
    )
from bzrlib.plugins.qbzr.lib.i18n import gettext, N_
from bzrlib.plugins.qbzr.lib.subprocess import SimpleSubProcessDialog
from bzrlib.plugins.qbzr.lib.util import (
    file_extension,
    runs_in_loading_queue,
    )


class WorkingTreeFileList(QtGui.QTreeWidget):

    SELECTALL_MESSAGE = N_("Select / deselect all")

    def __init__(self, parent, tree):
        QtGui.QTreeWidget.__init__(self, parent)
        self._ignore_select_all_changes = False
        self.selectall_checkbox = None # added by client.
        self.tree = tree

    def setup_actions(self):
        """Setup double-click and context menu"""
        parent = self.parentWidget()
        parent.connect(self,
                       QtCore.SIGNAL("itemDoubleClicked(QTreeWidgetItem *, int)"),
                       self.itemDoubleClicked)

        self.setContextMenuPolicy(QtCore.Qt.CustomContextMenu)
        parent.connect(self,
                       QtCore.SIGNAL("itemSelectionChanged()"),
                       self.update_context_menu_actions)
        parent.connect(self,
                       QtCore.SIGNAL("customContextMenuRequested(QPoint)"),
                       self.show_context_menu)

        self.context_menu = QtGui.QMenu(self)
        if has_ext_diff():
            self.diff_menu = ExtDiffMenu(self)
            self.context_menu.addMenu(self.diff_menu)
            self.connect(self.diff_menu, QtCore.SIGNAL("triggered(QString)"),
                         self.show_differences)
            self.show_diff_ui = self.diff_menu
        else:
            self.show_diff_action = self.context_menu.addAction(
                gettext("Show &differences..."), self.show_differences)
            self.context_menu.setDefaultAction(self.show_diff_action)
            self.show_diff_ui = self.show_diff_action

        self.revert_action = self.context_menu.addAction(
            gettext("&Revert..."), self.revert_selected)
        # set all actions to disabled so it does the right thing with an empty
        # list (our itemSelectionChanged() will fire as soon as we select one)
        self.revert_action.setEnabled(False)
        self.show_diff_ui.setEnabled(False)

    @runs_in_loading_queue
    def fill(self, items_iter):
        self.setTextElideMode(QtCore.Qt.ElideMiddle)
        self.setSelectionMode(QtGui.QAbstractItemView.ExtendedSelection)
        self.setSortingEnabled(True)
        self.setHeaderLabels([gettext("File"), gettext("Extension"), gettext("Status")])
        header = self.header()
        header.setStretchLastSection(False)
        header.setResizeMode(0, QtGui.QHeaderView.Stretch)
        header.setResizeMode(1, QtGui.QHeaderView.ResizeToContents)
        header.setResizeMode(2, QtGui.QHeaderView.ResizeToContents)
        self.setRootIsDecorated(False)
        self._ignore_select_all_changes = True # don't update as we add items!

        # Each items_iter returns a tuple of (changes_tuple, is_checked)
        # Where changes_tuple is a single item from iter_changes():
        # (file_id, (path_in_source, path_in_target),
        # changed_content, versioned, parent, name, kind,
        # executable)
        # Note that the current filter is used to determine if the items are
        # shown or not
        self.item_to_data = {}
        items = []
        for change_desc, visible, checked in items_iter:
            (file_id, (path_in_source, path_in_target),
             changed_content, versioned, parent, name, kind,
             executable) = change_desc

            if versioned == (False, False):
                if self.tree.is_ignored(path_in_target):
                    status = gettext("ignored")
                else:
                    status = gettext("non-versioned")
                ext = file_extension(path_in_target)
                name = path_in_target
            elif versioned == (False, True):
                status = gettext("added")
                ext = file_extension(path_in_target)
                name = path_in_target + osutils.kind_marker(kind[1])
            elif versioned == (True, False):
                status = gettext("removed")
                ext = file_extension(path_in_source)
                name = path_in_source + osutils.kind_marker(kind[0])
            elif kind[0] is not None and kind[1] is None:
                status = gettext("missing")
                ext = file_extension(path_in_source)
                name = path_in_source + osutils.kind_marker(kind[0])
            else:
                # versioned = True, True - so either renamed or modified
                # or properties changed (x-bit).
                renamed = (parent[0], name[0]) != (parent[1], name[1])
                if renamed:
                    if changed_content:
                        status = gettext("renamed and modified")
                    else:
                        status = gettext("renamed")
                    name = "%s%s => %s%s" % (path_in_source,
                                             osutils.kind_marker(kind[0]),
                                             path_in_target,
                                             osutils.kind_marker(kind[0]))
                    ext = file_extension(path_in_target)
                elif changed_content:
                    status = gettext("modified")
                    name = path_in_target +  osutils.kind_marker(kind[1])
                    ext = file_extension(path_in_target)
                elif executable[0] != executable[1]:
                    status = gettext("modified (x-bit)")
                    name = path_in_target +  osutils.kind_marker(kind[1])
                    ext = file_extension(path_in_target)
                else:
                    raise RuntimeError, "what status am I missing??"

            item = QtGui.QTreeWidgetItem()
            item.setText(0, name)
            item.setText(1, ext)
            item.setText(2, status)
            if visible:
                items.append(item)

            if checked is None:
                item.setCheckState(0, QtCore.Qt.PartiallyChecked)
                item.setFlags(item.flags() & ~QtCore.Qt.ItemIsUserCheckable)
            elif checked:
                item.setCheckState(0, QtCore.Qt.Checked)
            else:
                item.setCheckState(0, QtCore.Qt.Unchecked)
            self.item_to_data[item] = change_desc
        # add them all to the tree in one hit.
        self.insertTopLevelItems(0, items)
        self._ignore_select_all_changes = False
        if self.selectall_checkbox is not None:
            self.update_selectall_state(None, None)

    def set_item_hidden(self, item, hide):
        # Due to what seems a bug in Qt "hiding" an item isn't always
        # reliable - so a "hidden" item is simply not added to the tree!
        # See https://bugs.launchpad.net/qbzr/+bug/274295
        index = self.indexOfTopLevelItem(item)
        if index == -1 and not hide:
            self.addTopLevelItem(item)
        elif index != -1 and hide:
            self.takeTopLevelItem(index)

    def is_item_hidden(self, item):
        return self.indexOfTopLevelItem(item) == -1

    def iter_treeitem_and_desc(self, include_hidden=False):
        """iterators to help work with the selection, checked items, etc"""
        for ti, desc in self.item_to_data.iteritems():
            if include_hidden or not self.is_item_hidden(ti):
                yield ti, desc

    def iter_selection(self):
        for i in self.selectedItems():
            yield self.item_to_data[i]

    def iter_checked(self):
        # XXX - just use self.iter_treeitem_and_desc() - no need to hit the
        # XXX   tree object at all!?
        for i in range(self.topLevelItemCount()):
            item = self.topLevelItem(i)
            if item.checkState(0) == QtCore.Qt.Checked:
                yield self.item_to_data[item]

    def show_context_menu(self, pos):
        """Context menu and double-click related functions..."""
        self.context_menu.popup(self.viewport().mapToGlobal(pos))

    def update_context_menu_actions(self):
        contains_non_versioned = False
        for desc in self.iter_selection():
            if desc[3] == (False, False):
                contains_non_versioned = True
                break
        self.revert_action.setEnabled(not contains_non_versioned)
        self.show_diff_ui.setEnabled(not contains_non_versioned)

    def revert_selected(self):
        """Revert the selected file."""
        items = self.selectedItems()
        if not items:
            return
        
        paths = [self.item_to_data[item][1][1] for item in items]
        
        args = ["revert"]
        args.extend(paths)
        desc = (gettext("Revert %s to latest revision.") % ", ".join(paths))
        revert_dialog = SimpleSubProcessDialog(gettext("Revert"),
                                         desc=desc,
                                         args=args,
                                         dir=self.tree.basedir,
                                         parent=self,
                                         hide_progress=True,
                                        )
        res = revert_dialog.exec_()
        if res == QtGui.QDialog.Accepted:
            for item in items:
                index = self.indexOfTopLevelItem(item)
                self.takeTopLevelItem(index)

    def itemDoubleClicked(self, items=None, column=None):
        self.show_differences()
    
    def show_differences(self, ext_diff=None):
        """Show differences between the working copy and the last revision."""
        if not self.show_diff_ui.isEnabled():
            return
        
        entries = [desc.path() for desc in self.iter_selection()]
        if entries:
            arg_provider = InternalWTDiffArgProvider(
                self.tree.basis_tree().get_revision_id(), self.tree,
                self.tree.branch, self.tree.branch,
                specific_files=entries)
            
            show_diff(arg_provider, ext_diff=ext_diff,
                      parent_window=self.topLevelWidget())

    def set_selectall_checkbox(self, checkbox):
        """Helpers for a 'show all' checkbox.  Parent widgets must create the
        widget and pass it to us.
        """
        checkbox.setTristate(True)
        self.selectall_checkbox = checkbox
        parent = self.parentWidget()
        parent.connect(self,
                     QtCore.SIGNAL("itemChanged(QTreeWidgetItem *, int)"),
                     self.update_selectall_state)
        
        parent.connect(checkbox, QtCore.SIGNAL("stateChanged(int)"),
                                               self.selectall_changed)

    def update_selectall_state(self, item, column):
        """Update the state of the 'select all' checkbox to reflect the state
        of the items in the list.
        """
        if self._ignore_select_all_changes:
            return
        checked = 0
        num_items = 0

        for (tree_item, change_desc) in self.iter_treeitem_and_desc():
            if tree_item.checkState(0) == QtCore.Qt.Checked:
                checked += 1
            num_items += 1
        self._ignore_select_all_changes = True
        if checked == 0:
            self.selectall_checkbox.setCheckState(QtCore.Qt.Unchecked)
        elif checked == num_items:
            self.selectall_checkbox.setCheckState(QtCore.Qt.Checked)
        else:
            self.selectall_checkbox.setCheckState(QtCore.Qt.PartiallyChecked)
        self._ignore_select_all_changes = False

    def selectall_changed(self, state):
        if self._ignore_select_all_changes or not self.selectall_checkbox.isEnabled():
            return
        if state == QtCore.Qt.PartiallyChecked:
            self.selectall_checkbox.setCheckState(QtCore.Qt.Checked)
            return

        self._ignore_select_all_changes = True
        for (tree_item, change_desc) in self.iter_treeitem_and_desc():
            tree_item.setCheckState(0, QtCore.Qt.CheckState(state))
        self._ignore_select_all_changes = False


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

    NOTE: None value used for non-existing entry in corresponding
          tree, e.g. for added/deleted/ignored/unversioned
    """

    def path(desc):
        """Return a suitable entry for a 'specific_files' param to bzr functions."""
        oldpath, newpath = desc[1]
        return newpath or oldpath

    def oldpath(desc):
        """Return oldpath for renames."""
        return desc[1][0]

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


def closure_in_selected_list(selected_list):
    """Return in_selected_list(path) function for given selected_list."""

    def in_selected_list(path):
        """Check: is path belongs to some selected_list."""
        if path in selected_list:
            return True
        for p in selected_list:
            if path.startswith(p):
                return True
        return False

    if not selected_list:
        return lambda path: True
    return in_selected_list
