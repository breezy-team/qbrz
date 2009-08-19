# -*- coding: utf-8 -*-
#
# QBzr - Qt frontend to Bazaar commands
# Copyright (C) 2008 Lukáš Lalinský <lalinsky@gmail.com>
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

from bzrlib import bzrdir, osutils

from bzrlib.plugins.qbzr.lib.i18n import gettext
from bzrlib.plugins.qbzr.lib.ui_info import Ui_InfoForm
from bzrlib.plugins.qbzr.lib.util import (
    BTN_CLOSE,
    QBzrWindow,
    url_for_display,
    )
from bzrlib.plugins.qbzr.lib.uifactory import ui_current_widget


def _set_location(edit, location):
    location = location or u'-'
    location = url_for_display(location)
    edit.setText(location)


class QBzrInfoWindow(QBzrWindow):

    def __init__(self, location, parent=None):
        QBzrWindow.__init__(self, [gettext("Info")], parent)
        self.restoreSize("info", (500, 300))
        self.buttonbox = self.create_button_box(BTN_CLOSE)
        self.ui = Ui_InfoForm()
        self.ui.setupUi(self.centralwidget)
        self.ui.vboxlayout.addWidget(self.buttonbox)
        self.refresh_view(location)

    def refresh_view(self, location):
        (tree, branch, repository, relpath) = \
            bzrdir.BzrDir.open_containing_tree_branch_or_repository(location)
        path_to_display = osutils.abspath(location)
        _set_location(self.ui.local_location, path_to_display)
        self.populate_tree_info(tree)
        self.populate_branch_info(branch)
        self.populate_repository_info(repository)
        self.populate_bzrdir_info(repository.bzrdir)

    @ui_current_widget
    def populate_tree_info(self, tree):
        if tree:
            format = tree._format.get_format_description()
        else:
            format = gettext("Location has no working tree")
        self.ui.tree_format.setText(format)

    def populate_branch_info(self, branch):
        if branch:
            _set_location(self.ui.push_branch, branch.get_push_location())
            _set_location(self.ui.submit_branch, branch.get_submit_branch())
            _set_location(self.ui.parent_branch, branch.get_parent())
            _set_location(self.ui.public_branch_location, branch.get_public_branch())
            format = branch._format.get_format_description()
        else:
            # TODO: Hide Related branches tab
            na_value = gettext("Not applicable")
            _set_location(self.ui.push_branch, na_value)
            _set_location(self.ui.submit_branch, na_value)
            _set_location(self.ui.parent_branch, na_value)
            _set_location(self.ui.public_branch_location, na_value)
            format = gettext("Location has no branch")
        self.ui.branch_format.setText(format)

    def populate_repository_info(self, repo):
        format = repo._format.get_format_description()
        self.ui.repository_format.setText(format)

    def populate_bzrdir_info(self, control):
        format = control._format.get_format_description()
        self.ui.bzrdir_format.setText(format)
