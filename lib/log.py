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
from bzrlib import bugtracker, lazy_regex
from bzrlib.log import LogFormatter, show_log
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


TagNameRole = QtCore.Qt.UserRole + 1
BugIdRole = QtCore.Qt.UserRole + 100

FilterIdRole = QtCore.Qt.UserRole + 200
FilterMessageRole = QtCore.Qt.UserRole + 201
FilterAuthorRole = QtCore.Qt.UserRole + 202
FilterRevnoRole = QtCore.Qt.UserRole + 203

PathRole = QtCore.Qt.UserRole + 1


_bug_id_re = lazy_regex.lazy_compile(r'(?:bugs/|ticket/|show_bug\.cgi\?id=)(\d+)(?:\b|$)')

def get_bug_id(branch, bug_url):
    match = _bug_id_re.search(bug_url)
    if match:
        return match.group(1)
    return None


class LogWidgetDelegate(QtGui.QItemDelegate):

    _tagColor = QtGui.QColor(255, 255, 170)
    _tagColorBorder = QtGui.QColor(255, 238, 0)

    _bugColor = QtGui.QColor(255, 188, 188)
    _bugColorBorder = QtGui.QColor(255, 79, 79)

    def paint(self, painter, option, index):
        self.labels = []
        if index.column() == 3:
            # collect tag names
            for i in range(10):
                tag = index.data(TagNameRole + i)
                if not tag.isNull():
                    self.labels.append(
                        (tag.toString(), self._tagColor,
                         self._tagColorBorder))
                else:
                    break
            # collect bug ids
            for i in range(10):
                bug = index.data(BugIdRole + i)
                if not bug.isNull():
                    self.labels.append(
                        (bug.toString(), self._bugColor,
                         self._bugColorBorder))
                else:
                    break
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


class StopLoading(Exception): pass


class QLogFormatter(LogFormatter):

    supports_merge_revisions = True
    supports_tags = True
    supports_delta = True

    def __init__(self, parent):
        self.parent = parent
        self.items = []
        self.n = 10

    def add_items(self):
        for revision in self.items:
            self.parent.add_log_entry(revision)
        self.items = []

    def log_revision(self, revision):
        if self.parent.isHidden():
            raise StopLoading()
        self.items.append(revision)
        if len(self.items) > self.n:
            self.add_items()
            self.n = max(200, int(self.n * 1.5))
        QtCore.QCoreApplication.processEvents()


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

        self.changesModel = QtGui.QStandardItemModel()
        self.changesModel.setHorizontalHeaderLabels(
            [gettext("Rev"), gettext("Date"), gettext("Author"), gettext("Message")])

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

        self.delegate = LogWidgetDelegate(self)
        self.changesList.setItemDelegate(self.delegate)

        self.last_item = None
        self.merge_stack = [self.changesModel.invisibleRootItem()]

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
        formatter = QLogFormatter(self)
        try:
            show_log(self.branch, formatter, verbose=False,
                     specific_fileid=self.specific_fileid)
        except StopLoading:
            pass
        else:
            formatter.add_items()

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
