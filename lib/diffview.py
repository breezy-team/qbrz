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

from bzrlib import timestamp
from bzrlib.plugins.qbzr.lib.i18n import gettext
from bzrlib.plugins.qbzr.lib.util import htmlencode
from bzrlib.plugins.qbzr.lib.util import (
    file_extension,
    format_timestamp,
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
        self.infoBlocks = []

    def paintEvent(self, event):
        w = self.width()
        y = self.verticalScrollBar().value()
        painter = QtGui.QPainter(self.viewport())
        painter.setClipRect(event.rect())
        pen = QtGui.QPen(QtCore.Qt.black)
        pen.setWidth(2)
        painter.setPen(pen)
        for block in self.infoBlocks:
            block_y = block.position().y() - y
            painter.drawLine(0, block_y, w, block_y)
            
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
        self.changes = []

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


def insert_line_intraline_changes(line1, line2, cursor, format):
    start, end = get_change_extent(line1[1:], line2[1:])
    if start == 0 and end < 0:
        parts = ("", line1[:end], line1[end:])
    elif start > 0 and end == 0:
        start += 1
        parts = (line1[:start], line1[start:],"")
    elif start > 0 and end < 0:
        start += 1
        parts = (line1[:start], line1[start:end], line1[end:])
    else:
        parts= (line1, "", "")
    cursor.insertText(parts[0])
    oldformat = cursor.charFormat()
    cursor.insertText(parts[1], format)
    cursor.insertText(parts[2], oldformat)


class SidebySideDiffView(QtGui.QSplitter):
    """Widget to show differences in side-by-side format."""

    def __init__(self, parent=None):
        QtGui.QSplitter.__init__(self, QtCore.Qt.Horizontal, parent)
        self.setHandleWidth(30)

        font = QtGui.QFont("Courier New,courier", 8)
        self.lineHeight = QtGui.QFontMetrics(font).height()

        titleFont = QtGui.QFont(self.font())
        titleFont.setBold(True)
        titleFont.setPixelSize(14)

        monospacedFont = QtGui.QFont("Courier New, Courier",
                                     self.font().pointSize())
        titleFont = QtGui.QFont(self.font())
        titleFont.setPointSize(titleFont.pointSize() * 140 / 100)
        titleFont.setBold(True)
        metadataFont = QtGui.QFont(self.font())
        metadataFont.setPointSize(titleFont.pointSize() * 70 / 100)
        metadataLabelFont = QtGui.QFont(metadataFont)
        metadataLabelFont.setBold(True)
    
        self.monospacedFormat = QtGui.QTextCharFormat()
        self.monospacedFormat.setFont(monospacedFont)
        self.interLineChangeFormat = QtGui.QTextCharFormat()
        self.interLineChangeFormat.setFont(monospacedFont)
        self.interLineChangeFormat.setBackground(
            QtGui.QBrush(QtGui.QColor.fromRgb(90, 130, 180)))
        self.titleFormat = QtGui.QTextCharFormat()
        self.titleFormat.setFont(titleFont)
        self.metadataFormat = QtGui.QTextCharFormat()
        self.metadataFormat.setFont(metadataFont)
        self.metadataLabelFormat = QtGui.QTextCharFormat()
        self.metadataLabelFormat.setFont(metadataLabelFont)

        self.docs = (QtGui.QTextDocument(),
                     QtGui.QTextDocument())
        for doc in self.docs:
            doc.setUndoRedoEnabled(False)
            doc.setDefaultFont(monospacedFont)

        self.browser1 = DiffSourceView(self)
        self.browser2 = DiffSourceView(self)

        self.ignoreUpdate = False
        self.connect(self.browser1.verticalScrollBar(), QtCore.SIGNAL("valueChanged(int)"), self.updateHandle1)
        self.connect(self.browser2.verticalScrollBar(), QtCore.SIGNAL("valueChanged(int)"), self.updateHandle2)
        self.connect(self.browser1.horizontalScrollBar(), QtCore.SIGNAL("valueChanged(int)"), self.syncHorizontalSlider1)
        self.connect(self.browser2.horizontalScrollBar(), QtCore.SIGNAL("valueChanged(int)"), self.syncHorizontalSlider2)

        self.setCollapsible(0, False)
        self.setCollapsible(1, False)

        self.browser1.setDocument(self.docs[0])
        self.browser2.setDocument(self.docs[1])
        self.browsers = (self.browser1, self.browser2)

        self.addWidget(self.browser1)
        self.addWidget(self.browser2)
        self.rewinded = False
        
        self.cursors = [QtGui.QTextCursor(doc) for doc in self.docs]
        for cursor in self.cursors :
            format = QtGui.QTextCharFormat()
            format.setAnchorNames(["top"])
            cursor.insertText("", format)
        
        self.lastModifiedLabel = gettext('Last modified:')
        self.statusLabel = gettext('Status:')
        self.kindLabel = gettext('Kind:')
        self.propertiesLabel = gettext('Properties:')
        
        self.image_exts = ['.'+str(i)
            for i in QtGui.QImageReader.supportedImageFormats()]

    def append_diff(self, paths, file_id, kind, status, dates,
                    present, binary, lines, groups, data, properties_changed):
        cursors = self.cursors
        for i in range(2):
            cursor = cursors[i]
            cursor.beginEditBlock()
            cursor.insertText(paths[i] if paths[i] is not None else " ", self.titleFormat)
            cursor.insertBlock()
            if present[i]:
                cursor.insertText(self.lastModifiedLabel, self.metadataLabelFormat)
                cursor.insertText(" %s, " % format_timestamp(dates[i]), self.metadataFormat)
                cursor.insertText(self.statusLabel, self.metadataLabelFormat)
                cursor.insertText(" %s, " % gettext(status), self.metadataFormat)
                cursor.insertText(self.kindLabel, self.metadataLabelFormat)
                cursor.insertText(" %s" % gettext(kind[i]), self.metadataFormat)
                if properties_changed:
                    cursor.insertText(", ", self.metadataFormat)
                    cursor.insertText(self.propertiesLabel, self.metadataLabelFormat)
                    cursor.insertText(" ", self.metadataFormat)
                    cursor.insertText(", ".join([p[i] for p in properties_changed]), self.metadataFormat)
            else:
                cursor.insertText(" ", self.metadataFormat)
            cursor.insertBlock()
            self.browsers[i].infoBlocks.append(cursor.block().layout())
            
        if not binary:
            for cursor in cursors:
                cursor.insertBlock()
                cursor.setCharFormat(self.monospacedFormat)
            changes = []

            def fix_last_line(lines):
                """Fix last line if there is no new line.

                @param  lines:  list of lines
                @return:    original lines if lastline is OK,
                            or new list with fixed last line.
                """
                if lines:
                    last = lines[-1]
                    if last and last[-1] not in ('\r', '\n'):
                        lines = lines[:-1] + [last+'\n']
                return lines

            a = fix_last_line(lines[0])
            b = fix_last_line(lines[1])

            for i, group in enumerate(groups):
                if i > 0:
                    block0 = [cursor.block().layout() for cursor in self.cursors]
                    for cursor in cursors:
                        cursor.insertBlock()
                    block1 = [cursor.block().layout() for cursor in self.cursors]
                    changes.append((block0[0], block0[1], block1[0], block1[1], 'blank'))
                linediff = 0
                for tag, i1, i2, j1, j2 in group:
                    ni = i2 - i1
                    nj = j2 - j1
                    if tag == "equal":
                        text = "".join(l for l in a[i1:i2])
                        for cursor in cursors:
                            cursor.insertText(text)
                    else:
                        blocka0 = cursors[0].block().layout()
                        blockb0 = cursors[1].block().layout()
                        if ni == nj:
                            for i in xrange(ni):
                                linea = a[i1 + i]
                                lineb = b[j1 + i]
                                insert_line_intraline_changes(linea, lineb,
                                                              cursors[0],
                                                              self.interLineChangeFormat)
                                insert_line_intraline_changes(lineb, linea,
                                                              cursors[1],
                                                              self.interLineChangeFormat)
                        else:
                            linediff += ni - nj
                            text = "".join(l for l in a[i1:i2])
                            cursors[0].insertText(text)
                            text = "".join(l for l in b[j1:j2])
                            cursors[1].insertText(text)
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
                cursor.insertText("".join(lines))
            for cursor in self.cursors:
                cursor.insertBlock()
    
            changes1 = [(line[0], line[2], line[4]) for line in changes]
            changes2 = [(line[1], line[3], line[4]) for line in changes]
    
            self.browser1.changes.extend(changes1)
            self.browser2.changes.extend(changes2)
            self.handle(1).changes.extend(changes)
        else:
            heights = [0,0]
            is_images = [False, False]
            for i in range(2):
                if present[i]:
                    ext = file_extension(paths[i]).lower()
                    if ext in self.image_exts:
                        is_images[i] = True
                        image = QtGui.QImage()
                        image.loadFromData(data[i])
                        heights[i] = image.height() + 4 # QTextDocument seems to add 1 pixel when layouting the text
                        self.docs[i].addResource(QtGui.QTextDocument.ImageResource,
                                        QtCore.QUrl(file_id),
                                        QtCore.QVariant(image))
            
            max_height = max(heights)
            for i, cursor in enumerate(self.cursors):
                format = QtGui.QTextBlockFormat()
                format.setBottomMargin(max_height - heights[i])
                cursor.insertBlock(format)
                if present[i]:
                    if is_images[i]:
                        cursor.insertImage(file_id)
                        cursor.insertBlock()
                    else:
                        cursor.insertText(gettext('[binary file]'))
                else:
                    cursor.insertText(" ")
                cursor.insertBlock(QtGui.QTextBlockFormat())
        
        for cursor in self.cursors:
            cursor.endEditBlock()
        self.update()

    def rewind(self):
        if not self.rewinded:
            self.rewinded = True
            self.browser1.scrollToAnchor("top")
            self.browser2.scrollToAnchor("top")

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


class SimpleDiffView(QtGui.QTextBrowser):
    """Widget to show differences in unidiff format."""

    def __init__(self, parent=None):
        QtGui.QTextBrowser.__init__(self, parent)
        self.doc = QtGui.QTextDocument(parent)
        self.doc.setUndoRedoEnabled(False)
        self.setDocument(self.doc)
        self.rewinded = False
        self.cursor = QtGui.QTextCursor(self.doc)
        self.cursor.beginEditBlock()
        format = QtGui.QTextCharFormat()
        format.setAnchorNames(["top"])
        self.cursor.insertText("", format)
        monospacedFont = QtGui.QFont("Courier New, Courier",
                                     self.font().pointSize())
        self.monospacedFormat = QtGui.QTextCharFormat()
        self.monospacedFormat.setFont(monospacedFont)

        self.monospacedInsertFormat = QtGui.QTextCharFormat(self.monospacedFormat)
        self.monospacedInsertFormat.setForeground(QtGui.QColor(0, 136, 11))
        self.monospacedDeleteFormat = QtGui.QTextCharFormat(self.monospacedFormat)
        self.monospacedDeleteFormat.setForeground(QtGui.QColor(204, 0, 0))
    
        monospacedBoldFont = QtGui.QFont(monospacedFont)
        monospacedBoldFont.setBold(True)
    
        monospacedItalicFont = QtGui.QFont(monospacedFont)
        monospacedItalicFont.setItalic(True)
    
        self.monospacedBoldInsertFormat = QtGui.QTextCharFormat(self.monospacedInsertFormat)
        self.monospacedBoldInsertFormat.setFont(monospacedBoldFont)
        self.monospacedBoldDeleteFormat = QtGui.QTextCharFormat(self.monospacedDeleteFormat)
        self.monospacedBoldDeleteFormat.setFont(monospacedBoldFont)
    
        self.monospacedHeaderFormat = QtGui.QTextCharFormat()
        self.monospacedHeaderFormat.setFont(monospacedBoldFont)
        self.monospacedHeaderFormat.setBackground(QtGui.QColor(246, 245, 238))
        self.monospacedHeaderFormat.setForeground(QtGui.QColor(117, 117, 117))
    
        self.monospacedHunkFormat = QtGui.QTextCharFormat()
        self.monospacedHunkFormat.setFont(monospacedItalicFont)
        self.monospacedHunkFormat.setForeground(QtGui.QColor(153, 30, 199))

    def rewind(self):
        if not self.rewinded:
            self.rewinded = True
            self.scrollToAnchor("top")

    def append_diff(self, paths, file_id, kind, status, dates,
                    present, binary, lines, groups, data, properties_changed):
        path_info = paths[1] or paths[0]
        if status in ('renamed', 'renamed and modified'):
            path_info = paths[0] + ' => ' + paths[1]
        kind_info = kind[0] or kind[1]
        self.cursor.insertText("=== %s %s %s" % (gettext(status),
            gettext(kind_info), path_info),
            self.monospacedHeaderFormat)
        if properties_changed:
            self.cursor.insertText(" (properties changed: %s)" % \
                                   (", ".join(["%s to %s" % p for p in properties_changed])))
        self.cursor.insertText("\n")
        
        # GNU Patch uses the epoch date to detect files that are being added
        # or removed in a diff.
        EPOCH_DATE = '1970-01-01 00:00:00 +0000'
        for i in range(2):
            if present[i]:
                dates[i] = timestamp.format_patch_date(dates[i])
            else:
                paths[i] = paths[(i+1)%2]
                dates[i] = EPOCH_DATE
        
        if not binary:
            self.cursor.insertText('--- %s %s\n' % (paths[0], dates[0]),
                                      self.monospacedBoldInsertFormat)
            self.cursor.insertText('+++ %s %s\n' % (paths[1], dates[1]),
                                   self.monospacedBoldDeleteFormat)

            def fix_last_line(lines):
                """Fix last line if there is no new line.

                @param  lines:  original list of lines
                @return:    lines if lastline is OK,
                            or new list with fixed last line.
                """
                if lines:
                    last = lines[-1]
                    if last and last[-1] not in ('\r', '\n'):
                        last += ('\n' +
                                 gettext('\\ No newline at end of file') +
                                 '\n')
                        lines = lines[:-1] + [last]
                return lines

            a = fix_last_line(lines[0])
            b = fix_last_line(lines[1])

            for i, group in enumerate(groups):
                i1, i2, j1, j2 = group[0][1], group[-1][2], group[0][3], group[-1][4]
                self.cursor.insertText("@@ -%d,%d +%d,%d @@\n" % (i1+1, i2-i1, j1+1, j2-j1), self.monospacedHunkFormat)
                for tag, i1, i2, j1, j2 in group:
                    ni = i2 - i1
                    nj = j2 - j1
                    if tag == "equal":
                        text = "".join(" " + l for l in a[i1:i2])
                        self.cursor.insertText(text, self.monospacedFormat)
                    else:
                        text = "".join("-" + l for l in a[i1:i2])
                        self.cursor.insertText(text, self.monospacedDeleteFormat)
                        text = "".join("+" + l for l in b[j1:j2])
                        self.cursor.insertText(text, self.monospacedInsertFormat)
        else:
            self.cursor.insertText("Binary files %s %s and %s %s differ\n" % \
                                   (paths[0], dates[0], paths[1], dates[1]))
        self.cursor.insertText("\n")
