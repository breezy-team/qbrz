# -*- coding: utf-8 -*-
#
# QBzr - Qt frontend to Bazaar commands
# Copyright (C) 2009 Mark Hammond <mhammond@skippinet.com.au>
# Copyright (C) 2009 Gary van der Merwe <garyvdm@gmail.com>
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

import sys

from PyQt4 import QtCore, QtGui

from bzrlib import errors

from bzrlib.plugins.qbzr.lib.i18n import gettext, N_, ngettext

class StopException(Exception):
    """A exception that is ignored in our error reporting, which can be used
    to stop a process due to user action. (Similar to KeyInterupt)
    """
    pass

MAIN_LOAD_METHOD = 0
"""The exception is beening reported from the main loading method.
Causes the window to be closed.
"""
SUB_LOAD_METHOD = 1
"""The exception is beening reported from the sub loading method.
Does not cause the window to me closed. This is typicaly used when a user
enters a branch location on one of our forms, and we try load that branch.
"""
ITEM_OR_EVENT_METHOD = 2
"""The exception is beening reported from a method that is called per item.
The user is allowed to ignore the error, or close the window.
"""

def report_exception(exc_info=None, type=MAIN_LOAD_METHOD, window=None):
    """Report an exception.

    The error is reported to the console or a message box, depending
    on the type. 
    """
    from cStringIO import StringIO
    import traceback
    from bzrlib.trace import report_exception

    if exc_info is None:
        exc_info = sys.exc_info()
    
    exc_type, exc_object, exc_tb = exc_info
    
    # Don't show error for StopException
    if isinstance(exc_object, StopException):
        # Do we maybe want to log this?
        return
    
    msg_box = (type == MAIN_LOAD_METHOD and window and window.ui_mode) \
              or not type == MAIN_LOAD_METHOD
    
    if msg_box:
        err_file = StringIO()
    else:
        err_file = sys.stderr
    
    # always tell bzr to report it, so it ends up in the log.        
    error_type = report_exception(exc_info, err_file)
    
    close = True
    if msg_box:
        if type == MAIN_LOAD_METHOD:
            buttons = QtGui.QMessageBox.Close
        elif type == SUB_LOAD_METHOD:
            buttons = QtGui.QMessageBox.Ok
        elif type == ITEM_OR_EVENT_METHOD:
            buttons == QtGui.QMessageBox.Close | QtGui.QMessageBox.Ignore
        
        if error_type == errors.EXIT_INTERNAL_ERROR:
            icon = QtGui.QMessageBox.Critical
        else:
            icon = QtGui.QMessageBox.Warning
        
        msg_box = QtGui.QMessageBox(icon,
                                    gettext("Error"),
                                    err_file.getvalue(),
                                    buttons,
                                    window)
        
        if error_type == errors.EXIT_INTERNAL_ERROR:
            # We need to make the dialog wider, becuase we are probably
            # showing a stack trace.
            # TODO: resize the msg box. I have tried every thing I can
            # think of - but can't get it to work. We might have to
            # remplement the msgbox.
            pass
            # To do: make link to fill bug page.
        
        msg_box.exec_()
        
        if not msg_box.result() == QtGui.QMessageBox.Close:
            close = False
    
    if close:
        if window is None:
            QtCore.QCoreApplication.instance().quit()
        else:
            window.close()


def reports_exception(type=MAIN_LOAD_METHOD):
    """Decorator to report Exceptions raised from the called method
    """
    def reports_exception_decorator(f):
        
        def reports_exception_decorate(*args, **kargs):
            try:
                return f(*args, **kargs)
            except Exception:
                # args[0] - typycaly self, may have it's own report_exception
                # method.
                if getattr(args[0], 'report_exception', None) is not None:
                    args[0].report_exception(type=type)
                else:
                    report_exception(type=type)
        
        return reports_exception_decorate
    
    return reports_exception_decorator
