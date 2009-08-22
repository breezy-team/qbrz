# -*- coding: utf-8 -*-
#
# QBzr - Qt frontend to Bazaar commands
#
# Contributor:
#   Alexander Belchenko, 2009
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

"""Dialog to run arbitrary bzr command."""

from PyQt4 import QtCore, QtGui

from bzrlib import osutils

from bzrlib.plugins.qbzr.lib.i18n import gettext
from bzrlib.plugins.qbzr.lib.subprocess import SubProcessDialog
from bzrlib.plugins.qbzr.lib.ui_run import Ui_RunDialog


class QBzrRunDialog(SubProcessDialog):

    def __init__(self, location=None, ui_mode=False, parent=None):
        super(QBzrRunDialog, self).__init__(name="run", ui_mode=ui_mode,
            dialog=True, parent=parent)
        self.ui = Ui_RunDialog()
        self.ui.setupUi(self)
        if location is None:
            location = osutils.getcwd()
        self.ui.wd_edit.setText(location)
        # fill cmd_combobox with available commands
        # XXX
        # set help_browser with some default text
        # XXX
        # and add the subprocess widgets
        vbox = QtGui.QVBoxLayout(self)
        for w in self.make_default_layout_widgets():
            self.ui.splitter.addWidget(w)
        self.process_widget.hide_progress()
        self.ui.cmd_combobox.setFocus()
