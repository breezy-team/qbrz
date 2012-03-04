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

from PyQt4 import QtCore, QtGui

from bzrlib import errors
from bzrlib.plugins.qbzr.lib.diff import (
    DiffButtons,
    show_diff,
    InternalWTDiffArgProvider,
    )
from bzrlib.plugins.qbzr.lib.i18n import gettext
from bzrlib.plugins.qbzr.lib.subprocess import SubProcessDialog
from bzrlib.plugins.qbzr.lib.treewidget import (
    TreeWidget,
    SelectAllCheckBox,
    )
from bzrlib.plugins.qbzr.lib.util import (
    ThrobberWidget,
    runs_in_loading_queue,
    )
from bzrlib.plugins.qbzr.lib.uifactory import ui_current_widget
from bzrlib.plugins.qbzr.lib.trace import reports_exception
from bzrlib.plugins.qbzr.lib.commit import PendingMergesList


class RevertWindow(SubProcessDialog):

    def __init__(self, tree, selected_list, dialog=True, parent=None,
                 local=None, message=None, ui_mode=True, backup=True):
        self.tree = tree
        self.has_pending_merges = len(tree.get_parent_ids())>1
        self.initial_selected_list = selected_list
        
        SubProcessDialog.__init__(self,
                                  gettext("Revert"),
                                  name = "revert",
                                  default_size = (400, 400),
                                  ui_mode = ui_mode,
                                  dialog = dialog,
                                  parent = parent,
                                  hide_progress=True)

        self.throbber = ThrobberWidget(self) 

        # Display the list of changed files
        self.file_groupbox = QtGui.QGroupBox(gettext("Select changes to revert"), self)

        self.filelist = TreeWidget(self.file_groupbox)
        self.filelist.throbber = self.throbber 
        self.filelist.tree_model.set_select_all_kind('versioned')

        def filter_context_menu():
            TreeWidget.filter_context_menu(self.filelist)
            self.filelist.action_add.setVisible(False)
            self.filelist.action_revert.setVisible(False)
        self.filelist.filter_context_menu = filter_context_menu

        self.selectall_checkbox = SelectAllCheckBox(self.filelist, self.file_groupbox)
        self.selectall_checkbox.setEnabled(True)

        self.no_backup_checkbox = QtGui.QCheckBox(
            gettext('Do not save backups of reverted files'))
        if not backup:
            self.no_backup_checkbox.setCheckState(QtCore.Qt.Checked)
        self.no_backup_checkbox.setEnabled(True)

        filesbox = QtGui.QVBoxLayout(self.file_groupbox)
        filesbox.addWidget(self.filelist)
        filesbox.addWidget(self.selectall_checkbox)
        filesbox.addWidget(self.no_backup_checkbox)
        
        if self.has_pending_merges:
            self.file_groupbox.setCheckable(True)
            self.merges_groupbox = QtGui.QGroupBox(gettext("Forget pending merges"))
            self.merges_groupbox.setCheckable(True)
            # This keeps track of what the merges_groupbox was before the
            # select all changes it, so that it can put it back to the state
            # it was.
            self.merges_base_checked = True
            self.pending_merges = PendingMergesList(
                self.processEvents, self.throbber, self)
            merges_box = QtGui.QVBoxLayout(self.merges_groupbox)
            merges_box.addWidget(self.pending_merges)
            
            self.connect(self.selectall_checkbox,
                         QtCore.SIGNAL("stateChanged(int)"),
                         self.selectall_state_changed)
            self.connect(self.merges_groupbox,
                         QtCore.SIGNAL("clicked(bool)"),
                         self.merges_clicked)
            self.connect(self.file_groupbox,
                         QtCore.SIGNAL("clicked(bool)"),
                         self.file_groupbox_clicked)
            self.connect(self.filelist.tree_model,
                         QtCore.SIGNAL("dataChanged(QModelIndex, QModelIndex)"),
                         self.filelist_data_changed)
            
        
        # groupbox gets disabled as we are executing.
        QtCore.QObject.connect(self,
                               QtCore.SIGNAL("disableUi(bool)"),
                               self.file_groupbox,
                               QtCore.SLOT("setDisabled(bool)"))

        self.splitter = QtGui.QSplitter(QtCore.Qt.Vertical)
        self.splitter.addWidget(self.file_groupbox)
        if self.has_pending_merges:
            self.splitter.addWidget(self.merges_groupbox)
        
        self.splitter.addWidget(self.make_default_status_box())
        self.splitter.setStretchFactor(0, 10)
        self.restoreSplitterSizes([150, 150])

        layout = QtGui.QVBoxLayout(self)
        layout.addWidget(self.throbber)
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
        self.throbber.show()

    def show(self): 
        SubProcessDialog.show(self) 
        QtCore.QTimer.singleShot(1, self.initial_load) 

    @runs_in_loading_queue 
    @ui_current_widget 
    @reports_exception() 
    def initial_load(self):
        self.filelist.tree_model.checkable = True 
        #fmodel.setFilter(fmodel.UNVERSIONED, False) 
        if self.initial_selected_list is None and not self.has_pending_merges:
            self.initial_selected_list = []

        self.filelist.set_tree(self.tree, changes_mode=True,
                               want_unversioned=False,
                               initial_checked_paths=self.initial_selected_list)
        self.filelist_checked_base = list(
            self.filelist.tree_model.iter_checked())
        self.selectall_checkbox.update_state()
        self.processEvents()

        if self.has_pending_merges:
            self.pending_merges.load_tree(self.tree)
            self.processEvents()

        self.throbber.hide()

    # The logic for the next 4 methods is like this:
    # * Either file_groupbox or merges_groupbox or both must be checked,
    #   never neither.
    # * If merges_groupbox is checked, all files must be checked. If a file is
    #   unchecked, merges_groupbox must be unchecked.
    # Unless:
    # * file_groupbox is unchecked - then all files are unchecked.
    #
    # We keep a recored of what was checked, so that we we change something,
    # and then later we go back to a state where that change was not necessary,
    # we can return to what it was. This is stored in merges_base_checked, and
    # filelist_checked_base.
    
    def selectall_state_changed(self, state):
        if state == QtCore.Qt.Checked:
            self.merges_groupbox.setChecked(self.merges_base_checked)
        elif self.file_groupbox.isChecked():
            self.merges_groupbox.setChecked(False)
    
    def merges_clicked(self, state):
        self.merges_base_checked = state
        
        if state:
            if self.file_groupbox.isChecked():
                self.selectall_checkbox.clicked(QtCore.Qt.Checked)
            else:
                self.selectall_checkbox.clicked(QtCore.Qt.Unchecked)
        
        if not state:
            self.file_groupbox.setChecked(True)
            self.filelist.tree_model.set_checked_items(
                self.filelist_checked_base,
                ignore_no_file_error=True)
    
    def file_groupbox_clicked(self, state):
        if not state:
            self.merges_groupbox.setChecked(True)
            self.selectall_checkbox.clicked(QtCore.Qt.Unchecked)
        if state:
            if not self.merges_base_checked:
                self.filelist.tree_model.set_checked_items(
                    self.filelist_checked_base,
                    ignore_no_file_error=True)
            else:
                self.selectall_checkbox.clicked(QtCore.Qt.Checked)
    
    def filelist_data_changed(self, start, end):
        if (self.file_groupbox.isChecked() and
            not self.merges_groupbox.isChecked()):
            self.filelist_checked_base = list(
                self.filelist.tree_model.iter_checked())

    def _is_revert_pending_merges(self):
        """Return True if selected to revert pending merges,
        False if not selected, None if there is no pending merges.
        """
        if not self.has_pending_merges:
            return None
        return bool(self.merges_groupbox.isChecked())

    def _get_files_to_revert(self):
        return [ref.path
                for ref in self.filelist.tree_model.iter_checked(
                    include_unchanged_dirs=False)
                ]

    def validate(self):
        if (self._is_revert_pending_merges() is False and
            self.selectall_checkbox.checkState() == QtCore.Qt.Checked):

            if not self.ask_confirmation(
                gettext("You have selected revert for all changed paths\n"
                        "but keep pending merges.\n\n"
                        "Do you want to continue?")
                ):
                return False

        # It doesn't matter if selectall_checkbox checkbox is activated or not -
        # we really need to check if there are files selected, because you can
        # check the 'select all' checkbox if there are no files selectable.
        if not self._is_revert_pending_merges() and not self._get_files_to_revert():
            self.operation_blocked(gettext("You have not selected anything to revert."))
            return False

        return True

    def do_start(self):
        """Revert the files."""
        args = ["revert"]
        if (self._is_revert_pending_merges() is None or
            (self._is_revert_pending_merges() is False and
             self.file_groupbox.isChecked())):
            args.extend(self._get_files_to_revert())
        if (self._is_revert_pending_merges() is True and
            not self.file_groupbox.isChecked()):
            args.append("--forget-merges")
        if self.no_backup_checkbox.checkState():
            args.append("--no-backup")
        self.process_widget.do_start(self.tree.basedir, *args)

    def _saveSize(self, config):
        SubProcessDialog._saveSize(self, config)
        self._saveSplitterSizes(config, self.splitter)

    def show_diff_for_checked(self, ext_diff=None, dialog_action='revert'):
        """Diff button clicked: show the diff for checked entries.

        @param  ext_diff:       selected external diff tool (if any)
        @param  dialog_action:  purpose of parent window (main action)
        """
        # XXX make this function universal for both qcommit and qrevert (?)
        checked = [ref.path for ref in self.filelist.tree_model.iter_checked()]

        if checked:
            arg_provider = InternalWTDiffArgProvider(
                self.tree.basis_tree().get_revision_id(), self.tree,
                self.tree.branch, self.tree.branch,
                specific_files=checked)
            
            show_diff(arg_provider, ext_diff=ext_diff, parent_window=self,
                      context=self.filelist.diff_context)

        else:
            msg = "No changes selected to " + dialog_action
            QtGui.QMessageBox.warning(self,
                "QBzr - " + gettext("Diff"),
                gettext(msg),
                QtGui.QMessageBox.Ok)
