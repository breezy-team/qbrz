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

import os

from PyQt4 import QtCore

from bzrlib import osutils
from bzrlib.commands import get_cmd_object

from bzrlib.plugins.qbzr.lib.subprocess import SubProcessDialog
from bzrlib.plugins.qbzr.lib.ui_branch import Ui_BranchForm
from bzrlib.plugins.qbzr.lib.util import (
    iter_saved_pull_locations,
    save_pull_location,
    fill_combo_with,
    hookup_directory_picker,
    DIRECTORYPICKER_SOURCE,
    DIRECTORYPICKER_TARGET,
    )


class QBzrBranchWindow(SubProcessDialog):

    NAME = "branch"

    def __init__(self, from_location, to_location=None, revision=None,
            bind=False, parent_dir=None, ui_mode=True, parent=None):
        super(QBzrBranchWindow, self).__init__(name = self.NAME,
                                             ui_mode = ui_mode,
                                             parent = parent)

        # Unless instructed otherwise, use the current directory as
        # the parent directory.
        if parent_dir is None:
            parent_dir = os.getcwdu()
        self.parent_dir = parent_dir

        # Layout the form, adding the subprocess widgets
        self.ui = Ui_BranchForm()
        self.setupUi(self.ui)
        self.cmd_branch_options = get_cmd_object('branch').options()
        if 'bind' not in self.cmd_branch_options:
            self.ui.bind.setVisible(False)
        for w in self.make_default_layout_widgets():
            self.layout().addWidget(w)

        # Setup smart setting of fields as others are edited.
        QtCore.QObject.connect(self.ui.from_location,
            QtCore.SIGNAL("editTextChanged(const QString&)"),
            self.from_changed)

        # Initialise the fields
        fill_combo_with(self.ui.from_location,
                        u'',
                        iter_saved_pull_locations())
        if from_location:
            self.ui.from_location.setEditText(from_location)
        if to_location:
            self.ui.to_location.setEditText(to_location)
        if bind:
            self.ui.bind.setChecked(True)
        if revision:
            self.ui.revision.setText(revision)

        # Hook up our directory pickers
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

    def from_changed(self, from_location):
        to_location = self._default_to_location(unicode(from_location))
        if to_location is not None:
            self.ui.to_location.setEditText(to_location)

    def _default_to_location(self, from_location):
        """Work out a good To location give a From location.

        :return: the To location or None if unsure
        """
        # We want to avoid opening the from location here so
        # we 'guess' the basename using some simple heuristics
        from_location = from_location.replace('\\', '/').rstrip('/')
        if from_location.find('/') >= 0:
            basename = osutils.basename(from_location)
        else:
            # Handle 'directory services' like lp:
            ds_sep = from_location.find(':')
            if ds_sep >= 0:
                basename = from_location[ds_sep + 1:]
            else:
                return None

        # Calculate the To location and check it's not the same as the
        # From location.
        to_location = osutils.pathjoin(self.parent_dir, basename)
        if to_location == from_location:
            return None
        else:
            return to_location

    def get_to_location(self):
        """The path the branch was created in."""
        # This is used by explorer to find the location to open on completion
        return unicode(self.ui.to_location.currentText())

    def do_start(self):
        args = []
        if self.ui.bind.isChecked():
            args.append('--bind')
        revision = str(self.ui.revision.text())
        if revision:
            args.append('--revision')
            args.append(revision)
        from_location = unicode(self.ui.from_location.currentText())
        to_location = self.get_to_location()
        if 'use-existing-dir' in self.cmd_branch_options:
            # always use this options because it should be mostly harmless
            args.append('--use-existing-dir')
        self.process_widget.do_start(None, 'branch', from_location, to_location, *args)
        save_pull_location(None, from_location)
