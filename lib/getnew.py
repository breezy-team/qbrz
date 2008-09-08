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
import re
from PyQt4 import QtCore, QtGui
from bzrlib.plugins.qbzr.lib.i18n import gettext, N_
from bzrlib.plugins.qbzr.lib.subprocess import SubProcessDialog
from bzrlib.plugins.qbzr.lib.ui_new_tree import Ui_NewWorkingTreeForm
from bzrlib.plugins.qbzr.lib.util import (
    iter_saved_pull_locations,
    save_pull_location,
    fill_pull_combo,
    )
from bzrlib import errors, urlutils


class GetNewWorkingTreeWindow(SubProcessDialog):

    TITLE = N_("Create a new Bazaar Working Tree")
    NAME = "new_tree"
    DEFAULT_SIZE = (100, 100)

    def __init__(self, to_location, parent=None):
        self.to_location = os.path.abspath(to_location)
        SubProcessDialog.__init__(self,
                                  self.TITLE,
                                  name = self.NAME,
                                  default_size = self.DEFAULT_SIZE,
                                  parent = parent)

    def create_ui(self, parent):
        ui_widget = QtGui.QWidget(parent)
        self.ui = Ui_NewWorkingTreeForm()
        self.ui.setupUi(ui_widget)
        fill_pull_combo(self.ui.from_location, None)

        # Our 2 directory pickers hook up to our combos.
        self.hookup_directory_picker(self.ui.from_picker,
                                     self.ui.from_location,
                                     self.DIRECTORYPICKER_SOURCE)

        self.hookup_directory_picker(self.ui.to_picker,
                                     self.ui.to_location,
                                     self.DIRECTORYPICKER_TARGET)

        # signal to manage updating the 'location' on the fly.
        self.connect(self.ui.from_location, QtCore.SIGNAL("editTextChanged(const QString &)"),
                     self.from_location_changed)

        self.connect(self.ui.but_checkout, QtCore.SIGNAL("toggled(bool)"),
                     self.checkout_toggled)
        self.connect(self.ui.but_rev_specific, QtCore.SIGNAL("toggled(bool)"),
                     self.rev_toggled)
        self.connect(self.ui.link_help, QtCore.SIGNAL("linkActivated(const QString &)"),
                     self.link_help_activated)

        self.ui.but_checkout.setChecked(True)
        self.ui.but_rev_tip.setChecked(True)
        self.ui.to_location.setText(self.to_location)
        return ui_widget

    def from_location_changed(self, new_text):
        new_val = self.to_location
        tail = re.split("[:$#\\\\/]", unicode(new_text))[-1]
        if tail:
            new_val = os.path.join(new_val, tail)
        self.ui.to_location.setText(new_val)

    def link_help_activated(self, target):
        # This point isn't quite correct, but its close enough and I can't
        # work out how to position it exactly where the mouse is.
        pt = self.pos()+self.ui.link_help.parentWidget().pos()+self.ui.link_help.pos()
        event = QtGui.QHelpEvent(QtCore.QEvent.ToolTip, QtCore.QPoint(), pt)
        QtGui.QApplication.sendEvent(self.ui.link_help, event)
        
    def checkout_toggled(self, bool):
        # The widgets for 'checkout'
        for w in [self.ui.but_lightweight]:
            w.setEnabled(bool)
        # The widgets for 'branch'
        for w in [self.ui.but_stacked]:
            w.setEnabled(not bool)

    def rev_toggled(self, bool):
        for w in [self.ui.revision]:
            w.setEnabled(bool)
        
    def start(self):
        from_location = unicode(self.ui.from_location.currentText())
        to_location = unicode(self.ui.to_location.text())
        if not from_location or not to_location:
            return
        revision_args = []
        if self.ui.but_rev_specific.isChecked() and self.ui.revision.text():
            revision_args.append('--revision='+unicode(self.ui.revision.text()))

        if self.ui.but_checkout.isChecked():
            args = ['checkout']
            if self.ui.but_lightweight.isChecked():
                args.append('--lightweight')
            args.extend(revision_args)
            args.append(from_location)
            args.append(to_location)
        else:
            # its a 'branch'
            args = ['branch']
            if self.ui.but_stacked.isChecked():
                args.append('--stacked')
            args.extend(revision_args)
            args.append(from_location)
            args.append(to_location)

        self.process_widget.start(*args)
        save_pull_location(None, from_location)
