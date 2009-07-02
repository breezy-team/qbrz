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

from bzrlib.commands import get_cmd_object

from bzrlib.plugins.qbzr.lib.subprocess import SubProcessDialog
from bzrlib.plugins.qbzr.lib.ui_branch import Ui_BranchForm
from bzrlib.plugins.qbzr.lib.ui_pull import Ui_PullForm
from bzrlib.plugins.qbzr.lib.ui_push import Ui_PushForm
from bzrlib.plugins.qbzr.lib.ui_merge import Ui_MergeForm
from bzrlib.plugins.qbzr.lib.util import (
    iter_branch_related_locations,
    iter_saved_pull_locations,
    save_pull_location,
    fill_pull_combo,
    fill_combo_with,
    hookup_directory_picker,
    DIRECTORYPICKER_SOURCE,
    DIRECTORYPICKER_TARGET,
    url_for_display,
    )


class QBzrPullWindow(SubProcessDialog):

    NAME = "pull"

    def __init__(self, branch, tree=None, location=None, revision=None, remember=None,
                 overwrite=None, ui_mode=True, parent=None):
        self.branch = branch
        self.tree = tree
        super(QBzrPullWindow, self).__init__(name = self.NAME,
                                             ui_mode = ui_mode,
                                             parent = parent)
        self.ui = Ui_PullForm()
        self.setupUi(self.ui)
        # add the subprocess widgets.
        for w in self.make_default_layout_widgets():
            self.layout().addWidget(w)

        fill_pull_combo(self.ui.location, self.branch)
        if location:
            self.ui.location.setEditText(location)
        else:
            self.ui.location.setFocus()

        if remember:
            self.ui.remember.setCheckState(QtCore.Qt.Checked)
        if overwrite:
            self.ui.overwrite.setCheckState(QtCore.Qt.Checked)
        if revision:
            self.ui.revision.setText(revision)

        # One directory picker for the pull location.
        hookup_directory_picker(self,
                                self.ui.location_picker,
                                self.ui.location,
                                DIRECTORYPICKER_SOURCE)

    def start(self):
        if self.tree:
            dest = self.tree.basedir
        else:
            dest = self.branch.base
        args = ['--directory', dest]
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


class QBzrPushWindow(SubProcessDialog):

    NAME = "push"

    def __init__(self, branch, location=None,
                 create_prefix=None, use_existing_dir=None,
                 remember=None, overwrite=None, ui_mode=True, parent=None):

        self.branch = branch
        super(QBzrPushWindow, self).__init__(name = self.NAME,
                                             ui_mode = ui_mode,
                                             parent = parent)

        self.ui = Ui_PushForm()
        self.setupUi(self.ui)
        # and add the subprocess widgets.
        for w in self.make_default_layout_widgets():
            self.layout().addWidget(w)

        df = url_for_display(self.branch.get_push_location() or '')
        fill_combo_with(self.ui.location, df,
                        iter_branch_related_locations(self.branch))
        if location:
            self.ui.location.setEditText(location)
        else:
            self.ui.location.setFocus()

        if remember:
            self.ui.remember.setCheckState(QtCore.Qt.Checked)
        if overwrite:
            self.ui.overwrite.setCheckState(QtCore.Qt.Checked)
        if create_prefix:
            self.ui.create_prefix.setCheckState(QtCore.Qt.Checked)
        if use_existing_dir:
            self.ui.use_existing_dir.setCheckState(QtCore.Qt.Checked)

        # One directory picker for the push location.
        hookup_directory_picker(self,
                                self.ui.location_picker,
                                self.ui.location,
                                DIRECTORYPICKER_TARGET)

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

    def start(self):
        args = []
        revision = str(self.ui.revision.text())
        if revision:
            args.append('--revision')
            args.append(revision)
        from_location = str(self.ui.from_location.currentText())
        to_location = str(self.ui.to_location.currentText())
        cmd_branch = get_cmd_object('branch')
        if 'use-existing-dir' in cmd_branch.options():
            # always use this options because it should be mostly harmless
            args.append('--use-existing-dir')
        self.process_widget.start(None, 'branch', from_location, to_location, *args)
        save_pull_location(None, from_location)


class QBzrMergeWindow(SubProcessDialog):

    NAME = "merge"

    def __init__(self, branch, tree=None, location=None, revision=None, remember=None,
                 ui_mode=True, parent=None):
        super(QBzrMergeWindow, self).__init__(name = self.NAME,
                                             ui_mode = ui_mode,
                                             parent = parent)
        self.branch = branch
        self.tree = tree
        self.ui = Ui_MergeForm()
        self.setupUi(self.ui)
        # and add the subprocess widgets.
        for w in self.make_default_layout_widgets():
            self.layout().addWidget(w)

        fill_pull_combo(self.ui.location, self.branch)
        if location:
            self.ui.location.setEditText(location)
        else:
            self.ui.location.setFocus()

        if remember:
            self.ui.remember.setCheckState(QtCore.Qt.Checked)
        if revision:
            self.ui.revision.setText(revision)
    
        # One directory picker for the pull location.
        hookup_directory_picker(self,
                                self.ui.location_picker,
                                self.ui.location,
                                DIRECTORYPICKER_SOURCE)

    def start(self):
        if self.tree:
            dest = self.tree.basedir
        else:
            dest = self.branch.base
        args = ['--directory', dest]
        if self.ui.remember.isChecked():
            args.append('--remember')
        rev = unicode(self.ui.revision.text()).strip()
        if rev:
            args.extend(['--revision', rev])
        location = unicode(self.ui.location.currentText())
        self.process_widget.start(None, 'merge', location, *args)
        save_pull_location(None, location)
