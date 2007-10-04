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
from bzrlib.plugins.qbzr.diff import DiffWindow
from bzrlib.plugins.qbzr.util import QBzrWindow, open_browser


TagNameRole = QtCore.Qt.UserRole + 1
BugIdRole = QtCore.Qt.UserRole + 100


_email_re = lazy_regex.lazy_compile(r'([a-z0-9_\-.+]+@[a-z0-9_\-.+]+)')
_link1_re = lazy_regex.lazy_compile(r'([\s>])(https?)://([^\s<>{}()]+[^\s.,<>{}()])')
_link2_re = lazy_regex.lazy_compile(r'(\s)www\.([a-z0-9\-]+)\.([a-z0-9\-.\~]+)((?:/[^ <>{}()\n\r]*[^., <>{}()\n\r]?)?)')


def htmlize(text):
    global _email_re, _link1_re, _link2_re
    text = text.replace('&', '&amp;').replace('<', '&lt;').replace('>', '&gt;').replace("\n", '<br />')
    text = _email_re.sub('<a href="mailto:\\1">\\1</a>', text)
    text = _link1_re.sub('\\1<a href="\\2://\\3">\\2://\\3</a>', text)
    text = _link2_re.sub('\\1<a href="http://www.\\2.\\3\\4">www.\\2.\\3\\4</a>', text)
    return text


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
                        ("bug #" + bug.toString(), self._bugColor,
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
        if option.state & QtGui.QStyle.State_Selected:
            painter.setPen(option.palette.highlightedText().color())
        else:
            painter.setPen(option.palette.text().color())
        painter.drawText(rect.left() + x + 2, rect.bottom() - option.fontMetrics.descent(), text)
        painter.restore()


class LogMessageBrowser(QtGui.QTextBrowser):

    def setSource(self, uri):
        pass


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


class LogWindow(QBzrWindow):

    def __init__(self, branch, location, specific_fileid, replace=None, parent=None):
        title = ["Log"]
        if location:
            title.append(location)
        QBzrWindow.__init__(self, title, (710, 580), parent)
        self.specific_fileid = specific_fileid

        self.replace = replace

        splitter = QtGui.QSplitter(QtCore.Qt.Vertical)

        #groupBox = QtGui.QGroupBox(u"Log", splitter)
        #splitter.addWidget(groupBox)

        self.changesList = QtGui.QTreeWidget(splitter)
        self.changesList.setHeaderLabels([u"Rev", u"Date", u"Author", u"Message"])
        self.changesList.setSelectionMode(QtGui.QAbstractItemView.ContiguousSelection);
        header = self.changesList.header()
        header.resizeSection(0, 50)
        header.resizeSection(1, 110)
        header.resizeSection(2, 190)
        self.connect(self.changesList, QtCore.SIGNAL("itemSelectionChanged()"), self.update_selection)

        self.connect(self.changesList,
                     QtCore.SIGNAL("itemDoubleClicked(QTreeWidgetItem *, int)"),
                     self.show_differences)

        splitter.addWidget(self.changesList)
        #vbox1 = QtGui.QVBoxLayout(groupBox)
        #vbox1.addWidget(self.changesList)

        self.branch = branch
        self.item_to_rev = {}

        delegate = LogWidgetDelegate(self)
        self.changesList.setItemDelegate(delegate)

        self.last_item = None
        self.merge_stack = [self.changesList]

        #groupBox = QtGui.QGroupBox(u"Details", splitter)

        splitter.setStretchFactor(0, 5)
        splitter.setStretchFactor(1, 1)

        #hbox = QtGui.QHBoxLayout(groupBox)
        hsplitter = QtGui.QSplitter(QtCore.Qt.Horizontal)
        #gridLayout.setColumnStretch(0, 0)
        #gridLayout.setColumnStretch(1, 3)
        #gridLayout.setColumnStretch(2, 1)

        #gridLayout.addWidget(QtGui.QLabel(u"Revision:", groupBox), 0, 0)
        #self.revisionEdit = QtGui.QLineEdit(u"", groupBox)
        #self.revisionEdit.setReadOnly(True)
        #gridLayout.addWidget(self.revisionEdit, 0, 1)

        #gridLayout.addWidget(QtGui.QLabel(u"Parents:", groupBox), 1, 0)
        #self.parentsEdit = QtGui.QLineEdit(u"", groupBox)
        #self.parentsEdit.setReadOnly(True)
        #gridLayout.addWidget(self.parentsEdit, 1, 1)

        self.message = QtGui.QTextDocument()
        self.message_browser = LogMessageBrowser(hsplitter)
        self.message_browser.setDocument(self.message)
        self.connect(self.message_browser, QtCore.SIGNAL("anchorClicked(QUrl)"), self.link_clicked)
        hsplitter.addWidget(self.message_browser)

        self.fileList = QtGui.QListWidget(hsplitter)
        hsplitter.addWidget(self.fileList)

        hsplitter.setStretchFactor(0, 3)
        hsplitter.setStretchFactor(1, 1)

        splitter.addWidget(hsplitter)

        buttonbox = QtGui.QDialogButtonBox(
            QtGui.QDialogButtonBox.StandardButtons(
                QtGui.QDialogButtonBox.Close),
            QtCore.Qt.Horizontal,
            self.centralwidget)
        self.connect(buttonbox, QtCore.SIGNAL("rejected()"), self.close)

        self.diffbutton = QtGui.QPushButton(u'Diff',self.centralwidget)
        self.diffbutton.setEnabled(False)
        self.connect(self.diffbutton, QtCore.SIGNAL("clicked(bool)"), self.diff_pushed)

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

    def closeEvent(self, event):
        for window in self.windows:
            window.close()
        event.accept()

    def diff_pushed(self, checked):
        """Show differences of the selected range or of a single revision"""
        items = self.changesList.selectedItems()
        if len(items) == 0:
            # the list is empty
            return
        elif len(items) == 1:
            item = items[0]
            rev = self.item_to_rev[item]
            if not rev.parent_ids:
                tree = self.branch.repository.revision_tree(rev.revision_id)
                old_tree = self.branch.repository.revision_tree(None)
            else:
                tree, old_tree = self.branch.repository.revision_trees([rev.revision_id, rev.parent_ids[0]])
        else:
            rev = self.item_to_rev[items[0]]
            revto = self.item_to_rev[items[-1]]
            tree = self.branch.repository.revision_tree(rev.revision_id)
            old_tree = self.branch.repository.revision_tree(revto.revision_id)

        window = DiffWindow(old_tree, tree, custom_title=rev.revision_id, branch=self.branch)
        window.show()
        self.windows.append(window)

    def link_clicked(self, url):
        scheme = unicode(url.scheme())
        if scheme == 'qlog-revid':
            revision_id = unicode(url.path())
            for item, rev in self.item_to_rev.iteritems():
                if rev.revision_id == revision_id:
                    self.changesList.setCurrentItem(item)
                    break
        else:
            open_browser(str(url.toEncoded()))

    def update_selection(self):
        items = self.changesList.selectedItems()
        if not items:
            return
        self.diffbutton.setEnabled(True)
        item = items[0]
        rev = self.item_to_rev[item]

        text = []
        text.append("<b>Revision:</b> " + rev.revision_id)

        parent_ids = rev.parent_ids
        if parent_ids:
            text.append("<b>Parent revisions:</b> " + ", ".join('<a href="qlog-revid:%s">%s</a>' % (a, a) for a in parent_ids))

        text.append('<b>Committer:</b> ' + htmlize(rev.committer))
        author = rev.properties.get('author')
        if author:
            text.append('<b>Author:</b> ' + htmlize(author))

        branch_nick = rev.properties.get('branch-nick')
        if branch_nick:
            text.append('<b>Branch nick:</b> ' + branch_nick)

        tags = rev.tags
        if tags:
            text.append('<b>Tags:</b> ' + ', '.join(tags))

        bugs = []
        for bug in rev.properties.get('bugs', '').split('\n'):
            if bug:
                url, status = bug.split(' ')
                bugs.append('<a href="%(url)s">%(url)s</a> %(status)s' % (
                    dict(url=url, status=status)))
        if bugs:
            text.append('<b>Bugs:</b> ' + ', '.join(bugs))

        message = htmlize(rev.message)
        if self.replace:
            for search, replace in self.replace:
                message = re.sub(search, replace, message)
        text.append("")
        text.append(message)

        self.message.setHtml("<br />".join(text))

        self.fileList.clear()

        if not rev.delta:
            # TODO move this to a thread
            rev.delta = \
                self.branch.repository.get_deltas_for_revisions([rev]).next()
        delta = rev.delta

        for path, _, _ in delta.added:
            item = QtGui.QListWidgetItem(path, self.fileList)
            item.setTextColor(QtGui.QColor("blue"))

        for path, _, _, _, _ in delta.modified:
            item = QtGui.QListWidgetItem(path, self.fileList)

        for path, _, _ in delta.removed:
            item = QtGui.QListWidgetItem(path, self.fileList)
            item.setTextColor(QtGui.QColor("red"))

        for oldpath, newpath, _, _, _, _ in delta.renamed:
            item = QtGui.QListWidgetItem("%s => %s" % (oldpath, newpath), self.fileList)
            item.setTextColor(QtGui.QColor("purple"))

    def show_differences(self, item, column):
        """Show differences between the working copy and the last revision."""
        rev = self.item_to_rev[item]
        if not rev.parent_ids:
            tree = self.branch.repository.revision_tree(rev.revision_id)
            old_tree = self.branch.repository.revision_tree(None)
        else:
            tree, old_tree = self.branch.repository.revision_trees([rev.revision_id, rev.parent_ids[0]])
        window = DiffWindow(old_tree, tree, custom_title=rev.revision_id, branch=self.branch)
        window.show()
        self.windows.append(window)

    def add_log_entry(self, revision):
        """Add loaded entries to the list."""

        merge_depth = revision.merge_depth
        if merge_depth > len(self.merge_stack) - 1:
            self.merge_stack.append(self.last_item)
        elif merge_depth < len(self.merge_stack) - 1:
            self.merge_stack.pop()

        item = QtGui.QTreeWidgetItem(self.merge_stack[-1])
        item.setText(0, str(revision.revno))
        rev = revision.rev
        date = QtCore.QDateTime()
        date.setTime_t(int(rev.timestamp))
        item.setText(1, date.toString(QtCore.Qt.LocalDate))

        author = rev.properties.get('author', rev.committer)
        item.setText(2, author)
        item.setText(3, rev.get_summary())

        tags = getattr(revision, 'tags', None)
        if tags:
            i = TagNameRole
            for tag in tags:
                item.setData(3, i, QtCore.QVariant(tag))
                i += 1

        #get_bug_id = getattr(bugtracker, 'get_bug_id', None)
        if get_bug_id:
            i = BugIdRole
            for bug in rev.properties.get('bugs', '').split('\n'):
                if bug:
                    url, status = bug.split(' ')
                    bug_id = get_bug_id(self.branch, url)
                    if bug_id:
                        item.setData(3, i, QtCore.QVariant(bug_id))
                        i += 1

        rev.delta = None
        rev.revno = revision.revno
        rev.tags = revision.tags
        self.item_to_rev[item] = rev
        self.last_item = item

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
