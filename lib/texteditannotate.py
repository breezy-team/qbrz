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

from PyQt4 import QtCore, QtGui


class AnnotateBarBase(QtGui.QWidget):

    def __init__(self, edit, parent):
        QtGui.QWidget.__init__(self, parent)
        self.edit = edit
        self.connect(self.edit,
            QtCore.SIGNAL("updateRequest(const QRect&,int)"),
            self.updateContents)

    def paintEvent(self, event):
        current_line = self.edit.document().findBlock(
            self.edit.textCursor().position()).blockNumber() + 1

        block = self.edit.firstVisibleBlock()
        line_count = block.blockNumber()
        painter = QtGui.QPainter(self)
        painter.fillRect(event.rect(), self.palette().background())

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
        
        QtGui.QWidget.paintEvent(self, event)
    
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
            self.emit(QtCore.SIGNAL("cursorPositionChanged()"))
    
    def wheelEvent(self, event):
        self.edit.wheelEvent(event)


class LineNumberBar(AnnotateBarBase):

    def __init__(self, edit, parent):
        super(LineNumberBar, self).__init__(edit, parent)
        self.adjustWidth(1)
        self.connect(self.edit,
            QtCore.SIGNAL("blockCountChanged(int)"),
            self.adjustWidth)

    def adjustWidth(self, count):
        width = self.fontMetrics().width(unicode(count))
        text_margin = self.style().pixelMetric(
            QtGui.QStyle.PM_FocusFrameHMargin, None, self) + 1
        width += text_margin * 2
        if self.width() != width:
            self.setFixedWidth(width)
    
    def paint_line(self, painter, rect, line_number, is_current):
        text_margin = self.style().pixelMetric(
            QtGui.QStyle.PM_FocusFrameHMargin, None, self) + 1
        painter.drawText(rect.adjusted(text_margin, 0, -text_margin, 0),
                         QtCore.Qt.AlignRight, unicode(line_number))


class AnnotateEditerFrameBase(QtGui.QFrame):

    def __init__(self, parent = None):
        QtGui.QFrame.__init__(self,parent)

        self.setFrameStyle(QtGui.QFrame.StyledPanel | QtGui.QFrame.Sunken)

        self.hbox = QtGui.QHBoxLayout(self)
        self.hbox.setSpacing(0)
        self.hbox.setMargin(0)


class LineNumberEditerFrame(AnnotateEditerFrameBase):
    
    def __init__(self, parent= None):
        super(LineNumberEditerFrame, self).__init__(parent)
        self.edit = QtGui.QPlainTextEdit(self)
        self.edit.setFrameStyle(QtGui.QFrame.NoFrame)
        
        self.number_bar = LineNumberBar(self.edit, self)
        self.hbox.addWidget(self.number_bar)
        self.hbox.addWidget(self.edit)

    def setFocus(self):
        self.edit.setFocus()
