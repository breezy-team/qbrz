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

import operator
from PyQt4 import QtCore, QtGui
from bzrlib.plugins.qbzr.util import (QBzrWindow, format_revision_html,
                                      get_apparent_author, extract_name)

have_pygments = True
try:
    from pygments import highlight
    from pygments.lexers import get_lexer_for_filename
    from pygments.formatters import HtmlFormatter
except ImportError:
    have_pygments = False


class AnnotateView(QtGui.QTextBrowser):

    def __init__(self, line_height, blocks, parent=None):
        QtGui.QTextBrowser.__init__(self, parent)
        self.line_height = line_height
        self.blocks = blocks

    def mousePressEvent(self, event):
        lineno = (self.verticalScrollBar().value() + event.y()) / self.line_height
        self.emit(QtCore.SIGNAL("lineClicked"), lineno)
        return QtGui.QTextBrowser.mousePressEvent(self, event)

    def paintEvent(self, event):
        w = self.width()
        h = self.height()
        y = 1 - self.verticalScrollBar().value()
        painter = QtGui.QPainter(self.viewport())
        painter.setClipRect(event.rect())
        painter.setPen(QtGui.QColor(150, 150, 150))
        for pos, length, col in self.blocks:
            y1 = y + self.line_height * pos
            y2 = y1 + self.line_height * length
            if y1 >= h:
                break
            if y2 >= 0:
                if y1 >= 0:
                    painter.fillRect(0, y1, w, y2, col)
                    painter.drawLine(0, y1, w, y1)
                else:
                    painter.fillRect(0, 0, w, y2, col)

        return QtGui.QTextBrowser.paintEvent(self, event)


class AnnotateWindow(QBzrWindow):

    def __init__(self, filename, lines, revisions, parent=None):
        QBzrWindow.__init__(self, ["Annotate", filename], (780, 680), parent)

        revisions.sort(key=operator.attrgetter('timestamp'), reverse=True)

        self.annotations = [a[0] for a in lines]

        c1 = (255, 255, 255)
        c2 = (255, 216, 132)

        self.blocks = []
        last_block = (self.annotations[0], 0)
        used_revisions = set([self.annotations[0]])
        for i, rev_id in enumerate(self.annotations):
            if rev_id != last_block[0]:
                self.blocks.append((last_block[0], last_block[1], i - last_block[1]))
                last_block = (rev_id, i)
                used_revisions.add(rev_id)

        rev_dict = dict((r.revision_id, r) for r in revisions)

        used_revisions = list(used_revisions)
        used_revisions.sort(lambda a, b: cmp(rev_dict[a].timestamp, rev_dict[b].timestamp))
        used_revisions = dict((r, i) for (i, r) in enumerate(used_revisions))

        def make_color(i):
            f = (float(used_revisions[i]) / (len(used_revisions) - 1)) ** 2
            return QtGui.QColor(
                c1[0] + (c2[0] - c1[0]) * f,
                c1[1] + (c2[1] - c1[1]) * f,
                c1[2] + (c2[2] - c1[2]) * f)

        self.blocks = [(a, b, make_color(rev_id)) for (rev_id, a, b) in self.blocks]

        code = "".join(a[1] for a in lines)
        try:
            code = code.decode('utf-8', 'errors')
        except UnicodeError:
            code = code.decode('iso-8859-1', 'replace')

        if not have_pygments:
            style = ''
            code_html = '%s' % code
        else:
            try:
                lexer = get_lexer_for_filename(filename)
                formatter = HtmlFormatter()
                style = formatter.get_style_defs()
                code_html = highlight(code, lexer, formatter)
            except ValueError:
                style = ''
                code_html = '%s' % code

        font = QtGui.QFont("Courier New,courier", 8)
        self.lineHeight = QtGui.QFontMetrics(font).height()

        html = '''<html><head><style>%s
body {white-space:pre;}
</style></head><body>%s</body></html>''' % (style, code_html)
        self.doc = QtGui.QTextDocument()
        self.doc.setHtml(html)
        self.doc.setDefaultFont(font)

        browser = AnnotateView(self.lineHeight, self.blocks)
        browser.setDocument(self.doc)
        self.connect(browser, QtCore.SIGNAL("lineClicked"), self.set_revision_by_line)

        self.message_doc = QtGui.QTextDocument()
        message = QtGui.QTextEdit()
        message.setDocument(self.message_doc)

        self.changes = QtGui.QTreeWidget()
        self.changes.setHeaderLabels(["Date", "Author", "Summary"])
        self.changes.setRootIsDecorated(False)
        self.changes.setUniformRowHeights(True)
        self.connect(self.changes, QtCore.SIGNAL("itemSelectionChanged()"), self.set_revision_by_item)
        self.itemToRev = {}
        for rev in revisions:
            item = QtGui.QTreeWidgetItem(self.changes)
            date = QtCore.QDateTime()
            date.setTime_t(int(rev.timestamp))
            item.setText(0, date.toString(QtCore.Qt.LocalDate))
            item.setText(1, extract_name(get_apparent_author(rev)))
            item.setText(2, rev.get_summary())
            self.itemToRev[item] = rev

        hsplitter = QtGui.QSplitter(QtCore.Qt.Horizontal)
        hsplitter.addWidget(self.changes)
        hsplitter.addWidget(message)

        hsplitter.setStretchFactor(0, 2)
        hsplitter.setStretchFactor(1, 2)

        splitter = QtGui.QSplitter(QtCore.Qt.Vertical)
        splitter.addWidget(browser)
        splitter.addWidget(hsplitter)

        splitter.setStretchFactor(0, 5)
        splitter.setStretchFactor(1, 2)

        buttonbox = QtGui.QDialogButtonBox(
            QtGui.QDialogButtonBox.StandardButtons(
                QtGui.QDialogButtonBox.Close),
            QtCore.Qt.Horizontal,
            self)
        self.connect(buttonbox, QtCore.SIGNAL("rejected()"), self.close)

        vbox = QtGui.QVBoxLayout(self.centralwidget)
        vbox.addWidget(splitter)
        vbox.addWidget(buttonbox)

    def set_revision_by_line(self, line):
        try:
            revisionId = self.annotations[line]
        except IndexError:
            pass
        else:
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
