# -*- coding: utf-8 -*-
#
# QBzr - Qt frontend to Bazaar commands
# Copyright (C) 2007 Lukáš Lalinský <lalinsky@gmail.com>
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

from PyQt4 import QtGui, QtCore

from bzrlib.plugins.qbzr.lib.i18n import gettext
from bzrlib.plugins.qbzr.lib.util import htmlencode
from bzrlib.plugins.qbzr.lib.util import (
    file_extension,
    )


colors = {
    'delete': (QtGui.QColor(255, 160, 180), QtGui.QColor(200, 60, 90)),
    'insert': (QtGui.QColor(180, 255, 180), QtGui.QColor(80, 210, 80)),
    'replace': (QtGui.QColor(180, 210, 250), QtGui.QColor(90, 130, 180)),
    'blank': (QtGui.QColor(240, 240, 240), QtGui.QColor(171, 171, 171)),
}

brushes = {}
for kind, cols in colors.items():
    brushes[kind] = (QtGui.QBrush(cols[0]), QtGui.QBrush(cols[1]))


class DiffSourceView(QtGui.QTextBrowser):

    def __init__(self, parent=None):
        QtGui.QTextBrowser.__init__(self, parent)
        self.setLineWrapMode(QtGui.QTextEdit.NoWrap)
        self.changes = []

    def setChanges(self, changes):
        self.changes = changes

    def paintEvent(self, event):
        w = self.width()
        y = self.verticalScrollBar().value()
        painter = QtGui.QPainter(self.viewport())
        painter.setClipRect(event.rect())
        for block0, block1, kind in self.changes:
            y1 = block0.position().y()
            y2 = block1.position().y()
            if y1 <= 0 or y2 <= 0:
                continue
            y1 -= y
            y2 -= y
            painter.fillRect(0, y1, w, y2 - y1, brushes[kind][0])
            painter.setPen(colors[kind][1])
            painter.drawLine(0, y1, w, y1)
            if y1 != y2:
                painter.drawLine(0, y2 - 1, w, y2 - 1)
        del painter
        QtGui.QTextBrowser.paintEvent(self, event)


class DiffViewHandle(QtGui.QSplitterHandle):

    def __init__(self, parent=None):
        QtGui.QSplitterHandle.__init__(self, QtCore.Qt.Horizontal, parent)
        self.view = parent

    def setChanges(self, changes):
        self.changes = changes

    def paintEvent(self, event):
        painter = QtGui.QPainter(self)
        painter.setClipRect(event.rect())
        frame = QtGui.QApplication.style().pixelMetric(QtGui.QStyle.PM_DefaultFrameWidth)
        value1 = self.view.browser1.verticalScrollBar().value() - frame
        value2 = self.view.browser2.verticalScrollBar().value() - frame
        w = self.width()
        for blocka0, blockb0, blocka1, blockb1, kind in self.changes:
            ly1 = blocka0.position().y()
            ly2 = blocka1.position().y()
            ry1 = blockb0.position().y()
            ry2 = blockb1.position().y()
            if ly1 <= 0 or ly2 <= 0 or ry1 <= 0 or ry2 <= 0:
                continue

            ly1 -= value1
            ly2 -= value1
            ry1 -= value2
            ry2 -= value2

            polygon = QtGui.QPolygon(4)
            polygon.setPoints(0, ly1, w, ry1, w, ry2, 0, ly2)
            painter.setPen(QtCore.Qt.NoPen)
            painter.setBrush(brushes[kind][0])
            painter.drawConvexPolygon(polygon)

            painter.setPen(colors[kind][1])
            painter.setRenderHints(QtGui.QPainter.Antialiasing, ly1 != ry1)
            painter.drawLine(0, ly1, w, ry1)
            painter.setRenderHints(QtGui.QPainter.Antialiasing, ly2 != ry2)
            painter.drawLine(0, ly2, w, ry2)
        del painter


def markup_line(line, encode=True):
    if encode:
        line = htmlencode(line)
    line = line.rstrip("\n").replace("\t", "&nbsp;" * 8)
    return line



def get_change_extent(str1, str2):
    start = 0
    limit = min(len(str1), len(str2))
    while start < limit and str1[start] == str2[start]:
        start += 1
    end = -1
    limit = limit - start
    while -end <= limit and str1[end] == str2[end]:
        end -= 1
    return (start, end + 1)


def markup_intraline_changes(line1, line2, color):
    line1 = line1.rstrip("\n")
    line2 = line2.rstrip("\n")
    line1 = line1.replace(u"&", u"\1").replace(u"<", u"\2").replace(u">", u"\3")
    line2 = line2.replace(u"&", u"\1").replace(u"<", u"\2").replace(u">", u"\3")
    start, end = get_change_extent(line1[1:], line2[1:])
    if start == 0 and end < 0:
        text = u'<span style="background-color:%s">%s</span>%s' % (color, line1[:end], line1[end:])
    elif start > 0 and end == 0:
        start += 1
        text = u'%s<span style="background-color:%s">%s</span>' % (line1[:start], color, line1[start:])
    elif start > 0 and end < 0:
        start += 1
        text = u'%s<span style="background-color:%s">%s</span>%s' % (line1[:start], color, line1[start:end], line1[end:])
    else:
        text = line1
    return text.replace(u"\1", u"&amp;").replace(u"\2", u"&lt;").replace(u"\3", u"&gt;")


STYLES = {
    'hunk': 'background-color:#666666;color:#FFF;font-weight:bold;',
    'delete': 'background-color:#FFDDDD',
    'insert': 'background-color:#DDFFDD',
    'missing': 'background-color:#E0E0E0',
    'title': 'font-size:14px; font-weight:bold;',
    'metainfo': 'font-size:9px;',
}


class DiffView(QtGui.QSplitter):
    """Widget to show differences in side-by-side format."""

    def __init__(self, treediff, parent=None):
        QtGui.QSplitter.__init__(self, QtCore.Qt.Horizontal, parent)
        self.setHandleWidth(30)

        font = QtGui.QFont("Courier New,courier", 8)
        self.lineHeight = QtGui.QFontMetrics(font).height()

        titleFont = QtGui.QFont(self.font())
        titleFont.setBold(True)
        titleFont.setPixelSize(14)

        metainfoFont = QtGui.QFont(self.font())
        metainfoFont.setPixelSize(9)

        metainfoTitleFont = QtGui.QFont(metainfoFont)
        metainfoTitleFont.setBold(True)

        self.doc1 = QtGui.QTextDocument()
        self.doc2 = QtGui.QTextDocument()

        self.browser1 = DiffSourceView(self)
        self.browser2 = DiffSourceView(self)

#        self.browser1 = DiffSourceView(font, titleFont, metainfoFont, metainfoTitleFont, self.lineHeight, self)
#        self.browser2 = DiffSourceView(font, titleFont, metainfoFont, metainfoTitleFont, self.lineHeight, self)

        self.ignoreUpdate = False
        self.connect(self.browser1.verticalScrollBar(), QtCore.SIGNAL("valueChanged(int)"), self.updateHandle1)
        self.connect(self.browser2.verticalScrollBar(), QtCore.SIGNAL("valueChanged(int)"), self.updateHandle2)
        self.connect(self.browser1.horizontalScrollBar(), QtCore.SIGNAL("valueChanged(int)"), self.syncHorizontalSlider1)
        self.connect(self.browser2.horizontalScrollBar(), QtCore.SIGNAL("valueChanged(int)"), self.syncHorizontalSlider2)

        self.setCollapsible(0, False)
        self.setCollapsible(1, False)

        self.treediff = treediff
        self.displayCombined()
        self.browser1.setDocument(self.doc1)
        self.browser2.setDocument(self.doc2)

        self.addWidget(self.browser1)
        self.addWidget(self.browser2)

    def _syncSliders(self, slider1, slider2, value):
        m = slider1.maximum()
        if m:
            value = slider2.minimum() + slider2.maximum() * (value - slider1.minimum()) / m
            self.ignoreUpdate = True
            slider2.setValue(value)
            self.ignoreUpdate = False

    def updateHandle1(self, value):
        if not self.ignoreUpdate:
            slider1 = self.browser1.verticalScrollBar()
            slider2 = self.browser2.verticalScrollBar()
            self._syncSliders(slider1, slider2, value)
            self.handle(1).update()

    def updateHandle2(self, value):
        if not self.ignoreUpdate:
            slider1 = self.browser1.verticalScrollBar()
            slider2 = self.browser2.verticalScrollBar()
            self._syncSliders(slider2, slider1, value)
            self.handle(1).update()

    def syncHorizontalSlider1(self, value):
        if not self.ignoreUpdate:
            slider1 = self.browser1.horizontalScrollBar()
            slider2 = self.browser2.horizontalScrollBar()
            self._syncSliders(slider1, slider2, value)
            self.handle(1).update()

    def syncHorizontalSlider2(self, value):
        if not self.ignoreUpdate:
            slider1 = self.browser1.horizontalScrollBar()
            slider2 = self.browser2.horizontalScrollBar()
            self._syncSliders(slider2, slider1, value)
            self.handle(1).update()

    def createHandle(self):
        return DiffViewHandle(self)

    def displayCombined(self):
        monospacedFont = QtGui.QFont("Courier New, Courier", self.font().pointSize())
        titleFont = QtGui.QFont(self.font())
        titleFont.setPointSize(titleFont.pointSize() * 140 / 100)
        titleFont.setBold(True)
        metadataFont = QtGui.QFont(self.font())
        metadataFont.setPointSize(titleFont.pointSize() * 70 / 100)
        metadataLabelFont = QtGui.QFont(metadataFont)
        metadataLabelFont.setBold(True)

        monospacedFormat = QtGui.QTextCharFormat()
        monospacedFormat.setFont(monospacedFont)
        titleFormat = QtGui.QTextCharFormat()
        titleFormat.setFont(titleFont)
        metadataFormat = QtGui.QTextCharFormat()
        metadataFormat.setFont(metadataFont)
        metadataLabelFormat = QtGui.QTextCharFormat()
        metadataLabelFormat.setFont(metadataLabelFont)

        cursors = [QtGui.QTextCursor(self.doc1), QtGui.QTextCursor(self.doc2)]

        changes = []

        lastModifiedLabel = gettext('Last modified:')
        statusLabel = gettext('Status:')
        kindLabel = gettext('Kind:')
        
        image_exts = ['.'+str(i)
            for i in QtGui.QImageReader.supportedImageFormats()]

        for diff in self.treediff:
            # file path
            cursors[0].insertText(diff.path, titleFormat)
            cursors[1].insertText(diff.path, titleFormat)
            # metadata
            cursors[0].insertBlock(QtGui.QTextBlockFormat(), monospacedFormat)
            cursors[0].insertText(lastModifiedLabel, metadataLabelFormat)
            cursors[0].insertText(" %s, " % diff.old_date, metadataFormat)
            cursors[0].insertText(statusLabel, metadataLabelFormat)
            cursors[0].insertText(" %s, " % gettext(diff.status), metadataFormat)
            cursors[0].insertText(kindLabel, metadataLabelFormat)
            cursors[0].insertText(" %s" % gettext(diff.kind), metadataFormat)
            cursors[1].insertBlock(QtGui.QTextBlockFormat(), monospacedFormat)
            cursors[1].insertText(lastModifiedLabel, metadataLabelFormat)
            cursors[1].insertText(" %s, " % diff.new_date, metadataFormat)
            cursors[1].insertText(statusLabel, metadataLabelFormat)
            cursors[1].insertText(" %s, " % gettext(diff.status), metadataFormat)
            cursors[1].insertText(kindLabel, metadataLabelFormat)
            cursors[1].insertText(" %s" % gettext(diff.kind), metadataFormat)
            for cursor in cursors:
                cursor.insertBlock(QtGui.QTextBlockFormat(), monospacedFormat)
                cursor.insertBlock(QtGui.QTextBlockFormat(), monospacedFormat)

            margins = [0, 0]
            if not diff.binary:
                a = diff.old_lines
                b = diff.new_lines
                for i, group in enumerate(diff.groups):
                    if i > 0:
                        blocka0 = cursors[0].block().layout()
                        blockb0 = cursors[1].block().layout()
                        for cursor in cursors:
                            cursor.insertBlock(QtGui.QTextBlockFormat(), monospacedFormat)
                        blocka1 = cursors[0].block().layout()
                        blockb1 = cursors[1].block().layout()
                        changes.append((blocka0, blockb0, blocka1, blockb1, 'blank'))
                    linediff = 0
                    for tag, i1, i2, j1, j2 in group:
                        ni = i2 - i1
                        nj = j2 - j1
                        if tag == "equal":
                            text = "".join(l for l in a[i1:i2])
                            for cursor in cursors:
                                cursor.insertText(text, monospacedFormat)
                        else:
                            blocka0 = cursors[0].block().layout()
                            blockb0 = cursors[1].block().layout()
                            if ni == nj:
                                for i in xrange(ni):
                                    linea = a[i1 + i]
                                    lineb = b[j1 + i]
                                    cursors[0].insertText(linea, monospacedFormat)
                                    cursors[1].insertText(lineb, monospacedFormat)
                            else:
                                linediff += ni - nj
                                text = "".join(l for l in a[i1:i2])
                                cursors[0].insertText(text, monospacedFormat)
                                text = "".join(l for l in b[j1:j2])
                                cursors[1].insertText(text, monospacedFormat)
                            blocka1 = cursors[0].block().layout()
                            blockb1 = cursors[1].block().layout()
                            changes.append((blocka0, blockb0, blocka1, blockb1, tag))
                    if linediff == 0:
                        continue
                    if linediff < 0:
                        i1 = group[-1][2]
                        i2 = i1 - linediff
                        lines = a[i1:i2]
                        linediff = -linediff - len(lines)
                        cursor = cursors[0]
                    else:
                        j1 = group[-1][4]
                        j2 = j1 + linediff
                        lines = b[j1:j2]
                        linediff = linediff - len(lines)
                        cursor = cursors[1]
                    lines.extend(["\n"] * linediff)
                    cursor.insertText("".join(lines), monospacedFormat)
            else:
                ext = file_extension(diff.path).lower()
                if ext in image_exts:
                    heights = [0, 0]
                    for i, (data, doc, cursor) in enumerate(
                            [(diff.old_data, self.doc1, cursors[0]),
                             (diff.new_data, self.doc2, cursors[1])]):
                        if data:
                            image = QtGui.QImage()
                            image.loadFromData(data)
                            heights[i] = image.height() + 1 # QTextDocument seems to add 1 pixel when layouting the text
                            doc.addResource(QtGui.QTextDocument.ImageResource,
                                            QtCore.QUrl(diff.file_id),
                                            QtCore.QVariant(image))
                            cursor.insertImage(diff.file_id)
                            cursor.insertBlock(QtGui.QTextBlockFormat(), monospacedFormat)
                    if heights[0] > heights[1]:
                        margins = [0, heights[0] - heights[1]]
                    else:
                        margins = [heights[1] - heights[0], 0]

            for i, cursor in enumerate(cursors):
                format = QtGui.QTextBlockFormat()
                format.setTopMargin(margins[i])
                cursor.insertBlock(format, monospacedFormat)

        changes1 = [(line[0], line[2], line[4]) for line in changes]
        changes2 = [(line[1], line[3], line[4]) for line in changes]

        self.browser1.setChanges(changes1)
        self.browser2.setChanges(changes2)
        self.handle(1).setChanges(changes)


class SimpleDiffView(QtGui.QTextEdit):
    """Widget to show differences in unidiff format."""

    def __init__(self, treeview, parent=None):
        QtGui.QTextEdit.__init__(self, parent)
        self.doc = QtGui.QTextDocument(parent)
        self.setReadOnly(1)
        res = treeview.html_unidiff()
        self.doc.setHtml("<html><body><pre>%s</pre></body></html>"%(res))
        self.setDocument(self.doc)
        self.verticalScrollBar().setValue(0)
