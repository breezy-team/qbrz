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
        
        self.throbber = ThrobberWidget(self) 

        # Display the list of changed files
        groupbox = QtGui.QGroupBox(gettext("Changes"), self)

        self.filelist = TreeWidget(groupbox)
        self.filelist.throbber = self.throbber 
        self.filelist.tree_model.is_item_in_select_all = lambda item: ( 
            item.change is not None and item.change.is_versioned())
        self.filelist.setRootIsDecorated(False)
        def filter_context_menu():
            TreeWidget.filter_context_menu(self.filelist)
            self.filelist.action_add.setVisible(False)
            self.filelist.action_revert.setVisible(False)
        self.filelist.filter_context_menu = filter_context_menu

        vbox = QtGui.QVBoxLayout(groupbox)
        vbox.addWidget(self.filelist)
        selectall_checkbox = SelectAllCheckBox(self.filelist, groupbox)
        selectall_checkbox.setCheckState(QtCore.Qt.Checked)
        selectall_checkbox.setEnabled(True)
        vbox.addWidget(selectall_checkbox)

        self.no_backup_checkbox = QtGui.QCheckBox(
            gettext('Do not save backups of reverted files'))
        if not backup:
            self.no_backup_checkbox.setCheckState(QtCore.Qt.Checked)
        self.no_backup_checkbox.setEnabled(True)
        vbox.addWidget(self.no_backup_checkbox)

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
        fmodel = self.filelist.tree_filter_model 
        #fmodel.setFilter(fmodel.UNVERSIONED, False) 
        self.filelist.set_tree(self.tree, changes_mode=True,
                               want_unversioned=False,
                               initial_checked_paths=self.initial_selected_list) 
        self.throbber.hide()

    def start(self):
        """Revert the files."""
        args = ["revert"]
        if self.no_backup_checkbox.checkState():
            args.append("--no-backup")
        args.extend([ref.path
                     for ref in self.filelist.tree_model.iter_checked()])
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
        checked = [ref.path for ref in self.filelist.iter_checked()]

        if checked:
            arg_provider = InternalWTDiffArgProvider(
                self.tree.basis_tree().get_revision_id(), self.tree,
                self.tree.branch, self.tree.branch,
                specific_files=checked)
            
            show_diff(arg_provider, ext_diff=ext_diff, parent_window=self)

        else:
            msg = "No changes selected to " + dialog_action
            QtGui.QMessageBox.warning(self,
                "QBzr - " + gettext("Diff"),
                gettext(msg),
                QtGui.QMessageBox.Ok)
