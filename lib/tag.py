# -*- coding: utf-8 -*-
#
# QBzr - Qt frontend to Bazaar commands
# Copyright (C) 2008 Lukáš Lalinský et al.
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

from PyQt4 import QtCore

from bzrlib.plugins.qbzr.lib.subprocess import SubProcessDialog
from bzrlib.plugins.qbzr.lib.ui_tag import Ui_TagForm
from bzrlib.plugins.qbzr.lib.util import url_for_display


class TagWindow(SubProcessDialog):

    # indices of actions in action combo box
    IX_CREATE = 0
    IX_MOVE = 1
    IX_DELETE = 2

    def __init__(self, branch, action=None, tag_name=None, revision=None,
        parent=None, ui_mode=False):

        super(TagWindow, self).__init__(name="tag", ui_mode=ui_mode,
            dialog=True, parent=parent)

        self.ui = Ui_TagForm()
        self.ui.setupUi(self)

        # and add the subprocess widgets.
        for w in self.make_default_layout_widgets():
            self.layout().addWidget(w)
        self.process_widget.hide_progress()

        self.set_branch(branch)

    def set_branch(self, branch):
        self.branch = branch
        self.tags = sorted(branch.tags.get_tag_dict().keys())
        # update ui
        self.ui.branch_location.setText(url_for_display(branch.base))
        self.ui.cb_tag.clear()
        self.ui.cb_tag.addItems(QtCore.QStringList(self.tags))
        self.ui.cb_tag.setEditable(
            self.IX_CREATE == self.ui.cb_action.currentIndex())
        self.ui.cb_tag.setEditText("")
