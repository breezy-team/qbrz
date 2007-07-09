# -*- coding: utf-8 -*-
#
# QBzr - Qt frontend to Bazaar commands
# Copyright (C) 2006 Lukáš Lalinský <lalinsky@gmail.com>
# Porions Copyright (C) 2004, 2005, 2006 by Canonical Ltd 
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
import Queue
from itertools import izip
from PyQt4 import QtCore, QtGui
from bzrlib.bzrdir import BzrDir
from bzrlib.commands import Command, register_command
from bzrlib.errors import NotVersionedError, BzrCommandError, NoSuchFile
from bzrlib.log import LogFormatter, show_log
from bzrlib.plugins.qbzr.diff import DiffWindow
from bzrlib.plugins.qbzr.util import QBzrWindow


TagNameRole = QtCore.Qt.UserRole + 1


class CustomFunctionThread(QtCore.QThread):

    def __init__(self, target, args=[], parent=None):
        QtCore.QThread.__init__(self, parent)
        self.target = target
        self.args = args

    def run(self):
        self.target(*self.args)


class LogWidgetDelegate(QtGui.QItemDelegate):

    def paint(self, painter, option, index):
        self.tag = None
        if index.column() == 3:
            tag = index.data(TagNameRole)
            if tag:
                self.tag = tag.toString()
        QtGui.QItemDelegate.paint(self, painter, option, index)

    def drawDisplay(self, painter, option, rect, text):
        if not self.tag:
            return QtGui.QItemDelegate.drawDisplay(self, painter, option, rect, text)

        tagRect = rect.adjusted(1, 1, -1, -1)
        tagFont = QtGui.QFont(option.font)
        tagFont.setPointSizeF(tagFont.pointSizeF() * 9 / 10)
        tagRect.setWidth(QtGui.QFontMetrics(tagFont).width(self.tag) + 6)

        painter.save()
        painter.fillRect(tagRect.adjusted(1, 1, -1, -1), QtGui.QColor(200, 247, 176))
        painter.setPen(QtGui.QColor(115, 191, 76))
        painter.drawRect(tagRect.adjusted(0, 0, -1, -1))
        painter.setFont(tagFont)
        painter.setPen(option.palette.text().color())
        painter.drawText(tagRect.left() + 3, tagRect.bottom() - option.fontMetrics.descent() + 1, self.tag)
        painter.setFont(option.font)
        painter.drawText(rect.left() + tagRect.width() + 5, rect.bottom() - option.fontMetrics.descent(), text)
        painter.restore()


class LogMessageBrowser(QtGui.QTextBrowser):

    def setSource(self, uri):
        pass


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

        if branch.tags.supports_tags():
            delegate = LogWidgetDelegate(self)
            self.changesList.setItemDelegate(delegate)

        self.last_item = None
        self.merge_stack = [self.changesList]
        self.connect(self, QtCore.SIGNAL("log_entry_loaded()"),
                     self.add_log_entry, QtCore.Qt.QueuedConnection)
        self.log_queue = Queue.Queue()
        self.thread = CustomFunctionThread(self.load_history, parent=self)
        self.thread.start()

        #groupBox = QtGui.QGroupBox(u"Details", splitter)

        splitter.setStretchFactor(0, 6)
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
        #self.message_browser.setOpenExternalLinks(True)
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

        vbox = QtGui.QVBoxLayout(self.centralwidget)
        vbox.addWidget(splitter)
        vbox.addWidget(buttonbox)
        self.windows = []

    def closeEvent(self, event):
        for window in self.windows:
            window.close()
        event.accept()

    def link_clicked(self, url):
        scheme = unicode(url.scheme())
        if scheme == 'qlog-revid':
            revision_id = unicode(url.path())
            for item, rev in self.item_to_rev.iteritems():
                if rev.revision_id == revision_id:
                    self.changesList.setCurrentItem(item)
                    break
        else:
            import webbrowser
            webbrowser.open(str(url.toEncoded()))

    def update_selection(self):
        item = self.changesList.selectedItems()[0]
        rev = self.item_to_rev[item]

        def htmlencode(text):
            return text.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;").replace("\n", "<br />")

        message = htmlencode(rev.message)
        message = re.sub(r"([\s>])(https?)://([^\s<>{}()]+[^\s.,<>{}()])", "\\1<a href=\"\\2://\\3\">\\2://\\3</a>", message)
        message = re.sub(r"(\s)www\.([a-z0-9\-]+)\.([a-z0-9\-.\~]+)((?:/[^ <>{}()\n\r]*[^., <>{}()\n\r]?)?)", "\\1<a href=\"http://www.\\2.\\3\\4\">www.\\2.\\3\\4</a>", message)
        message = re.sub(r"([a-z0-9_\-.+]+@[a-z0-9_\-.+]+)", '<a href="mailto:\\1">\\1</a>', message)
        if self.replace:
            for search, replace in self.replace:
                message = re.sub(search, replace, message)

        text = []
        text.append("<b>Revision:</b> " + rev.revision_id)

        parent_ids = rev.parent_ids
        if parent_ids:
            text.append("<b>Parent revisions:</b> " + ", ".join('<a href="qlog-revid:%s">%s</a>' % (a, a) for a in parent_ids))

        committer = htmlencode(rev.committer)
        committer = re.sub(r"([a-z0-9_\-.+]+@[a-z0-9_\-.+]+)", '<a href="mailto:\\1">\\1</a>', committer)
        text.append('<b>Author:</b> ' + committer)

        branch_nick = rev.properties.get('branch-nick')
        if branch_nick:
            text.append('<b>Branch nick:</b> ' + branch_nick)

        tags = rev.tags
        if tags:
            text.append('<b>Tags:</b> ' + ', '.join(tags))

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
        tree = self.branch.repository.revision_tree(rev.revision_id)
        if not rev.parent_ids:
            old_tree = self.branch.repository.revision_tree(None)
        else:
            old_tree = self.branch.repository.revision_tree(rev.parent_ids[0])
        window = DiffWindow(old_tree, tree, custom_title=rev.revision_id, branch=self.branch)
        window.show()
        self.windows.append(window)

    def add_log_entry(self):
        """Add loaded entries to the list."""
        revision = self.log_queue.get()

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
        item.setText(2, rev.committer)
        item.setText(3, rev.get_summary())
        tags = revision.tags
        if tags:
            # TODO support multiple tags
            item.setData(3, TagNameRole, QtCore.QVariant(tags[0]))
        rev.delta = revision.delta
        rev.revno = revision.revno
        rev.tags = revision.tags
        self.item_to_rev[item] = rev
        self.last_item = item

    def load_history(self):
        """Load branch history."""

        class QLogFormatter(LogFormatter):

            supports_merge_revisions = True
            supports_tags = True
            supports_delta = True

            def __init__(self, parent):
                self.parent = parent

            def log_revision(self, revision):
                self.parent.log_queue.put(revision)
                self.parent.emit(QtCore.SIGNAL("log_entry_loaded()"))

        formatter = QLogFormatter(self)
        show_log(self.branch, formatter, verbose=False,
                 specific_fileid=self.specific_fileid)
