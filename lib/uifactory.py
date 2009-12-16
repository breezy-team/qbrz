#!/usr/bin/env python
# -*- coding: utf-8 -*-
#
# QBzr - Qt frontend to Bazaar commands
# Copyright (C) 2008 Gary van der Merwe <garyvdm@gmail.com>
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
import time

from bzrlib import ui
from bzrlib.plugins.qbzr.lib.i18n import gettext

def ui_current_widget(f):
    def decorate(*args, **kargs):
        if isinstance(ui.ui_factory, QUIFactory):
            ui.ui_factory.current_widget_stack.append(args[0])
            try:
                r = f(*args, **kargs)
            finally:
                del ui.ui_factory.current_widget_stack[-1]
            return r
        else:
            return f(*args, **kargs)
    return decorate

def quifactory():
    if isinstance(ui.ui_factory, QUIFactory):
        return ui.ui_factory
    return None

def current_throbber():
    ui = quifactory()
    if ui:
        return ui.throbber()
    return None

class QUIFactory(ui.UIFactory):

    def __init__(self):
        super(QUIFactory, self).__init__()
        self.current_widget_stack = []
        
        self._transport_update_time = 0
        self._total_byte_count = 0
        self._bytes_since_update = 0
        self._transport_rate = None
    
    def current_widget(self):
        if self.current_widget_stack:
            return self.current_widget_stack[-1]
        return None
    
    def throbber(self):
        current_widget = self.current_widget()
        if current_widget and getattr(current_widget, 'throbber', None) is not None:
            return current_widget.throbber
        return None
    
    def report_transport_activity(self, transport, byte_count, direction):
        """Called by transports as they do IO.
        
        This may update a progress bar, spinner, or similar display.
        By default it does nothing.
        """
        
        self._total_byte_count += byte_count
        self._bytes_since_update += byte_count

        throbber = self.throbber()
        if throbber:
            now = time.time()
            if self._transport_update_time is None:
                self._transport_update_time = now
            elif now >= (self._transport_update_time + 0.2):
                # guard against clock stepping backwards, and don't update too
                # often
                self._transport_rate  = self._bytes_since_update / (now - self._transport_update_time)
                self._transport_update_time = now
                self._bytes_since_update = 0
            
            if self._transport_rate:
                msg = ("%6dkB @ %4dkB/s" %
                    (self._total_byte_count>>10, int(self._transport_rate)>>10,))
            else:
                msg = ("%6dkB @         " %
                    (self._total_byte_count>>10,))
            
            throbber.transport.setText(msg)
        
        QtCore.QCoreApplication.processEvents()

    def get_password(self, prompt='', **kwargs):
        password, ok = QtGui.QInputDialog.getText(self.current_widget(),
                                                  gettext("Enter Password"),
                                                  (prompt % kwargs),
                                                  QtGui.QLineEdit.Password)
        
        if ok:
            return str(password)
        else:
            raise KeyboardInterrupt()

    def get_username(self, prompt='', **kwargs):
        username, ok = QtGui.QInputDialog.getText(self.current_widget(),
                                                  gettext("Enter Username"),
                                                  (prompt % kwargs))
        
        if ok:
            return str(username)
        else:
            raise KeyboardInterrupt()
    
    def get_boolean(self, prompt):
        button = QtGui.QMessageBox.question(
            self.current_widget(), "Bazaar", prompt,
            QtGui.QMessageBox.Yes, QtGui.QMessageBox.No)
        
        return button == QtGui.QMessageBox.Yes

    def clear_term(self):
        """Prepare the terminal for output.

        This will, for example, clear text progress bars, and leave the
        cursor at the leftmost position."""
        pass
    

# You can run this file to test the ui factory. This is not in the test suit
# because it actualy open the ui, and so user interaction is required to run
# the test.
if __name__ == "__main__":
    application = QtGui.QApplication([])
    ui_factory = QUIFactory()
    print ui_factory.get_username("Enter password 123")
    #print ui_factory.get_boolean("Question?")
