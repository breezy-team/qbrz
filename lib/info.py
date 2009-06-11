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

    def __init__(self, tree, parent=None):
        QBzrWindow.__init__(self, [gettext("Info")], parent)
        self.restoreSize("info", (500, 300))
        self.buttonbox = self.create_button_box(BTN_CLOSE)
        self.ui = Ui_InfoForm()
        self.ui.setupUi(self.centralwidget)
        self.ui.vboxlayout.addWidget(self.buttonbox)
        self.populate_tree_info(tree)

    @ui_current_widget
    def populate_tree_info(self, tree):
        self.populate_branch_info(tree.branch)
        self.populate_bzrdir_info(tree.bzrdir)
        _set_location(self.ui.local_location, tree.bzrdir.root_transport.base)
        self.ui.tree_format.setText(tree._format.get_format_description())

    def populate_branch_info(self, branch):
        _set_location(self.ui.push_branch, branch.get_push_location())
        _set_location(self.ui.submit_branch, branch.get_submit_branch())
        _set_location(self.ui.parent_branch, branch.get_parent())
        _set_location(self.ui.public_branch_location, branch.get_public_branch())
        self.ui.branch_format.setText(branch._format.get_format_description())
        self.populate_repository_info(branch.repository)

    def populate_repository_info(self, repo):
        self.ui.repository_format.setText(repo._format.get_format_description())

    def populate_bzrdir_info(self, bzrdir):
        self.ui.bzrdir_format.setText(bzrdir._format.get_format_description())
