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
from bzrlib.trace import log_exception_quietly

from bzrlib.errors import BzrError
from bzrlib.plugins.qbzr.lib.subprocess import SubProcessWindow
from bzrlib.plugins.qbzr.lib.util import (
    BTN_CANCEL,
    BTN_OK,
    QBzrWindow,
    file_extension,
    get_apparent_author,
    get_global_config,
    )

from bzrlib.plugins.qbzr.lib.wtlist import WorkingTreeFileList

class AddWindow(SubProcessWindow):

    def __init__(self, tree, selected_list, dialog=True, ui_mode=True, parent=None, local=None, message=None):
        self.tree = tree
        self.initial_selected_list = selected_list
        
        SubProcessWindow.__init__(self,
                                  gettext("Add"),
                                  name = "add",
                                  default_size = (400, 400),
                                  ui_mode = ui_mode,
                                  dialog = dialog,
                                  parent = parent)
        
        self.process_widget.hide_progress()
    
    def create_ui(self, parent):
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

        return groupbox


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

        show_ignored = self.show_ignored_checkbox.isChecked()

        for desc in self.tree.iter_changes(self.tree.basis_tree(),
                                           want_unversioned=True):

            is_versioned = desc[3] != (False, False)
            if is_versioned:
                continue

            pis, pit = desc[1]
            visible = show_ignored or not self.tree.is_ignored(pit)
            check_state = visible and in_selected_list(pit)
            yield desc, visible, check_state

    def start(self):
        """Add the files."""
        args = ["add"]
        for desc in self.filelist.iter_checked():
            args.append(self.filelist.get_changedesc_path(desc))
        
        self.process_widget.start(*args)

    def show_ignored(self, state):
        """Show/hide ignored files."""
        state = not state
        for (tree_item, change_desc) in self.filelist.iter_treeitem_and_desc(True):
            path = self.filelist.get_changedesc_path(change_desc)
            if self.tree.is_ignored(path):
                tree_item.setHidden(state)
        self.filelist.update_selectall_state(None, None)
