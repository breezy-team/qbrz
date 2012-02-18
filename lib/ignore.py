# -*- coding: utf-8 -*-
#
# QBzr - Qt frontend to Bazaar commands
# Copyright (C) 2012 QBzr Developers
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
from bzrlib.plugins.qbzr.lib.i18n import gettext, N_, ngettext
from bzrlib.plugins.qbzr.lib.subprocess import SubProcessDialog


class IgnoreWindow(SubProcessDialog):

    def __init__(self, directory=None, ui_mode=False, parent=None):
        super(IgnoreWindow, self).__init__(
                                  gettext("Ignore"),
                                  name="ignore",
                                  default_size=(400,400),
                                  ui_mode=ui_mode,
                                  dialog=False,
                                  parent=parent,
                                  hide_progress=True,
                                  )

        groupbox = QtGui.QGroupBox(gettext("Unknown Files"), self)
        vbox = QtGui.QVBoxLayout(groupbox)

        self.unknowns_list = QtGui.QTreeWidget(groupbox)
        self.unknowns_list.setRootIsDecorated(False)
        self.unknowns_list.setUniformRowHeights(True)
        self.unknowns_list.setSelectionBehavior(QtGui.QAbstractItemView.SelectRows)
        self.unknowns_list.setHeaderLabels([
            gettext("File"),
            gettext("Extension"),
            gettext("Ignore as"),
            ])
        self.unknowns_list.setSortingEnabled(True)
        self.unknowns_list.sortByColumn(0, QtCore.Qt.AscendingOrder)

        vbox.addWidget(self.unknowns_list)

        layout = QtGui.QVBoxLayout(self)
        layout.addWidget(groupbox)
        layout.addWidget(self.make_default_status_box())
        layout.addWidget(self.buttonbox)
