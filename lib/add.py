# -*- coding: utf-8 -*-
#
# QBzr - Qt frontend to Bazaar commands
#
# Contributors:
#  Mark Hammond <mhammond@skippinet.com.au>
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
from bzrlib.plugins.qbzr.lib.subprocess import SubProcessDialog
from bzrlib.plugins.qbzr.lib.wtlist import (
    ChangeDesc,
    WorkingTreeFileList,
    closure_in_selected_list,
    )


class AddWindow(SubProcessDialog):

    def __init__(self, tree, selected_list, dialog=True, ui_mode=True, parent=None, local=None, message=None):
        self.tree = tree
        self.initial_selected_list = selected_list
        
        super(AddWindow, self).__init__(
                                  gettext("Add"),
                                  name = "add",
                                  default_size = (400, 400),
                                  ui_mode = ui_mode,
                                  dialog = dialog,
                                  parent = parent,
                                  hide_progress=True,
                                  )
    
        # Display the list of unversioned files
        groupbox = QtGui.QGroupBox(gettext("Unversioned Files"), self)
        vbox = QtGui.QVBoxLayout(groupbox)

        self.filelist = WorkingTreeFileList(groupbox, self.tree)
        vbox.addWidget(self.filelist)
        self.filelist.sortItems(0, QtCore.Qt.AscendingOrder)
        self.filelist.setup_actions()
        
        selectall_checkbox = QtGui.QCheckBox(
            gettext(self.filelist.SELECTALL_MESSAGE),
            groupbox)
        vbox.addWidget(selectall_checkbox)
        selectall_checkbox.setCheckState(QtCore.Qt.Checked)
        selectall_checkbox.setEnabled(True)
        self.filelist.set_selectall_checkbox(selectall_checkbox)

        self.show_ignored_checkbox = QtGui.QCheckBox(
            gettext("Show ignored files"),
            groupbox)
        vbox.addWidget(self.show_ignored_checkbox)
        self.connect(self.show_ignored_checkbox, QtCore.SIGNAL("toggled(bool)"), self.show_ignored)
        
        self.tree.lock_read()
        try:
            self.filelist.fill(self.iter_changes_and_state())
        finally:
            self.tree.unlock()

        # groupbox gets disabled as we are executing.
        QtCore.QObject.connect(self,
                               QtCore.SIGNAL("subprocessStarted(bool)"),
                               groupbox,
                               QtCore.SLOT("setDisabled(bool)"))

        self.splitter = QtGui.QSplitter(QtCore.Qt.Vertical)
        self.splitter.addWidget(groupbox)
        self.splitter.addWidget(self.make_default_status_box())
        self.splitter.setStretchFactor(0, 10)
        self.restoreSplitterSizes([150, 150])

        layout = QtGui.QVBoxLayout(self)
        layout.addWidget(self.splitter)
        layout.addWidget(self.buttonbox)

    def iter_changes_and_state(self):
        """An iterator for the WorkingTreeFileList widget"""

        in_selected_list = closure_in_selected_list(self.initial_selected_list)

        show_ignored = self.show_ignored_checkbox.isChecked()

        for desc in self.tree.iter_changes(self.tree.basis_tree(),
                                           want_unversioned=True):

            desc = ChangeDesc(desc)
            if desc.is_versioned():
                continue

            pit = desc.path()
            visible = show_ignored or not self.tree.is_ignored(pit)
            check_state = visible and in_selected_list(pit)
            yield desc, visible, check_state

    def start(self):
        """Add the files."""
        files = []
        for desc in self.filelist.iter_checked():
            files.append(desc.path())
        
        self.process_widget.start(self.tree.basedir, "add", *files)

    def show_ignored(self, state):
        """Show/hide ignored files."""
        state = not state
        for (tree_item, change_desc) in self.filelist.iter_treeitem_and_desc(True):
            path = change_desc.path()
            if self.tree.is_ignored(path):
                self.filelist.set_item_hidden(tree_item, state)
        self.filelist.update_selectall_state(None, None)

    def saveSize(self):
        SubProcessDialog.saveSize(self)
        self.saveSplitterSizes()
