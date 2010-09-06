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
import sys
from PyQt4 import QtCore, QtGui


from bzrlib import (
    errors,
    osutils,
    )
import bzrlib

from bzrlib.plugins import qbzr
from bzrlib.plugins.qbzr.lib.i18n import gettext
from bzrlib.plugins.qbzr.lib.statuscache import StatusCache
from bzrlib.plugins.qbzr.lib.ui_bookmark import Ui_BookmarkDialog
from bzrlib.plugins.qbzr.lib.util import (
    QBzrWindow,
    get_qbzr_config,
    open_browser,
    StandardButton,
    BTN_OK,
    BTN_CANCEL,
    )


def formatFileSize(size):
    if size < 1024:
        return "%d B" % (size,)
    else:
        return "%0.1f KB" % (size / 1024.0,)


class BookmarkDialog(QtGui.QDialog):

    def __init__(self, title, parent=None):
        QtGui.QDialog.__init__(self, parent)
        self.setWindowTitle(title)
        self.ui = Ui_BookmarkDialog()
        self.ui.setupUi(self)
        self.ui.buttonBox.addButton(StandardButton(BTN_OK),
                                    QtGui.QDialogButtonBox.AcceptRole)
        self.ui.buttonBox.addButton(StandardButton(BTN_CANCEL),
                                    QtGui.QDialogButtonBox.RejectRole)

    def setValues(self, name, location):
        self.ui.name.setText(name)
        self.ui.location.setText(location)

    def values(self):
        return (unicode(self.ui.name.text()),
                unicode(self.ui.location.text()))


class SideBarItem(object):

    def __init__(self):
        self.icon = QtCore.QVariant()
        self.text = QtCore.QVariant()
        self.parent = None
        self.children = []

    def loadChildren(self, sidebar):
        pass

    def showContextMenu(self, sidebar, pos):
        pass

    def __repr__(self):
        return '<%s ("%s")>' % (self.__class__.__name__, self.text.toString())


class DirectoryItem(SideBarItem):

    def __init__(self, fileInfo, parent, sidebar):
        self.path = fileInfo.filePath()
        self.icon = QtCore.QVariant(sidebar.window.icons['folder'])
        self.text = QtCore.QVariant(fileInfo.fileName() or fileInfo.path())
        self.parent = parent
        self.children = None

    def load(self, sidebar):
        self.children = []
        fileInfoList = QtCore.QDir(self.path).entryInfoList(
            QtCore.QDir.Dirs |
            QtCore.QDir.Drives |
            QtCore.QDir.NoDotAndDotDot)
        for fileInfo in fileInfoList:
            #print fileInfo.fileName(), sidebar.window.getDirectoryStatus(pathParts, unicode(fileInfo.fileName()))
            item = DirectoryItem(fileInfo, self, sidebar)
            self.children.append(item)

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
            self.children.append(item)


class BookmarkItem(DirectoryItem):

    def __init__(self, name, path, parent, sidebar):
        self.path = path
        self.icon = QtCore.QVariant(sidebar.window.icons['folder'])
        self.text = QtCore.QVariant(name)
        self.parent = parent
        self.children = None

    def showContextMenu(self, sidebar, pos):
        self.contextMenu = QtGui.QMenu()
        self.contextMenu.addAction(gettext("&Edit Bookmark..."), self.edit)
        self.contextMenu.addAction(gettext("&Remove Bookmark..."), self.remove)
        self.contextMenu.popup(pos)

    def edit(self):
        self.parent.window.editBookmark(self.parent.children.index(self))

    def remove(self):
        self.parent.window.removeBookmark(self.parent.children.index(self))


class BookmarksItem(SideBarItem):

    def __init__(self, sidebar):
        self.window = sidebar.window
        self.icon = QtCore.QVariant(sidebar.window.icons['bookmark'])
        self.text = QtCore.QVariant(gettext("Bookmarks"))
        self.parent = sidebar.root
        self.children = None
        self.contextMenu = QtGui.QMenu()
        self.contextMenu.addAction(sidebar.window.actions['add-bookmark'])

    def load(self, sidebar):
        config = get_qbzr_config()
        self.children = []
        for name, path in config.get_bookmarks():
            item = BookmarkItem(name, path, self, sidebar)
            self.children.append(item)

    def refresh(self):
        self.children = None

    def showContextMenu(self, sidebar, pos):
        self.contextMenu.popup(pos)


class SideBarModel(QtCore.QAbstractItemModel):

    def __init__(self, parent=None):
        QtCore.QAbstractItemModel.__init__(self, parent)
        self.window = parent
        self.root = SideBarItem()
        self.bookmarksItem = BookmarksItem(self)
        self.root.children.append(self.bookmarksItem)
        self.fileSystemItem = FileSystemItem(self)
        self.root.children.append(self.fileSystemItem)

    def itemFromIndex(self, index):
        if not index.isValid():
            return self.root
        else:
            return index.internalPointer()

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
            return self.createIndex(row, 0, item)

    def refresh(self, item=None):
        if item is None:
            items = self.root.children
        else:
            items = [item]
        self.emit(QtCore.SIGNAL("layoutAboutToBeChanged()"))
        for row, item in enumerate(items):
            if item.children:
                parent = self.createIndex(row, 0, item)
                self.beginRemoveRows(parent, 0, len(item.children) - 1)
                item.refresh()
                self.endRemoveRows()
        self.emit(QtCore.SIGNAL("layoutChanged()"))

    def showContextMenu(self, pos):
        index = self.window.sideBarView.indexAt(pos)
        if not index.isValid():
            return
        pos = self.window.sideBarView.viewport().mapToGlobal(pos)
        self.itemFromIndex(index).showContextMenu(self, pos)


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
        self.cache = StatusCache(self)
        self.currentDirectory = None

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
        action = QtGui.QAction(gettext("&Add Bookmark..."), self)
        self.connect(action, QtCore.SIGNAL("triggered(bool)"), self.addBookmark)
        self.actions['add-bookmark'] = action

    def createMenuBar(self):
        # FIXME: this maybe needs a special version for OS X
        mainMenu = self.menuBar()
        fileMenu = mainMenu.addMenu(gettext("&File"))
        fileMenu.addAction(gettext("&Configure..."), self.configure)
        fileMenu.addSeparator()
        fileMenu.addAction(gettext("&Quit"), self.close, "Ctrl+Q")
        viewMenu = mainMenu.addMenu(gettext("&View"))
        viewMenu.addAction(self.actions['refresh'])
        branchMenu = mainMenu.addMenu(gettext("&Branch"))
        branchMenu.addAction(self.actions['commit'])
        branchMenu.addAction(self.actions['push'])
        branchMenu.addAction(self.actions['pull'])
        bookmarksMenu = mainMenu.addMenu(gettext("&Bookmarks"))
        bookmarksMenu.addAction(self.actions['add-bookmark'])
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
        self.sideBarView.setContextMenuPolicy(QtCore.Qt.CustomContextMenu)
        self.connect(self.sideBarView,
                     QtCore.SIGNAL("customContextMenuRequested(QPoint)"),
                     self.sideBarModel.showContextMenu)
        self.connect(self.sideBarView.selectionModel(),
                     QtCore.SIGNAL("selectionChanged(QItemSelection, QItemSelection)"),
                     self.updateFileList)
        header = self.sideBarView.header()
        header.setResizeMode(QtGui.QHeaderView.ResizeToContents)
        header.setStretchLastSection(False)
        header.setVisible(False)

        self.fileListView = QtGui.QTreeWidget()
        self.fileListView.setRootIsDecorated(False)
        self.fileListView.setHeaderLabels([
            gettext("Name"),
            gettext("Size"),
            gettext("Status"),
            ])
        self.connect(self.fileListView,
                     QtCore.SIGNAL("itemDoubleClicked(QTreeWidgetItem *, int)"),
                     self.onFileActivated)

        self.hsplitter = QtGui.QSplitter(QtCore.Qt.Horizontal)
        self.hsplitter.addWidget(self.sideBarView)
        self.hsplitter.addWidget(self.fileListView)

        self.console = QtGui.QTextBrowser()
        self.vsplitter.addWidget(self.hsplitter)
        self.vsplitter.addWidget(self.console)

        self.setCentralWidget(self.vsplitter)

    def _saveSize(self, config):
        super(type(self),self)._saveSize(config)
        name = self._window_name
        config.set_option(
            name + "_vsplitter_state",
            str(self.vsplitter.saveState()).encode("base64").strip())
        config.set_option(
            name + "_hsplitter_state",
            str(self.hsplitter.saveState()).encode("base64").strip())
        config.set_option(
            name + "_file_list_header_state",
            str(self.fileListView.header().saveState()).encode("base64").strip())

    def restoreSize(self, name, defaultSize):
        config = QBzrWindow.restoreSize(self, name, defaultSize)
        name = self._window_name
        value = config.get_option(name + "_vsplitter_state")
        if value:
            self.vsplitter.restoreState(value.decode("base64"))
        value = config.get_option(name + "_hsplitter_state")
        if value:
            self.hsplitter.restoreState(value.decode("base64"))
        value = config.get_option(name + "_file_list_header_state")
        if value:
            self.fileListView.header().restoreState(value.decode("base64"))

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
                    u"Copyright \u00A9 2006-2008 Luk\xe1\u0161 Lalinsk\xfd and others<br>"
                    u"<br>"
                    u'<a href="http://bazaar-vcs.org/QBzr">http://bazaar-vcs.org/QBzr</a>') % tpl)

    def loadIcons(self):
        icons = [
            ('view-refresh', ('16x16', '22x22'), None),
            ('bookmark', ('16x16',), None),
            ('computer', ('16x16',), None),
            ('qbzr-pull', ('22x22',), None),
            ('qbzr-push', ('22x22',), None),
            ('image-missing', ('22x22',), None),
            ('folder', ('16x16',), 'folder-open'),
            ('folder-branch', ('16x16',), None),
            ('folder-unchanged', ('16x16',), None),
            ('folder-modified', ('16x16',), None),
            ('folder-added', ('16x16',), None),
            ('folder-conflict', ('16x16',), None),
            ('file', ('16x16',), None),
            ('file-unchanged', ('16x16',), None),
            ('file-modified', ('16x16',), None),
            ('file-added', ('16x16',), None),
            ('file-conflict', ('16x16',), None),
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

    def commit(self):
        from bzrlib.workingtree import WorkingTree
        from bzrlib.plugins.qbzr.lib.commit import CommitWindow
        tree = WorkingTree.open_containing(self.currentDirectory)[0]
        self.window = CommitWindow(tree, [], parent=self)
        self.window.show()

    def push(self):
        from bzrlib.workingtree import WorkingTree
        from bzrlib.plugins.qbzr.lib.pull import QBzrPushWindow
        tree = WorkingTree.open_containing(self.currentDirectory)[0]
        self.window = QBzrPushWindow(tree.branch, parent=self)
        self.window.show()

    def pull(self):
        from bzrlib.workingtree import WorkingTree
        from bzrlib.plugins.qbzr.lib.pull import QBzrPullWindow
        tree = WorkingTree.open_containing(self.currentDirectory)[0]
        self.window = QBzrPullWindow(tree.branch, parent=self)
        self.window.show()

    def configure(self):
        from bzrlib.plugins.qbzr.lib.config import QBzrConfigWindow
        window = QBzrConfigWindow(self)
        window.exec_()

    def addBookmark(self):
        dialog = BookmarkDialog(gettext("Add Bookmark"), self)
        if dialog.exec_() == QtGui.QDialog.Accepted:
            name, location = dialog.values()
            config = get_qbzr_config()
            config.add_bookmark(name, location)
            config.save()
            self.sideBarModel.refresh(self.sideBarModel.bookmarksItem)

    def editBookmark(self, pos):
        config = get_qbzr_config()
        bookmarks = list(config.getBookmarks())
        dialog = BookmarkDialog(gettext("Edit Bookmark"), self)
        dialog.setValues(*bookmarks[pos])
        if dialog.exec_() == QtGui.QDialog.Accepted:
            bookmarks[pos] = dialog.values()
            config.set_bookmarks(bookmarks)
            config.save()
            self.sideBarModel.refresh(self.sideBarModel.bookmarksItem)

    def removeBookmark(self, pos):
        res = QtGui.QMessageBox.question(self,
            gettext("Remove Bookmark"),
            gettext("Do you really want to remove the selected bookmark?"),
            QtGui.QMessageBox.Yes | QtGui.QMessageBox.No)
        if res == QtGui.QMessageBox.Yes:
            config = get_qbzr_config()
            bookmarks = list(config.getBookmarks())
            del bookmarks[pos]
            config.set_bookmarks(bookmarks)
            config.save()
            self.sideBarModel.refresh(self.sideBarModel.bookmarksItem)

    def updateFileList(self, selected, deselected):
        items = map(self.sideBarModel.itemFromIndex, self.sideBarView.selectedIndexes())
        if not items:
            return
        item = items[0]
        if not isinstance(item, DirectoryItem):
            return
        self.setDirectory(unicode(item.path))

    def onFileActivated(self, item, column):
        path = item.data(0, QtCore.Qt.UserRole).toString()
        if path:
            # directory
            self.setDirectory(unicode(path))
        else:
            # file
            basename = unicode(item.text(0))
            filepath = osutils.pathjoin(self.currentDirectory, basename)
            url = QtCore.QUrl(filepath)
            QtGui.QDesktopServices.openUrl(url)

    def refresh(self):
        if self.currentDirectory:
            self.setDirectory(self.currentDirectory)
        self.sideBarModel.refresh()

    def autoRefresh(self, path):
        try:
            self.setDirectory(self.currentDirectory)
        except errors.PathNotChild:
            pass

    def setDirectory(self, path):
        self.currentDirectory = path
        self.setWindowTitle("QBzr - %s" % path)
        QtGui.QApplication.setOverrideCursor(QtGui.QCursor(QtCore.Qt.WaitCursor))
        try:
            pathParts = osutils.splitpath(path)
            self.fileListView.invisibleRootItem().takeChildren()
            item = QtGui.QTreeWidgetItem(self.fileListView)
            item.setText(0, '..')
            item.setIcon(0, self.icons['folder'])
            item.setData(0, QtCore.Qt.UserRole, QtCore.QVariant(os.path.dirname(path)))
            fileInfoList = QtCore.QDir(path).entryInfoList(
                QtCore.QDir.AllEntries | QtCore.QDir.NoDotAndDotDot,
                QtCore.QDir.DirsFirst)
            for fileInfo in fileInfoList:
                item = QtGui.QTreeWidgetItem(self.fileListView)
                item.setText(0, fileInfo.fileName())
                if fileInfo.isDir():
                    status = self.cache.getDirectoryStatus(pathParts, unicode(fileInfo.fileName()))
                    if status == 'non-versioned':
                        icon = 'folder'
                    else:
                        icon = 'folder-' + status
                    item.setData(0, QtCore.Qt.UserRole, QtCore.QVariant(fileInfo.filePath()))
                    item.setIcon(0, self.icons[icon])
                else:
                    status = self.cache.getFileStatus(pathParts, unicode(fileInfo.fileName()))
                    if status == 'non-versioned':
                        icon = 'file'
                    else:
                        icon = 'file-' + status
                    item.setIcon(0, self.icons[icon])
                    item.setText(1, formatFileSize(fileInfo.size()))
                    item.setTextAlignment(1, QtCore.Qt.AlignRight)
                item.setText(2, status)
        finally:
            QtGui.QApplication.restoreOverrideCursor()
