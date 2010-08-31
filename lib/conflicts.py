# -*- coding: utf-8 -*-
#
# QBzr - Qt frontend to Bazaar commands
# Copyright (C) 2009 Lukáš Lalinský <lalinsky@gmail.com>
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
from bzrlib.config import GlobalConfig
from bzrlib.conflicts import resolve
from bzrlib.workingtree import WorkingTree
from bzrlib.plugins.qbzr.lib.i18n import gettext, N_, ngettext
from bzrlib.plugins.qbzr.lib.util import (
    BTN_CLOSE, BTN_REFRESH,
    QBzrWindow,
    get_qbzr_config,
    StandardButton,
    )

try:
    from bzrlib.cmdline import split as cmdline_split
except ImportError:
    from bzrlib.commands import shlex_split_unicode as cmdline_split


class ConflictsWindow(QBzrWindow):

    def __init__(self, wt_dir, parent=None):
        self.merge_action = None
        self.wt_dir = wt_dir
        QBzrWindow.__init__(self,
            [gettext("Conflicts")], parent)
        self.restoreSize("conflicts", (550, 380))

        vbox = QtGui.QVBoxLayout(self.centralwidget)

        self.conflicts_list = QtGui.QTreeWidget(self)
        self.conflicts_list.setRootIsDecorated(False)
        self.conflicts_list.setUniformRowHeights(True)
        self.conflicts_list.setSelectionBehavior(QtGui.QAbstractItemView.SelectRows)
        self.conflicts_list.setSelectionMode(QtGui.QAbstractItemView.ExtendedSelection)
        self.conflicts_list.setHeaderLabels([
            gettext("File"),
            gettext("Conflict"),
            ])
        self.connect(
            self.conflicts_list.selectionModel(),
            QtCore.SIGNAL("selectionChanged(QItemSelection, QItemSelection)"),
            self.update_selection)
        self.connect(
            self.conflicts_list,
            QtCore.SIGNAL("customContextMenuRequested(QPoint)"),
            self.show_context_menu)
        self.connect(
            self.conflicts_list,
            QtCore.SIGNAL("itemDoubleClicked(QTreeWidgetItem *, int)"),
            self.launch_merge_tool)
        self.conflicts_list.setContextMenuPolicy(QtCore.Qt.CustomContextMenu)
        self.conflicts_list.setSortingEnabled(True)
        self.conflicts_list.sortByColumn(0, QtCore.Qt.AscendingOrder)
        header = self.conflicts_list.header()
        header.setStretchLastSection(False)
        header.setResizeMode(0, QtGui.QHeaderView.Stretch)
        header.setResizeMode(1, QtGui.QHeaderView.ResizeToContents)
        vbox.addWidget(self.conflicts_list)

        hbox = QtGui.QHBoxLayout()
        self.program_edit = QtGui.QLineEdit(self)
        self.program_edit.setEnabled(False)
        self.connect(
            self.program_edit,
            QtCore.SIGNAL("textChanged(QString)"),
            self.check_merge_tool_edit)
        self.program_extmerge_default_button = QtGui.QCheckBox(gettext("Use Configured Default"))
        self.program_extmerge_default_button.setToolTip(gettext(
                "The merge tool configured in qconfig under Merge' file.\n"
                "It follows the convention used in the bzr plugin: extmerge\n"
                "external_merge = kdiff3 --output %r %b %t %o\n"
                "%r is output, %b is .BASE, %t is .THIS and %o is .OTHER file."))
        self.connect(
            self.program_extmerge_default_button,
            QtCore.SIGNAL("clicked()"),
            self.program_extmerge_default_clicked)
        self.program_launch_button = QtGui.QPushButton(gettext("&Launch..."), self)
        self.program_launch_button.setEnabled(False)
        self.connect(
            self.program_launch_button,
            QtCore.SIGNAL("clicked()"),
            self.launch_merge_tool)
        self.program_label = QtGui.QLabel(gettext("M&erge tool:"), self)
        self.program_label.setBuddy(self.program_edit)
        hbox.addWidget(self.program_label)
        hbox.addWidget(self.program_edit)
        hbox.addWidget(self.program_extmerge_default_button)
        hbox.addWidget(self.program_launch_button)
        vbox.addLayout(hbox)

        self.create_context_menu()

        buttonbox = self.create_button_box(BTN_CLOSE)
        refresh = StandardButton(BTN_REFRESH)
        buttonbox.addButton(refresh, QtGui.QDialogButtonBox.ActionRole)
        self.connect(refresh, QtCore.SIGNAL("clicked()"), self.refresh)

        autobutton = QtGui.QPushButton(gettext('Auto-resolve'),
            self.centralwidget)
        self.connect(autobutton, QtCore.SIGNAL("clicked(bool)"), self.auto_resolve)

        hbox = QtGui.QHBoxLayout()
        hbox.addWidget(autobutton)
        hbox.addWidget(buttonbox)
        vbox.addLayout(hbox)
        self.initialize_ui()        

    def initialize_ui(self):
        config = get_qbzr_config().get_option("merge_tool_extmerge")
        
        self.program_extmerge_default_button.setCheckState(QtCore.Qt.Unchecked)
        if merge_tool_extmerge in ("True", "1"):
            self.program_extmerge_default_button.setCheckState(QtCore.Qt.Checked)
        self.program_extmerge_default_clicked()
        enabled, error_msg = self.is_merge_tool_launchable()
        self.update_program_edit_text(enabled, error_msg)
        # if extmerge not configured then resort to using default
        if not enabled and self.program_extmerge_default_button.isChecked():
            bzr_config = GlobalConfig()
            extmerge_tool = bzr_config.get_user_option("external_merge")
            if not extmerge_tool:
                self.program_extmerge_default_button.setCheckState(QtCore.Qt.Unchecked)
                self.update_program_edit_text(False, "")

    def create_context_menu(self):
        self.context_menu = QtGui.QMenu(self.conflicts_list)
        self.merge_action = QtGui.QAction(gettext("&Merge conflict"),
                                     self.context_menu)
        self.connect(self.merge_action, QtCore.SIGNAL("triggered(bool)"),
                     self.launch_merge_tool)
        self.context_menu.addAction(self.merge_action)
        self.context_menu.setDefaultAction(self.merge_action)
        self.context_menu.addAction(gettext("Mark as &resolved"),
                                   self.mark_item_as_resolved)

    def show(self):
        QBzrWindow.show(self)
        QtCore.QTimer.singleShot(1, self.load)

    def refresh(self):
        QtCore.QTimer.singleShot(1, self.load)

    def load(self):
        self.wt = wt = WorkingTree.open_containing(self.wt_dir)[0]
        self.set_title([gettext("Conflicts"), wt.basedir])
        conflicts = self.wt.conflicts()
        items = []
        for conflict in conflicts:
            item = QtGui.QTreeWidgetItem()
            item.setText(0, conflict.path)
            item.setText(1, gettext(conflict.typestring))
            item.setData(0, QtCore.Qt.UserRole, QtCore.QVariant(conflict.file_id))
            item.setData(1, QtCore.Qt.UserRole, QtCore.QVariant(conflict.typestring))
            items.append(item)
        self.conflicts_list.clear()
        self.conflicts_list.addTopLevelItems(items)

    def auto_resolve(self):
        un_resolved, resolved = self.wt.auto_resolve()
        if len(un_resolved) > 0:
            n = len(resolved)
            QtGui.QMessageBox.information(self, gettext('Conflicts'),
                ngettext('%d conflict auto-resolved.',
                         '%d conflicts auto-resolved.',
                         n) % n,
                gettext('&OK'))
            QtCore.QTimer.singleShot(1, self.load)
        else:
            QtGui.QMessageBox.information(self, gettext('Conflicts'),
                gettext('All conflicts resolved.'),
                gettext('&OK'))
            self.close()

    def update_selection(self, selected, deselected):
        enabled, error_msg = self.is_merge_tool_launchable()
        self.program_edit.setEnabled(enabled and not self.program_extmerge_default_button.isChecked())
        self.program_launch_button.setEnabled(enabled)
        self.update_program_edit_text(enabled, error_msg)
        if enabled and self.program_extmerge_default_button.isChecked():
            self.program_edit.setEnabled(False)
        self.merge_action.setEnabled(enabled)

    def check_merge_tool_edit(self, text):
        enabled, error_msg = self.is_merge_tool_launchable()
        self.program_launch_button.setEnabled(enabled)

    def launch_merge_tool(self):
        items = self.conflicts_list.selectedItems()
        enabled, error_msg = self.is_merge_tool_launchable()
        if not enabled:
            return
        merge_tool = unicode(self.program_edit.text()).strip()
        if not merge_tool:
            return
        file_id = str(items[0].data(0, QtCore.Qt.UserRole).toString())
        file_name = self.wt.abspath(self.wt.id2path(file_id))
        base_file_name = file_name + ".BASE"
        this_file_name = file_name + ".THIS"
        other_file_name = file_name + ".OTHER"
        new_args = [base_file_name, this_file_name, other_file_name]
        config = get_qbzr_config()
        config.set_option("merge_tool_extmerge", False)

        if self.program_extmerge_default_button.isChecked():
            bzr_config = GlobalConfig()
            extmerge_tool = bzr_config.get_user_option("external_merge")
            args = cmdline_split(extmerge_tool)
            new_args = args[1:len(args)]
            i = 0
            while i < len(new_args):
                new_args[i] = new_args[i].replace('%r', file_name)
                new_args[i] = new_args[i].replace('%o', other_file_name)
                new_args[i] = new_args[i].replace('%b', base_file_name)
                new_args[i] = new_args[i].replace('%t', this_file_name)
                i = i + 1
            merge_tool = args[0]
            config.set_option("merge_tool_extmerge", True)
        else:
            config.set_option("merge_tool", merge_tool)

        process = QtCore.QProcess(self)
        self.connect(process, QtCore.SIGNAL("error(QProcess::ProcessError)"), self.show_merge_tool_error)
        process.start(merge_tool, new_args)

    def show_merge_tool_error(self, error):
        msg = gettext("Error while running merge tool (code %d)") % error
        QtGui.QMessageBox.critical(self, gettext("Error"), msg)

    def mark_item_as_resolved(self):
        items = self.conflicts_list.selectedItems()
        file_names = []
        for item in items:
            # XXX why we need to use file_id -> path conversion if we already have filename???
            # this conversion fails in the case when user removed file or directory
            # which marked as conflicted (e.g. in missing parent conflict case).
            #~file_id = str(item.data(0, QtCore.Qt.UserRole).toString())
            #~file_names.append(self.wt.id2path(file_id))
            file_names.append(unicode(item.text(0)))
        resolve(self.wt, file_names)
        self.refresh()

    def show_context_menu(self, pos):
        self.context_menu.popup(self.conflicts_list.viewport().mapToGlobal(pos))

    def program_extmerge_default_clicked(self):	
        enabled, error_msg = self.is_merge_tool_launchable()
        self.program_edit.setEnabled(enabled and not self.program_extmerge_default_button.isChecked())
        self.program_launch_button.setEnabled(enabled)
        self.update_program_edit_text(enabled, error_msg)
        config = get_qbzr_config()
        config.set_option("merge_tool_extmerge", 
                          self.program_extmerge_default_button.isChecked()) 

    def is_merge_tool_launchable(self):
        items = self.conflicts_list.selectedItems()
        error_msg = ""
        enabled = True
        if len(items) != 1 or items[0].data(1, QtCore.Qt.UserRole).toString() != "text conflict":
            enabled = False

        # check to see if the extmerge config is correct   
        if self.program_extmerge_default_button.isChecked():
            bzr_config = GlobalConfig()
            extmerge_tool = bzr_config.get_user_option("external_merge")
            if not extmerge_tool:
                error_msg = gettext("Set up external_merge app in qconfig under the Merge tab")
                enabled = False
                return enabled, error_msg
            error = self.is_extmerge_definition_valid(False)
            if len(error) > 0:
                enabled = False
                error_msg = error
        return enabled, error_msg

    def is_extmerge_definition_valid(self, showErrorDialog):
        bzr_config = GlobalConfig()
        extmerge_tool = bzr_config.get_user_option("external_merge")
        # Check if the definition format is correct
        flags = "%r"
        try:
            extmerge_tool.rindex('%r')
            flags = "%b"
            extmerge_tool.rindex('%b')
            flags = "%t"
            extmerge_tool.rindex('%t')
            flags = "%o"
            extmerge_tool.rindex('%o')
        except ValueError:
            if showErrorDialog:
                QtGui.QMessageBox.critical(self, gettext("Error"),
                    gettext("The extmerge definition: '%(tool)s' is invalid.\n"
                        "Missing the flag: %(flags)s. "
                        "This must be fixed in qconfig under the Merge tab.") % {
                        'tool': extmerge_tool,
                        'flags': flags,
                    })
            return gettext("Missing the flag: %s. Configure in qconfig under the merge tab.") % flags
        return ""

    def update_program_edit_text(self, enabled, error_msg):
        if self.program_extmerge_default_button.isChecked():
            if enabled or (len(error_msg) <= 0):
                config = GlobalConfig()
                extmerge = config.get_user_option("external_merge")
                self.program_edit.setText(gettext("%s (Configured external merge definition in qconfig)") % extmerge)
            else:
                self.program_edit.setText(error_msg)
        else:
            config = get_qbzr_config()
            self.program_edit.setText((config.get_user_option("merge_tool") or "").strip() or "meld")

if 0:
    N_("path conflict")
    N_("contents conflict")
    N_("text conflict")
    N_("duplicate id")
    N_("duplicate")
    N_("parent loop")
    N_("unversioned parent")
    N_("missing parent")
    N_("deleting parent")
    N_("non-directory parent")
