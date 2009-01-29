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

import sys
from PyQt4 import QtCore, QtGui
from bzrlib import (
    osutils,
    errors,
    )
from bzrlib.conflicts import resolve
from bzrlib.workingtree import WorkingTree
from bzrlib.plugins.qbzr.lib.i18n import gettext, N_
from bzrlib.plugins.qbzr.lib.util import (
    BTN_CLOSE, BTN_REFRESH,
    QBzrWindow,
    QBzrGlobalConfig,
    StandardButton,
    extract_name,
    format_timestamp,
    get_set_encoding,
    url_for_display,
    )


class ConflictsWindow(QBzrWindow):

    def __init__(self, wt_dir, parent=None):
        self.wt_dir = wt_dir
        QBzrWindow.__init__(self,
            [gettext("Conflicts")], parent)
        self.restoreSize("conflicts", (550, 380))

        vbox = QtGui.QVBoxLayout(self.centralwidget)

        self.conflicts_list = QtGui.QTreeWidget(self)
        self.conflicts_list.setRootIsDecorated(False)
        self.conflicts_list.setUniformRowHeights(True)
        self.conflicts_list.setSelectionBehavior(QtGui.QAbstractItemView.SelectRows)
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
        self.conflicts_list.setContextMenuPolicy(QtCore.Qt.CustomContextMenu)
        header = self.conflicts_list.header()
        header.setStretchLastSection(False)
        header.setResizeMode(0, QtGui.QHeaderView.Stretch)
        header.setResizeMode(1, QtGui.QHeaderView.Interactive)
        vbox.addWidget(self.conflicts_list)

        hbox = QtGui.QHBoxLayout()
        self.program_edit = QtGui.QLineEdit(self)
        self.program_edit.setEnabled(False)
        config = QBzrGlobalConfig()
        self.program_edit.setText((config.get_user_option("merge_tool") or "").strip() or "meld")
        self.connect(
            self.program_edit,
            QtCore.SIGNAL("textChanged(QString)"),
            self.check_merge_tool_edit)
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
        hbox.addWidget(self.program_launch_button)
        vbox.addLayout(hbox)

        self.context_menu = QtGui.QMenu(self.conflicts_list)
        self.context_menu.addAction(gettext("Mark as resolved"), self.mark_item_as_resolved)

        buttonbox = self.create_button_box(BTN_CLOSE)
        refresh = StandardButton(BTN_REFRESH)
        buttonbox.addButton(refresh, QtGui.QDialogButtonBox.ActionRole)
        self.connect(refresh, QtCore.SIGNAL("clicked()"), self.refresh)

        vbox.addWidget(buttonbox)

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

    def update_selection(self, selected, deselected):
        items = self.conflicts_list.selectedItems()
        enabled = True
        if len(items) != 1 or items[0].data(1, QtCore.Qt.UserRole).toString() != "text conflict":
            enabled = False
        self.program_edit.setEnabled(enabled)
        if enabled:
            self.check_merge_tool_edit(self.program_edit.text())
        else:
            self.program_launch_button.setEnabled(enabled)

    def check_merge_tool_edit(self, text):
        self.program_launch_button.setEnabled(not text.isEmpty())

    def launch_merge_tool(self):
        items = self.conflicts_list.selectedItems()
        if len(items) != 1 or items[0].data(1, QtCore.Qt.UserRole).toString() != "text conflict":
            return
        merge_tool = unicode(self.program_edit.text()).strip()
        if not merge_tool:
            return
        file_id = str(items[0].data(0, QtCore.Qt.UserRole).toString())
        file_name = self.wt.abspath(self.wt.id2path(file_id))
        base_file_name = file_name + ".BASE"
        this_file_name = file_name + ".THIS"
        other_file_name = file_name + ".OTHER"
        config = QBzrGlobalConfig()
        config.set_user_option("merge_tool", merge_tool)
        process = QtCore.QProcess(self)
        self.connect(process, QtCore.SIGNAL("error(QProcess::ProcessError)"), self.show_merge_tool_error)
        process.start(merge_tool, [base_file_name, this_file_name, other_file_name])

    def show_merge_tool_error(self, error):
        msg = gettext("Error while running merge tool (code %d)") % error
        QtGui.QMessageBox.critical(self, gettext("Error"), msg)

    def mark_item_as_resolved(self):
        items = self.conflicts_list.selectedItems()
        file_names = []
        for item in items:
            file_id = str(item.data(0, QtCore.Qt.UserRole).toString())
            file_names.append(self.wt.id2path(file_id))
        resolve(self.wt, file_names)
        self.refresh()

    def show_context_menu(self, pos):
        self.context_menu.popup(self.conflicts_list.viewport().mapToGlobal(pos))


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
