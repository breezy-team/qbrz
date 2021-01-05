# -*- coding: utf-8 -*-
#
# QBzr - Qt frontend to Bazaar commands
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

from PyQt5 import QtCore, QtGui, QtWidgets

# Range of tab widths to display by default on the menu (if others are
# specified in either bazaar.conf or branch.conf they'll be added after
# a separator).
MIN_TAB_WIDTH = 1
MAX_TAB_WIDTH = 12

class TabWidthMenuSelector(QtWidgets.QMenu):
    """Menu to control tab width."""
    def __init__(self, initial_tab_width=None, label_text=None, onChanged=None, *args):
        """Create tab width menu.
        @param label_text: text for label.
        @param onChanged: callback to processing tab width change.
        """
        QtWidgets.QMenu.__init__(self, *args)
        self.onChanged = onChanged
        if onChanged is None:
            self.onChanged = lambda settabwidth: None

        self.setTitle(label_text)

        self.action_group = QtWidgets.QActionGroup(self)

        self.tabwidth_actions = {}
        for tabwidth in range(MIN_TAB_WIDTH, MAX_TAB_WIDTH+1):
            action = QtWidgets.QAction(str(tabwidth), self.action_group)
            action.setCheckable(True)
            action.setData(tabwidth)
            self.addAction(action)
            self.tabwidth_actions[tabwidth] = action

        self._tabwidth = None
        self._has_separator = False
        # RJLRJL changed triggered to _triggered
        self.triggered[QtWidgets.QAction].connect(self._triggered)

        if initial_tab_width is not None:
            self.setTabWidth(initial_tab_width)
            self._triggered(self.tabwidth_actions[initial_tab_width])

    def _triggered(self, action):
        tw = action.data()
        if tw != self._tabwidth:
            self._tabwidth = tw
            self.onChanged(tw)

    def setTabWidth(self, width):
        if width not in self.tabwidth_actions:
            action = QtWidgets.QAction(str(width), self.action_group)
            action.setCheckable(True)
            action.setData(width)
            # Find the next highest tab width currently in the menu
            for tw in sorted(self.tabwidth_actions.keys()):
                if tw > width:
                    self.insertAction(action, self.tabwidth_actions[tw])
                    break
            else:
                # Not found
                if not self._has_separator:
                    self.addSeparator()
                    self._has_separator = True
                self.addAction(action)

            self.tabwidth_actions[width] = action

        self.tabwidth_actions[width].setChecked(True)
