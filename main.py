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
    QBzrGlobalConfig,
    open_browser,
    )


class SideBarItem(object):

    def __init__(self):
        self.icon = QtCore.QVariant()
        self.text = QtCore.QVariant()
        self.parent = None
        self.children = []

    def loadChildren(self, sidebar):
        pass

    def __repr__(self):
        return '<%s ("%s")>' % (self.__class__.__name__, self.text.toString())


class DirectoryItem(SideBarItem):

    def __init__(self, fileInfo, parent, sidebar):
        self.path = fileInfo.filePath()
        self.isBranch = parent.isBranch
        if not self.isBranch:
            self.isBranch = QtCore.QDir(self.path).exists('.bzr/branch')
        if self.isBranch:
            self.icon = QtCore.QVariant(sidebar.window.icons['folder-bzr'])
        else:
            self.icon = QtCore.QVariant(sidebar.window.icons['folder'])
        self.text = QtCore.QVariant(fileInfo.fileName())
        self.parent = parent
        self.children = None

    def load(self, sidebar):
        self.children = []
        fileInfoList = QtCore.QDir(self.path).entryInfoList(
            QtCore.QDir.Dirs |
            QtCore.QDir.Drives |
            QtCore.QDir.NoDotAndDotDot)
        for fileInfo in fileInfoList:
            item = DirectoryItem(fileInfo, self, sidebar)
            sidebar.addItem(item)

    def refresh(self):
        self.children = None


class FileSystemItem(DirectoryItem):

    def __init__(self, sidebar):
        self.isBranch = False
        self.icon = QtCore.QVariant(sidebar.window.icons['computer'])
        self.text = QtCore.QVariant(gettext("Computer"))
        self.parent = sidebar.root
        self.children = None

    def load(self, sidebar):
        self.children = []
        if sys.platform == 'win32':
            fileInfoList = QtCore.QDir.drives()
        else:
            fileInfoList = QtCore.QDir.root().entryInfoList(
                QtCore.QDir.Dirs |
                QtCore.QDir.Drives |
                QtCore.QDir.NoDotAndDotDot)
        for fileInfo in fileInfoList:
            item = DirectoryItem(fileInfo, self, sidebar)
            sidebar.addItem(item)


class BookmarkItem(DirectoryItem):

    def __init__(self, name, path, parent, sidebar):
        self.path = path
        self.isBranch = QtCore.QDir(self.path).exists('.bzr/branch')
        if self.isBranch:
            self.icon = QtCore.QVariant(sidebar.window.icons['folder-bzr'])
        else:
            self.icon = QtCore.QVariant(sidebar.window.icons['folder'])
        self.text = QtCore.QVariant(name)
        self.parent = parent
        self.children = None


class BookmarksItem(SideBarItem):

    def __init__(self, sidebar):
        self.icon = QtCore.QVariant(sidebar.window.icons['bookmark'])
        self.text = QtCore.QVariant(gettext("Bookmarks"))
        self.parent = sidebar.root
        self.children = None

    def load(self, sidebar):
        config = QBzrGlobalConfig()
        parser = config._get_parser()
        bookmarks = parser.get('BOOKMARKS', {})
        self.children = []
        for name, path in bookmarks.iteritems():
            item = BookmarkItem(name, path, self, sidebar)
            sidebar.addItem(item)

    def refresh(self):
        self.children = None


class SideBarModel(QtCore.QAbstractItemModel):

    def __init__(self, parent=None):
        QtCore.QAbstractItemModel.__init__(self, parent)
        self.window = parent
        self.byid = {}
        self.root = SideBarItem()
        self.bookmarksItem = BookmarksItem(self)
        self.addItem(self.bookmarksItem)
        self.fileSystemItem = FileSystemItem(self)
        self.addItem(self.fileSystemItem)

    def addItem(self, item):
        item.parent.children.append(item)
        self.byid[id(item)] = item

    def itemFromIndex(self, index):
        if not index.isValid():
            return self.root
        else:
            return self.byid[index.internalId()]

    def data(self, index, role):
        item = self.itemFromIndex(index)
        if role == QtCore.Qt.DecorationRole:
            return item.icon
        elif role == QtCore.Qt.DisplayRole:
            return item.text
        return QtCore.QVariant()

    def columnCount(self, parent):
        return 1

    def rowCount(self, index):
        item = self.itemFromIndex(index)
        if item.children is None:
            item.load(self)
        return len(item.children)

    def hasChildren(self, index):
        children = self.itemFromIndex(index).children
        return children is None or bool(children)

    def index(self, row, column, parent):
        return self.createIndex(row, column,
            self.itemFromIndex(parent).children[row])

    def parent(self, index):
        item = self.itemFromIndex(index).parent
        if item is None or item.parent is None:
            return QtCore.QModelIndex()
        else:
            row = item.parent.children.index(item)
            return self.createIndex(row, 0, id(item))

    def refresh(self):
        self.emit(QtCore.SIGNAL("layoutAboutToBeChanged()"))
        for item in self.byid.values():
            item.refresh()
        self.emit(QtCore.SIGNAL("layoutChanged()"))


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
        action.setStatusTip(gettext("Refresh the directory tree"))
        self.connect(action, QtCore.SIGNAL("triggered(bool)"), self.refresh)
        self.actions['refresh'] = action
        action = QtGui.QAction(self.icons['image-missing'],
                               gettext("&Commit"), self)
        action.setStatusTip(gettext("Commit changes into a new revision"))
        self.connect(action, QtCore.SIGNAL("triggered(bool)"), self.commit)
        self.actions['commit'] = action
        action = QtGui.QAction(self.icons['qbzr-push'],
                               gettext("&Push"), self)
        action.setStatusTip(gettext("Turn this branch into a mirror of another branch"))
        self.connect(action, QtCore.SIGNAL("triggered(bool)"), self.push)
        self.actions['push'] = action
        action = QtGui.QAction(self.icons['qbzr-pull'],
                               gettext("Pu&ll"), self)
        action.setStatusTip(gettext("Update a mirror of this branch"))
        self.connect(action, QtCore.SIGNAL("triggered(bool)"), self.pull)
        self.actions['pull'] = action

    def createMenuBar(self):
        # FIXME: this maybe needs a special version for OS X
        mainMenu = self.menuBar()
        fileMenu = mainMenu.addMenu(gettext("&File"))
        fileMenu.addAction(gettext("&Configure..."), self.configure)
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
        self.toolBar.addSeparator()
        self.toolBar.addAction(self.actions['commit'])
        self.toolBar.addAction(self.actions['pull'])
        self.toolBar.addAction(self.actions['push'])

    def createStatusBar(self):
        self.statusBar().showMessage("Ready")

    def createUi(self):
        self.vsplitter = QtGui.QSplitter(QtCore.Qt.Vertical)

        self.sideBarView = QtGui.QTreeView()
        self.sideBarModel = SideBarModel(self)
        self.sideBarView.setModel(self.sideBarModel)
        self.sideBarView.setTextElideMode(QtCore.Qt.ElideLeft)
        header = self.sideBarView.header()
        header.setResizeMode(QtGui.QHeaderView.ResizeToContents)
        header.setStretchLastSection(False)
        header.setVisible(False)

        self.fileListView = QtGui.QTreeWidget()
        self.fileListView.setHeaderLabels([
            gettext("Name"),
            gettext("Size"),
            gettext("Status"),
            gettext("Revision"),
            ])

        self.hsplitter = QtGui.QSplitter(QtCore.Qt.Horizontal)
        self.hsplitter.addWidget(self.sideBarView)
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
        icons = [
            ('view-refresh', ('16x16', '22x22'), None),
            ('bookmark', ('16x16',), None),
            ('computer', ('16x16',), None),
            ('folder', ('16x16',), 'folder-open'),
            ('folder-bzr', ('16x16',), 'folder-bzr-open'),
            ('folder-remote', ('16x16',), None),
            ('qbzr-pull', ('22x22',), None),
            ('qbzr-push', ('22x22',), None),
            ('image-missing', ('22x22',), None),
            ]
        self.icons = {}
        for name, sizes, name_on in icons:
            icon = QtGui.QIcon()
            for size in sizes:
                icon.addFile('/'.join([':', size, name]) + '.png')
            if name_on is not None:
                for size in sizes:
                    icon.addFile('/'.join([':', size, name_on]) + '.png',
                        QtCore.QSize(), QtGui.QIcon.Normal, QtGui.QIcon.On)
            self.icons[name] = icon

    def refresh(self):
        self.sideBarModel.refresh()

    def commit(self):
        from bzrlib.workingtree import WorkingTree
        from bzrlib.plugins.qbzr.commit import CommitWindow
        tree = WorkingTree.open('.')
        self.window = CommitWindow(tree, [])
        self.window.show()

    def push(self):
        print "push"

    def pull(self):
        print "pull"

    def configure(self):
        from bzrlib.plugins.qbzr.config import QBzrConfigWindow
        window = QBzrConfigWindow(self)
        window.exec_()
