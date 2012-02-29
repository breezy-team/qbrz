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

import os
import re
from PyQt4 import QtCore, QtGui
from bzrlib.plugins.qbzr.lib.i18n import gettext
from bzrlib.plugins.qbzr.lib.subprocess import SubProcessDialog
from bzrlib.plugins.qbzr.lib.ui_new_tree import Ui_NewWorkingTreeForm
from bzrlib.plugins.qbzr.lib.util import (
    save_pull_location,
    fill_pull_combo,
    hookup_directory_picker,
    DIRECTORYPICKER_SOURCE,
    DIRECTORYPICKER_TARGET,
    get_qbzr_config,
    )


class GetNewWorkingTreeWindow(SubProcessDialog):

    NAME = "new_tree"

    def __init__(self, to_location, ui_mode=True, parent=None):
        config = get_qbzr_config()
        checkout_basedir = config.get_option("checkout_basedir")
        branchsource_basedir = config.get_option("branchsource_basedir")
        if not to_location:
            to_location = checkout_basedir or u'.'
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
        self.connect(self.ui.to_location, QtCore.SIGNAL("textChanged(const QString &)"),
                     self.to_location_changed)

        self.ui.but_checkout.setChecked(True)
        self.ui.but_rev_tip.setChecked(True)
        self.ui.to_location.setText(self.to_location)
        if branchsource_basedir is not None:
            self.from_location = branchsource_basedir
            self.ui.from_location.setEditText(self.from_location)

    def to_location_changed(self):
        self.disconnect(self.ui.from_location, QtCore.SIGNAL("editTextChanged(const QString &)"),
                     self.from_location_changed)
        self.disconnect(self.ui.to_location, QtCore.SIGNAL("textChanged(const QString &)"),
                     self.to_location_changed)

    def from_location_changed(self, new_text):
        new_val = self.to_location
        tail = re.split("[:$#\\\\/]", unicode(new_text))[-1]
        try:
            projectname = re.split("[:$#\\\\/]", unicode(new_text))[-2]
        except:
            projectname = ""
        if tail:
            if self.checkout_basedir is not None:
                new_val = os.path.join(self.checkout_basedir, projectname)
            else:
                new_val = os.path.join(new_val, tail)
        self.ui.to_location.setText(new_val)

    def _get_from_location(self):
        return unicode(self.ui.from_location.currentText())

    def _get_to_location(self):
        return unicode(self.ui.to_location.text())

    def _is_checkout_action(self):
        return self.ui.but_checkout.isChecked()

    def validate(self):
        if not self._get_from_location():
            self.operation_blocked(gettext("You should specify branch source"))
            return False
        to_location = self._get_to_location()
        if not to_location:
            self.operation_blocked(gettext("You should select destination directory"))
            return False
        # This is a check if the user really wants to checkout to a non-empty directory.
        # Because this may create conflicts, we want to make sure this is intended.
        if os.path.exists(to_location) and os.listdir(to_location):
            if self._is_checkout_action():
                quiz = gettext("Do you really want to checkout into a non-empty folder?")
            else:
                quiz = gettext("Do you really want to branch into a non-empty folder?")
            reason = gettext("The destination folder is not empty.\n"
                             "Populating new working tree there may create conflicts.")
            if not self.ask_confirmation(reason+'\n\n'+quiz, type='warning'):
                return False
        return True

    def do_start(self):
        from_location = self._get_from_location()
        to_location = self._get_to_location()
        revision_args = []
        if self.ui.but_rev_specific.isChecked() and self.ui.revision.text():
            revision_args.append('--revision='+unicode(self.ui.revision.text()))

        if self._is_checkout_action():
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

        self.process_widget.do_start(None, *args)
        save_pull_location(None, from_location)
