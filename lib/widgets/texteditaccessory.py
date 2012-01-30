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
from bzrlib import errors

GBAR_LEFT  = 1
GBAR_RIGHT = 2

class _Entry(object):
    __slots__ = ['key', 'color', 'data', 'index']
    def __init__(self, key, color, index=0):
        self.key = key
        self.color = color
        self.data = []
        self.index = index

class GuideBar(QtGui.QWidget):
    def __init__(self, edit, base_width=10, parent=None):
        QtGui.QWidget.__init__(self, parent)
        self.base_width = base_width
        self.edit = edit
        self.block_count = 0

        if not isinstance(edit, QtGui.QTextEdit) and \
           not isinstance(edit, QtGui.QPlainTextEdit):
            raise ValueError('edit must be QTextEdit or QPlainTextEdit')

        self.connect(edit, QtCore.SIGNAL("documentChangeFinished()"), 
                     self.reset_gui)
        self.connect(edit.verticalScrollBar(), QtCore.SIGNAL("valueChanged(int)"),
                     lambda val: self.update())
        self.connect(edit.verticalScrollBar(), QtCore.SIGNAL("rangeChanged(int, int)"),
                     self.vscroll_rangeChanged)
        if isinstance(edit, QtGui.QPlainTextEdit):
            self.connect(edit, QtCore.SIGNAL("updateRequest(const QRect&, int)"),
                         lambda r, dy:self.update())

        self.entries = {}
        self.vscroll_visible = None

    def add_entry(self, key, color, index=0):
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
        Determine show or hide, and width of guidebar.
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
        for key, value in data.iteritems():
            self.entries[key].data[:] = value
        self.reset_gui()

    def get_visible_block_range(self):
        pos = QtCore.QPoint(0, 1)
        block = self.edit.cursorForPosition(pos).block()
        first_visible_block = block.blockNumber()

        y = self.geometry().height()
        scrollbar = self.edit.horizontalScrollBar()
        if scrollbar.isVisible():
            y -= scrollbar.height()

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
        painter.setRenderHints(QtGui.QPainter.Antialiasing, True)
        block_height = float(self.height()) / self.block_count

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
                y = block_index * block_height
                height = max(1, block_num * block_height)
                painter.fillRect(x, y, width, height, e.color)

        # Draw scroll indicator.
        x, width = 0, self.width()
        first_block, visible_blocks = self.get_visible_block_range()
        y, height = first_block * block_height, max(1, visible_blocks * block_height)
        painter.fillRect(x, y, width, height, QtGui.QColor(0, 0, 0, 24))

class GuideBarPanel(QtGui.QWidget):
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
    def on_highlight_changed():
        if guidebar.edit in find_toolbar.text_edits:
            guidebar.update_data(
                find=[(n, 1) for n in guidebar.edit.highlight_lines]
            )
    guidebar.add_entry('find', QtGui.QColor(255, 196, 0), index)
    guidebar.connect(find_toolbar, QtCore.SIGNAL("highlightChanged()"),
                     on_highlight_changed)
