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

from PyQt4 import QtCore, QtGui

if not hasattr(QtGui, 'QDialogButtonBox'):
    class FakeQDialogButtonBox(QtGui.QWidget):
        """Fake QDialogButtonBox for Qt 4.1"""
        Ok = 1
        Cancel = 2
        Close = 4

        def __init__(self, buttons, orientation, parent=None):
            QtGui.QWidget.__init__(self, parent)
            self.hbox = QtGui.QHBoxLayout(self)
            self.hbox.setMargin(0)
            self.hbox.addStretch()
            if buttons & self.Ok:
                button = QtGui.QPushButton('Ok')
                self.hbox.addWidget(button)
                self.connect(button, QtCore.SIGNAL('clicked()'), self, QtCore.SIGNAL('accepted()'))
            if buttons & self.Cancel:
                button = QtGui.QPushButton('Cancel')
                self.hbox.addWidget(button)
                self.connect(button, QtCore.SIGNAL('clicked()'), self, QtCore.SIGNAL('rejected()'))
            if buttons & self.Close:
                button = QtGui.QPushButton('Close')
                self.hbox.addWidget(button)
                self.connect(button, QtCore.SIGNAL('clicked()'), self, QtCore.SIGNAL('rejected()'))

        @staticmethod
        def StandardButtons(buttons):
            return buttons

    QtGui.QDialogButtonBox = FakeQDialogButtonBox


class QBzrWindow(QtGui.QMainWindow):

    def __init__(self, title=[], size=(540, 500), parent=None):
        QtGui.QMainWindow.__init__(self, parent)

        self.setWindowTitle(" - ".join(["QBzr"] + title))
        icon = QtGui.QIcon()
        icon.addFile(":/bzr-16.png", QtCore.QSize(16, 16))
        icon.addFile(":/bzr-48.png", QtCore.QSize(48, 48))
        self.setWindowIcon(icon)
        self.resize(QtCore.QSize(size[0], size[1]).expandedTo(self.minimumSizeHint()))

        self.centralwidget = QtGui.QWidget(self)
        self.setCentralWidget(self.centralwidget)


