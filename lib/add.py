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

import os
from PyQt4 import QtCore, QtGui
from bzrlib.plugins.qbzr.lib.i18n import gettext
from bzrlib.trace import log_exception_quietly

from bzrlib.errors import BzrError
from bzrlib.plugins.qbzr.lib.util import (
    BTN_CANCEL,
    BTN_OK,
    QBzrWindow,
    file_extension,
    get_apparent_author,
    get_global_config,
    )

from bzrlib.plugins.qbzr.lib.wtlist import WorkingTreeFileList

class AddWindow(QBzrWindow):

    def __init__(self, tree, selected_list, dialog=True, parent=None, local=None, message=None):
        title = [gettext("Add")]
        QBzrWindow.__init__(self, title, parent)
        self.restoreSize("add", (400, 400))
        if dialog:
            flags = (self.windowFlags() & ~QtCore.Qt.Window) | QtCore.Qt.Dialog
            self.setWindowFlags(flags)

        self.tree = tree
        self.initial_selected_list = selected_list

        vbox = QtGui.QVBoxLayout(self.centralwidget)

        # Display the list of unversioned files
        groupbox = QtGui.QGroupBox(gettext("Unversioned Files"), self)
        vbox.addWidget(groupbox)

        self.filelist = WorkingTreeFileList(groupbox, self.tree)

        buttonbox = self.create_button_box(BTN_OK, BTN_CANCEL)
        vbox.addWidget(buttonbox)

        tree.lock_read()
        try:
            self.filelist.fill(self.iter_changes_and_state())
        finally:
            tree.unlock()

        self.filelist.setup_actions()

        vbox = QtGui.QVBoxLayout(groupbox)
        vbox.addWidget(self.filelist)
        self._ignore_select_all_changes = False
        self.select_all_checkbox = QtGui.QCheckBox(
            gettext("Select / deselect all"))
        self.select_all_checkbox.setTristate(True)
        self.select_all_checkbox.setCheckState(QtCore.Qt.Checked)
        self.select_all_checkbox.setEnabled(True)
        self.connect(self.select_all_checkbox, QtCore.SIGNAL("stateChanged(int)"), self.select_all_files)
        vbox.addWidget(self.select_all_checkbox)

        self.filelist.sortItems(0, QtCore.Qt.AscendingOrder)

        self.connect(self.filelist,
                     QtCore.SIGNAL("itemChanged(QTreeWidgetItem *, int)"),
                     self.update_selected_files)
        self.update_selected_files(None, None)


    def iter_changes_and_state(self):
        """An iterator for the WorkingTreeFileList widget"""

        def in_selected_list(path):
            if not self.initial_selected_list:
                return True
            if path in self.initial_selected_list:
                return True
            for p in self.initial_selected_list:
                if path.startswith(p):
                    return True
            return False

        for desc in self.tree.iter_changes(self.tree.basis_tree(),
                                           want_unversioned=True):

            is_versioned = desc[3] != (False, False)
            if is_versioned:
                continue

            pis, pit = desc[1]
            check_state = in_selected_list(pit)
            yield desc, check_state

    def accept(self):
        """Add the files."""
        try:
            for desc in self.filelist.iter_checked():
                self.tree.add(self.filelist.get_changedesc_path(desc))
        except BzrError, e:
            log_exception_quietly()
            QtGui.QMessageBox.warning(self,
                "QBzr - " + gettext("Add"), str(e), QtGui.QMessageBox.Ok)

        self.close()

    def reject(self):
        """Cancel the add."""
        self.close()

    def show_nonversioned(self, state):
        """Show/hide non-versioned files."""
        state = not state
        for (tree_item, change_desc) in self.filelist.iter_tree_and_desc():
            if change_desc[3] == (False, False):
                tree_item.setHidden(state)
        self.update_selected_files(None, None)

    def update_selected_files(self, item, column):
        checked = 0
        num_items = 0

        for (tree_item, change_desc) in self.filelist.iter_treeitem_and_desc():
            if tree_item.checkState(0) == QtCore.Qt.Checked:
                checked += 1
            num_items += 1
        self._ignore_select_all_changes = True
        if checked == 0:
            self.select_all_checkbox.setCheckState(QtCore.Qt.Unchecked)
        elif checked == num_items:
            self.select_all_checkbox.setCheckState(QtCore.Qt.Checked)
        else:
            self.select_all_checkbox.setCheckState(QtCore.Qt.PartiallyChecked)
        self._ignore_select_all_changes = False

    def select_all_files(self, state):
        if self._ignore_select_all_changes:
            return
        if state == QtCore.Qt.PartiallyChecked:
            self.select_all_checkbox.setCheckState(QtCore.Qt.Checked)
            return

        for (tree_item, change_desc) in self.filelist.iter_treeitem_and_desc():
            tree_item.setCheckState(0, QtCore.Qt.CheckState(state))
