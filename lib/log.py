# -*- coding: utf-8 -*-
#
# QBzr - Qt frontend to Bazaar commands
# Copyright (C) 2006-2007 Lukáš Lalinský <lalinsky@gmail.com>
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
from bzrlib.plugins.qbzr.lib import logmodel
from bzrlib.plugins.qbzr.lib.diff import DiffWindow
from bzrlib.plugins.qbzr.lib.i18n import gettext
from bzrlib.plugins.qbzr.lib.util import (
    BTN_CLOSE,
    QBzrWindow,
    format_revision_html,
    format_timestamp,
    open_browser,
    RevisionMessageBrowser,
    )

have_search = True
try:
    from bzrlib.plugins.search import errors as search_errors
    from bzrlib.plugins.search import index as search_index
except ImportError:
    have_search = False

PathRole = QtCore.Qt.UserRole + 1

class GraphTagsBugsItemDelegate(QtGui.QItemDelegate):

    _tagColor = QtGui.QColor(255, 255, 170)
    _tagColorBorder = QtGui.QColor(255, 238, 0)

    _bugColor = QtGui.QColor(255, 188, 188)
    _bugColorBorder = QtGui.QColor(255, 79, 79)

    _twistyColor = QtCore.Qt.black

    def paint(self, painter, option, index):
        node = index.data(logmodel.GraphNodeRole)
        if node.isValid():
            self.drawGraph = True
            self.node = node.toList()
            self.lines = index.data(logmodel.GraphLinesRole).toList()
            self.twisty_state = index.data(logmodel.GraphTwistyStateRole)
            
            prevIndex = index.sibling (index.row()-1, index.column())
            if prevIndex.isValid ():
                self.prevLines = prevIndex.data(logmodel.GraphLinesRole).toList()
            else:
                self.prevLines = []
        else:
            self.drawGraph = False
        
        self.labels = []
        # collect tag names
        for tag in index.data(logmodel.TagsRole).toList():
            self.labels.append(
                (tag.toString(), self._tagColor,
                 self._tagColorBorder))
        # collect bug ids
        for bug in index.data(logmodel.BugIdsRole).toList():
            self.labels.append(
                (bug.toString(), self._bugColor,
                 self._bugColorBorder))
        QtGui.QItemDelegate.paint(self, painter, option, index)
    
    def get_color(self, color, back):
        qcolor = QtGui.QColor()
        if color == 0:
            if back:
                qcolor.setHsvF(0,0,0.8)
            else:
                qcolor.setHsvF(0,0,0)
        else:
            h = float(color % 6) / 6
            if back:
                qcolor.setHsvF(h,0.4,1)
            else:
                qcolor.setHsvF(h,1,0.7)
        
        return qcolor
    
    def drawLine(self, painter, pen, rect, boxsize, mid, height,
                 start, end, color, direct):
        pen.setColor(self.get_color(color,False))
        if direct:
            pen.setStyle(QtCore.Qt.SolidLine)
        else:
            pen.setStyle(QtCore.Qt.DotLine)            
        painter.setPen(pen)
        startx = rect.x() + boxsize * start + boxsize / 2 
        endx = rect.x() + boxsize * end + boxsize / 2 
        
        path = QtGui.QPainterPath()
        path.moveTo(QtCore.QPointF(startx, mid - height / 2))
        
        if start - end == 0 :
            path.lineTo(QtCore.QPointF(endx, mid + height / 2)) 
        else:
            path.cubicTo(QtCore.QPointF(startx, mid - height / 5),
                         QtCore.QPointF(startx, mid - height / 5),
                         QtCore.QPointF(startx + (endx - startx) / 2, mid))

            path.cubicTo(QtCore.QPointF(endx, mid + height / 5),
                         QtCore.QPointF(endx, mid + height / 5),
                         QtCore.QPointF(endx, mid + height / 2 + 1))
        painter.drawPath(path)
        pen.setStyle(QtCore.Qt.SolidLine)

    def drawDisplay(self, painter, option, rect, text):
        graphCols = 0
        if self.drawGraph:
            painter.save()
            try:
                painter.setRenderHint(QtGui.QPainter.Antialiasing)            
                boxsize = float(rect.height())
                dotsize = 0.7
                pen = QtGui.QPen()
                penwidth = 1
                pen.setWidth(penwidth)
                pen.setCapStyle(QtCore.Qt.FlatCap)
                #this is to try get lines 1 pixel wide to actualy be 1 pixel wide.
                painter.translate(0.5, 0.5)
                
                
                # Draw lines into the cell
                for line in self.prevLines:
                    start, end, color = [linei.toInt()[0] for linei in line.toList()[0:3]]
                    direct = line.toList()[3].toBool()
                    self.drawLine (painter, pen, rect, boxsize,
                                   rect.y(), boxsize,
                                   start, end, color, direct)
                    graphCols = max((graphCols, min(start, end)))
        
                # Draw lines out of the cell
                for line in self.lines:
                    start, end, color = [linei.toInt()[0] for linei in line.toList()[0:3]]
                    direct = line.toList()[3].toBool()
                    self.drawLine (painter, pen, rect,boxsize,
                                   rect.y() + boxsize, boxsize,
                                   start, end, color, direct)
                    graphCols = max((graphCols, min(start, end)))
                
                # Draw the revision node in the right column
                color = self.node[1].toInt()[0]
                column = self.node[0].toInt()[0]
                graphCols = max((graphCols, column))
                pen.setColor(self.get_color(color,False))
                painter.setPen(pen)
                painter.setBrush(QtGui.QBrush(self.get_color(color,True)))
                centerx = rect.x() + boxsize * (column + 0.5)
                centery = rect.y() + boxsize * 0.5
                painter.drawEllipse(
                    QtCore.QRectF(centerx - (boxsize * dotsize * 0.5 ),
                                  centery - (boxsize * dotsize * 0.5 ),
                                 boxsize * dotsize, boxsize * dotsize))

                # Draw twisty
                if self.twisty_state.isValid():
                    linesize = 0.35
                    pen.setColor(self._twistyColor)
                    painter.setPen(pen)
                    painter.drawLine(QtCore.QLineF (centerx - boxsize * linesize / 2,
                                                    centery,
                                                    centerx + boxsize * linesize / 2,
                                                    centery))
                    if not self.twisty_state.toBool():
                        painter.drawLine(QtCore.QLineF (centerx,
                                                        centery - boxsize * linesize / 2,
                                                        centerx,
                                                        centery + boxsize * linesize / 2))
                
            finally:
                painter.restore()
            rect.adjust( (graphCols + 1.7) * boxsize, 0, 0, 0)
        
        painter.save()
        try:
            tagFont = QtGui.QFont(option.font)
            tagFont.setPointSizeF(tagFont.pointSizeF() * 9 / 10)
    
            x = 0
            for label, color, borderColor in self.labels:
                tagRect = rect.adjusted(1, 1, -1, -1)
                tagRect.setWidth(QtGui.QFontMetrics(tagFont).width(label) + 6)
                tagRect.moveLeft(tagRect.x() + x)
                painter.fillRect(tagRect.adjusted(1, 1, -1, -1), color)
                painter.setPen(borderColor)
                painter.drawRect(tagRect.adjusted(0, 0, -1, -1))
                painter.setFont(tagFont)
                painter.setPen(option.palette.text().color())
                painter.drawText(tagRect.left() + 3, tagRect.bottom() - option.fontMetrics.descent() + 1, label)
                x += tagRect.width() + 3
        finally:
            painter.restore()
        
        rect.adjust( x, 0, 0, 0)
        
        return QtGui.QItemDelegate.drawDisplay(self, painter, option, rect, text)

class Compleater(QtGui.QCompleter):
    def splitPath (self, path):
        return path.split(" ")

class LogWindow(QBzrWindow):

    def __init__(self, branch, location, specific_fileid, replace=None, parent=None):
        title = [gettext("Log")]
        self.branch = branch

        if location:
            title.append(location)
        QBzrWindow.__init__(self, title, parent)
        self.restoreSize("log", (710, 580))
        self.specific_fileid = specific_fileid

        self.replace = replace
        self.revisions = {}

        self.changesModel = logmodel.GraphModel()

        self.changesProxyModel = logmodel.GraphFilterProxyModel()
        self.changesProxyModel.setSourceModel(self.changesModel)
        self.changesProxyModel.setFilterCaseSensitivity(QtCore.Qt.CaseInsensitive)
        self.changesProxyModel.setFilterRole(logmodel.FilterMessageRole)
        self.changesProxyModel.setDynamicSortFilter(True)
        self.changesModel.setGraphFilterProxyModel(self.changesProxyModel)
        

        logwidget = QtGui.QWidget()
        logbox = QtGui.QVBoxLayout(logwidget)
        logbox.setContentsMargins(0, 0, 0, 0)

        searchbox = QtGui.QHBoxLayout()

        self.search_label = QtGui.QLabel(gettext("&Search:"))
        self.search_edit = QtGui.QLineEdit()
        self.search_label.setBuddy(self.search_edit)
        self.connect(self.search_edit, QtCore.SIGNAL("textEdited(QString)"),
                     self.set_search_timer)

        self.search_timer = QtCore.QTimer(self)
        self.search_timer.setSingleShot(True)
        self.connect(self.search_timer, QtCore.SIGNAL("timeout()"),
                     self.update_search)

        searchbox.addWidget(self.search_label)
        searchbox.addWidget(self.search_edit)

        self.searchType = QtGui.QComboBox()
        if have_search:
            try:
                self.index = search_index.open_index_branch(self.branch)
                self.completer = Compleater(self)
                suggestions = QtCore.QStringList()
                for s in self.index.suggest((("",),)):
                    suggestions.append(s[0])
                self.completer.setModel(QtGui.QStringListModel(suggestions, self.completer))
                self.searchType.addItem(gettext("Messages and File text (indexed)"),
                                        QtCore.QVariant(logmodel.FilterSearchRole))
                self.search_edit.setCompleter(self.completer)
            except search_errors.NoSearchIndex:
                self.index = None
                self.compleater = None
            
        self.searchType.addItem(gettext("Messages"),
                                QtCore.QVariant(logmodel.FilterMessageRole))
        self.searchType.addItem(gettext("Authors"),
                                QtCore.QVariant(logmodel.FilterAuthorRole))
        self.searchType.addItem(gettext("Revision IDs"),
                                QtCore.QVariant(logmodel.FilterIdRole))
        self.searchType.addItem(gettext("Revision Numbers"),
                                QtCore.QVariant(logmodel.FilterRevnoRole))
        searchbox.addWidget(self.searchType)
        self.connect(self.searchType,
                     QtCore.SIGNAL("currentIndexChanged(int)"),
                     self.updateSearchType)

        logbox.addLayout(searchbox)

        self.changesList = QtGui.QTreeView()
        self.changesList.setContextMenuPolicy(QtCore.Qt.CustomContextMenu)
        self.changesList.setModel(self.changesProxyModel)
        self.changesList.setSelectionMode(QtGui.QAbstractItemView.ContiguousSelection)
        self.changesList.setUniformRowHeights(True)
        self.changesList.setAllColumnsShowFocus(True)
        self.changesList.setRootIsDecorated (False)
        self.changesList.setVerticalScrollBarPolicy(QtCore.Qt.ScrollBarAlwaysOn)
        header = self.changesList.header()
        header.setStretchLastSection(False)
        header.setResizeMode(logmodel.COL_REV, QtGui.QHeaderView.Interactive)
        header.setResizeMode(logmodel.COL_MESSAGE, QtGui.QHeaderView.Stretch)
        header.setResizeMode(logmodel.COL_DATE, QtGui.QHeaderView.Interactive)
        header.setResizeMode(logmodel.COL_AUTHOR, QtGui.QHeaderView.Interactive)
        header.resizeSection(logmodel.COL_REV, 70)
        header.resizeSection(logmodel.COL_DATE, 100)
        header.resizeSection(logmodel.COL_AUTHOR, 150)

        logbox.addWidget(self.changesList)

        self.current_rev = None
        self.connect(self.changesList.selectionModel(),
                     QtCore.SIGNAL("selectionChanged(QItemSelection, QItemSelection)"),
                     self.update_selection)
        self.connect(self.changesList,
                     QtCore.SIGNAL("doubleClicked(QModelIndex)"),
                     self.show_differences)
        self.connect(self.changesList,
                     QtCore.SIGNAL("customContextMenuRequested(QPoint)"),
                     self.show_context_menu)
        #self.connect(self.changesList,
        #             QtCore.SIGNAL("clicked (QModelIndex)"),
        #             self.changesList_clicked)
        self.changesList.mouseReleaseEvent  = self.changesList_mouseReleaseEvent
        self.changesList.keyPressEvent  = self.changesList_keyPressEvent
        
        self.changesList.setItemDelegateForColumn(logmodel.COL_MESSAGE,
                                                  GraphTagsBugsItemDelegate(self))

        self.last_item = None
        #self.merge_stack = [self.changesModel.invisibleRootItem()]

        self.message = QtGui.QTextDocument()
        self.message_browser = RevisionMessageBrowser()
        self.message_browser.setDocument(self.message)
        self.connect(self.message_browser,
                     QtCore.SIGNAL("anchorClicked(QUrl)"),
                     self.link_clicked)

        self.fileList = QtGui.QListWidget()
        self.connect(self.fileList,
                     QtCore.SIGNAL("doubleClicked(QModelIndex)"),
                     self.show_file_differences)

        hsplitter = QtGui.QSplitter(QtCore.Qt.Horizontal)
        hsplitter.addWidget(self.message_browser)
        hsplitter.addWidget(self.fileList)
        hsplitter.setStretchFactor(0, 3)
        hsplitter.setStretchFactor(1, 1)

        splitter = QtGui.QSplitter(QtCore.Qt.Vertical)
        splitter.addWidget(logwidget)
        splitter.addWidget(hsplitter)
        splitter.setStretchFactor(0, 5)
        splitter.setStretchFactor(1, 3)

        buttonbox = self.create_button_box(BTN_CLOSE)

        self.diffbutton = QtGui.QPushButton(gettext('Diff'),
            self.centralwidget)
        self.diffbutton.setEnabled(False)
        self.connect(self.diffbutton, QtCore.SIGNAL("clicked(bool)"), self.diff_pushed)

        self.contextMenu = QtGui.QMenu(self)
        self.contextMenu.addAction(gettext("Show tree..."), self.show_revision_tree)

        vbox = QtGui.QVBoxLayout(self.centralwidget)
        vbox.addWidget(splitter)
        hbox = QtGui.QHBoxLayout()
        hbox.addWidget(self.diffbutton)
        hbox.addWidget(buttonbox)
        vbox.addLayout(hbox)
        self.windows = []
        # set focus on search edit widget
        self.changesList.setFocus()

    def show(self):
        QBzrWindow.show(self)
        QtCore.QTimer.singleShot(1, self.load_history)

    def link_clicked(self, url):
        scheme = unicode(url.scheme())
        if scheme == 'qlog-revid':
            revision_id = unicode(url.path())
            self.changesModel.ensure_rev_visible(revision_id)
            index = self.changesModel.indexFromRevId(revision_id)
            index = self.changesProxyModel.mapFromSource(index)
            self.changesList.setCurrentIndex(index)
        else:
            open_browser(str(url.toEncoded()))


    def update_selection(self, selected, deselected):
        indexes = [index for index in self.changesList.selectedIndexes() if index.column()==0]
        if not indexes:
            self.diffbutton.setEnabled(False)
            self.message.setHtml("")
            self.fileList.clear()
        else:
            self.diffbutton.setEnabled(True)
            index = indexes[0]
            revid = str(index.data(logmodel.RevIdRole).toString())
            rev = self.changesModel.revision(revid)
            self.current_rev = rev
    
            self.message.setHtml(format_revision_html(rev, self.replace))
    
            #print children
    
            self.fileList.clear()
        
            if not hasattr(rev, 'delta'):
                # TODO move this to a thread
                self.branch.repository.lock_read()
                try:
                    rev.delta = self.branch.repository.get_deltas_for_revisions(
                        [rev]).next()
                finally:
                    self.branch.repository.unlock()
            delta = rev.delta
    
            for path, id_, kind in delta.added:
                item = QtGui.QListWidgetItem(path, self.fileList)
                item.setTextColor(QtGui.QColor("blue"))
    
            for path, id_, kind, text_modified, meta_modified in delta.modified:
                item = QtGui.QListWidgetItem(path, self.fileList)
    
            for path, id_, kind in delta.removed:
                item = QtGui.QListWidgetItem(path, self.fileList)
                item.setTextColor(QtGui.QColor("red"))
    
            for (oldpath, newpath, id_, kind,
                text_modified, meta_modified) in delta.renamed:
                item = QtGui.QListWidgetItem("%s => %s" % (oldpath, newpath), self.fileList)
                item.setData(PathRole, QtCore.QVariant(newpath))
                item.setTextColor(QtGui.QColor("purple"))

    def show_diff_window(self, rev1, rev2, specific_files=None):
        self.branch.repository.lock_read()
        try:
            self._show_diff_window(rev1, rev2, specific_files)
        finally:
            self.branch.repository.unlock()

    def _show_diff_window(self, rev1, rev2, specific_files=None):
        # repository should be locked
        if not rev2.parent_ids:
            revs = [rev1.revision_id]
            tree = self.branch.repository.revision_tree(rev1.revision_id)
            old_tree = self.branch.repository.revision_tree(None)
        else:
            revs = [rev1.revision_id, rev2.parent_ids[0]]
            tree, old_tree = self.branch.repository.revision_trees(revs)
        window = DiffWindow(old_tree, tree, custom_title="..".join(revs),
                            branch=self.branch, specific_files=specific_files)
        window.show()
        self.windows.append(window)

    def show_differences(self, index):
        """Show differences of a single revision"""
        revid = str(index.data(logmodel.RevIdRole).toString())
        rev = self.changesModel.revision(revid)
        self.show_diff_window(rev, rev)

    def show_file_differences(self, index):
        """Show differences of a specific file in a single revision"""
        item = self.fileList.itemFromIndex(index)
        if item and self.current_rev:
            path = item.data(PathRole).toString()
            if path.isNull():
                path = item.text()
            rev = self.current_rev
            self.show_diff_window(rev, rev, [unicode(path)])

    def diff_pushed(self, checked):
        """Show differences of the selected range or of a single revision"""
        indexes = [index for index in self.changesList.selectedIndexes() if index.column()==0]
        if not indexes:
            # the list is empty
            return
        revid1 = str(indexes[0].data(logmodel.RevIdRole).toString())
        rev1 = self.changesModel.revision(revid1)
        revid2 = str(indexes[-1].data(logmodel.RevIdRole).toString())
        rev2 = self.changesModel.revision(revid2)
        self.show_diff_window(rev1, rev2)

    def load_history(self):
        """Load branch history."""
        self.changesModel.loadBranch(self.branch, specific_fileid = self.specific_fileid)

    def update_search(self):
        # TODO in_paths = self.search_in_paths.isChecked()
        role = self.searchType.itemData(self.searchType.currentIndex()).toInt()[0]
        search_text = self.search_edit.text()
        search_mode = not role == logmodel.FilterIdRole and \
                      not role == logmodel.FilterRevnoRole and \
                      not role == logmodel.FilterSearchRole and \
                      search_text.length() > 0
        self.changesModel.set_search_mode(search_mode)
        if role == logmodel.FilterIdRole:
            self.changesProxyModel.clearSearch()
            search_text = str(search_text)
            if self.changesModel.has_rev_id(search_text):
                self.changesModel.ensure_rev_visible(search_text)
                index = self.changesModel.indexFromRevId(search_text)
                index = self.changesProxyModel.mapFromSource(index)
                self.changesList.setCurrentIndex(index)
        elif role == logmodel.FilterRevnoRole:
            self.changesProxyModel.clearSearch()
            try:
                revno = tuple((int(number) for number in str(search_text).split('.')))
            except ValueError:
                revno = ()
                # Not sure what to do if there is an error. Nothing for now
            revid = self.changesModel.revid_from_revno(revno)
            if revid:
                self.changesModel.ensure_rev_visible(revid)
                index = self.changesModel.indexFromRevId(revid)
                index = self.changesProxyModel.mapFromSource(index)
                self.changesList.setCurrentIndex(index)
        else:
            self.changesProxyModel.setFilter(self.search_edit.text(), role)
    
    def closeEvent (self, QCloseEvent):
        self.changesModel.closing = True
        
    def updateSearchType(self, index=None):
        self.update_search()

    def set_search_timer(self):
        self.search_timer.start(200)

    def show_revision_tree(self):
        from bzrlib.plugins.qbzr.lib.browse import BrowseWindow
        rev = self.current_rev
        window = BrowseWindow(self.branch, revision_id=rev.revision_id,
                              revision_spec=rev.revno, parent=self)
        window.show()
        self.windows.append(window)

    def show_context_menu(self, pos):
        index = self.changesList.indexAt(pos)
        revid = str(index.data(logmodel.RevIdRole).toString())
        rev = self.changesModel.revision(revid)
        #print index, item, rev
        self.contextMenu.popup(self.changesList.viewport().mapToGlobal(pos))
    
    def changesList_mouseReleaseEvent (self, e):
        if e.button() & QtCore.Qt.LeftButton:
            pos = e.pos()
            index = self.changesList.indexAt(pos)
            rect = self.changesList.visualRect(index)
            boxsize = rect.height()
            node = index.data(logmodel.GraphNodeRole).toList()
            if len(node)>0:
                node_column = node[0].toInt()[0]
                twistyRect = QtCore.QRect (rect.x() + boxsize * node_column,
                                           rect.y() ,
                                           boxsize,
                                           boxsize)
                if twistyRect.contains(pos):
                    e.accept ()
                    twisty_state = index.data(logmodel.GraphTwistyStateRole)
                    if twisty_state.isValid():
                        revision_id = str(index.data(logmodel.RevIdRole).toString())
                        self.changesModel.colapse_expand_rev(revision_id, not twisty_state.toBool())
        QtGui.QTreeView.mouseReleaseEvent(self.changesList, e)
    
    def changesList_keyPressEvent (self, e):
        if e.key() == QtCore.Qt.Key_Left or e.key() == QtCore.Qt.Key_Right:
            e.accept()
            indexes = [index for index in self.changesList.selectedIndexes() if index.column()==0]
            if not indexes:
                return
            index = indexes[0]
            revision_id = str(index.data(logmodel.RevIdRole).toString())
            twisty_state = index.data(logmodel.GraphTwistyStateRole)
            if e.key() == QtCore.Qt.Key_Right \
                    and twisty_state.isValid() \
                    and not twisty_state.toBool():
                self.changesModel.colapse_expand_rev(revision_id, True)
            if e.key() == QtCore.Qt.Key_Left:
                if twisty_state.isValid() and twisty_state.toBool():
                    self.changesModel.colapse_expand_rev(revision_id, False)
                else:
                    #find merge of child branch
                    revision_id = self.changesModel.findChildBranchMergeRevision(revision_id)
                    if revision_id is None:
                        return
            newindex = self.changesModel.indexFromRevId(revision_id)
            newindex = self.changesProxyModel.mapFromSource(newindex)
            self.changesList.setCurrentIndex(newindex)
        else:
            QtGui.QTreeView.keyPressEvent(self.changesList, e)
