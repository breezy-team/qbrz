# -*- coding: utf-8 -*-
#
# QBzr - Qt frontend to Bazaar commands
# Copyright (C) 2008 Canonical
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

# This implements the 'qupdate-hybrid' command - a hybrid update command
# that examines the tree being updated and displays one of 2 dialogs
# depending on if the tree is bound (ie, a checkout) or not.

import sys
import os
from PyQt4 import QtCore, QtGui
from bzrlib.plugins.qbzr.lib.i18n import gettext, N_
from bzrlib.plugins.qbzr.lib.subprocess import SubProcessDialog
from bzrlib.plugins.qbzr.lib.ui_update_branch import Ui_UpdateBranchForm
from bzrlib.plugins.qbzr.lib.ui_update_checkout import Ui_UpdateCheckoutForm
from bzrlib.plugins.qbzr.lib.util import (
    iter_branch_related_locations,
    iter_saved_pull_locations,
    save_pull_location,
    fill_combo_with,
    fill_pull_combo,
    )
from bzrlib import errors, urlutils


class UpdateBranchWindow(SubProcessDialog):

    TITLE = N_("Update Branch")
    NAME = "update_branch"

    def __init__(self, branch, parent=None):
        self.branch = branch
        SubProcessDialog.__init__(self,
                                  self.TITLE,
                                  name = self.NAME,
                                  default_size = None,
                                  parent = parent)

    def create_ui(self, parent):
        ui_widget = QtGui.QGroupBox(parent)
        self.ui = Ui_UpdateBranchForm()
        self.ui.setupUi(ui_widget)
        # nuke existing items in the combo.
        while self.ui.location.count():
            self.ui.location.removeItem(0)

        fill_pull_combo(self.ui.location, branch)

        self.connect(self.ui.but_pull, QtCore.SIGNAL("toggled(bool)"),
                     self.pull_toggled)
                     
        # One directory picker for the pull location.
        self.hookup_directory_picker(self.ui.location_picker,
                                     self.ui.location,
                                     self.DIRECTORYPICKER_SOURCE)

        self.ui.but_pull.setChecked(not not self.branch.get_parent())

        return ui_widget

    def pull_toggled(self, bool):
        for w in [self.ui.location, self.ui.location_picker,
                  self.ui.but_pull_remember, self.ui.but_pull_overwrite,
                  ]:
            w.setEnabled(bool)
        # no widgets for 'update'!
        
    def start(self):
        if self.ui.but_pull.isChecked():
            # its a 'pull'
            args = ['--directory', self.branch.base]
            if self.ui.but_pull_overwrite.isChecked():
                args.append('--overwrite')
            if self.ui.but_pull_remember.isChecked():
                args.append('--remember')
            location = str(self.ui.location.currentText())
            if not location:
                return

            self.process_widget.start('pull', location, *args)
            save_pull_location(self.branch, location)
        else:
            # its an 'update'.
            self.process_widget.start('update', self.branch.base)


class UpdateCheckoutWindow(SubProcessDialog):

    TITLE = N_("Update Checkout")
    NAME = "update_checkout"

    def __init__(self, branch, parent=None):
        self.branch = branch
        SubProcessDialog.__init__(self,
                                  self.TITLE,
                                  name = self.NAME,
                                  default_size = None,
                                  parent = parent)

    def create_ui(self, parent):
        ui_widget = QtGui.QGroupBox(parent)
        self.ui = Ui_UpdateCheckoutForm()
        self.ui.setupUi(ui_widget)
        # nuke existing items in the combo.
        while self.ui.location.count():
            self.ui.location.removeItem(0)
        # We don't look at 'related' branches etc when doing a 'pull' from
        # a checkout - the default is empty, but saved locations are used.
        fill_combo_with(self.ui.location,
                        u'',
                        iter_saved_pull_locations())
        # and the directory picker for the pull location.
        self.hookup_directory_picker(self.ui.location_picker,
                                     self.ui.location,
                                     self.DIRECTORYPICKER_SOURCE)

        self.connect(self.ui.but_pull, QtCore.SIGNAL("toggled(bool)"),
                     self.pull_toggled)

        # Our 'label' object is ready to have the bound location specified.
        loc = urlutils.unescape_for_display(self.branch.get_bound_location(),
                                            'utf-8')
        self.ui.label.setText(unicode(self.ui.label.text()) % loc)
        self.ui.but_pull.setChecked(False)
        return ui_widget

    def pull_toggled(self, bool):
        for w in [self.ui.location, self.ui.location_picker,
                  self.ui.but_pull_overwrite]:
            w.setEnabled(bool)
        # no widgets for 'update'!
        
    def start(self):
        if self.ui.but_pull.isChecked():
            args = ['--directory', self.branch.base]
            if self.ui.but_pull_overwrite.isChecked():
                args.append('--overwrite')
            #if self.ui.but_pull_remember.isChecked():
            #    args.append('--remember')
            location = str(self.ui.location.currentText())
            if not location:
                return
            self.process_widget.start('pull', location, *args)
        else:
            # its an update.
            self.process_widget.start('update', self.branch.base)
