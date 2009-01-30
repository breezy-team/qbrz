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
from bzrlib import errors
from bzrlib.plugins.qbzr.lib.i18n import gettext, N_
from bzrlib.plugins.qbzr.lib.subprocess import SubProcessDialog
from bzrlib.plugins.qbzr.lib.ui_new_tree import Ui_NewWorkingTreeForm
from bzrlib.plugins.qbzr.lib.help import show_help
from bzrlib.plugins.qbzr.lib.util import (
    iter_saved_pull_locations,
    save_pull_location,
    fill_pull_combo,
    hookup_directory_picker,
    DIRECTORYPICKER_SOURCE,
    DIRECTORYPICKER_TARGET,
    )


class GetNewWorkingTreeWindow(SubProcessDialog):

    NAME = "new_tree"

    def __init__(self, to_location, ui_mode=True, parent=None):
        self.to_location = os.path.abspath(to_location)
        super(GetNewWorkingTreeWindow, self).__init__(
                                  name = self.NAME,
                                  ui_mode = ui_mode,
                                  parent = parent)

        self.ui = Ui_NewWorkingTreeForm()
        self.ui.setupUi(self)
        fill_pull_combo(self.ui.from_location, None)
        # and add the subprocess widgets.
        for w in self.make_default_layout_widgets():
            self.layout().addWidget(w)

        # Our 2 directory pickers hook up to our combos.
        hookup_directory_picker(self,
                                self.ui.from_picker,
                                self.ui.from_location,
                                DIRECTORYPICKER_SOURCE)

        hookup_directory_picker(self,
                                self.ui.to_picker,
                                self.ui.to_location,
                                DIRECTORYPICKER_TARGET)

        # signal to manage updating the 'location' on the fly.
        self.connect(self.ui.from_location, QtCore.SIGNAL("editTextChanged(const QString &)"),
                     self.from_location_changed)

        self.ui.but_checkout.setChecked(True)
        self.ui.but_rev_tip.setChecked(True)
        self.ui.to_location.setText(self.to_location)

    def from_location_changed(self, new_text):
        new_val = self.to_location
        tail = re.split("[:$#\\\\/]", unicode(new_text))[-1]
        if tail:
            new_val = os.path.join(new_val, tail)
        self.ui.to_location.setText(new_val)

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

        self.process_widget.start(None, *args)
        save_pull_location(None, from_location)
