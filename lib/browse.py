# -*- coding: utf-8 -*-
#
# QBzr - Qt frontend to Bazaar commands
# Copyright (C) 2006 Lukáš Lalinský <lalinsky@gmail.com>
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

from time import clock
from PyQt4 import QtCore, QtGui
from bzrlib import (
    osutils,
    errors,
    )
from bzrlib.branch import Branch
from bzrlib.osutils import pathjoin
from bzrlib.revisionspec import RevisionSpec

from bzrlib.plugins.qbzr.lib.cat import QBzrCatWindow
from bzrlib.plugins.qbzr.lib.annotate import AnnotateWindow
from bzrlib.plugins.qbzr.lib.i18n import gettext
from bzrlib.plugins.qbzr.lib.log import LogWindow
from bzrlib.plugins.qbzr.lib.util import (
    BTN_CLOSE,
    QBzrWindow,
    ThrobberWidget,
    extract_name,
    format_timestamp,
    get_set_encoding,
    runs_in_loading_queue,
    url_for_display,
    get_summary,
    )
from bzrlib.plugins.qbzr.lib.uifactory import ui_current_widget
from bzrlib.plugins.qbzr.lib.trace import reports_exception


class TreeModel(QtCore.QAbstractItemModel):
    #NAME, AUTHOR, REVNO, TEXT = range(4)
    NAME = 0
    REVID = QtCore.Qt.UserRole + 1
    FILEID = QtCore.Qt.UserRole + 2
    
    def __init__(self, file_icon, dir_icon, get_revno=None, parent=None):
        QtCore.QAbstractTableModel.__init__(self, parent)
        
        self.horizontalHeaderLabels = [gettext("File Name"),]

        self.get_revno = get_revno
        self.file_icon = file_icon
        self.dir_icon = dir_icon
        self.tree = None
    
    def set_tree(self, tree, branch):
        self.emit(QtCore.SIGNAL("layoutAboutToBeChanged()"))
        self.tree = tree
        self.id2fileid = []
        self.fileid2id = {}
        self.dir_children_ids = {}
        self.parent_ids = []
        
        # Create internal ids for all items in the tree for use in
        # ModelIndex's.
        root_fileid = tree.path2id('.')
        self.append_fileid(root_fileid, None)
        remaining_dirs = [root_fileid,]
        while remaining_dirs:
            dir_fileid = remaining_dirs.pop(0)
            dir_id = self.fileid2id[dir_fileid]
            dir_children_ids = []
            for name, child in tree.inventory[dir_fileid].sorted_children():
                id = self.append_fileid(child.file_id, dir_id)
                dir_children_ids.append(id)
                if child.kind == "directory":
                    remaining_dirs.append(child.file_id)
                
                if len(self.id2fileid) % 100 == 0:
                    QtCore.QCoreApplication.processEvents()
            self.dir_children_ids[dir_id] = dir_children_ids
        
        self.emit(QtCore.SIGNAL("layoutChanged()"))
    
    def append_fileid(self, fileid, parent_id):
        ix = len(self.id2fileid)
        self.id2fileid.append(fileid)
        self.parent_ids.append(parent_id)
        self.fileid2id[fileid] = ix
        return ix
    
    def columnCount(self, parent):
        return len(self.horizontalHeaderLabels)

    def rowCount(self, parent):
        if self.tree is None:
            return 0
        parent_id = parent.internalId()
        if parent_id not in self.dir_children_ids:
            return 0
        return len(self.dir_children_ids[parent_id])

    def _index(self, row, column, parent_id):
        item_id = self.dir_children_ids[parent_id][row]
        return self.createIndex(row, column, item_id)
    
    def index(self, row, column, parent = QtCore.QModelIndex()):
        if self.tree is None:
            return self.createIndex(row, column, 0)
        parent_id = parent.internalId()
        return self._index(row, column, parent_id)
    
    def sibling(self, row, column, index):
        sibling_id = child.internalId()
        if sibling_id == 0:
            return QtCore.QModelIndex()
        parent_id = self.parent_ids[child_id]
        return self._index(row, column, parent_id)
    
    def parent(self, child):
        child_id = child.internalId()
        if child_id == 0:
            return QtCore.QModelIndex()
        item_id = self.parent_ids[child_id]
        if item_id == 0 :
            return QtCore.QModelIndex()
        
        parent_id = self.parent_ids[item_id]
        row = self.dir_children_ids[parent_id].index(item_id)
        return self.createIndex(row, 0, item_id)

    def hasChildren(self, parent):
        if self.tree is None:
            return False
        
        parent_id = parent.internalId()
        return parent_id in self.dir_children_ids
    
    def data(self, index, role):
        if not index.isValid():
            return QtCore.QVariant()
        
        fileid = self.id2fileid[index.internalId()]
        
        if role == self.FILEID:
            return QtCore.QVariant(fileid)
        
        item = self.tree.inventory[fileid]
        
        if role == self.REVID:
            return QtCore.QVariant(item.revision)
        
        
        #if revid in cached_revisions:
        #    rev = cached_revisions[revid]
        #else:
        #    rev = None

        column = index.column()
        if column == self.NAME:
            if role == QtCore.Qt.DisplayRole:
                return QtCore.QVariant(item.name)
            if role == QtCore.Qt.DecorationRole:
                if item.kind == "file":
                    return QtCore.QVariant(self.file_icon)
                if item.kind == "directory":
                    return QtCore.QVariant(self.dir_icon)
                # XXX Simlink
                return QtCore.QVariant()
        
        #if column == self.AUTHOR:
        #    if role == QtCore.Qt.DisplayRole:
        #        if is_top and rev:
        #            return QtCore.QVariant(get_apparent_author_name(rev))
        #
        #if column == self.REVNO:
        #    if role == QtCore.Qt.DisplayRole:
        #        if is_top:
        #            revno = self.get_revno(revid)
        #            if revno is None:
        #                revno = ""
        #            return QtCore.QVariant(revno)
        #    if role == QtCore.Qt.TextAlignmentRole:
        #        return QtCore.QVariant(QtCore.Qt.AlignRight)
        #
        #if column == self.TEXT:
        #    if role == QtCore.Qt.DisplayRole:
        #        return QtCore.QVariant(text)
        #    if role == QtCore.Qt.FontRole:
        #        return QtCore.QVariant(self.font)
        #
        #if column == self.TEXT and role == QtCore.Qt.BackgroundRole and rev:
        #    if self.now < rev.timestamp:
        #        days = 0
        #    else:
        #        days = (self.now - rev.timestamp) / (24 * 60 * 60)
        #    
        #    saturation = 0.5/((days/50) + 1)
        #    hue =  1-float(abs(hash(get_apparent_author_name(rev)))) / sys.maxint 
        #    return QtCore.QVariant(QtGui.QColor.fromHsvF(hue, saturation, 1 ))
        
        return QtCore.QVariant()
    
    def get_revid(self, row):
        return self.annotate[row][0]

    def flags(self, index):
        if not index.isValid():
            return QtCore.Qt.ItemIsEnabled

        return QtCore.Qt.ItemIsEnabled | QtCore.Qt.ItemIsSelectable

    def headerData(self, section, orientation, role):
        if orientation == QtCore.Qt.Horizontal and role == QtCore.Qt.DisplayRole:
            return QtCore.QVariant(self.horizontalHeaderLabels[section])
        return QtCore.QVariant()
    
    def on_revisions_loaded(self, revisions, last_call):
        for revid in revisions.iterkeys():
            for row in self.revid_indexes[revid]:
                self.emit(QtCore.SIGNAL("dataChanged(QModelIndex, QModelIndex)"),
                          self.createIndex (row, 0, QtCore.QModelIndex()),
                          self.createIndex (row, 4, QtCore.QModelIndex()))

    def get_repo(self):
        return self.branch.repository

class FileTreeWidget(QtGui.QTreeView):

    def __init__(self, window, *args):
        QtGui.QTreeWidget.__init__(self, *args)
        self.window = window

    def contextMenuEvent(self, event):
        self.window.context_menu.popup(event.globalPos())
        event.accept()


class BrowseWindow(QBzrWindow):

    NAME, DATE, AUTHOR, REV, MESSAGE = range(5)     # indices of columns in the window

    FILEID = QtCore.Qt.UserRole + 1

    def __init__(self, branch=None, location=None, revision=None,
                 revision_id=None, revision_spec=None, parent=None):
        if branch:
            self.branch = branch
            self.location = url_for_display(branch.base)
        else:
            self.branch = None
            if location is None:
                location = osutils.getcwd()
            self.location = location
        
        self.revision_id = revision_id
        self.revision_spec = revision_spec
        self.revision = revision
        self.root_file_id = None

        QBzrWindow.__init__(self,
            [gettext("Browse"), self.location], parent)
        self.restoreSize("browse", (780, 580))

        vbox = QtGui.QVBoxLayout(self.centralwidget)
        
        self.throbber = ThrobberWidget(self)
        vbox.addWidget(self.throbber)

        hbox = QtGui.QHBoxLayout()
        hbox.addWidget(QtGui.QLabel(gettext("Location:")))
        self.location_edit = QtGui.QLineEdit()
        self.location_edit.setReadOnly(True)
        self.location_edit.setText(self.location)
        hbox.addWidget(self.location_edit, 7)
        hbox.addWidget(QtGui.QLabel(gettext("Revision:")))
        self.revision_edit = QtGui.QLineEdit()
        hbox.addWidget(self.revision_edit, 1)
        self.show_button = QtGui.QPushButton(gettext("Show"))
        self.connect(self.show_button, QtCore.SIGNAL("clicked()"), self.reload_tree)
        hbox.addWidget(self.show_button, 0)
        vbox.addLayout(hbox)
        
        file_icon = self.style().standardIcon(QtGui.QStyle.SP_FileIcon)
        dir_icon = self.style().standardIcon(QtGui.QStyle.SP_DirIcon)

        self.file_tree = FileTreeWidget(self)
        #self.file_tree.setHeaderLabels([
        #    gettext("Name"),
        #    gettext("Date"),
        #    gettext("Author"),
        #    gettext("Rev"),
        #    gettext("Message"),
        #    ])

        self.file_tree_model = TreeModel(file_icon, dir_icon)
        self.file_tree.setModel(self.file_tree_model)
        
        header = self.file_tree.header()
        header.setResizeMode(self.NAME, QtGui.QHeaderView.ResizeToContents)
        header.setResizeMode(self.REV, QtGui.QHeaderView.ResizeToContents)

        self.context_menu = QtGui.QMenu(self.file_tree)
        self.context_menu.addAction(gettext("Show log..."), self.show_file_log)
        self.context_menu.addAction(gettext("Annotate"), self.show_file_annotate)
        self.context_menu.setDefaultAction(
            self.context_menu.addAction(gettext("View file"),
                                        self.show_file_content))

        self.connect(self.file_tree,
                     QtCore.SIGNAL("doubleClicked(QModelIndex)"),
                     self.show_file_content)

        vbox.addWidget(self.file_tree)

        buttonbox = self.create_button_box(BTN_CLOSE)
        vbox.addWidget(buttonbox)

        self.windows = []

    def show(self):
        # we show the bare form as soon as possible.
        QBzrWindow.show(self)
        QtCore.QTimer.singleShot(1, self.load)
   
    @runs_in_loading_queue
    @ui_current_widget
    @reports_exception()
    def load(self):
        self.throbber.show()
        self.processEvents()
        try:
            if not self.branch:
                self.branch, path = Branch.open_containing(self.location) 
            
            if self.revision is None:
                if self.revision_id is None:
                    revno, self.revision_id = self.branch.last_revision_info()
                    self.revision_spec = str(revno)
                self.set_revision(revision_id=self.revision_id, text=self.revision_spec)
            else:
                self.set_revision(self.revision)
        finally:
            self.throbber.hide()
    
    def get_current_file_id(self):
        '''Gets the file_id for the currently selected item, or returns
        the root_file_id if nothing is currently selected.'''

        item = self.file_tree.currentItem()
        if item == None:
            file_id = self.root_file_id
        else:
            file_id = unicode(item.data(self.NAME, self.FILEID).toString())

        return file_id

    def load_file_tree(self, entry, parent_item):
        files, dirs = [], []
        revs = set()
        for name, child in entry.sorted_children():
            revs.add(child.revision)
            if child.kind == "directory":
                dirs.append(child)
            else:
                files.append(child)
            
            current_time = clock()
            if 0.1 < current_time - self.start_time:
                self.processEvents()
                self.start_time = clock()
            
        for child in dirs:
            item = QtGui.QTreeWidgetItem(parent_item)
            item.setIcon(self.NAME, self.dir_icon)
            item.setText(self.NAME, child.name)
            item.setData(self.NAME, self.FILEID,
                                        QtCore.QVariant(child.file_id))
            revs.update(self.load_file_tree(child, item))
            self.items.append((item, child.revision))
        for child in files:
            item = QtGui.QTreeWidgetItem(parent_item)
            item.setIcon(self.NAME, self.file_icon)
            item.setText(self.NAME, child.name)
            item.setData(self.NAME, self.FILEID,
                                        QtCore.QVariant(child.file_id))
            self.items.append((item, child.revision))
        return revs

    def get_current_path(self):
        # Get selected item.
        item = self.file_tree.currentItem()
        if item == None: return

        # Build full item path.
        path_parts = [unicode(item.text(0))]
        parent = item.parent()
        while parent is not None:
            path_parts.append(unicode(parent.text(0)))
            parent = parent.parent()
        #path_parts.append('.')      # IMO with leading ./ path looks better
        path_parts.reverse()
        return pathjoin(*path_parts)
    
    @runs_in_loading_queue
    @ui_current_widget
    def show_file_content(self, index=None):
        """Launch qcat for one selected file."""
        # XXX - We just ignore index - which gets passed to us when the user
        # dbl clicks on a file. We should be able to pass index to
        # get_current_path to make this more reusable.
        path = self.get_current_path()

        tree = self.branch.repository.revision_tree(self.revision_id)
        encoding = get_set_encoding(None, self.branch)
        window = QBzrCatWindow(filename = path, tree = tree, parent=self,
            encoding=encoding)
        window.show()
        self.windows.append(window)

    @ui_current_widget
    def show_file_log(self):
        """Show qlog for one selected file."""
        branch = self.branch
        
        file_id = self.get_current_file_id()

        window = LogWindow(None, branch, file_id)
        window.show()
        self.windows.append(window)
    
    @ui_current_widget
    def show_file_annotate(self):
        """Show qannotate for selected file."""
        path = self.get_current_path()

        branch = self.branch
        tree = self.branch.repository.revision_tree(self.revision_id)
        file_id = self.get_current_file_id()
        window = AnnotateWindow(branch, tree, path, file_id)
        window.show()
        self.windows.append(window)
    
    @ui_current_widget
    def set_revision(self, revspec=None, revision_id=None, text=None):
        branch = self.branch
        branch.lock_read()
        self.processEvents()
        #revno_map = branch.get_revision_id_to_revno_map()   # XXX make this operation lazy? how?
        self.processEvents()
        try:
            if revision_id is None:
                text = revspec.spec or ''
                if revspec.in_branch == revspec.in_history:
                    args = [branch]
                else:
                    args = [branch, False]
                try:
                    revision_id = revspec.in_branch(*args).rev_id
                except errors.InvalidRevisionSpec, e:
                    QtGui.QMessageBox.warning(self,
                        "QBzr - " + gettext("Browse"), str(e),
                        QtGui.QMessageBox.Ok)
                    return
            self.revision_id = revision_id
            self.tree = branch.repository.revision_tree(revision_id)
            self.processEvents()
            self.file_tree_model.set_tree(self.tree, self.branch)
        finally:
            branch.unlock()
        self.revision_edit.setText(text)
        #for item, revision_id in self.items:
        #    rev = revs[revision_id]
        #    revno = ''
        #    rt = revno_map.get(revision_id)
        #    if rt:
        #        revno = '.'.join(map(str, rt))
        #    item.setText(self.REV, revno)
        #    item.setText(self.DATE, format_timestamp(rev.timestamp))
        #    author = rev.properties.get('author', rev.committer)
        #    item.setText(self.AUTHOR, extract_name(author))
        #    item.setText(self.MESSAGE, get_summary(rev))

    @ui_current_widget
    def reload_tree(self):
        revstr = unicode(self.revision_edit.text())
        if not revstr:
            revno, revision_id = self.branch.last_revision_info()
            revision_spec = str(revno)
            self.set_revision(revision_id=revision_id, text=revision_spec)
        else:
            try:
                revspec = RevisionSpec.from_string(revstr)
            except errors.NoSuchRevisionSpec, e:
                QtGui.QMessageBox.warning(self,
                    "QBzr - " + gettext("Browse"), str(e),
                    QtGui.QMessageBox.Ok)
                return
            self.set_revision(revspec)

