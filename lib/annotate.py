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
    get_branch_config,
    get_set_encoding,
    open_browser,
    RevisionMessageBrowser,
    split_tokens_at_lines,
    format_for_ttype,
    )

have_pygments = True
try:
    from pygments import lex
    from pygments.util import ClassNotFound
    from pygments.lexers import get_lexer_for_filename
except ImportError:
    have_pygments = False


class FormatedCodeItemDelegate(QtGui.QItemDelegate):
    
    def __init__(self, lines, parent = None):
        QtGui.QItemDelegate.__init__(self, parent)
        self.lines = lines

    def paint(self, painter, option, index):
        self.line = self.lines[index.row()]
        QtGui.QItemDelegate.paint(self, painter, option, index)

    def drawDisplay(self, painter, option, rect, text):
        painter.setFont(option.font)
        if (option.state & QtGui.QStyle.State_Selected
            and option.state & QtGui.QStyle.State_Active):
            painter.setPen(option.palette.highlightedText().color())
        else:
            painter.setPen(option.palette.text().color())
        
        textPoint = QtCore.QPoint(rect.left() + 2, rect.bottom() - option.fontMetrics.descent())
        for ttype, text in self.line:
            painter.save()
            format_for_ttype(ttype, painter)
            painter.drawText(textPoint, text.rstrip())
            textPoint.setX(textPoint.x() + QtGui.QFontMetrics(painter.font()).width(text))
            painter.restore()


class AnnotateWindow(QBzrWindow):

    def __init__(self, branch, tree, path, fileId, encoding=None, parent=None):
        QBzrWindow.__init__(self,
            [gettext("Annotate"), path], parent)
        self.restoreSize("annotate", (780, 680))

        self.encoding = get_set_encoding(encoding, get_branch_config(branch))

        self.windows = []

        self.branch = branch
        self.tree = tree
        self.fileId = fileId

        self.browser = QtGui.QTreeWidget()
        self.browser.setRootIsDecorated(False)
        self.browser.setUniformRowHeights(True)
        self.browser.setHeaderLabels([gettext("Line"), gettext("Author"), gettext("Rev"), ""])
        self.browser.header().setStretchLastSection(False)
        self.browser.header().setResizeMode(QtGui.QHeaderView.ResizeToContents) 
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
            self.annotate(tree, fileId, path)
        finally:
            branch.unlock()

    def annotate(self, tree, fileId, path):
        revnos = self.branch.get_revision_id_to_revno_map()
        revnos = dict((k, '.'.join(map(str, v))) for k, v in revnos.iteritems())
        font = QtGui.QFont("Courier New,courier", self.browser.font().pointSize())
        revisionIds = set()
        items = []
        item_revisions = []
        lastRevisionId = None
        lines = []
        for i, (origin, text) in enumerate(tree.annotate_iter(fileId)):
            text = text.decode(self.encoding, 'replace')
            lines.append(text)
            revisionIds.add(origin)
            item = QtGui.QTreeWidgetItem()
            item.setData(0, QtCore.Qt.UserRole, QtCore.QVariant(origin))
            item.setText(0, QtCore.QString.number(i + 1))
            if lastRevisionId != origin:
                item.setText(2, revnos[origin])
                item.setTextAlignment(2, QtCore.Qt.AlignRight)
            item.setText(3, text.rstrip())
            item.setFont(3, font)
            items.append(item)
            item_revisions.append(origin)
            lastRevisionId = origin
        self.browser.insertTopLevelItems(0, items)

        revisionIds = list(revisionIds)
        revisions = self.branch.repository.get_revisions(revisionIds)
        revisionDict = dict(zip(revisionIds, revisions))
        now = time.time()
        lastRevisionId = None
        for revisionId, item in zip(item_revisions, items):
            r = revisionDict[revisionId]
            r._author_name = extract_name(get_apparent_author(r))
            if lastRevisionId != revisionId:
                item.setText(1, r._author_name)
            item.setBackground(3, self.get_color(r, now))
            lastRevisionId = revisionId

        revisions.sort(key=operator.attrgetter('timestamp'), reverse=True)

        revid_to_tags = self.branch.tags.get_reverse_tag_dict()

        self.itemToRev = {}
        items = []
        for rev in revisions:
            item = QtGui.QTreeWidgetItem()
            item.setText(0, format_timestamp(rev.timestamp))
            item.setText(1, rev._author_name)
            item.setText(2, rev.get_summary())
            items.append(item)
            rev.revno = revnos[rev.revision_id]
            rev.tags = sorted(revid_to_tags.get(rev.revision_id, []))
            self.itemToRev[item] = rev
        self.changes.insertTopLevelItems(0, items)
        
        self.lines = None
        if have_pygments:
            try:
                # A more correct way to do this would be to add the tokens as
                # a data role to each respective tree item. But it is to much
                # effort to wrap them as QVariants. We will just pass the line
                # tokens to the delegate.
                lines_tokens = list(split_tokens_at_lines(\
                                  lex("".join(lines),
                                  get_lexer_for_filename(path))))
                self.browser.setItemDelegateForColumn(3,FormatedCodeItemDelegate(lines_tokens, self))
                
            except ClassNotFound:
                pass
    

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
                tree = repo.revision_tree(rev.revision_id)
                old_tree = repo.revision_tree(None)
            else:
                revs = [rev.revision_id, rev.parent_ids[0]]
                tree, old_tree = repo.revision_trees(revs)
        finally:
            repo.unlock()
        window = DiffWindow(old_tree, tree,
                            self.branch, self.branch,
                            )
        window.show()
        self.windows.append(window)

    def linkClicked(self, url):
        open_browser(str(url.toEncoded()))

    def get_color(self, revision, now):
        if  now < revision.timestamp:
            days = 0
        else:
            days = (now - revision.timestamp) / (24 * 60 * 60)
        
        saturation = 0.5/((days/50) + 1)
        hue =  1-float(abs(hash(revision._author_name))) / sys.maxint 
        return QtGui.QColor.fromHsvF(hue, saturation, 1 )

