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

try:
    from bzrlib import mergetools
except ImportError:
    mergetools = None


class ConflictsWindow(QBzrWindow):

    def __init__(self, wt_dir, parent=None):
        self.merge_action = None
        self.wt = None
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
            self.update_merge_tool_ui)
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
        self.merge_tools_combo = QtGui.QComboBox(self)
        self.merge_tools_combo.setEditable(False)
        self.connect(self.merge_tools_combo,
                     QtCore.SIGNAL("currentIndexChanged(int)"),
                     self.update_merge_tool_ui)
        
        self.merge_tool_error = QtGui.QLabel('', self)
        
        self.program_launch_button = QtGui.QPushButton(gettext("&Launch..."), self)
        self.program_launch_button.setEnabled(False)
        self.connect(
            self.program_launch_button,
            QtCore.SIGNAL("clicked()"),
            self.launch_merge_tool)
        self.program_label = QtGui.QLabel(gettext("M&erge tool:"), self)
        self.program_label.setBuddy(self.merge_tools_combo)
        hbox.addWidget(self.program_label)
        hbox.addWidget(self.merge_tools_combo)
        hbox.addWidget(self.merge_tool_error)
        hbox.addStretch(1)
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
        config = GlobalConfig()
        if mergetools is not None:
            # get user-defined merge tools
            defined_tools = config.get_merge_tools().keys()
            # get predefined merge tools
            defined_tools += mergetools.known_merge_tools.keys()
            # sort them nicely
            defined_tools.sort()
            for merge_tool in defined_tools:
                self.merge_tools_combo.insertItem(
                    self.merge_tools_combo.count(), merge_tool)
            default_tool = config.get_user_option('bzr.default_mergetool')
            if default_tool is not None:
                self.merge_tools_combo.setCurrentIndex(
                    self.merge_tools_combo.findText(default_tool))
        # update_merge_tool_ui invokes is_merge_tool_launchable, which displays
        # error message if mergetools module is not available.
        self.update_merge_tool_ui()

    def create_context_menu(self):
        self.context_menu = QtGui.QMenu(self.conflicts_list)
        self.merge_action = QtGui.QAction(gettext("&Merge conflict"),
                                     self.context_menu)
        self.connect(self.merge_action, QtCore.SIGNAL("triggered(bool)"),
                     self.launch_merge_tool)
        self.context_menu.addAction(self.merge_action)
        self.context_menu.setDefaultAction(self.merge_action)
        self.context_menu.addAction(gettext('Take "&THIS" version'),
                                   self.take_this)
        self.context_menu.addAction(gettext('Take "&OTHER" version'),
                                   self.take_other)
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
            item.setData(0, QtCore.Qt.UserRole, QtCore.QVariant(conflict.file_id or ''))  # file_id is None for non-versioned items, so we force it to be empty string to avoid Qt error
            item.setData(1, QtCore.Qt.UserRole, QtCore.QVariant(conflict.typestring))
            items.append(item)

        if len(items) == 0 and self.conflicts_list.topLevelItemCount() > 0:
            self.emit(QtCore.SIGNAL("allResolved(bool)"), True)
        self.conflicts_list.clear()
        self.conflicts_list.addTopLevelItems(items)

    def auto_resolve(self):
        while self.wt is None:
            QtGui.QApplication.processEvents()
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

    def update_merge_tool_ui(self):
        enabled, error_msg = self.is_merge_tool_launchable()
        self.merge_tool_error.setText(error_msg)
        self.program_launch_button.setEnabled(enabled)
        self.merge_action.setEnabled(enabled)

    def launch_merge_tool(self):
        items = self.conflicts_list.selectedItems()
        enabled, error_msg = self.is_merge_tool_launchable()
        if not enabled:
            return
        config = GlobalConfig()
        cmdline = config.find_merge_tool(unicode(self.merge_tools_combo.currentText()))
        file_id = str(items[0].data(0, QtCore.Qt.UserRole).toString())
        if not file_id:
            # bug https://bugs.launchpad.net/qbzr/+bug/655451
            return
        file_name = self.wt.abspath(self.wt.id2path(file_id))
        process = QtCore.QProcess(self)
        def qprocess_invoker(executable, args, cleanup):
            def qprocess_error(error):
                self.show_merge_tool_error(error)
                cleanup(process.exitCode())
            def qprocess_finished(exit_code, exit_status):
                cleanup(exit_code)
            self.connect(process, QtCore.SIGNAL("error(QProcess::ProcessError)"), qprocess_error)
            self.connect(process, QtCore.SIGNAL("finished(int,QProcess::ExitStatus)"), qprocess_finished)
            process.start(executable, args)
        mergetools.invoke(cmdline, file_name, qprocess_invoker)

    def show_merge_tool_error(self, error):
        msg = gettext("Error while running merge tool (code %d)") % error
        QtGui.QMessageBox.critical(self, gettext("Error"), msg)

    def take_this(self):
        self._resolve_action('take_this')

    def take_other(self):
        self._resolve_action('take_other')

    def mark_item_as_resolved(self):
        self._resolve_action('done')

    def _resolve_action(self, action):
        items = self.conflicts_list.selectedItems()
        file_names = []
        for item in items:
            # XXX why we need to use file_id -> path conversion if we already have filename???
            # this conversion fails in the case when user removed file or directory
            # which marked as conflicted (e.g. in missing parent conflict case).
            #~file_id = str(item.data(0, QtCore.Qt.UserRole).toString())
            #~file_names.append(self.wt.id2path(file_id))
            file_names.append(unicode(item.text(0)))
        resolve(self.wt, file_names, action=action)
        self.refresh()

    def show_context_menu(self, pos):
        self.context_menu.popup(self.conflicts_list.viewport().mapToGlobal(pos))

    def is_merge_tool_launchable(self):
        if mergetools is None:
            return False, gettext("Bazaar 2.4 or later is required for external mergetools support")
        items = self.conflicts_list.selectedItems()
        error_msg = ""
        enabled = True
        if len(items) != 1 or items[0].data(1, QtCore.Qt.UserRole).toString() != "text conflict":
            enabled = False
        config = GlobalConfig()
        tool = unicode(self.merge_tools_combo.currentText())
        cmdline = config.find_merge_tool(tool)
        if cmdline is None:
            error_msg = gettext("Set up external_merge app in qconfig under the Merge tab")
            enabled = False
        elif not mergetools.check_availability(cmdline):
            enabled = False
            error_msg = gettext("External merge tool %(tool)s is not available") % \
                    { 'tool': tool }
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
