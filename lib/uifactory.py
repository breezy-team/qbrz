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
from bzrlib.plugins.qbzr.lib.i18n import gettext, N_
from bzrlib.plugins.qbzr.lib.util import StopException

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
    
        self._progress_view._repaint = self.progress_view_repaint
    
    def report_transport_activity(self, transport, byte_count, direction):
        """Called by transports as they do IO.
        
        This may update a progress bar, spinner, or similar display.
        By default it does nothing.
        """
        
        self._total_byte_count += byte_count
        self._bytes_since_update += byte_count

        current_widget = self.current_widget()
        if current_widget and getattr(current_widget, 'throbber', None) is not None:
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
            
            current_widget.throbber.transport.setText(msg)
        
        QtCore.QCoreApplication.processEvents()
        if current_widget and getattr(current_widget, 'closing', None) is not None \
            and current_widget.closing:
            raise StopException()

    def get_password(self, prompt='', **kwargs):
        password, ok = QtGui.QInputDialog.getText(self.current_widget(),
                                                  gettext("Enter Password"),
                                                  (prompt % kwargs),
                                                  QtGui.QLineEdit.Password)
        
        if ok:
            return str(password)
        else:
            raise KeyboardInterrupt()
