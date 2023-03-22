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

from PyQt5 import QtCore, QtGui, QtWidgets

from breezy.plugins.qbrz.lib.i18n import gettext
from breezy.plugins.qbrz.lib.subprocess import SubProcessDialog
from breezy.plugins.qbrz.lib.treewidget import (
    TreeWidget,
    SelectAllCheckBox,
    )
from breezy.plugins.qbrz.lib.util import (
    ThrobberWidget,
    runs_in_loading_queue,
    )
from breezy.plugins.qbrz.lib.uifactory import ui_current_widget
from breezy.plugins.qbrz.lib.trace import reports_exception


class AddWindow(SubProcessDialog):

    def __init__(self, tree, selected_list, dialog=True, ui_mode=True, parent=None, local=None, message=None):
        self.tree = tree
        self.initial_selected_list = selected_list
        # print('*^*^*^^ tree is', self.tree, 'initial_selected', selected_list)

        super(AddWindow, self).__init__(
            gettext("Add"),
            name = "add",
            default_size = (400, 400),
            ui_mode = ui_mode,
            dialog = dialog,
            parent = parent,
            hide_progress=True,
            )

        self.throbber = ThrobberWidget(self)

        # Display the list of unversioned files
        groupbox = QtWidgets.QGroupBox(gettext("Unversioned Files"), self)
        vbox = QtWidgets.QVBoxLayout(groupbox)

        self.filelist_widget = TreeWidget(groupbox)
        self.filelist_widget.throbber = self.throbber

        self.filelist_widget.tree_model.is_item_in_select_all = lambda item: (
            # Is in select all. - Not versioned, and not Ignored
            item.change is not None and item.change.is_ignored() is None and not item.change.is_versioned(),
            # look at children. - Not ignored
            item.change is not None and item.change.is_ignored() is None or item.change is None
            )

        def filter_context_menu():
            items = self.filelist_widget.get_selection_items()
            selection_len = len(items)
            single_file = (selection_len == 1 and items[0].item.kind == "file")
            single_item_in_tree = (selection_len == 1 and (items[0].change is None or items[0].change[6][1] is not None))

            self.filelist_widget.action_open_file.setEnabled(True)
            self.filelist_widget.action_open_file.setVisible(True)
            self.filelist_widget.action_show_file.setEnabled(single_file)
            self.filelist_widget.action_show_file.setVisible(True)
            self.filelist_widget.action_show_annotate.setVisible(False)
            self.filelist_widget.action_show_log.setVisible(False)
            self.filelist_widget.action_show_diff.setVisible(False)
            self.filelist_widget.action_add.setVisible(False)
            self.filelist_widget.action_revert.setVisible(False)
            self.filelist_widget.action_merge.setVisible(False)
            self.filelist_widget.action_resolve.setVisible(False)
            self.filelist_widget.action_rename.setVisible(True)
            self.filelist_widget.action_rename.setEnabled(single_item_in_tree)
            self.filelist_widget.action_remove.setVisible(False)
            self.filelist_widget.action_mark_move.setVisible(False)

        self.filelist_widget.filter_context_menu = filter_context_menu

        vbox.addWidget(self.filelist_widget)

        selectall_checkbox = SelectAllCheckBox(self.filelist_widget, groupbox)
        vbox.addWidget(selectall_checkbox)
        selectall_checkbox.setCheckState(QtCore.Qt.Checked)
        selectall_checkbox.setEnabled(True)

        self.show_ignored_checkbox = QtWidgets.QCheckBox(gettext("Show ignored files"), groupbox)
        vbox.addWidget(self.show_ignored_checkbox)
        self.show_ignored_checkbox.toggled[bool].connect(self.show_ignored)

        # groupbox gets disabled as we are executing.
        self.disableUi[bool].connect(groupbox.setDisabled)

        self.splitter = QtWidgets.QSplitter(QtCore.Qt.Vertical)
        self.splitter.addWidget(groupbox)
        self.splitter.addWidget(self.make_default_status_box())
        self.splitter.setStretchFactor(0, 10)
        self.restoreSplitterSizes([150, 150])

        layout = QtWidgets.QVBoxLayout(self)
        layout.addWidget(self.throbber)
        layout.addWidget(self.splitter)
        layout.addWidget(self.buttonbox)
        self.throbber.show()
        self.processEvents()

    def show(self):
        # SubProcessDialog.show(self)
        super().show()
        # QtCore.QTimer.singleShot(1, self.initial_load)
        self.initial_load()

    # @runs_in_loading_queue
    @ui_current_widget
    @reports_exception()
    def initial_load(self):
        self.filelist_widget.tree_model.checkable = True
        fmodel = self.filelist_widget.tree_filter_model
        fmodel.setFilter(fmodel.CHANGED, False)
        fmodel.setFilter(fmodel.UNCHANGED, False)
        self.filelist_widget.set_tree(self.tree, changes_mode=True, want_unversioned=True,
            initial_checked_paths=self.initial_selected_list,
            change_load_filter=lambda c:not c.is_versioned())
        self.throbber.hide()

    def _get_files_to_add(self):
        # OK pressed
        return [ref.path for ref in self.filelist_widget.tree_model.iter_checked()]

    def validate(self):
        if not self._get_files_to_add():
            self.operation_blocked(gettext("Nothing selected to add"))
            return False
        return True

    def do_start(self):
        """Add the files."""
        files = self._get_files_to_add()
        self.process_widget.do_start(self.tree.basedir, "add", "--no-recurse", *files)

    def show_ignored(self, state):
        """Show/hide ignored files."""
        fmodel = self.filelist_widget.tree_filter_model
        fmodel.setFilter(fmodel.IGNORED, state)
        # self.filelist_widget.update_selectall_state(None, None)

    def _saveSize(self, config):
        SubProcessDialog._saveSize(self, config)
        self._saveSplitterSizes(config, self.splitter)
