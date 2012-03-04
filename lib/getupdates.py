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

from bzrlib.plugins.qbzr.lib.i18n import gettext
from bzrlib.plugins.qbzr.lib.subprocess import SubProcessDialog
from bzrlib.plugins.qbzr.lib.ui_update_branch import Ui_UpdateBranchForm
from bzrlib.plugins.qbzr.lib.ui_update_checkout import Ui_UpdateCheckoutForm
from bzrlib.plugins.qbzr.lib.util import (
    iter_saved_pull_locations,
    save_pull_location,
    fill_combo_with,
    fill_pull_combo,
    hookup_directory_picker,
    DIRECTORYPICKER_SOURCE,
    url_for_display,
    )


class UpdateBranchWindow(SubProcessDialog):

    NAME = "update_branch"

    def __init__(self, branch, ui_mode=True, parent=None):
        self.branch = branch
        super(UpdateBranchWindow, self).__init__(
                                  name = self.NAME,
                                  ui_mode = ui_mode,
                                  parent = parent)

        self.ui = Ui_UpdateBranchForm()
        self.ui.setupUi(self)
        # and add the subprocess widgets.
        for w in self.make_default_layout_widgets():
            self.layout().addWidget(w)
        # nuke existing items in the combo.
        while self.ui.location.count():
            self.ui.location.removeItem(0)

        fill_pull_combo(self.ui.location, self.branch)

        # One directory picker for the pull location.
        hookup_directory_picker(self,
                                self.ui.location_picker,
                                self.ui.location,
                                DIRECTORYPICKER_SOURCE)

        self.ui.but_pull.setChecked(not not self.branch.get_parent())

    def _is_pull_selected(self):
        return self.ui.but_pull.isChecked()

    def _get_pull_location(self):
        return unicode(self.ui.location.currentText())

    def validate(self):
        if self._is_pull_selected() and not self._get_pull_location():
            self.operation_blocked(gettext("You should specify source branch location"))
            return False
        return True

    def do_start(self):
        if self._is_pull_selected():
            # its a 'pull'
            args = ['--directory', self.branch.base]
            if self.ui.but_pull_overwrite.isChecked():
                args.append('--overwrite')
            if self.ui.but_pull_remember.isChecked():
                args.append('--remember')
            location = self._get_pull_location()
            self.process_widget.do_start(None, 'pull', location, *args)
            save_pull_location(self.branch, location)
        else:
            # its an 'update'.
            self.process_widget.do_start(None, 'update', self.branch.base)


class UpdateCheckoutWindow(SubProcessDialog):

    NAME = "update_checkout"

    def __init__(self, branch, ui_mode=True, parent=None):
        self.branch = branch
        super(UpdateCheckoutWindow, self).__init__(
                                  name = self.NAME,
                                  ui_mode = ui_mode,
                                  parent = parent)

        self.ui = Ui_UpdateCheckoutForm()
        self.ui.setupUi(self)
        # and add the subprocess widgets.
        for w in self.make_default_layout_widgets():
            self.layout().addWidget(w)
        # nuke existing items in the combo.
        while self.ui.location.count():
            self.ui.location.removeItem(0)
        # We don't look at 'related' branches etc when doing a 'pull' from
        # a checkout - the default is empty, but saved locations are used.
        fill_combo_with(self.ui.location,
                        u'',
                        iter_saved_pull_locations())
        # and the directory picker for the pull location.
        hookup_directory_picker(self,
                                self.ui.location_picker,
                                self.ui.location,
                                DIRECTORYPICKER_SOURCE)

        # Our 'label' object is ready to have the bound location specified.
        loc = url_for_display(self.branch.get_bound_location())
        self.ui.label.setText(unicode(self.ui.label.text()) % loc)
        self.ui.but_pull.setChecked(False)

    def _is_pull_selected(self):
        return self.ui.but_pull.isChecked()

    def _get_pull_location(self):
        return unicode(self.ui.location.currentText())

    def validate(self):
        if self._is_pull_selected() and not self._get_pull_location():
            self.operation_blocked(gettext("You should specify source branch location"))
            return False
        return True

    def do_start(self):
        if self._is_pull_selected():
            args = ['--directory', self.branch.base]
            if self.ui.but_pull_overwrite.isChecked():
                args.append('--overwrite')
            location = self._get_pull_location()
            self.process_widget.do_start(None, 'pull', location, *args)
        else:
            # its an update.
            self.process_widget.do_start(None, 'update', self.branch.base)
