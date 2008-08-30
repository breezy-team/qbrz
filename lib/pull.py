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

from bzrlib.plugins.qbzr.lib.diff import DiffWindow
from bzrlib.plugins.qbzr.lib.i18n import gettext, N_
from bzrlib.plugins.qbzr.lib.subprocess import SubProcessDialog
from bzrlib.plugins.qbzr.lib.ui_branch import Ui_BranchForm
from bzrlib.plugins.qbzr.lib.ui_pull import Ui_PullForm
from bzrlib.plugins.qbzr.lib.ui_push import Ui_PushForm
from bzrlib.plugins.qbzr.lib.ui_merge import Ui_MergeForm
from bzrlib.plugins.qbzr.lib.util import (
    BTN_CANCEL,
    BTN_OK,
    QBzrWindow,
    StandardButton,
    )


class QBzrPullWindow(SubProcessDialog):

    TITLE = N_("Pull")
    NAME = "pull"
    PICKER_CAPTION = N_("Select Source Location")
    DEFAULT_SIZE = (500, 420)

    def __init__(self, branch, parent=None):
        self.branch = branch
        SubProcessDialog.__init__(self,
                                  self.TITLE,
                                  name = self.NAME,
                                  default_size = self.DEFAULT_SIZE,
                                  parent = parent)

    def get_stored_location(self, branch):
        return branch.get_parent()

    def add_related_locations(self, locations, branch):
        def add_location(location):
            if location and location not in locations:
                locations.append(location)
        add_location(branch.get_parent())
        add_location(branch.get_bound_location())
        add_location(branch.get_push_location())
        add_location(branch.get_submit_branch())

    def get_related_locations(self, branch):
        # Add the stored location, if it's not set make it empty
        locations = [self.get_stored_location(branch) or u'']
        # Add other related locations to the combo box
        self.add_related_locations(locations, branch)
        return locations

    def append_related_locations(self, combo_box ):
        locations = self.get_related_locations(self.branch)
        for location in locations:
            if location:
                location = urlutils.unescape_for_display(location, 'utf-8')
                combo_box.addItem(location)
    
    def location_picker_clicked(self):
        self._do_directory_picker(self.ui.location, gettext(self.PICKER_CAPTION))

    def _do_directory_picker(self, widget, caption):
        """Called by the clicked() signal for the various directory pickers"""
        dir = widget.currentText()
        if not os.path.isdir(dir):
            dir = ""
        dir = QtGui.QFileDialog.getExistingDirectory(self, caption, dir)
        if dir:
            widget.setEditText(dir)
    
    def create_ui(self, parent):
        ui_widget = QtGui.QGroupBox(parent)
        self.ui = Ui_PullForm()
        self.ui.setupUi(ui_widget)
        self.append_related_locations(self.ui.location)
        
        # One directory picker for the pull location.
        self.connect(self.ui.location_picker, QtCore.SIGNAL("clicked()"),
                     self.location_picker_clicked)
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
        self.process_widget.start('pull', location, *args)


class QBzrPushWindow(QBzrPullWindow):

    TITLE = N_("Push")
    NAME = "push"
    PICKER_CAPTION = N_("Select Target Location")
    DEFAULT_SIZE = (500, 420)

    def get_stored_location(self, branch):
        return branch.get_push_location()

    def create_ui(self, parent):
        ui_widget = QtGui.QGroupBox(parent)
        self.ui = Ui_PushForm()
        self.ui.setupUi(ui_widget)
        self.append_related_locations(self.ui.location)
        
        # One directory picker for the pull location.
        self.connect(self.ui.location_picker, QtCore.SIGNAL("clicked()"),
                     self.location_picker_clicked)
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
        self.process_widget.start('push', location, *args)

class QBzrBranchWindow(QBzrPullWindow):

    TITLE = N_("Branch")
    NAME = "branch"
    DEFAULT_SIZE = (500, 420)

    def create_ui(self, parent):
        ui_widget = QtGui.QGroupBox(parent)
        self.ui = Ui_BranchForm()
        self.ui.setupUi(ui_widget)
        #self.append_related_locations(self.ui.location)
        
        # Our 2 directory pickers hook up to our combos.
        self.connect(self.ui.from_picker, QtCore.SIGNAL("clicked()"),
                     self.from_picker_clicked)
        self.connect(self.ui.to_picker, QtCore.SIGNAL("clicked()"),
                     self.to_picker_clicked)
        return ui_widget
    
    def to_picker_clicked(self):
        self._do_directory_picker(self.ui.to_location,
                                  gettext("Select Target Location"))

    def from_picker_clicked(self):
        self._do_directory_picker(self.ui.from_location,
                                  gettext("Select Source Location"))

    def accept(self):
        args = []
        revision = str(self.ui.revision.text())
        if revision:
            args.append('--revision')
            args.append(revision)
        from_location = str(self.ui.from_location.currentText())
        to_location = str(self.ui.to_location.currentText())
        self.process_widget.start('branch', from_location, to_location, *args)


class QBzrMergeWindow(QBzrPullWindow):

    TITLE = N_("Merge")
    NAME = "pull"
    PICKER_CAPTION = N_("Select Source Location")
    DEFAULT_SIZE = (500, 420)

    def create_ui(self, parent):
        ui_widget = QtGui.QGroupBox(parent)
        self.ui = Ui_MergeForm()
        self.ui.setupUi(ui_widget)
        self.append_related_locations(self.ui.location)
        
        # One directory picker for the pull location.
        self.connect(self.ui.location_picker, QtCore.SIGNAL("clicked()"),
                     self.location_picker_clicked)
        return ui_widget
    
    def accept(self):
        args = ['--directory', self.branch.base]
        if self.ui.remember.isChecked():
            args.append('--remember')
        location = str(self.ui.location.currentText())
        self.process_widget.start('merge', location, *args)
