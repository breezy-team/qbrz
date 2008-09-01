# -*- coding: utf-8 -*-
#
# QBzr - Qt frontend to Bazaar commands:
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
from bzrlib.plugins.qbzr.lib.util import (
    BTN_CANCEL,
    BTN_OK,
    QBzrWindow,
    file_extension,
    get_apparent_author,
    get_global_config,
    )

from bzrlib.plugins.qbzr.lib.wtlist import WorkingTreeFileList

class RevertWindow(QBzrWindow):

    def __init__(self, tree, selected_list, dialog=True, parent=None, local=None, message=None):
        title = [gettext("Revert")]
        QBzrWindow.__init__(self, title, parent)
        self.restoreSize("revert", (400, 400))
        if dialog:
            flags = (self.windowFlags() & ~QtCore.Qt.Window) | QtCore.Qt.Dialog
            self.setWindowFlags(flags)

        self.tree = tree
        self.initial_selected_list = selected_list

        vbox = QtGui.QVBoxLayout(self.centralwidget)

        # Display the list of changed files
        groupbox = QtGui.QGroupBox(gettext("Changes"), self)
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
        selectall_checkbox = QtGui.QCheckBox(
            gettext(self.filelist.SELECTALL_MESSAGE))
        selectall_checkbox.setCheckState(QtCore.Qt.Checked)
        selectall_checkbox.setEnabled(True)
        self.filelist.set_selectall_checkbox(selectall_checkbox)
        vbox.addWidget(selectall_checkbox)

        self.filelist.sortItems(0, QtCore.Qt.AscendingOrder)

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

        for desc in self.tree.iter_changes(self.tree.basis_tree()):
            assert self.filelist.is_changedesc_modified(desc), "expecting only modified!"
            path = self.filelist.get_changedesc_path(desc)
            check_state = in_selected_list(path)
            yield desc, True, check_state

    def accept(self):
        """Revert the files."""
        paths = [self.filelist.get_changedesc_path(d)
                 for d in self.filelist.iter_checked()]
        try:
            self.tree.revert(paths, self.tree.branch.repository.revision_tree(self.tree.last_revision()))
        except BzrError, e:
            log_exception_quietly()
            QtGui.QMessageBox.warning(self,
                "QBzr - " + gettext("Revert"), str(e), QtGui.QMessageBox.Ok)

        self.close()

    def reject(self):
        """Cancel the revert."""
        self.close()
