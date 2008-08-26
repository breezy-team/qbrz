# -*- coding: utf-8 -*-
#
# QBzr - Qt frontend to Bazaar commands
# Copyright (C) 2007 Lukáš Lalinský <lalinsky@gmail.com>
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

import os.path
import re
import sys
from PyQt4 import QtCore, QtGui

from bzrlib.util import bencode
from bzrlib import (
    bugtracker,
    errors,
    osutils,
    urlutils,
    )
from bzrlib.errors import BzrError, NoSuchRevision
from bzrlib.option import Option
from bzrlib.commands import Command, register_command
from bzrlib.commit import ReportCommitToLog
from bzrlib.workingtree import WorkingTree

from bzrlib.plugins.qbzr.lib.i18n import gettext, N_
from bzrlib.plugins.qbzr.lib.subprocess import SubProcessWindow
from bzrlib.plugins.qbzr.lib.ui_branch import Ui_BranchForm
from bzrlib.plugins.qbzr.lib.ui_pull import Ui_PullForm
from bzrlib.plugins.qbzr.lib.ui_push import Ui_PushForm
from bzrlib.plugins.qbzr.lib.ui_merge import Ui_MergeForm
from bzrlib.plugins.qbzr.lib.util import (
    BTN_CANCEL,
    BTN_OK,
    QBzrWindow,
    StandardButton,
    iter_branch_related_locations,
    iter_saved_pull_locations,
    save_pull_location,
    fill_pull_combo,
    fill_combo_with,
    hookup_directory_picker,
    DIRECTORYPICKER_SOURCE,
    DIRECTORYPICKER_TARGET,
)


class QBzrPullWindow(SubProcessWindow):

    TITLE = N_("Pull")
    NAME = "pull"
    DEFAULT_SIZE = (500, 420)

    def __init__(self, branch, ui_mode=True, parent=None):
        self.branch = branch
        SubProcessWindow.__init__(self,
                                  self.TITLE,
                                  name = self.NAME,
                                  default_size = self.DEFAULT_SIZE,
                                  ui_mode = ui_mode,
                                  parent = parent)

    def create_ui(self, parent):
        ui_widget = QtGui.QWidget(parent)
        self.ui = Ui_PullForm()
        self.ui.setupUi(ui_widget)
        fill_pull_combo(self.ui.location, self.branch)
        # One directory picker for the pull location.
        hookup_directory_picker(self,
                                self.ui.location_picker,
                                self.ui.location,
                                DIRECTORYPICKER_SOURCE)
        return ui_widget

    def start(self):
        args = ['--directory', self.branch.base]
        if self.ui.overwrite.isChecked():
            args.append('--overwrite')
        if self.ui.remember.isChecked():
            args.append('--remember')
        revision = str(self.ui.revision.text())
        if revision:
            args.append('--revision')
            args.append(revision)
        location = str(self.ui.location.currentText())
        self.process_widget.start(None, 'pull', location, *args)
        save_pull_location(self.branch, location)


class QBzrPushWindow(QBzrPullWindow):

    TITLE = N_("Push")
    NAME = "push"
    DEFAULT_SIZE = (500, 420)

    def create_ui(self, parent):
        ui_widget = QtGui.QWidget(parent)
        self.ui = Ui_PushForm()
        self.ui.setupUi(ui_widget)

        df = urlutils.unescape_for_display(self.branch.get_push_location() or '', "utf-8")
        fill_combo_with(self.ui.location, df,
                        iter_branch_related_locations(self.branch))

        # One directory picker for the push location.
        hookup_directory_picker(self,
                                self.ui.location_picker,
                                self.ui.location,
                                DIRECTORYPICKER_TARGET)
        return ui_widget

    def start(self):
        args = ['--directory', self.branch.base]
        if self.ui.overwrite.isChecked():
            args.append('--overwrite')
        if self.ui.remember.isChecked():
            args.append('--remember')
        if self.ui.create_prefix.isChecked():
            args.append('--create-prefix')
        if self.ui.use_existing_dir.isChecked():
            args.append('--use-existing-dir')
        location = str(self.ui.location.currentText())
        self.process_widget.start(None, 'push', location, *args)


class QBzrBranchWindow(QBzrPullWindow):

    TITLE = N_("Branch")
    NAME = "branch"
    DEFAULT_SIZE = (500, 420)

    def create_ui(self, parent):
        ui_widget = QtGui.QWidget(parent)
        self.ui = Ui_BranchForm()
        self.ui.setupUi(ui_widget)

        fill_combo_with(self.ui.from_location,
                        u'',
                        iter_saved_pull_locations())

        # Our 2 directory pickers hook up to our combos.
        hookup_directory_picker(self,
                                self.ui.from_picker,
                                self.ui.from_location,
                                DIRECTORYPICKER_SOURCE)

        hookup_directory_picker(self,
                                self.ui.to_picker,
                                self.ui.to_location,
                                DIRECTORYPICKER_TARGET)

        return ui_widget
    
    def accept(self):
        args = []
        revision = str(self.ui.revision.text())
        if revision:
            args.append('--revision')
            args.append(revision)
        from_location = str(self.ui.from_location.currentText())
        to_location = str(self.ui.to_location.currentText())
        self.process_widget.start(None, 'branch', from_location, to_location, *args)


class QBzrMergeWindow(QBzrPullWindow):

    TITLE = N_("Merge")
    NAME = "pull"
    DEFAULT_SIZE = (500, 420)

    def create_ui(self, parent):
        ui_widget = QtGui.QWidget(parent)
        self.ui = Ui_MergeForm()
        self.ui.setupUi(ui_widget)
        fill_pull_combo(self.ui.location, self.branch)
            
        # One directory picker for the pull location.
        hookup_directory_picker(self,
                                self.ui.location_picker,
                                self.ui.location,
                                DIRECTORYPICKER_SOURCE)
        return ui_widget
    
    def accept(self):
        args = ['--directory', self.branch.base]
        if self.ui.remember.isChecked():
            args.append('--remember')
        location = str(self.ui.location.currentText())
        self.process_widget.start(None, 'merge', location, *args)
