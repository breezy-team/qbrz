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

import sys
import re
from PyQt4 import QtCore, QtGui
from time import (strftime, localtime)
from bzrlib import bugtracker, lazy_regex
from bzrlib.log import LogFormatter, show_log
from bzrlib.revision import NULL_REVISION
from bzrlib.plugins.qbzr.lib.linegraph import linegraph
from bzrlib.plugins.qbzr.lib.diff import DiffWindow
from bzrlib.plugins.qbzr.lib.i18n import gettext
from bzrlib.plugins.qbzr.lib.util import (
    BTN_CLOSE,
    QBzrWindow,
    extract_name,
    format_revision_html,
    format_timestamp,
    htmlize,
    open_browser,
    RevisionMessageBrowser,
    )


TagsRole = QtCore.Qt.UserRole + 1
BugIdsRole = QtCore.Qt.UserRole + 2
GraphNodeRole = QtCore.Qt.UserRole + 3
GraphLinesInRole = QtCore.Qt.UserRole + 4
GraphLinesOutRole = QtCore.Qt.UserRole + 5

FilterIdRole = QtCore.Qt.UserRole + 100
FilterMessageRole = QtCore.Qt.UserRole + 101
FilterAuthorRole = QtCore.Qt.UserRole + 102
FilterRevnoRole = QtCore.Qt.UserRole + 103

COL_REV = 0
COL_GRAPH = 1
COL_DATE = 2
COL_AUTHOR = 3
COL_MESSAGE = 4

PathRole = QtCore.Qt.UserRole + 1


_bug_id_re = lazy_regex.lazy_compile(r'(?:bugs/|ticket/|show_bug\.cgi\?id=)(\d+)(?:\b|$)')

def get_bug_id(branch, bug_url):
    match = _bug_id_re.search(bug_url)
    if match:
        return match.group(1)
    return None

class GraphItemDelegate(QtGui.QItemDelegate):
    
    def get_colour(self, colour, back):
        """Set the context source colour.

        Picks a distinct colour based on an internal wheel; the bg
        parameter provides the value that should be assigned to the 'zero'
        colours and the fg parameter provides the multiplier that should be
        applied to the foreground colours.
        """

        qcolor = QtGui.QColor()
        if colour == 0:
            if back:
                qcolor.setHsvF(0,0,0.5)
            else:
                qcolor.setHsvF(0,0,0)
        else:
            h = float(colour % 6) / 6
            if back:
                qcolor.setHsvF(h,0.4,1)
            else:
                qcolor.setHsvF(h,0.8,1)
        
        return qcolor
    
    def paint(self, painter, option, index):        
        self.node = index.data(GraphNodeRole).toList()
        self.linesIn = index.data(GraphLinesInRole).toList()
        self.linesOut = index.data(GraphLinesOutRole).toList()
        QtGui.QItemDelegate.paint(self, painter, option, index)
    
    def render_line(self, painter, pen, rect, boxsize, mid, height, start, end, colour):
        pen.setColor(self.get_colour(colour,False))
        painter.setPen(pen)
        if start is -1:
            x = rect.x() + boxsize * end + boxsize / 2
            painter.drawPoint(QtCore.QPointF (x, mid + height / 3)) 
            painter.drawPoint(QtCore.QPointF (x, mid + height / 6)) 
            
        elif end is -1:
            x = rect.x() + boxsize * end + boxsize / 2
            painter.drawPoint(QtCore.QPointF (x, mid - height / 3)) 
            painter.drawPoint(QtCore.QPointF (x, mid - height / 6)) 

        else:
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


    def drawDisplay(self, painter, option, rect, text):
        painter.save()
        try:
            painter.setRenderHint(QtGui.QPainter.Antialiasing)
            
            boxsize = rect.height()
            dotsize = 0.6
            pen = QtGui.QPen()
            pen.setWidth(boxsize*0.15)
            
            # Draw lines into the cell
            for line in self.linesIn:
                start, end, colour = [linei.toInt()[0] for linei in line.toList()]
                self.render_line (painter, pen, rect, boxsize,
                                  rect.y(), boxsize,
                                  start, end, colour)
    
            # Draw lines out of the cell
            for line in self.linesOut:
                start, end, colour = [linei.toInt()[0] for linei in line.toList()]
                self.render_line (painter, pen, rect,boxsize,
                                  rect.y() + boxsize, boxsize,
                                  start, end, colour)
            
            # Draw the revision node in the right column
            colour = self.node[1].toInt()[0]
            column = self.node[0].toInt()[0]
            pen.setColor(self.get_colour(colour,False))
            painter.setPen(pen)
            painter.setBrush(QtGui.QBrush(self.get_colour(colour,True)))
            painter.drawEllipse(
                QtCore.QRectF(option.rect.x() + (boxsize * (1 - dotsize) / 2) + boxsize * column,
                             option.rect.y() + (boxsize * (1 - dotsize) / 2),
                             boxsize * dotsize, boxsize * dotsize))
        finally:
            painter.restore()

class TagsBugsItemDelegate(QtGui.QItemDelegate):

    _tagColor = QtGui.QColor(255, 255, 170)
    _tagColorBorder = QtGui.QColor(255, 238, 0)

    _bugColor = QtGui.QColor(255, 188, 188)
    _bugColorBorder = QtGui.QColor(255, 79, 79)


    def paint(self, painter, option, index):
        self.labels = []
        # collect tag names
        for tag in index.data(TagsRole).toList():
            self.labels.append(
                (tag.toString(), self._tagColor,
                 self._tagColorBorder))
        # collect bug ids
        for bug in index.data(BugIdsRole).toList():
            self.labels.append(
                (bug.toString(), self._bugColor,
                 self._bugColorBorder))
        QtGui.QItemDelegate.paint(self, painter, option, index)

    def drawDisplay(self, painter, option, rect, text):
        if not self.labels:
            return QtGui.QItemDelegate.drawDisplay(self, painter, option, rect, text)

        painter.save()
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

        painter.setFont(option.font)
        if (option.state & QtGui.QStyle.State_Selected
            and option.state & QtGui.QStyle.State_Active):
            painter.setPen(option.palette.highlightedText().color())
        else:
            painter.setPen(option.palette.text().color())
        painter.drawText(rect.left() + x + 2, rect.bottom() - option.fontMetrics.descent(), text)
        painter.restore()


class TreeFilterProxyModel(QtGui.QSortFilterProxyModel):

    def __init__(self):
        QtGui.QSortFilterProxyModel.__init__(self)
        self._filterCache = {}

    def filterAcceptsRow(self, sourceRow, sourceParent):
        # TODO this seriously needs to be in C++

        filterRegExp = self.filterRegExp()
        sourceModel = self.sourceModel()
        #if filterRegExp != self._filterCacheRegExp:
        #    print "clearing cache"
        #    self._filterCache = {}

        if filterRegExp.isEmpty():
            return True

        index = sourceModel.index(sourceRow, 0, sourceParent)
        if not index.isValid():
            return True

        filterId = sourceModel.data(index, FilterIdRole).toString()
        accepts = self._filterCache.get(filterId)
        if accepts is not None:
            return accepts

        key = sourceModel.data(index, self.filterRole()).toString()
        if key.contains(filterRegExp):
            self._filterCache[filterId] = True
            return True

        if sourceModel.hasChildren(index):
            childRow = 0
            while True:
                child = index.child(childRow, index.column())
                if not child.isValid():
                    break
                if self.filterAcceptsRow(childRow, index):
                    self._filterCache[filterId] = True
                    return True
                childRow += 1

        self._filterCache[filterId] = False
        return False


try:
    from bzrlib.plugins.qbzr.lib._ext import (
        TreeFilterProxyModel,
        LogWidgetDelegate,
        )
except ImportError:
    pass

class TreeModel(QtCore.QAbstractTableModel):
    def __init__(self, parent=None):
        QtCore.QAbstractTableModel.__init__(self, parent)
        
        self.horizontalHeaderLabels = [gettext("Rev"),
                                       gettext("Graph"),
                                       gettext("Date"),
                                       gettext("Author"),
                                       gettext("Message"),
                                       ]
        
        self.linegraphdata = []
        self.index = {}
        self.columns_len = 0
        self.revisions = {}
        self.tags = {}

    def loadBranch(self, branch, start_revs = None, maxnum = None,
                   broken_line_length = 32, graph_data = True,
                   mainline_only = False):
        self.branch = branch
        branch.lock_read()
        self.emit(QtCore.SIGNAL("layoutAboutToBeChanged()"))
        self.revisions = {}
        try:
            if start_revs is None:
                start_revs = [branch.last_revision()]
            (self.linegraphdata, self.index, self.columns_len) = linegraph(branch.repository,
                                                            start_revs,
                                                            maxnum, 
                                                            broken_line_length,
                                                            graph_data,
                                                            mainline_only)
            self.tags = branch.tags.get_reverse_tag_dict()
        except:
            self.linegraphdata = []
            self.index = {}
            self.columns_len = 0
            self.tags = {}
        finally:
            self.emit(QtCore.SIGNAL("layoutChanged()"))
            branch.unlock

    def columnCount(self, parent):
        if parent.isValid():
            return 0
        return len(self.horizontalHeaderLabels)

    def rowCount(self, parent):
        if parent.isValid():
            return 0
        return len(self.linegraphdata)
    
    def linesToQVariant(self,lines):
        qlines = []
        for start, end, colour in lines:
            if start is None: start = -1
            if end is None: end = -1
            qlines.append(QtCore.QVariant([QtCore.QVariant(start),
                                           QtCore.QVariant(end),
                                           QtCore.QVariant(colour)]))
        return QtCore.QVariant(qlines)

    def data(self, index, role):
        if not index.isValid():
            return QtCore.QVariant()
        
        (revid, node, lines, parents, children, revno_sequence) = \
            self.linegraphdata[index.row()]
        
        if role == QtCore.Qt.DisplayRole and index.column() == COL_REV:
            revnos = ".".join(["%d" % (revno)
                                      for revno in revno_sequence])
            return QtCore.QVariant(revnos)
        if role == TagsRole:
            tags = []
            if revid in self.tags:
                tags = self.tags[revid]
            return QtCore.QVariant(tags)
        if role == GraphNodeRole:
            return QtCore.QVariant([QtCore.QVariant(nodei) for nodei in node])
        if role == GraphLinesOutRole:
            return self.linesToQVariant(lines)
        if role == GraphLinesInRole:
            if index.row()>0:
                return self.linesToQVariant(self.linegraphdata[index.row()-1][2])
            return QtCore.QVariant([])
        
        #Everything from here foward need to have the revision loaded.
        if not revid or revid == NULL_REVISION:
            return QtCore.QVariant()
        if revid not in self.revisions:
            revision = self.branch.repository.get_revisions([revid])[0]
            self.revisions[revid] = revision
        else:
            revision = self.revisions[revid]
        
        if role == QtCore.Qt.DisplayRole and index.column() == COL_DATE:
            return QtCore.QVariant(strftime("%Y-%m-%d %H:%M",
                                            localtime(revision.timestamp)))
        if role == QtCore.Qt.DisplayRole and index.column() == COL_AUTHOR:
            return QtCore.QVariant(extract_name(revision.committer))
        if role == QtCore.Qt.DisplayRole and index.column() == COL_MESSAGE:
            return QtCore.QVariant(revision.get_summary())
        if role == BugIdsRole:
            bugtext = gettext("bug #%s")
            bugs = []
            for bug in revision.properties.get('bugs', '').split('\n'):
                if bug:
                    url, status = bug.split(' ')
                    bug_id = get_bug_id(self.branch, url)
                    if bug_id:
                        bugs.append(bugtext % bug_id)
            return QtCore.QVariant(bugs)

        
        #return QtCore.QVariant(item.data(index.column()))
        return QtCore.QVariant()

    def flags(self, index):
        if not index.isValid():
            return QtCore.Qt.ItemIsEnabled

        return QtCore.Qt.ItemIsEnabled | QtCore.Qt.ItemIsSelectable

    def headerData(self, section, orientation, role):
        if orientation == QtCore.Qt.Horizontal and role == QtCore.Qt.DisplayRole:
            return QtCore.QVariant(self.horizontalHeaderLabels[section])

        return QtCore.QVariant()



class LogWindow(QBzrWindow):

    def __init__(self, branch, location, specific_fileid, replace=None, parent=None):
        title = [gettext("Log")]
        if location:
            title.append(location)
        QBzrWindow.__init__(self, title, parent)
        self.restoreSize("log", (710, 580))
        self.specific_fileid = specific_fileid

        self.replace = replace
        self.item_to_rev = {}
        self.revisions = {}

        self.changesModel = TreeModel()

        self.changesProxyModel = TreeFilterProxyModel()
        self.changesProxyModel.setSourceModel(self.changesModel)
        self.changesProxyModel.setFilterCaseSensitivity(QtCore.Qt.CaseInsensitive)
        self.changesProxyModel.setFilterRole(FilterMessageRole)

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
        self.searchType.addItem(gettext("Messages"),
                                QtCore.QVariant(FilterMessageRole))
        self.searchType.addItem(gettext("Authors"),
                                QtCore.QVariant(FilterAuthorRole))
        self.searchType.addItem(gettext("Revision IDs"),
                                QtCore.QVariant(FilterIdRole))
        self.searchType.addItem(gettext("Revision Numbers"),
                                QtCore.QVariant(FilterRevnoRole))
        searchbox.addWidget(self.searchType)
        self.connect(self.searchType,
                     QtCore.SIGNAL("currentIndexChanged(int)"),
                     self.updateSearchType)

        #self.search_in_messages = QtGui.QRadioButton(gettext("Messages"))
        #self.connect(self.search_in_messages, QtCore.SIGNAL("toggled(bool)"),
        #             self.update_search_type)
        #self.search_in_paths = QtGui.QRadioButton(gettext("Paths"))
        #self.search_in_paths.setEnabled(False)
        #self.connect(self.search_in_paths, QtCore.SIGNAL("toggled(bool)"),
        #             self.update_search_type)
        #searchbox.addWidget(self.search_in_messages)
        #searchbox.addWidget(self.search_in_paths)
        #self.search_in_messages.setChecked(True)

        logbox.addLayout(searchbox)

        self.changesList = QtGui.QTreeView()
        self.changesList.setContextMenuPolicy(QtCore.Qt.CustomContextMenu)
        self.changesList.setModel(self.changesProxyModel)
        self.changesList.setSelectionMode(QtGui.QAbstractItemView.ContiguousSelection)
        self.changesList.setUniformRowHeights(True)
        header = self.changesList.header()
        header.resizeSection(0, 70)
        header.resizeSection(1, 110)
        header.resizeSection(2, 150)
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

        self.branch = branch

        self.changesList.setItemDelegateForColumn(COL_GRAPH,
                                                  GraphItemDelegate(self))
        self.changesList.setItemDelegateForColumn(COL_MESSAGE,
                                                  TagsBugsItemDelegate(self))

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

    def show(self):
        QBzrWindow.show(self)
        QtCore.QTimer.singleShot(5, self.load_history)

    def link_clicked(self, url):
        scheme = unicode(url.scheme())
        if scheme == 'qlog-revid':
            revision_id = unicode(url.path())
            for item, rev in self.item_to_rev.iteritems():
                if rev.revision_id == revision_id:
                    index = self.changesProxyModel.mapFromSource(
                        self.changesModel.indexFromItem(item))
                    self.changesList.setCurrentIndex(index)
                    break
        else:
            open_browser(str(url.toEncoded()))

    def selected_items(self):
        items = []
        for index in self.changesList.selectedIndexes():
            index = self.changesProxyModel.mapToSource(index)
            item = self.changesModel.itemFromIndex(index)
            if item.column() == 0:
                items.append(item)
        return items

    def update_selection(self, selected, deselected):
        items = self.selected_items()
        if not items:
            return
        self.diffbutton.setEnabled(True)
        item = items[0]
        rev = self.item_to_rev[item]
        self.current_rev = rev

        try:
            if not hasattr(rev, 'parents'):
                rev.parents = [self.revisions[i] for i in rev.parent_ids]
        except KeyError:
            pass

        try:
            if not hasattr(rev, 'children'):
                rev.children = [
                    child for child in self.revisions.itervalues()
                    if rev.revision_id in child.parent_ids]
        except KeyError:
            pass

        self.message.setHtml(format_revision_html(rev, self.replace))

        #print children

        self.fileList.clear()

        if not rev.delta:
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
        index = self.changesProxyModel.mapToSource(index)
        item = self.changesModel.itemFromIndex(index)
        rev = self.item_to_rev[item]
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
        items = self.selected_items()
        if not items:
            # the list is empty
            return
        rev1 = self.item_to_rev[items[0]]
        rev2 = self.item_to_rev[items[-1]]
        self.show_diff_window(rev1, rev2)

    def add_log_entry(self, revision):
        """Add loaded entries to the list."""

        # Use flat list for a single-file log
        if self.specific_fileid:
            merge_depth = 0
        else:
            merge_depth = revision.merge_depth
        if merge_depth > len(self.merge_stack) - 1:
            self.merge_stack.append(self.last_item)
        elif merge_depth < len(self.merge_stack) - 1:
            self.merge_stack.pop()

        rev = revision.rev
        author = rev.properties.get('author', rev.committer)

        revno = str(revision.revno)
        item1 = QtGui.QStandardItem(revno)
        item1.setFlags(QtCore.Qt.ItemIsSelectable | QtCore.Qt.ItemIsEnabled)
        item1.setData(QtCore.QVariant(rev.message), FilterMessageRole)
        item1.setData(QtCore.QVariant(rev.committer + author), FilterAuthorRole)
        item1.setData(QtCore.QVariant(rev.revision_id), FilterIdRole)
        item1.setData(QtCore.QVariant(revno), FilterRevnoRole)
        item2 = QtGui.QStandardItem(format_timestamp(rev.timestamp))
        item2.setFlags(QtCore.Qt.ItemIsSelectable | QtCore.Qt.ItemIsEnabled)

        item3 = QtGui.QStandardItem(extract_name(author))
        item3.setFlags(QtCore.Qt.ItemIsSelectable | QtCore.Qt.ItemIsEnabled)
        item4 = QtGui.QStandardItem(rev.get_summary())
        item4.setFlags(QtCore.Qt.ItemIsSelectable | QtCore.Qt.ItemIsEnabled)

        tags = getattr(revision, 'tags', None)
        if tags:
            tags.sort()
            i = TagNameRole
            for tag in tags:
                item4.setData(QtCore.QVariant(tag), i)
                i += 1

        #get_bug_id = getattr(bugtracker, 'get_bug_id', None)
        if get_bug_id:
            i = BugIdRole
            bugtext = gettext("bug #%s")
            for bug in rev.properties.get('bugs', '').split('\n'):
                if bug:
                    url, status = bug.split(' ')
                    bug_id = get_bug_id(self.branch, url)
                    if bug_id:
                        item4.setData(QtCore.QVariant(bugtext % bug_id), i)
                        i += 1

        self.merge_stack[-1].appendRow([item1, item2, item3, item4])

        rev.delta = None
        rev.revno = revision.revno
        rev.tags = tags
        self.item_to_rev[item1] = rev
        self.item_to_rev[item2] = rev
        self.item_to_rev[item3] = rev
        self.item_to_rev[item4] = rev
        self.last_item = item1
        self.revisions[rev.revision_id] = rev

    def load_history(self):
        """Load branch history."""
        self.changesModel.loadBranch(self.branch)

    def update_search_type(self, checked):
        if checked:
            self.update_search()

    def update_search(self):
        # TODO in_paths = self.search_in_paths.isChecked()
        self.changesProxyModel._filterCache = {}
        self.changesProxyModel.setFilterRegExp(self.search_edit.text())

    def updateSearchType(self, index=None):
        role = self.searchType.itemData(index).toInt()[0]
        self.changesProxyModel._filterCache = {}
        self.changesProxyModel.setFilterRole(role)

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
        index = self.changesProxyModel.mapToSource(index)
        item = self.changesModel.itemFromIndex(index)
        rev = self.item_to_rev[item]
        #print index, item, rev
        self.contextMenu.popup(self.changesList.viewport().mapToGlobal(pos))
