# -*- coding: utf-8 -*-
#
# QBzr - Qt frontend to Bazaar commands
# Copyright (C) 2012 QBzr Developers
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
from bzrlib.globbing import Globster
from bzrlib.plugins.qbzr.lib.i18n import gettext, N_, ngettext
from bzrlib.plugins.qbzr.lib.subprocess import SubProcessDialog
from bzrlib.plugins.qbzr.lib.util import file_extension

ACTION_NONE = 'none'
ACTION_BY_EXT = 'ext'
ACTION_BY_EXT_CASE_INSENSITIVE = 'ext,case-insensitive'
ACTION_BY_BASENAME = 'basename'
ACTION_BY_FULLNAME = 'fullname'

class IgnoreWindow(SubProcessDialog):

    def __init__(self, tree, ui_mode=False, parent=None):
        super(IgnoreWindow, self).__init__(
                                  gettext("Ignore"),
                                  name="ignore",
                                  default_size=(400,400),
                                  ui_mode=ui_mode,
                                  dialog=False,
                                  parent=parent,
                                  hide_progress=True,
                                  )

        self.wt = tree
        self.unknowns = {}

        groupbox = QtGui.QGroupBox(gettext("Unknown Files"), self)
        vbox = QtGui.QVBoxLayout(groupbox)

        self.unknowns_list = QtGui.QTreeWidget(groupbox)
        self.unknowns_list.setRootIsDecorated(False)
        self.unknowns_list.setUniformRowHeights(True)
        self.unknowns_list.setSelectionBehavior(QtGui.QAbstractItemView.SelectRows)
        self.unknowns_list.setHeaderLabels([
            gettext("File"),
            gettext("Extension"),
            gettext("Ignore as"),
            ])
        self.unknowns_list.setSortingEnabled(True)
        self.unknowns_list.sortByColumn(0, QtCore.Qt.AscendingOrder)
        self.connect(self.unknowns_list,
            QtCore.SIGNAL("itemClicked(QTreeWidgetItem*, int)"),
            self.item_clicked)

        self.no_action = QtGui.QRadioButton(gettext('No action'), groupbox)
        self.no_action.setChecked(True)
        self.connect(self.no_action, QtCore.SIGNAL('clicked(bool)'), self.select_no_action)
        self.by_extension = QtGui.QRadioButton(gettext('Ignore all files with this extension'), groupbox)
        self.connect(self.by_extension, QtCore.SIGNAL('clicked(bool)'), self.select_by_extension)
        hbox = QtGui.QHBoxLayout()
        hbox.insertSpacing(0, 20)
        self.case_insensitive = QtGui.QCheckBox(gettext('Case-insensitive pattern'), groupbox)
        self.connect(self.case_insensitive, QtCore.SIGNAL('clicked(bool)'), self.select_case_insensitive)
        hbox.addWidget(self.case_insensitive)
        self.by_basename = QtGui.QRadioButton(gettext('Ignore by basename'), groupbox)
        self.connect(self.by_basename, QtCore.SIGNAL('clicked(bool)'), self.select_by_basename)
        self.by_fullname = QtGui.QRadioButton(gettext('Ignore by fullname'), groupbox)
        self.connect(self.by_fullname, QtCore.SIGNAL('clicked(bool)'), self.select_by_fullname)
        self._disable_actions()

        vbox.addWidget(self.unknowns_list)
        vbox.addWidget(self.no_action)
        vbox.addWidget(self.by_extension)
        vbox.addLayout(hbox)
        vbox.addWidget(self.by_basename)
        vbox.addWidget(self.by_fullname)

        layout = QtGui.QVBoxLayout(self)
        layout.addWidget(groupbox)
        layout.addWidget(self.make_default_status_box())
        layout.addWidget(self.buttonbox)

    def _disable_actions(self):
        self._set_disabled_for_actions(True)

    def _enable_actions(self):
        self._set_disabled_for_actions(False)

    def _set_disabled_for_actions(self, flag):
        self.no_action.setDisabled(flag)
        self.by_extension.setDisabled(flag)
        self.case_insensitive.setDisabled(flag)
        self.by_basename.setDisabled(flag)
        self.by_fullname.setDisabled(flag)

    def show(self):
        SubProcessDialog.show(self)
        QtCore.QTimer.singleShot(1, self.load)

    def load(self):
        self.set_title([gettext("Ignore"), self.wt.basedir])
        items = []
        for i in self.wt.unknowns():
            item = QtGui.QTreeWidgetItem()
            item.setText(0, i)
            item.setText(1, file_extension(i))
            item.setData(0, QtCore.Qt.UserRole, QtCore.QVariant(i))
            item.setData(2, QtCore.Qt.UserRole, QtCore.QVariant(ACTION_NONE))
            items.append(item)
            self.unknowns[i] = item
        self.unknowns_list.clear()
        self.unknowns_list.addTopLevelItems(items)

    def _filename_from_item(self, item):
        return unicode(item.data(0, QtCore.Qt.UserRole).toString())

    def _action_from_item(self, item):
        return str(item.data(2, QtCore.Qt.UserRole).toString())

    def item_clicked(self, item, column):
        self._enable_actions()
        action = self._action_from_item(item)
        self._widgets_for_action(action)

    def _widgets_for_action(self, action):
        self.case_insensitive.setChecked(False)
        if action == ACTION_NONE:
            self.no_action.setChecked(True)
        elif action == ACTION_BY_EXT:
            self.by_extension.setChecked(True)
        elif action == ACTION_BY_EXT_CASE_INSENSITIVE:
            self.by_extension.setChecked(True)
            self.case_insensitive.setChecked(True)
        elif action == ACTION_BY_BASENAME:
            self.by_basename.setChecked(True)
        elif action == ACTION_BY_FULLNAME:
            self.by_fullname.setChecked(True)

    def select_no_action(self, checked):
        self.case_insensitive.setChecked(False)
        self.change_action(ACTION_NONE)

    def select_by_extension(self, checked):
        self.change_action(ACTION_BY_EXT)

    def select_case_insensitive(self, checked):
        if checked:
            self.by_extension.setChecked(True)
            self.change_action(ACTION_BY_EXT_CASE_INSENSITIVE)
        else:
            self.change_action(ACTION_BY_EXT)

    def select_by_basename(self, checked):
        self.case_insensitive.setChecked(False)
        self.change_action(ACTION_BY_BASENAME)

    def select_by_fullname(self, checked):
        self.case_insensitive.setChecked(False)
        self.change_action(ACTION_BY_FULLNAME)

    def change_action(self, new_action):
        item = self.unknowns_list.currentItem()
        old_action = self._action_from_item(item)
        if old_action == new_action:
            return
        filename = self._filename_from_item(item)
        if old_action != ACTION_NONE:
            old_pattern = self._pattern_for_action(filename, old_action)
            self._update_items(old_pattern, ACTION_NONE, self._clear_action_for_item)
        if new_action != ACTION_NONE:
            new_pattern = self._pattern_for_action(filename, new_action)
            self._update_items(new_pattern, new_action, self._set_pattern_action_for_item)

    def _update_items(self, pattern, action, method):
        globster = Globster([pattern])
        for filename, item in self.unknowns.iteritems():
            if globster.match(filename) is not None:
                method(item, pattern, action)

    def _clear_action_for_item(self, item, pattern, action):
        item.setText(2, '')
        item.setData(2, QtCore.Qt.UserRole, QtCore.QVariant(action))

    def _set_pattern_action_for_item(self, item, pattern, action):
        item.setText(2, pattern)
        item.setData(2, QtCore.Qt.UserRole, QtCore.QVariant(action))

# ignore pattern for *.foo case-insensitive RE:(?i).*\.foo
# ignore pattern for files without extension (.first dot allowed though) RE:\.?[^.]+

    def _pattern_for_action(self, filename, action):
        if action == ACTION_NONE:
            return ''
        elif action == ACTION_BY_EXT:
            ext = file_extension(filename)
            if ext:
                return '*'+ext
            else:
                return 'RE:\\.?[^.]+'
        elif action == ACTION_BY_EXT_CASE_INSENSITIVE:
            ext = file_extension(filename)
            if ext:
                return 'RE:(?i).*\\'+ext.lower()
            else:
                return 'RE:\\.?[^.]+'
        elif action == ACTION_BY_BASENAME:
            return os.path.basename(filename)
        elif action == ACTION_BY_FULLNAME:
            return './'+filename

    def validate(self):
        patterns = self._collect_patterns()
        if not patterns:
            self.operation_blocked(gettext("No action selected"))
            return False
        self.args = ['ignore'] + patterns
        self.process_widget.force_passing_args_via_file = True
        return True

    def _collect_patterns(self):
        patterns = set()
        for filename, item in self.unknowns.iteritems():
            action = self._action_from_item(item)
            if action != ACTION_NONE:
                pattern = self._pattern_for_action(filename, action)
                patterns.add(pattern)
        return sorted(list(patterns))
