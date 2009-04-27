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

from bzrlib.plugins.qbzr.lib.diff import (
    DiffButtons,
    show_diff,
    )
from bzrlib.plugins.qbzr.lib.i18n import gettext
from bzrlib.plugins.qbzr.lib.subprocess import SubProcessDialog
from bzrlib.plugins.qbzr.lib.wtlist import (
    ChangeDesc,
    WorkingTreeFileList,
    closure_in_selected_list,
    )


class RevertWindow(SubProcessDialog):

    def __init__(self, tree, selected_list, dialog=True, parent=None,
                 local=None, message=None, ui_mode=True, backup=True):
        self.tree = tree
        self.initial_selected_list = selected_list
        
        SubProcessDialog.__init__(self,
                                  gettext("Revert"),
                                  name = "revert",
                                  default_size = (400, 400),
                                  ui_mode = ui_mode,
                                  dialog = dialog,
                                  parent = parent,
                                  hide_progress=True)
        
        # Display the list of changed files
        groupbox = QtGui.QGroupBox(gettext("Changes"), self)

        self.filelist = WorkingTreeFileList(groupbox, self.tree)

        self.tree.lock_read()
        try:
            self.filelist.fill(self.iter_changes_and_state())
        finally:
            self.tree.unlock()

        self.filelist.setup_actions()

        vbox = QtGui.QVBoxLayout(groupbox)
        vbox.addWidget(self.filelist)
        selectall_checkbox = QtGui.QCheckBox(
            gettext(self.filelist.SELECTALL_MESSAGE))
        selectall_checkbox.setCheckState(QtCore.Qt.Checked)
        selectall_checkbox.setEnabled(True)
        self.filelist.set_selectall_checkbox(selectall_checkbox)
        vbox.addWidget(selectall_checkbox)

        self.no_backup_checkbox = QtGui.QCheckBox(
            gettext('Do not save backups of reverted files'))
        if not backup:
            self.no_backup_checkbox.setCheckState(QtCore.Qt.Checked)
        self.no_backup_checkbox.setEnabled(True)
        vbox.addWidget(self.no_backup_checkbox)

        self.filelist.sortItems(0, QtCore.Qt.AscendingOrder)

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

        # Diff button to view changes in files selected to revert
        self.diffbuttons = DiffButtons(self)
        self.diffbuttons.setToolTip(
            gettext("View changes in files selected to revert"))
        self.connect(self.diffbuttons, QtCore.SIGNAL("triggered(QString)"),
                     self.show_diff_for_checked)
        hbox = QtGui.QHBoxLayout()
        hbox.addWidget(self.diffbuttons)
        hbox.addWidget(self.buttonbox)
        layout.addLayout(hbox)

    def iter_changes_and_state(self):
        """An iterator for the WorkingTreeFileList widget"""

        in_selected_list = closure_in_selected_list(self.initial_selected_list)

        for desc in self.tree.iter_changes(self.tree.basis_tree()):
            desc = ChangeDesc(desc)
            assert desc.is_modified(), "expecting only modified!"
            if desc.is_tree_root():
                continue
            path = desc.path()
            check_state = in_selected_list(path)
            yield desc, True, check_state

    def start(self):
        """Revert the files."""
        args = ["revert"]
        if self.no_backup_checkbox.checkState():
            args.append("--no-backup")
        for desc in self.filelist.iter_checked():
            args.append(desc.path())
        self.process_widget.start(self.tree.basedir, *args)

    def saveSize(self):
        SubProcessDialog.saveSize(self)
        self.saveSplitterSizes()

    def show_diff_for_checked(self, ext_diff=None, dialog_action='revert'):
        """Diff button clicked: show the diff for checked entries.

        @param  ext_diff:       selected external diff tool (if any)
        @param  dialog_action:  purpose of parent window (main action)
        """
        # XXX make this function universal for both qcommit and qrevert (?)
        checked = []
        for desc in self.filelist.iter_checked():
            path = desc.path()
            checked.append(path)

        if checked:
            show_diff(self.tree.basis_tree().get_revision_id(), None,
                     self.tree.branch, self.tree.branch,
                     new_wt=self.tree,
                     specific_files=checked,
                     ext_diff=ext_diff,
                     parent_window=self)
        else:
            msg = "No changes selected to " + dialog_action
            QtGui.QMessageBox.warning(self,
                "QBzr - " + gettext("Diff"),
                gettext(msg),
                QtGui.QMessageBox.Ok)
