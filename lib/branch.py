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

from PyQt4 import QtCore, QtGui

from bzrlib import errors, urlutils
from bzrlib.commands import get_cmd_object

from bzrlib.plugins.qbzr.lib.i18n import gettext
from bzrlib.plugins.qbzr.lib.subprocess import SubProcessDialog
from bzrlib.plugins.qbzr.lib.ui_branch import Ui_BranchForm
from bzrlib.plugins.qbzr.lib.util import (
    iter_saved_pull_locations,
    save_pull_location,
    fill_pull_combo,
    fill_combo_with,
    hookup_directory_picker,
    DIRECTORYPICKER_SOURCE,
    DIRECTORYPICKER_TARGET,
    url_for_display,
    )


class QBzrBranchWindow(SubProcessDialog):

    NAME = "branch"

    def __init__(self, from_location, to_location=None,
                 revision=None, ui_mode=True, parent=None):
        super(QBzrBranchWindow, self).__init__(name = self.NAME,
                                             ui_mode = ui_mode,
                                             parent = parent)

        self.ui = Ui_BranchForm()
        self.setupUi(self.ui)
        # and add the subprocess widgets.
        for w in self.make_default_layout_widgets():
            self.layout().addWidget(w)

        fill_combo_with(self.ui.from_location,
                        u'',
                        iter_saved_pull_locations())
        if from_location:
            self.ui.from_location.setEditText(from_location)
        if to_location:
            self.ui.to_location.setEditText(to_location)
        if revision:
            self.ui.revision.setText(revision)

        # Our 2 directory pickers hook up to our combos.
        hookup_directory_picker(self,
                                self.ui.from_picker,
                                self.ui.from_location,
                                DIRECTORYPICKER_SOURCE)

        hookup_directory_picker(self,
                                self.ui.to_picker,
                                self.ui.to_location,
                                DIRECTORYPICKER_TARGET)

        # Put the focus on the To location if From is already set
        if from_location:
            self.ui.to_location.setFocus()
        else:
            self.ui.from_location.setFocus()

    def do_start(self):
        args = []
        revision = str(self.ui.revision.text())
        if revision:
            args.append('--revision')
            args.append(revision)
        from_location = unicode(self.ui.from_location.currentText())
        to_location = unicode(self.ui.to_location.currentText())
        cmd_branch = get_cmd_object('branch')
        if 'use-existing-dir' in cmd_branch.options():
            # always use this options because it should be mostly harmless
            args.append('--use-existing-dir')
        self.process_widget.do_start(None, 'branch', from_location, to_location, *args)
        save_pull_location(None, from_location)
