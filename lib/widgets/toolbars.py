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
from bzrlib.plugins.qbzr.lib.decorators import lazy_call
import sip

def create_toolbar_button(text, parent=None, icon_name=None, icon_size=22,
                enabled=True, checkable=False, checked=False, 
                shortcut=None, onclick=None):
    if icon_name:
        button = QtGui.QAction(get_icon(icon_name, size=icon_size),
                                gettext(text), parent)
    else:
        button = QtGui.QAction(gettext(text), parent)
    if checkable:
        button.setCheckable(True)
        button.setChecked(checked)
        signal = "toggled(bool)"
    else:
        signal = "triggered()"
    if not enabled:
        button.setEnabled(False)
    if shortcut:
        button.setShortcut(shortcut)
        show_shortcut_hint(button)
    if onclick:
        parent.connect(button, QtCore.SIGNAL(signal), onclick)
    return button

def add_toolbar_button(toolbar, text, parent, icon_name=None, icon_size=22,
                        enabled=True, checkable=False, checked=False,
                        shortcut=None, onclick=None): 
    button = create_toolbar_button(text, parent, icon_name, icon_size, 
                        enabled, checkable, checked, shortcut, onclick)
    toolbar.addAction(button)
    return button


class FindToolbar(QtGui.QToolBar):

    def __init__(self, window, text_edit, show_action):
        QtGui.QToolBar.__init__(self, gettext("Find"), window)
        self.text_edits = []
        if isinstance(text_edit, list) or isinstance(text_edit, tuple):
            self.set_text_edits(text_edit)
        else:
            self.set_text_edits([text_edit])
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
        self.highlight()
    
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

    def set_text_edits(self, text_edits):
        if len(text_edits) == 0:
            raise ValueError('text_edits is empty.')

        for t in self.text_edits:
            self.disconnect(t, QtCore.SIGNAL("documentChangeFinished()"), 
                    self.highlight)
            t.setExtraSelections([])

        for t in text_edits:
            t.highlight_lines = []
            self.connect(t, QtCore.SIGNAL("documentChangeFinished()"), 
                    self.highlight)

        self.text_edits = text_edits
        self.text_edit = text_edits[0]
        self.highlight()

    def set_text_edit(self, text_edit):
        if text_edit in self.text_edits:
            self.text_edit = text_edit
        else:
            raise ValueError('Invalid text_edit instance.')

    @lazy_call(200, per_instance=True)
    def highlight(self):
        """Highlight matched words in the text edits."""
        if sip.isdeleted(self):
            return
        text = self.find_text.text()
        flags = self.find_get_flags()
        for text_edit in self.text_edits:
            selections = []
            highlight_lines = []
            if text:
                find = text_edit.document().find
                pos = 0
                fmt = QtGui.QTextCharFormat()
                fmt.setBackground(QtCore.Qt.yellow)
                while True:
                    cursor = find(text, pos, flags)
                    if cursor.isNull():
                        break

                    sel = QtGui.QTextEdit.ExtraSelection()
                    sel.cursor, sel.format = cursor, fmt
                    selections.append(sel)
                    highlight_lines.append(cursor.blockNumber())
                    pos = cursor.selectionEnd()

            text_edit.setExtraSelections(selections)
            text_edit.highlight_lines = highlight_lines

        self.emit(QtCore.SIGNAL("highlightChanged()"))

class ToolbarPanel(QtGui.QWidget):
    def __init__(self, slender=True, icon_size=16, parent=None):
        QtGui.QWidget.__init__(self, parent)
        vbox = QtGui.QVBoxLayout(self)
        vbox.setSpacing(0)
        vbox.setMargin(0)

        toolbar = QtGui.QToolBar(self)
        toolbar.setMovable(False)
        toolbar.setIconSize(QtCore.QSize(icon_size,icon_size))
        self.icon_size=icon_size
        if slender:
            self.setStyleSheet('QToolBar { margin:1px; padding:0px; border:none; }')
        toolbar.setToolButtonStyle(QtCore.Qt.ToolButtonTextBesideIcon)

        vbox.addWidget(toolbar)
        self.vbox = vbox
        self.toolbar = toolbar

    def add_toolbar_button(self, text, icon_name=None, icon_size=0, enabled=True, 
            checkable=False, checked=False, shortcut=None, onclick=None, menu=None):
        button = create_toolbar_button(text, self, icon_name=icon_name,
                icon_size=icon_size or self.icon_size, enabled=enabled, 
                checkable=checkable, checked=checked, shortcut=shortcut, onclick=onclick)
        if menu is not None:
            button.setMenu(menu)
        self.toolbar.addAction(button)
        return button

    def add_toolbar_menu(self, text, menu, icon_name=None, icon_size=0, enabled=True, shortcut=None):
        button = self.add_toolbar_button(text, icon_name=icon_name, 
                    icon_size=icon_size or self.icon_size, enabled=enabled, menu=menu)
        widget = self.toolbar.widgetForAction(button)
        widget.setPopupMode(QtGui.QToolButton.InstantPopup)
        if shortcut:
            widget.setShortcut(shortcut)
            show_shortcut_hint(widget)
        return button

    def create_button(self, text, icon_name=None, icon_size=0, enabled=True,
            checkable=False, checked=False, shortcut=None, onclick=None):
        return create_toolbar_button(text, self, icon_name=icon_name, 
                icon_size=icon_size or self.icon_size, enabled=enabled, 
                checkable=checkable, checked=checked, shortcut=shortcut, onclick=onclick)

    def add_separator(self):
        self.toolbar.addSeparator()

    def add_widget(self, widget):
        self.vbox.addWidget(widget)

    def add_layout(self, layout):
        self.vbox.addLayout(layout)

class LayoutSelector(QtGui.QMenu):
    """Menu to select layout."""
    def __init__(self, num, onchanged, parent=None, initial_no=1):
        QtGui.QMenu.__init__(self, gettext('Layout'), parent)

        self.current = initial_no
        
        def selected(no):
            self.current = initial_no
            onchanged(no)

        def get_handler(no):
            return lambda:selected(no)
        
        group = QtGui.QActionGroup(self)
        self.buttons = []
        for i in range(1, num + 1):
            btn = create_toolbar_button(gettext("Layout %d") % i, self,
                        checkable=True, shortcut="Ctrl+%d" % i, 
                        checked=(i == initial_no),
                        onclick=get_handler(i))
            group.addAction(btn)
            self.addAction(btn)
            self.buttons.append(btn)

