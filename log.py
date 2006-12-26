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
from bzrlib.log import get_view_revisions, _enumerate_history
from bzrlib.plugins.qbzr.diff import DiffWindow
from bzrlib.plugins.qbzr.util import QBzrWindow


class CustomFunctionThread(QtCore.QThread):

    def __init__(self, target, args=[], parent=None):
        QtCore.QThread.__init__(self, parent)
        self.target = target
        self.args = args

    def run(self):
        self.target(*self.args)


class LogWindow(QBzrWindow):

    def __init__(self, branch, location, specific_fileid, replace=None, parent=None):
        title = ["Log"]
        if location:
            title.append(location)
        QBzrWindow.__init__(self, title, (710, 580), parent)
        self.specific_fileid = specific_fileid

        self.replace = replace

        splitter = QtGui.QSplitter(QtCore.Qt.Vertical)

        groupBox = QtGui.QGroupBox(u"Log", splitter)
        splitter.addWidget(groupBox)

        self.changesList = QtGui.QTreeWidget(groupBox)
        self.changesList.setHeaderLabels([u"Rev", u"Date", u"Author", u"Message"])
        header = self.changesList.header()
        header.resizeSection(0, 50)
        header.resizeSection(1, 110)
        header.resizeSection(2, 190)
        self.connect(self.changesList, QtCore.SIGNAL("itemSelectionChanged()"), self.update_selection)

        self.connect(self.changesList,
                     QtCore.SIGNAL("itemDoubleClicked(QTreeWidgetItem *, int)"),
                     self.show_differences)

        vbox1 = QtGui.QVBoxLayout(groupBox)
        vbox1.addWidget(self.changesList)

        self.branch = branch
        self.item_to_rev = {}

        self.last_item = None
        self.merge_stack = [self.changesList]
        self.connect(self, QtCore.SIGNAL("log_entry_loaded()"),
                     self.add_log_entry, QtCore.Qt.QueuedConnection)
        self.log_queue = Queue.Queue()
        self.thread = CustomFunctionThread(self.load_history, parent=self)
        self.thread.start()

        groupBox = QtGui.QGroupBox(u"Details", splitter)
        splitter.addWidget(groupBox)

        splitter.setStretchFactor(0, 5)
        splitter.setStretchFactor(1, 1)

        gridLayout = QtGui.QGridLayout(groupBox)
        gridLayout.setColumnStretch(0, 0)
        gridLayout.setColumnStretch(1, 3)
        gridLayout.setColumnStretch(2, 1)

        gridLayout.addWidget(QtGui.QLabel(u"Revision:", groupBox), 0, 0)
        self.revisionEdit = QtGui.QLineEdit(u"", groupBox)
        self.revisionEdit.setReadOnly(True)
        gridLayout.addWidget(self.revisionEdit, 0, 1)

        gridLayout.addWidget(QtGui.QLabel(u"Parents:", groupBox), 1, 0)
        self.parentsEdit = QtGui.QLineEdit(u"", groupBox)
        self.parentsEdit.setReadOnly(True)
        gridLayout.addWidget(self.parentsEdit, 1, 1)

        gridLayout.addWidget(QtGui.QLabel(u"Message:", groupBox), 2, 0)
        self.message = QtGui.QTextDocument()
        self.message_browser = QtGui.QTextBrowser(groupBox)
        if hasattr(self.message_browser, "setOpenExternalLinks"):
            self.message_browser.setOpenExternalLinks(True)
        self.message_browser.setDocument(self.message)
        gridLayout.addWidget(self.message_browser, 2, 1)

        self.fileList = QtGui.QListWidget(groupBox)
        gridLayout.addWidget(self.fileList, 0, 2, 3, 1)

        buttonbox = QtGui.QDialogButtonBox(
            QtGui.QDialogButtonBox.StandardButtons(
                QtGui.QDialogButtonBox.Close),
            QtCore.Qt.Horizontal,
            self)
        self.connect(buttonbox, QtCore.SIGNAL("rejected()"), self.close)

        vbox = QtGui.QVBoxLayout(self.centralwidget)
        vbox.addWidget(splitter)
        vbox.addWidget(buttonbox)
        self.windows = []

    def closeEvent(self, event):
        for window in self.windows:
            window.close()
        event.accept()
        
    def update_selection(self):
        item = self.changesList.selectedItems()[0]
        rev = self.item_to_rev[item]

        self.revisionEdit.setText(rev.revision_id)
        self.parentsEdit.setText(u", ".join(rev.parent_ids))

        message = rev.message
        message = message.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;").replace("\n", "<br />")
        message = re.sub(r"([\s>])(https?)://([^\s<>{}()]+[^\s.,<>{}()])", "\\1<a href=\"\\2://\\3\">\\2://\\3</a>", message)
        message = re.sub(r"(\s)www\.([a-z0-9\-]+)\.([a-z0-9\-.\~]+)((?:/[^ <>{}()\n\r]*[^., <>{}()\n\r]?)?)", "\\1<a href=\"http://www.\\2.\\3\\4\">www.\\2.\\3\\4</a>", message)
        message = re.sub(r"([a-z0-9_\-.]+@[a-z0-9_\-.]+)", '<a href="mailto:\\1">\\1</a>', message)
        if self.replace:
            for search, replace in self.replace:
                message = re.sub(search, replace, message)

        self.message.setHtml(message)

        self.fileList.clear()

        if not rev.delta:
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
        window = DiffWindow(old_tree, tree, custom_title=rev.revision_id)
        window.show()
        self.windows.append(window)

    def add_log_entry(self):
        """Add loaded entries to the list."""
        revno, rev, delta, merge_depth = self.log_queue.get()

        if merge_depth > len(self.merge_stack) - 1:
            self.merge_stack.append(self.last_item)
        elif merge_depth < len(self.merge_stack) - 1:
            self.merge_stack.pop()

        item = QtGui.QTreeWidgetItem(self.merge_stack[-1])
        if revno:
            item.setText(0, str(revno))
        date = QtCore.QDateTime()
        date.setTime_t(int(rev.timestamp))
        item.setText(1, date.toString(QtCore.Qt.LocalDate))
        item.setText(2, rev.committer)
        item.setText(3, rev.message.split("\n")[0])
        rev.delta = delta
        self.item_to_rev[item] = rev
        self.last_item = item
        rev.revno = revno

    def load_history(self):
        """Load branch history."""
        branch = self.branch
        repository = branch.repository
        specific_fileid = self.specific_fileid

        start_revision = None
        end_revision = None

        which_revs = _enumerate_history(branch)

        if start_revision is None:
            start_revision = 1
        else:
            branch.check_real_revno(start_revision)
        
        if end_revision is None:
            end_revision = len(which_revs)
        else:
            branch.check_real_revno(end_revision)
    
        # list indexes are 0-based; revisions are 1-based
        cut_revs = which_revs[(start_revision-1):(end_revision)]
        if not cut_revs:
            return
    
        # convert the revision history to a dictionary:
        rev_nos = dict((k, v) for v, k in cut_revs)
    
        # override the mainline to look like the revision history.
        mainline_revs = [revision_id for index, revision_id in cut_revs]
        if cut_revs[0][0] == 1:
            mainline_revs.insert(0, None)
        else:
            mainline_revs.insert(0, which_revs[start_revision-2][1])
        include_merges = True
        direction = 'reverse'
        view_revisions = list(get_view_revisions(mainline_revs, rev_nos, branch,
                              direction, include_merges=include_merges))
            
        def iter_revisions():
            revision_ids = [r for r, n, d in view_revisions]
            #revision_ids.reverse()
            num = 20
            while revision_ids:
                cur_deltas = {}
                cur_revision_ids = revision_ids[:num]
                revisions = repository.get_revisions(cur_revision_ids)
                if specific_fileid:
                    deltas = repository.get_deltas_for_revisions(revisions)
                    cur_deltas = dict(izip(cur_revision_ids, deltas))
                    
                for revision in revisions:
                    delta = cur_deltas.get(revision.revision_id)
                    if specific_fileid and \
                       not delta.touches_file_id(specific_fileid):
                        continue
                    yield revision, delta
                revision_ids  = revision_ids[num:]
                num = int(num * 1.5)

        for ((rev_id, revno, merge_depth), (rev, delta)) in \
             izip(view_revisions, iter_revisions()): 
            self.log_queue.put((revno, rev, delta, merge_depth))
            self.emit(QtCore.SIGNAL("log_entry_loaded()"))
