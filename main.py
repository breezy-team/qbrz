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
        self.loadIcons()
        self.createActions()
        self.createMenuBar()
        self.createToolBar()
        self.createStatusBar()
        self.createUi()
        self.restoreSize("main", (800, 600))

    def createActions(self):
        self.actions = {}
        action = QtGui.QAction(self.icons['view-refresh'],
                               gettext("&Refresh"), self)
        action.setShortcut("Ctrl+R")
        self.connect(action, QtCore.SIGNAL("triggered(bool)"), self.refresh)
        self.actions['refresh'] = action

    def createMenuBar(self):
        # FIXME: this maybe needs a special version for OS X
        mainMenu = self.menuBar()
        fileMenu = mainMenu.addMenu(gettext("&File"))
        fileMenu.addSeparator()
        fileMenu.addAction(gettext("&Quit"), self.close, "Ctrl+Q")
        viewMenu = mainMenu.addMenu(gettext("&View"))
        viewMenu.addAction(self.actions['refresh'])
        helpMenu = mainMenu.addMenu(gettext("&Help"))
        helpMenu.addAction(gettext("&Help..."), self.showHelp, "F1")
        helpMenu.addSeparator()
        helpMenu.addAction(gettext("&About..."), self.showAboutDialog)

    def createToolBar(self):
        self.setUnifiedTitleAndToolBarOnMac(True)
        self.toolBar = self.addToolBar("Main")
        self.toolBar.setToolButtonStyle(QtCore.Qt.ToolButtonTextUnderIcon)
        self.toolBar.addAction(self.actions['refresh'])

    def createStatusBar(self):
        self.statusBar().showMessage("Ready")

    def createUi(self):
        self.vsplitter = QtGui.QSplitter(QtCore.Qt.Vertical)

        self.dirView = QtGui.QTreeView()
        self.dirView.header().setVisible(False)

        self.fileListView = QtGui.QTreeWidget()
        self.fileListView.setHeaderLabels([
            gettext("Name"),
            gettext("Size"),
            gettext("Status"),
            gettext("Revision"),
            ])

        self.hsplitter = QtGui.QSplitter(QtCore.Qt.Horizontal)
        self.hsplitter.addWidget(self.dirView)
        self.hsplitter.addWidget(self.fileListView)

        self.console = QtGui.QTextBrowser()
        self.vsplitter.addWidget(self.hsplitter)
        self.vsplitter.addWidget(self.console)

        self.setCentralWidget(self.vsplitter)

    def saveSize(self):
        config = QBzrWindow.saveSize(self)
        name = self._window_name
        config.set_user_option(
            name + "_vsplitter_state",
            str(self.vsplitter.saveState()).encode("base64"))
        config.set_user_option(
            name + "_hsplitter_state",
            str(self.hsplitter.saveState()).encode("base64"))

    def restoreSize(self, name, defaultSize):
        config = QBzrWindow.restoreSize(self, name, defaultSize)
        name = self._window_name
        value = config.get_user_option(name + "_vsplitter_state")
        if value:
            self.vsplitter.restoreState(value.decode("base64"))
        value = config.get_user_option(name + "_hsplitter_state")
        if value:
            self.hsplitter.restoreState(value.decode("base64"))

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

    def loadIcons(self):
        icon_names = ['view-refresh', 'bookmark']
        sizes = ['16x16', '22x22']
        self.icons = {}
        for name in icon_names:
            icon = QtGui.QIcon()
            for size in sizes:
                icon.addFile('/'.join([':', size, name]) + '.png')
            self.icons[name] = icon

    def refresh(self):
        print "refresh"
