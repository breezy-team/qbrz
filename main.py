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

import os.path
import re
import sys
from PyQt4 import QtCore, QtGui


from bzrlib import (
    bugtracker,
    errors,
    osutils,
    urlutils,
    )
import bzrlib
from bzrlib.plugins import qbzr
from bzrlib.plugins.qbzr.i18n import gettext, N_
from bzrlib.plugins.qbzr.util import (
    QBzrWindow,
    open_browser,
    )

class QBzrMainWindow(QBzrWindow):

    def __init__(self, parent=None):
        QBzrWindow.__init__(self, [], parent)
        self.restoreSize("main", (800, 600))
        # FIXME: this maybe needs a special version for OS X
        self.createMenuBar()

    def createMenuBar(self):
        mainMenu = self.menuBar()
        fileMenu = mainMenu.addMenu(gettext("&File"))
        fileMenu.addSeparator()
        fileMenu.addAction(gettext("&Quit"), self.close, "Ctrl+Q")
        helpMenu = mainMenu.addMenu(gettext("&Help"))
        helpMenu.addAction(gettext("&Help..."), self.showHelp, "F1")
        helpMenu.addSeparator()
        helpMenu.addAction(gettext("&About..."), self.showAboutDialog)

    def showHelp(self):
        open_browser("http://bazaar-vcs.org/QBzr/Documentation")

    def showAboutDialog(self):
        tpl = {
            'qbzr_version': qbzr.__version__,
            'bzrlib_version': bzrlib.__version__,
        }
        QtGui.QMessageBox.about(self,
            gettext("About QBzr"),
            gettext(u"<b>QBzr</b> \u2014 A graphical user interface for Bazaar<br>"
                    u"<small>Version %(qbzr_version)s (bzrlib %(bzrlib_version)s)</small><br>"
                    u"<br>"
                    u"Copyright \u00A9 2006-2007 Luk\xe1\u0161 Lalinsk\xfd and others<br>"
                    u"<br>"
                    u'<a href="http://bazaar-vcs.org/QBzr">http://bazaar-vcs.org/QBzr</a>') % tpl)
