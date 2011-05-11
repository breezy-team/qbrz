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

from bzrlib.plugins.qbzr.lib.util import (
    get_icon,
    show_shortcut_hint
    )

from PyQt4 import QtCore, QtGui
from bzrlib.plugins.qbzr.lib.i18n import gettext, N_

class FindToolbar(QtGui.QToolBar):

    def __init__(self, window, text_edit, show_action):
        QtGui.QToolBar.__init__(self, gettext("Find"), window)
        self.text_edit = text_edit
        if 0: self.text_edit = QtGui.QTextEdit()
        self.show_action = show_action
        
        self.setToolButtonStyle(QtCore.Qt.ToolButtonTextBesideIcon)
        self.setMovable (False)
        
        find_label = QtGui.QLabel(gettext("Find: "), self)
        self.addWidget(find_label)
        
        self.find_text = QtGui.QLineEdit(self)
        self.addWidget(self.find_text)
        find_label.setBuddy(self.find_text)

        self.found_palette = QtGui.QPalette()
        self.not_found_palette = QtGui.QPalette()
        self.not_found_palette.setColor(QtGui.QPalette.Active,
                QtGui.QPalette.Base,
                QtCore.Qt.red)
        self.not_found_palette.setColor(QtGui.QPalette.Active,
                QtGui.QPalette.Text,
                QtCore.Qt.white)
        
        prev = self.addAction(get_icon("go-previous"), gettext("Previous"))
        prev.setShortcut(QtGui.QKeySequence.FindPrevious)
        show_shortcut_hint(prev)
        
        next = self.addAction(get_icon("go-next"), gettext("Next"))
        next.setShortcut(QtGui.QKeySequence.FindNext)
        show_shortcut_hint(next)
        
        self.case_sensitive = QtGui.QCheckBox(gettext("Case sensitive"), self)
        self.addWidget(self.case_sensitive)
        self.whole_words = QtGui.QCheckBox(gettext("Whole words"), self)
        self.addWidget(self.whole_words)
        
        close_find = QtGui.QAction(self)
        close_find.setIcon(self.style().standardIcon(
                                        QtGui.QStyle.SP_DialogCloseButton))
        self.addAction(close_find)
        close_find.setShortcut((QtCore.Qt.Key_Escape))
        close_find.setShortcutContext(QtCore.Qt.WidgetWithChildrenShortcut)
        close_find.setStatusTip(gettext("Close find"))
        self.connect(self.show_action,
                     QtCore.SIGNAL("toggled (bool)"),
                     self.show_action_toggle)
        self.connect(close_find,
                     QtCore.SIGNAL("triggered(bool)"),
                     self.close_triggered)
        self.connect(self.find_text,
                     QtCore.SIGNAL("textChanged(QString)"),
                     self.find_text_changed)
        self.connect(next,
                     QtCore.SIGNAL("triggered(bool)"),
                     self.find_next)
        self.connect(prev,
                     QtCore.SIGNAL("triggered(bool)"),
                     self.find_prev)
        self.connect(self.case_sensitive,
                     QtCore.SIGNAL("stateChanged(int)"),
                     self.find_text_changed)
        self.connect(self.whole_words,
                     QtCore.SIGNAL("stateChanged(int)"),
                     self.find_text_changed)
        self.connect(self.find_text,
                     QtCore.SIGNAL("returnPressed()"),
                     self.find_next)        
        
    def show_action_toggle(self, state):
        self.setVisible(state)
        if state:
            self.find_text.setFocus()
        else:
            self.find_text.setText('')
    
    def close_triggered(self, state):
        self.show_action.setChecked(False)
    
    def find_text_changed(self, text):
        self.find_avoid_moving()
    
    def find_get_flags(self):
        flags = QtGui.QTextDocument.FindFlags()
        if self.case_sensitive.isChecked():
            flags = flags | QtGui.QTextDocument.FindCaseSensitively
        if self.whole_words.isChecked():
            flags = flags | QtGui.QTextDocument.FindWholeWords
        return flags
    
    def find_avoid_moving(self):
        self.find(self.text_edit.textCursor().selectionStart(), 0,
                  self.find_get_flags())
    
    def find_next(self):
        self.find(self.text_edit.textCursor().selectionEnd(), 0,
                  self.find_get_flags())
    
    def find_prev(self, state):
        self.find(self.text_edit.textCursor().selectionStart(),
                  self.text_edit.document().characterCount(),
                  self.find_get_flags() | QtGui.QTextDocument.FindBackward)
    
    def find(self, from_pos, restart_pos, flags):
        doc = self.text_edit.document()
        text = self.find_text.text()
        cursor = doc.find(text, from_pos, flags)
        if cursor.isNull():
            # try again from the restart pos
            cursor = doc.find(text, restart_pos, flags)
        if cursor.isNull():
            cursor = self.text_edit.textCursor()
            cursor.setPosition(cursor.selectionStart())
            self.text_edit.setTextCursor(cursor)
            # Make find_text background red like Firefox
            if len(text) > 0:
                self.find_text.setPalette(self.not_found_palette)
            else:
                self.find_text.setPalette(self.found_palette)
        else:
            self.text_edit.setTextCursor(cursor)
            self.find_text.setPalette(self.found_palette)

    def set_text_edit(self, new_text_edit):
        if self.text_edit:
            self.text_edit.setTextCursor(QtGui.QTextCursor())
        self.text_edit = new_text_edit


