# -*- coding: utf-8 -*-
#
# QBzr - Qt frontend to Bazaar commands
# Copyright (C) 2011 QBzr Developers
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

GBAR_LEFT  = 1
GBAR_RIGHT = 2

class _Entry(object):
    """
    Represent each group of guide bar.

    :key:   string key to identify this group
    :color: color or marker
    :data:  marker positions, list of tuple (block index, num of blocks)
    :index: index of the column to render this entry.
            * Two or more groups can be rendered on same columns.
            * If index == -1, the group is renderd on all columns.
    """
    __slots__ = ['key', 'color', 'data', 'index']
    def __init__(self, key, color, index=0):
        self.key = key
        self.color = color
        self.data = []
        self.index = index

class PlainTextEditHelper(QtCore.QObject):
    """
    Helper class to encapsulate gap between QPlainTextEdit and QTextEdit
    """
    def __init__(self, edit):
        QtCore.QObject.__init__(self)
        if not isinstance(edit, QtGui.QPlainTextEdit):
            raise ValueError('edit must be QPlainTextEdit')
        self.edit = edit

        self.connect(edit, QtCore.SIGNAL("updateRequest(const QRect&, int)"),
                     self.onUpdateRequest)

    def onUpdateRequest(self, rect, dy):
        self.emit(QtCore.SIGNAL("updateRequest()"))

    def center_block(self, block):
        """
        scroll textarea as specified block locates to center

        NOTE: This code is based on Qt source code (qplaintextedit.cpp)
        """
        edit = self.edit
        height = edit.viewport().rect().height() / 2
        h = self.edit.blockBoundingRect(block).center().y()
        def iter_visible_block_backward(b):
            while True:
                b = b.previous()
                if not b.isValid(): return
                if b.isVisible():   yield b
        for block in iter_visible_block_backward(block):
            h += edit.blockBoundingRect(block).height()
            if height < h:
                break
        edit.verticalScrollBar().setValue(block.firstLineNumber())

class TextEditHelper(QtCore.QObject):
    """
    Helper class to encapsulate gap between QPlainTextEdit and QTextEdit
    """
    def __init__(self, edit):
        QtCore.QObject.__init__(self)
        if not isinstance(edit, QtGui.QTextEdit):
            raise ValueError('edit must be QTextEdit')
        self.edit = edit

        self.connect(edit.verticalScrollBar(), QtCore.SIGNAL("valueChanged(int)"),
                     self.onVerticalScroll)

    def onVerticalScroll(self, value):
        self.emit(QtCore.SIGNAL("updateRequest()"))

    def center_block(self, block):
        """
        scroll textarea as specified block locates to center
        """
        y = block.layout().position().y()
        vscroll = self.edit.verticalScrollBar()
        vscroll.setValue(y - vscroll.pageStep() / 2)

def get_edit_helper(edit):
    if isinstance(edit, QtGui.QPlainTextEdit):
        return PlainTextEditHelper(edit)
    if isinstance(edit, QtGui.QTextEdit):
        return TextEditHelper(edit)
    raise ValueError("edit is unsupported type.")

class GuideBar(QtGui.QWidget):
    """
    Vertical bar attached to TextEdit.
    This shows that where changed or highlighted lines are.

    Guide bar can have multiple columns.
    """
    def __init__(self, edit, base_width=10, parent=None):
        """
        :edit:          target widget, must be QPlainTextEdit or QTextEdit
        :base_width:    width of each column.
        """
        QtGui.QWidget.__init__(self, parent)
        self.base_width = base_width
        self.edit = edit
        self._helper = get_edit_helper(edit)
        self.block_count = 0

        self.connect(edit, QtCore.SIGNAL("documentChangeFinished()"), 
                     self.reset_gui)
        self.connect(edit.verticalScrollBar(), QtCore.SIGNAL("rangeChanged(int, int)"),
                     self.vscroll_rangeChanged)

        self.connect(self._helper, QtCore.SIGNAL("updateRequest()"), self.update)

        self.entries = {}
        self.vscroll_visible = None

    def add_entry(self, key, color, index=0):
        """
        Add marker group
        """
        entry = _Entry(key, color, index)
        self.entries[key] = entry

    def vscroll_rangeChanged(self, min, max):
        vscroll_visible = (min < max)
        if self.vscroll_visible != vscroll_visible:
            self.vscroll_visible = vscroll_visible
            self.reset_gui()
        self.update()

    def reset_gui(self):
        """
        Determine show or hide, and num of columns.
        """
        # Hide when vertical scrollbar is not shown.
        if not self.vscroll_visible:
            self.setVisible(False)
            return
        valid_entries = [e for e in self.entries.itervalues() if e.data]
        if not valid_entries:
            self.setVisible(False)
            return

        self.setVisible(True)
        self.repeats = len(set([e.index for e in valid_entries if e.index >= 0]))
        if self.repeats == 0:
            self.repeats = 1
        self.setFixedWidth(self.repeats * self.base_width + 4)

        self.block_count = self.edit.document().blockCount()
        self.update()

    def update_data(self, **data):
        """
        Update each marker positions.

        :arg_name:  marker key
        :value:     list of marker positions.
                    Each position is tuple of (block index, num of blocks).
        """
        for key, value in data.iteritems():
            self.entries[key].data[:] = value
        self.reset_gui()

    def get_visible_block_range(self):
        """
        Return tuple of (index of first visible block, num of visible block)
        """
        pos = QtCore.QPoint(0, 1)
        block = self.edit.cursorForPosition(pos).block()
        first_visible_block = block.blockNumber()

        y = self.edit.viewport().height()

        pos = QtCore.QPoint(0, y)
        block = self.edit.cursorForPosition(pos).block()
        if block.isValid():
            visible_blocks = block.blockNumber() - first_visible_block + 1
        else:
            visible_blocks = self.block_count - first_visible_block + 1

        return first_visible_block, visible_blocks

    def paintEvent(self, event):
        QtGui.QWidget.paintEvent(self, event)
        painter = QtGui.QPainter(self)
        painter.fillRect(event.rect(), QtCore.Qt.white)
        if self.block_count == 0:
            return
        block_height = float(self.height()) / self.block_count

        def get_top_and_height(index, num):
            y, height = index * block_height, num * block_height
            # Inflate height if it is smaller than 1.
            if height < 1:
                return y - (1-height)/2, 1
            else:
                return y, height

        # Draw entries
        x_origin = 2
        index = -1
        prev_index = -1
        for e in sorted(self.entries.itervalues(), 
                        key=lambda x:x.index if x.index >= 0 else 999):
            if not e.data:
                continue
            if e.index < 0:
                x, width = 0, self.width()
            else:
                if e.index != prev_index:
                    index += 1
                    prev_index = e.index
                x, width = x_origin + index * self.base_width, self.base_width
            for block_index, block_num in e.data:
                y, height = get_top_and_height(block_index, block_num)
                painter.fillRect(QtCore.QRectF(x, y, width, height), e.color)

        # Draw scroll indicator.
        x, width = 0, self.width()
        first_block, visible_blocks = self.get_visible_block_range()
        y, height = get_top_and_height(first_block, visible_blocks)
        painter.fillRect(QtCore.QRectF(x, y, width, height), QtGui.QColor(0, 0, 0, 24))

    def mousePressEvent(self, event):
        QtGui.QWidget.mousePressEvent(self, event)
        if event.button() == QtCore.Qt.LeftButton:
            self.scroll_to_pos(event.y())

    def mouseMoveEvent(self, event):
        QtGui.QWidget.mouseMoveEvent(self, event)
        self.scroll_to_pos(event.y())

    def scroll_to_pos(self, y):
        block_no = int(float(y) / self.height() * self.block_count)
        block = self.edit.document().findBlockByNumber(block_no)
        if not block.isValid():
            return
        self._helper.center_block(block)

class GuideBarPanel(QtGui.QWidget):
    """
    Composite widget of TextEdit and GuideBar
    """
    def __init__(self, edit, base_width=10, align=GBAR_RIGHT, parent=None):
        QtGui.QWidget.__init__(self, parent)
        hbox = QtGui.QHBoxLayout(self)
        hbox.setSpacing(0)
        hbox.setMargin(0)
        self.bar = GuideBar(edit, base_width=base_width, parent=parent)
        self.edit = edit
        if align == GBAR_RIGHT:
            hbox.addWidget(self.edit)
            hbox.addWidget(self.bar)
        else:
            hbox.addWidget(self.bar)
            hbox.addWidget(self.edit)

    def add_entry(self, key, color, index=0):
        self.bar.add_entry(key, color, index)

    def reset_gui(self):
        self.bar.reset_gui()

    def update_data(self, **data):
        return self.bar.update_data(**data)

def setup_guidebar_for_find(guidebar, find_toolbar, index=0):
    """
    Make guidebar enable to show positions that highlighted by FindToolBar
    """
    def on_highlight_changed():
        if guidebar.edit in find_toolbar.text_edits:
            guidebar.update_data(
                find=[(n, 1) for n in guidebar.edit.highlight_lines]
            )
    guidebar.add_entry('find', QtGui.QColor(255, 196, 0), index) # Gold
    guidebar.connect(find_toolbar, QtCore.SIGNAL("highlightChanged()"),
                     on_highlight_changed)
