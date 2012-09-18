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

"""Exception handeling and reporting.

Please see docs/exception_reporting.txt for info on how to use this.
"""

import sys
import os
from cStringIO import StringIO
import traceback

from PyQt4 import QtCore, QtGui

import bzrlib            
from bzrlib import (
    errors,
    osutils,
    plugin,
    )
from bzrlib.trace import (
    mutter,
    note,
    print_exception as _bzrlib_print_exception,
    report_exception as _bzrlib_report_exception,
    )
from bzrlib.plugins.qbzr.lib.i18n import gettext
import bzrlib.plugins.qbzr.lib.resources


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

_file_bugs_url = "https://bugs.launchpad.net/qbzr/+filebug"

def set_file_bugs_url(url):
    global _file_bugs_url
    _file_bugs_url = url

closing_due_to_error = False

def create_lockerror_dialog(type, window=None):
    msgbox = QtGui.QMessageBox(parent=window)
    msgbox.setIcon(QtGui.QMessageBox.Warning)
    msgbox.setText(gettext("Could not acquire lock. Please retry later."))
    if type == MAIN_LOAD_METHOD:
        msgbox.addButton(QtGui.QMessageBox.Close)
    else:
        msgbox.addButton(QtGui.QMessageBox.Ok)
    return msgbox

def report_exception(exc_info=None, type=MAIN_LOAD_METHOD, window=None,
                     ui_mode=False):
    """Report an exception.

    The error is reported to the console or a message box, depending
    on the type. 
    """

    # We only want one error to show if the user chose Close
    global closing_due_to_error
    # 0.20 special: We check hasattr() first to work around
    # <http://bugs.python.org/issue4230>
    if closing_due_to_error or \
            (hasattr(window, 'closing_due_to_error') and
             window.closing_due_to_error):
        return

    if exc_info is None:
        exc_info = sys.exc_info()
    
    exc_type, exc_object, exc_tb = exc_info
    
    # Don't show error for StopException
    if isinstance(exc_object, StopException):
        # Do we maybe want to log this?
        return
    
    msg_box = ((type == MAIN_LOAD_METHOD and
                (window and window.ui_mode or ui_mode)) 
               or not type == MAIN_LOAD_METHOD)
    pdb = os.environ.get('BZR_PDB')
    if pdb:
        msg_box = False
    
    if msg_box:
        err_file = StringIO()
    else:
        err_file = sys.stderr
    
    # always tell bzr to report it, so it ends up in the log.        
    # See https://bugs.launchpad.net/bzr/+bug/785695
    error_type = _bzrlib_report_exception(exc_info, err_file)
    backtrace = traceback.format_exception(*exc_info)
    mutter(''.join(backtrace))
    
    if (type == MAIN_LOAD_METHOD and window):
        window.ret_code = error_type
    
    # XXX This is very similar to bzrlib.commands.exception_to_return_code.
    # We shoud get bzr to refactor so that that this is reuseable.
    if pdb:
        # With out this - pyQt shows lot of warnings. see:
        # http://www.riverbankcomputing.co.uk/static/Docs/PyQt4/pyqt4ref.html#using-pyqt-from-the-python-shell
        QtCore.pyqtRemoveInputHook()
        
        print '**** entering debugger'
        tb = exc_info[2]
        import pdb
        if sys.version_info[:2] < (2, 6):
            # XXX: we want to do
            #    pdb.post_mortem(tb)
            # but because pdb.post_mortem gives bad results for tracebacks
            # from inside generators, we do it manually.
            # (http://bugs.python.org/issue4150, fixed in Python 2.6)
            
            # Setup pdb on the traceback
            p = pdb.Pdb()
            p.reset()
            p.setup(tb.tb_frame, tb)
            # Point the debugger at the deepest frame of the stack
            p.curindex = len(p.stack) - 1
            p.curframe = p.stack[p.curindex][0]
            # Start the pdb prompt.
            p.print_stack_entry(p.stack[p.curindex])
            p.execRcLines()
            p.cmdloop()
        else:
            pdb.post_mortem(tb)
    
    close = True
    if msg_box:
        if isinstance(exc_object, errors.LockContention):
            msg_box = create_lockerror_dialog(error_type, window)

        elif error_type == errors.EXIT_INTERNAL_ERROR:
            # this is a copy of bzrlib.trace.report_bug
            # but we seperate the message, and the trace back,
            # and addes a hyper link to the filebug page.
            traceback_file = StringIO()
            _bzrlib_print_exception(exc_info, traceback_file)
            traceback_file.write('\n')
            traceback_file.write('bzr %s on python %s (%s)\n' % \
                               (bzrlib.__version__,
                                bzrlib._format_version_tuple(sys.version_info),
                                sys.platform))
            traceback_file.write('arguments: %r\n' % sys.argv)
            traceback_file.write(
                'encoding: %r, fsenc: %r, lang: %r\n' % (
                    osutils.get_user_encoding(), sys.getfilesystemencoding(),
                    os.environ.get('LANG')))
            traceback_file.write("plugins:\n")
            for name, a_plugin in sorted(plugin.plugins().items()):
                traceback_file.write("  %-20s %s [%s]\n" %
                    (name, a_plugin.path(), a_plugin.__version__))
            
            
            msg_box = ErrorReport(gettext("Error"),
                                  True,
                                  traceback_file.getvalue(),
                                  exc_info,
                                  type,
                                  window)
        else:
            msg_box = ErrorReport(gettext("Error"),
                                  False,
                                  err_file.getvalue(),
                                  exc_info,
                                  type,
                                  window)
        if window is None:
            icon = QtGui.QIcon()
            icon.addFile(":/bzr-16.png", QtCore.QSize(16, 16))
            icon.addFile(":/bzr-32.png", QtCore.QSize(32, 32))
            icon.addFile(":/bzr-48.png", QtCore.QSize(48, 48))
            msg_box.setWindowIcon(icon)
        
        msg_box.exec_()
        
        if not msg_box.result() == QtGui.QMessageBox.Close:
            close = False
    
    if close:
        if window is None:
            closing_due_to_error = True
            QtCore.QCoreApplication.instance().quit()
        else:
            window.closing_due_to_error = True
            window.close()
    return error_type

class ErrorReport(QtGui.QDialog):
    """A dialogue box for displaying and optionally reporting crashes in bzr/qbzr/bzr explorer."""
    def __init__(self, title, message_internal, trace_back, exc_info, type=MAIN_LOAD_METHOD,
                 parent=None):

        QtGui.QDialog.__init__ (self, parent)

        self.buttonbox = QtGui.QDialogButtonBox()

        if parent:
            win_title = None
            if hasattr(parent, 'title'):
                if isinstance(parent.title, basestring):
                    win_title = parent.title
                elif isinstance(title, (list, tuple)):
                    # just the first item is more usefull.
                    win_title = parent.title[0]            
            else:
                if hasattr(parent, 'windowTitle'):
                    win_title = parent.windowTitle()
            
            if win_title:
                close_label = gettext("Close %s Window") % win_title
            else:
                close_label = gettext("Close Window")
        else:
            close_label = gettext("Close Application")
        
        # PyQt is stupid and thinks QMessageBox.StandardButton and
        # QDialogButtonBox.StandardButton are different, so we have to
        # duplicate this :-(
        if type == MAIN_LOAD_METHOD:
            button = self.buttonbox.addButton(QtGui.QDialogButtonBox.Close)
            button.setText(close_label)
        elif type == SUB_LOAD_METHOD:
            button = self.buttonbox.addButton(QtGui.QDialogButtonBox.Ok)
            button.setText(gettext("Close Error Dialog"))
        elif type == ITEM_OR_EVENT_METHOD:
            button = self.buttonbox.addButton(QtGui.QDialogButtonBox.Close)
            button.setText(close_label)
            button = self.buttonbox.addButton(QtGui.QDialogButtonBox.Ignore)
            button.setText(gettext("Ignore Error"))

        def report_bug():
            from bzrlib import crash
            #Using private method because bzrlib.crash is not currently intended for reuse from GUIs
            #see https://bugs.launchpad.net/bzr/+bug/785696
            crash_filename = crash._write_apport_report_to_file(exc_info)

        try:
            import apport
        except ImportError, e:
            mutter("No Apport available to Bazaar")
            if message_internal:
                message = ('Bazaar has encountered an internal error. Please ' 
                           'report a bug at <a href="%s">%s</a> including this ' 
                           'traceback, and a description of what you were doing ' 
                           'when the error occurred.'
                           % (_file_bugs_url, _file_bugs_url))
            else:
                message = ('Bazaar has encountered an environmental error. Please ' 
                           'report a bug if this is not the result of a local problem '
                           'at <a href="%s">%s</a> including this ' 
                           'traceback, and a description of what you were doing ' 
                           'when the error occurred.'
                           % (_file_bugs_url, _file_bugs_url))                
        else:
            report_bug_button = self.buttonbox.addButton(gettext("Report Bazaar Error"), QtGui.QDialogButtonBox.ActionRole)
            report_bug_button.connect(report_bug_button, QtCore.SIGNAL("clicked()"), report_bug)
            if message_internal:
                message = ("Bazaar has encountered an internal error. Please report a"
                           " bug.")
            else:
                message = ("Bazaar has encountered an environmental error. Please report a"
                           " bug if this is not the result of a local problem.")
        message = "<big>%s</big>" % (message)

        label = QtGui.QLabel(message)
        label.setWordWrap(True)
        label.setAlignment(QtCore.Qt.AlignVCenter|QtCore.Qt.AlignLeft)
        self.connect(label,
                     QtCore.SIGNAL("linkActivated(QString)"),
                     self.link_clicked)

        icon_label = QtGui.QLabel()
        icon_label.setPixmap(self.style().standardPixmap(
            QtGui.QStyle.SP_MessageBoxCritical))

        self.show_trace_back_button = QtGui.QPushButton(gettext("Show Error Details >>>"))
        self.connect(self.show_trace_back_button,
                     QtCore.SIGNAL("clicked()"),
                     self.show_trace_back)
        self.trace_back_label = QtGui.QTextEdit()
        self.trace_back_label.setPlainText (trace_back)
        self.trace_back_label.setReadOnly(True)
        self.trace_back_label.hide()
                    
        self.connect(self.buttonbox,
                     QtCore.SIGNAL("clicked (QAbstractButton *)"),
                     self.clicked)

        vbox = QtGui.QVBoxLayout()
        
        hbox = QtGui.QHBoxLayout()
        hbox.addWidget(icon_label)
        hbox.addWidget(label, 10)
        vbox.addLayout(hbox)
        
        hbox = QtGui.QHBoxLayout()
        hbox.addWidget(self.show_trace_back_button)
        hbox.addStretch()
        vbox.addLayout(hbox)
        vbox.addWidget(self.trace_back_label)

        hbox = QtGui.QHBoxLayout()
        hbox.addWidget(self.buttonbox)
        vbox.addLayout(hbox)
        
        self.setLayout(vbox)
        
        self.setWindowTitle(title)
        
        icon = QtGui.QIcon()
        icon.addFile(":/bzr-16.png", QtCore.QSize(16, 16))
        icon.addFile(":/bzr-32.png", QtCore.QSize(32, 32))
        icon.addFile(":/bzr-48.png", QtCore.QSize(48, 48))
        self.setWindowIcon(icon)

    def show_trace_back(self):
        """toggle the text box containing the full exception details"""
        self.trace_back_label.setVisible(not self.trace_back_label.isVisible())
        if self.trace_back_label.isVisible():
            self.show_trace_back_button.setText(gettext("<<< Hide Error Details"))
        else:
            self.show_trace_back_button.setText(gettext("Show Error Details >>>"))
        self.resize(self.sizeHint())

    def clicked(self, button):
        self.done(int(self.buttonbox.standardButton(button)))

    def link_clicked(self, url):
        # We can't import this at the top of the file because util imports
        # this file. XXX - The is probably a sign that util is to big, and
        # we need to split it up.
        from bzrlib.plugins.qbzr.lib.util import open_browser
        open_browser(str(url))

def reports_exception(type=MAIN_LOAD_METHOD):
    """Decorator to report Exceptions raised from the called method
    """
    def reports_exception_decorator(f):
        
        def reports_exception_decorate(*args, **kargs):
            try:
                return f(*args, **kargs)
            except Exception:
                # args[0] - typycaly self, may be a QWidget. Pass it's window
                if isinstance(args[0], QtGui.QWidget):
                    report_exception(type=type, window=args[0].window())
                else:
                    report_exception(type=type)
        
        return reports_exception_decorate
    
    return reports_exception_decorator

def excepthook(type, value, traceback):
    exc_info = (type, value, traceback)
    report_exception(exc_info=exc_info,
                     type=ITEM_OR_EVENT_METHOD)
