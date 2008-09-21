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

from bzrlib.plugins.qbzr.lib.diff import DiffWindow
from bzrlib.plugins.qbzr.lib.i18n import gettext, N_
from bzrlib.plugins.qbzr.lib.subprocess import SubProcessDialog
from bzrlib.plugins.qbzr.lib.util import (
    file_extension,
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
                       self.show_differences)

        self.setContextMenuPolicy(QtCore.Qt.CustomContextMenu)
        parent.connect(self,
                       QtCore.SIGNAL("itemSelectionChanged()"),
                       self.update_context_menu_actions)
        parent.connect(self,
                       QtCore.SIGNAL("customContextMenuRequested(QPoint)"),
                       self.show_context_menu)

        self.context_menu = QtGui.QMenu(self)
        self.show_diff_action = self.context_menu.addAction(
            gettext("Show &differences..."), self.show_differences)
        self.context_menu.setDefaultAction(self.show_diff_action)
        self.revert_action = self.context_menu.addAction(
            gettext("&Revert..."), self.revert_selected)
        # set all actions to disabled so it does the right thing with an empty
        # list (our itemSelectionChanged() will fire as soon as we select one)
        self.revert_action.setEnabled(False)
        self.show_diff_action.setEnabled(False)

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
        ivs = [] # work around the fact visibility seems to be ignored at creation
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
                # versioned = True, True - so either renamed or modified.
                if path_in_source != path_in_target:
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
                else:
                    raise RuntimeError, "what status am I missing??"

            item = QtGui.QTreeWidgetItem()
            item.setText(0, name)
            item.setText(1, ext)
            item.setText(2, status)
            items.append(item)
            ivs.append((item, visible))

            if checked is None:
                pass
            elif checked:
                item.setCheckState(0, QtCore.Qt.Checked)
            else:
                item.setCheckState(0, QtCore.Qt.Unchecked)
            item.setHidden(not visible)
            self.item_to_data[item] = change_desc
        # add them all to the tree in one hit.
        self.insertTopLevelItems(0, items)
        # for some reason the visibility doesn't work when added above??
        for item, visible in ivs:
            self.setItemHidden(item, not visible)
        self._ignore_select_all_changes = False
        if self.selectall_checkbox is not None:
            self.update_selectall_state(None, None)

    def iter_treeitem_and_desc(self, include_hidden=False):
        """iterators to help work with the selection, checked items, etc"""
        for ti, desc in self.item_to_data.iteritems():
            if include_hidden or not ti.isHidden():
                yield ti, desc

    def iter_selection(self):
        for i in self.selectedItems():
            yield self.item_to_data[i]

    def iter_checked(self):
        # XXX - just use self.iter_treeitem_and_desc() - no need to hit the
        # XXX   tree object at all!?
        for i in range(self.topLevelItemCount()):
            item = self.topLevelItem(i)
            if not item.isHidden() and item.checkState(0) == QtCore.Qt.Checked:
                yield self.item_to_data[item]

    # desc: iter_changes return tuple with info about changed entry
    # desc[0]: file_id         -> ascii string
    # desc[1]: paths           -> 2-tuple (old, new) fullpaths unicode/None
    # desc[2]: changed_content -> bool
    # desc[3]: versioned       -> 2-tuple (bool, bool)
    # desc[4]: parent          -> 2-tuple
    # desc[5]: name            -> 2-tuple (old_name, new_name) utf-8?/None
    # desc[6]: kind            -> 2-tuple (string/None, string/None)
    # desc[7]: executable      -> 2-tuple (bool/None, bool/None)
    # NOTE: None value used for non-existing entry in corresponding
    #       tree, e.g. for added/deleted file

    @classmethod
    def is_changedesc_versioned(cls, desc):
        """Given bzr changedesc tuple, return if the item is 'versioned'"""
        return desc[3] != (False, False)

    @classmethod
    def is_changedesc_tree_root(cls, desc):
        """Check is entry actually tree root."""
        if desc[0] is not None and desc[4] == (None, None):
            # TREE_ROOT has not parents (desc[4]).
            # But because we could want to see unversioned files
            # we need to check for file_id too (desc[0])
            return True
        return False

    @classmethod
    def is_changedesc_modified(cls, desc):
        """Is the item 'versioned' and considered modified."""
        return cls.is_changedesc_versioned(desc) and desc[2]

    @classmethod
    def is_changedesc_renamed(cls, desc):
        """Is the item renamed."""
        return (desc[3] == (True, True)
                and (desc[4][0], desc[5][0]) != (desc[4][1], desc[5][1]))

    @classmethod
    def get_changedesc_path(cls, desc):
        """Return a suitable entry for a 'specific_files' param to bzr functions."""
        pis, pit = desc[1]
        return pit or pis

    @classmethod
    def get_changedesc_oldpath(cls, desc):
        """Return oldpath for renames."""
        return desc[1][0]

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
        self.show_diff_action.setEnabled(not contains_non_versioned)

    def revert_selected(self):
        """Revert the selected file."""
        items = self.selectedItems()
        if not items:
            return
        
        paths = [self.item_to_data[item][1][1] for item in items]
        
        args = ["revert"]
        args.extend(paths)
        desc = (gettext("Revert %s to latest revision.") % ", ".join(paths))
        revert_dialog = SubProcessDialog(gettext("Revert"),
                                         desc=desc,
                                         args=args,
                                         dir=self.tree.basedir,
                                         parent=self,
                                        )
        res = revert_dialog.exec_()
        if res == QtGui.QDialog.Accepted:
            for item in items:
                index = self.indexOfTopLevelItem(item)
                self.takeTopLevelItem(index)

    def show_differences(self, items=None, column=None):
        """Show differences between the working copy and the last revision."""
        if not self.show_diff_action.isEnabled():
            return
    
        entries = [self.get_changedesc_path(d) for d in self.iter_selection()]
        if entries:
            window = DiffWindow(self.tree.basis_tree(), self.tree,
                                self.tree.branch, self.tree.branch,
                                specific_files=entries,
                                parent=self,
                                )
            self.topLevelWidget().windows.append(window)
            window.show()

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
