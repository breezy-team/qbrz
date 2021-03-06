# -*- coding: utf-8 -*-
#
# QBzr - Qt frontend to Bazaar commands
# Copyright (C) 2009 Gary van der Merwe <garyvdm@gmail.com>
#
# Some of this code was coppied from
# http://john.nachtimwald.com/better-qplaintextedit-with-line-numbers/
# Copyright (C) 2009 John Schember
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

from PyQt5 import QtCore, QtGui, QtWidgets


class AnnotateBarBase(QtWidgets.QWidget):
    cursorPositionChanged = QtCore.pyqtSignal()

    def __init__(self, edit, parent):
        QtWidgets.QWidget.__init__(self, parent)
        self.edit = edit
        self.edit.updateRequest[QtCore.QRect, int].connect(self.updateContents)

    def paintEvent(self, event):
        current_line = self.edit.document().findBlock(
            self.edit.textCursor().position()).blockNumber() + 1

        block = self.edit.firstVisibleBlock()
        line_count = block.blockNumber()
        painter = QtGui.QPainter(self)
        painter.fillRect(event.rect(), self.palette().window())

        # Iterate over all visible text blocks in the document.
        while block.isValid():
            line_count += 1
            rect = self.edit.blockBoundingGeometry(block)
            rect = rect.translated(self.edit.contentOffset())
            rect.setWidth(self.width())

            # Check if the position of the block is out side of the visible
            # area.
            if not block.isVisible() or rect.top() >= event.rect().bottom():
                break
            self.paint_line(painter, rect, line_count, line_count==current_line)
            block = block.next()

        painter.end()

        QtWidgets.QWidget.paintEvent(self, event)

    def paint_line(self, painter, rect, line_number, is_current):
        pass

    def updateContents(self, rect, scroll):
        if scroll:
            self.scroll(0, scroll)
        else:
            self.update(0, rect.y(), self.width(), rect.height())

    def mousePressEvent(self, event):
        if event.button() == QtCore.Qt.LeftButton:
            cursor = self.edit.cursorForPosition(event.pos())
            cursor.movePosition(QtGui.QTextCursor.StartOfBlock)
            cursor.movePosition(QtGui.QTextCursor.EndOfBlock,
                                QtGui.QTextCursor.KeepAnchor)
            self.edit.setTextCursor(cursor)
            self.cursorPositionChanged.emit()

    def wheelEvent(self, event):
        self.edit.wheelEvent(event)


class LineNumberBar(AnnotateBarBase):

    def __init__(self, edit, parent):
        super(LineNumberBar, self).__init__(edit, parent)
        self.adjustWidth(1)
        self.edit.blockCountChanged[int].connect(self.adjustWidth)

    def adjustWidth(self, count):
        width = self.fontMetrics().width(str(count))
        text_margin = self.style().pixelMetric(
            QtWidgets.QStyle.PM_FocusFrameHMargin, None, self) + 1
        width += text_margin * 2
        if self.width() != width:
            self.setFixedWidth(width)

    def paint_line(self, painter, rect, line_number, is_current):
        text_margin = self.style().pixelMetric(
            QtWidgets.QStyle.PM_FocusFrameHMargin, None, self) + 1
        painter.drawText(rect.adjusted(text_margin, 0, -text_margin, 0),
                         QtCore.Qt.AlignRight, str(line_number))


class AnnotateEditerFrameBase(QtWidgets.QFrame):

    def __init__(self, parent = None):
        QtWidgets.QFrame.__init__(self,parent)

        self.setFrameStyle(QtWidgets.QFrame.StyledPanel | QtWidgets.QFrame.Sunken)

        self.hbox = QtWidgets.QHBoxLayout(self)
        self.hbox.setSpacing(0)
        self.hbox.setContentsMargins(0, 0, 0, 0)


class LineNumberEditerFrame(AnnotateEditerFrameBase):

    def __init__(self, parent= None):
        super(LineNumberEditerFrame, self).__init__(parent)
        self.edit = QtWidgets.QPlainTextEdit(self)
        self.edit.setFrameStyle(QtWidgets.QFrame.NoFrame)

        self.number_bar = LineNumberBar(self.edit, self)
        self.hbox.addWidget(self.number_bar)
        self.hbox.addWidget(self.edit)

    def setFocus(self):
        self.edit.setFocus()
