# -*- coding: utf-8 -*-
#
# QBzr - Qt frontend to Bazaar commands
# Copyright (C) 2006 Lukáš Lalinský <lalinsky@gmail.com>
# Copyright (C) 2005 Dan Loda <danloda@gmail.com>
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

# TODO:
#  - better annotate algorithm on packs
#  - syntax highlighting of the source code

import operator, sys, time
from PyQt4 import QtCore, QtGui
from bzrlib.plugins.qbzr.lib.diff import DiffWindow
from bzrlib.plugins.qbzr.lib.i18n import gettext
from bzrlib.plugins.qbzr.lib.util import (
    BTN_CLOSE,
    QBzrWindow,
    extract_name,
    format_revision_html,
    format_timestamp,
    get_apparent_author,
    open_browser,
    RevisionMessageBrowser,
    )


class AnnotateColorSaturation(object):

    def __init__(self):
        self.current_angle = 0

    def hue(self, angle):
        return tuple([self.v(angle, r) for r in (0, 120, 240)])

    def ang(self, angle, rotation):
        angle += rotation
        angle = angle % 360
        if angle > 180:
            angle = 180 - (angle - 180)
        return abs(angle)

    def v(self, angle, rotation):
        ang = self.ang(angle, rotation)
        if ang < 60:
            return 1
        elif ang > 120:
            return 0
        else:
            return 1 - ((ang - 60) / 60)

    def saturate_v(self, saturation, hv):
        return int(255 - (saturation/3*(1-hv)))

    def committer_angle(self, committer):
        return float(abs(hash(committer))) / sys.maxint * 360.0

    def _days(self, revision, now):
        return (now - revision.timestamp) / (24 * 60 * 60)

    def get_color(self, revision, now):
        days = self._days(revision, now)
        saturation = 255/((days/50) + 1)
        hue = self.hue(self.committer_angle(revision._author_name))
        color = tuple([self.saturate_v(saturation, h) for h in hue])
        return QtGui.QColor(*color)


class AnnotateWindow(QBzrWindow):

    def __init__(self, branch, tree, path, fileId, encoding=None, parent=None):
        QBzrWindow.__init__(self,
            [gettext("Annotate"), path], parent)
        self.restoreSize("annotate", (780, 680))

        self.encoding = encoding or 'utf-8'

        self.windows = []

        self.branch = branch
        self.tree = tree
        self.fileId = fileId
        self.colormap = AnnotateColorSaturation()

        self.browser = QtGui.QTreeWidget()
        self.browser.setRootIsDecorated(False)
        self.browser.setUniformRowHeights(True)
        self.browser.setHeaderLabels([gettext("Line"), gettext("Author"), gettext("Rev"), ""])
        self.browser.header().setStretchLastSection(False)
        self.browser.header().setResizeMode(3, QtGui.QHeaderView.ResizeToContents)
        self.connect(self.browser,
            QtCore.SIGNAL("itemSelectionChanged()"),
            self.setRevisionByLine)

        self.message_doc = QtGui.QTextDocument()
        message = RevisionMessageBrowser()
        message.setDocument(self.message_doc)
        self.connect(message,
                     QtCore.SIGNAL("anchorClicked(QUrl)"),
                     self.linkClicked)

        self.changes = QtGui.QTreeWidget()
        self.changes.setHeaderLabels(
            [gettext("Date"), gettext("Author"), gettext("Summary")])
        self.changes.setRootIsDecorated(False)
        self.changes.setUniformRowHeights(True)
        self.connect(self.changes,
                     QtCore.SIGNAL("itemSelectionChanged()"),
                     self.set_revision_by_item)
        self.connect(self.changes,
                     QtCore.SIGNAL("doubleClicked(QModelIndex)"),
                     self.show_revision_diff)

        hsplitter = QtGui.QSplitter(QtCore.Qt.Horizontal)
        hsplitter.addWidget(self.changes)
        hsplitter.addWidget(message)

        hsplitter.setStretchFactor(0, 2)
        hsplitter.setStretchFactor(1, 2)

        splitter = QtGui.QSplitter(QtCore.Qt.Vertical)
        splitter.addWidget(self.browser)
        splitter.addWidget(hsplitter)

        splitter.setStretchFactor(0, 5)
        splitter.setStretchFactor(1, 2)

        buttonbox = self.create_button_box(BTN_CLOSE)

        vbox = QtGui.QVBoxLayout(self.centralwidget)
        vbox.addWidget(splitter)
        vbox.addWidget(buttonbox)

        branch.lock_read()
        try:
            self.annotate(tree, fileId)
        finally:
            branch.unlock()

    def annotate(self, tree, fileId):
        revnos = self.branch.get_revision_id_to_revno_map()
        revnos = dict((k, '.'.join(map(str, v))) for k, v in revnos.iteritems())
        font = QtGui.QFont("Courier New,courier", 8)
        revisionIds = set()
        items = []
        lastRevisionId = None
        for i, (origin, text) in enumerate(tree.annotate_iter(fileId)):
            revisionIds.add(origin)
            item = QtGui.QTreeWidgetItem(self.browser)
            item.setData(0, QtCore.Qt.UserRole, QtCore.QVariant(origin))
            item.setText(0, QtCore.QString.number(i + 1))
            if lastRevisionId != origin:
                item.setText(2, revnos[origin])
                item.setTextAlignment(2, QtCore.Qt.AlignRight)
            item.setText(3, text.rstrip().decode(self.encoding, 'replace'))
            item.setFont(3, font)
            items.append((origin, item))
            lastRevisionId = origin

        revisionIds = list(revisionIds)
        revisions = self.branch.repository.get_revisions(revisionIds)
        revisionDict = dict(zip(revisionIds, revisions))
        now = time.time()
        lastRevisionId = None
        for revisionId, item in items:
            r = revisionDict[revisionId]
            r._author_name = extract_name(get_apparent_author(r))
            if lastRevisionId != revisionId:
                item.setText(1, r._author_name)
            item.setBackground(3, self.colormap.get_color(r, now))
            lastRevisionId = revisionId

        revisions.sort(key=operator.attrgetter('timestamp'), reverse=True)

        revid_to_tags = self.branch.tags.get_reverse_tag_dict()

        self.itemToRev = {}
        for rev in revisions:
            item = QtGui.QTreeWidgetItem(self.changes)
            item.setText(0, format_timestamp(rev.timestamp))
            item.setText(1, rev._author_name)
            item.setText(2, rev.get_summary())
            rev.revno = revnos[rev.revision_id]
            rev.tags = sorted(revid_to_tags.get(rev.revision_id, []))
            self.itemToRev[item] = rev

    def setRevisionByLine(self):
        items = self.browser.selectedItems()
        if not items:
            return
        revisionId = str(items[0].data(0, QtCore.Qt.UserRole).toString())
        for item, rev in self.itemToRev.iteritems():
            if rev.revision_id == revisionId:
                self.changes.setCurrentItem(item)
                self.message_doc.setHtml(format_revision_html(rev))
                break

    def set_revision_by_item(self):
        items = self.changes.selectedItems()
        if len(items) == 1:
            for item, rev in self.itemToRev.iteritems():
                if item == items[0]:
                    self.message_doc.setHtml(format_revision_html(rev))
                    break

    def show_revision_diff(self, index):
        item = self.changes.itemFromIndex(index)
        rev = self.itemToRev[item]
        repo = self.branch.repository
        repo.lock_read()
        try:
            if not rev.parent_ids:
                revs = [rev.revision_id]
                tree = repo.revision_tree(rev1.revision_id)
                old_tree = repo.revision_tree(None)
            else:
                revs = [rev.revision_id, rev.parent_ids[0]]
                tree, old_tree = repo.revision_trees(revs)
        finally:
            repo.unlock()
        window = DiffWindow(old_tree, tree, custom_title="..".join(revs),
                            branch=self.branch)
        window.show()
        self.windows.append(window)

    def linkClicked(self, url):
        open_browser(str(url.toEncoded()))

