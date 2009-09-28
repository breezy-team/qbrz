# -*- coding: utf-8 -*-
#
# QBzr - Qt frontend to Bazaar commands
# Copyright (C) 2006 Lukáš Lalinský <lalinsky@gmail.com>
# Copyright (C) 2008 Gary van der Merwe <garyvdm@gmail.com>
# Copyright (C) 2009 Alexander Belchenko
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

import codecs
import os
import signal
import sys
import tempfile

from PyQt4 import QtCore, QtGui

from bzrlib import osutils, progress, errors

try:
    # this works with bzr 1.16+
    from bzrlib import bencode
except ImportError:
    # this works with bzr 1.15-
    from bzrlib.util import bencode

from bzrlib.plugins.qbzr.lib import MS_WINDOWS
from bzrlib.plugins.qbzr.lib.i18n import gettext
from bzrlib.plugins.qbzr.lib.util import (
    BTN_CANCEL,
    BTN_CLOSE,
    BTN_OK,
    QBzrDialog,
    QBzrWindow,
    StandardButton,
    ensure_unicode,
    )
from bzrlib.plugins.qbzr.lib.uifactory import ui_current_widget
from bzrlib.plugins.qbzr.lib.trace import (
   report_exception,
   SUB_LOAD_METHOD)

from bzrlib.ui.text import TextProgressView, TextUIFactory


class SubProcessWindowBase:

    def __init_internal__(self, title,
                          name="genericsubprocess",
                          args=None,
                          dir=None,
                          default_size=None,
                          ui_mode=True,
                          dialog=True,
                          parent=None,
                          hide_progress=False):
        self.restoreSize(name, default_size)
        self._name = name
        self._default_size = default_size
        self.args = args
        self.dir = dir
        self.ui_mode = ui_mode

        self.return_code = 1

        if dialog:
            flags = (self.windowFlags() & ~QtCore.Qt.Window) | QtCore.Qt.Dialog
            self.setWindowFlags(flags)

        self.process_widget = SubProcessWidget(self.ui_mode, self, hide_progress)
        self.connect(self.process_widget,
            QtCore.SIGNAL("finished()"),
            self.on_finished)
        self.connect(self.process_widget,
            QtCore.SIGNAL("failed()"),
            self.on_failed)
        self.connect(self.process_widget,
            QtCore.SIGNAL("error()"),
            self.on_error)

        closeButton = StandardButton(BTN_CLOSE)
        okButton = StandardButton(BTN_OK)
        cancelButton = StandardButton(BTN_CANCEL)

        # ok button gets disabled when we start.
        QtCore.QObject.connect(self,
                               QtCore.SIGNAL("subprocessStarted(bool)"),
                               okButton,
                               QtCore.SLOT("setDisabled(bool)"))

        # ok button gets hidden when we finish.
        QtCore.QObject.connect(self,
                               QtCore.SIGNAL("subprocessFinished(bool)"),
                               okButton,
                               QtCore.SLOT("setHidden(bool)"))

        # close button gets shown when we finish.
        QtCore.QObject.connect(self,
                               QtCore.SIGNAL("subprocessFinished(bool)"),
                               closeButton,
                               QtCore.SLOT("setShown(bool)"))

        # cancel button gets disabled when finished.
        QtCore.QObject.connect(self,
                               QtCore.SIGNAL("subprocessFinished(bool)"),
                               cancelButton,
                               QtCore.SLOT("setDisabled(bool)"))

        # ok button gets enabled when we fail.
        QtCore.QObject.connect(self,
                               QtCore.SIGNAL("subprocessFailed(bool)"),
                               okButton,
                               QtCore.SLOT("setDisabled(bool)"))

        self.buttonbox = QtGui.QDialogButtonBox(self)
        self.buttonbox.addButton(okButton,
            QtGui.QDialogButtonBox.AcceptRole)
        self.buttonbox.addButton(closeButton,
            QtGui.QDialogButtonBox.AcceptRole)
        self.buttonbox.addButton(cancelButton,
            QtGui.QDialogButtonBox.RejectRole)
        self.connect(self.buttonbox, QtCore.SIGNAL("accepted()"), self.do_accept)
        self.connect(self.buttonbox, QtCore.SIGNAL("rejected()"), self.do_reject)
        closeButton.setHidden(True) # but 'close' starts as hidden.

    def make_default_status_box(self):
        status_group_box = QtGui.QGroupBox(gettext("Status"))
        status_layout = QtGui.QVBoxLayout(status_group_box)
        status_layout.setContentsMargins(0, 0, 0, 0)
        status_layout.addWidget(self.process_widget)
        return status_group_box

    def make_default_layout_widgets(self):
        """Yields widgets to add to main dialog layout: status and button boxes.
        Status box has progress bar and console area.
        Button box has 2 buttons: OK and Cancel (after successfull command 
        execution there will be Close and Cancel).
        """
        yield self.make_default_status_box()
        yield self.buttonbox

    def validate(self):
        """Override this method in your class and do any validation there.
        Return True if all parameters is OK and subprocess can be started.
        """
        return True

    def _check_args(self):
        """Check that self.args is not None and return True.
        Otherwise show error dialog to the user and return False.
        """
        if self.args is None:
            raise RuntimeError('Subprocess action "%s" cannot be started\n'
                               'because self.args is None.' % self._name)
        return True

    def do_accept(self):
        if self.process_widget.finished:
            self.close()
        else:
            try:
                if not self.validate():
                    return
            except:
                report_exception(type=SUB_LOAD_METHOD, window=self.window())
                return

            self.emit(QtCore.SIGNAL("subprocessStarted(bool)"), True)
            self.emit(QtCore.SIGNAL("disableUi(bool)"), True)
            self.do_start()

    def do_start(self):
        if self._check_args():
            self.process_widget.do_start(self.dir, *self.args)
        else:
            self.on_failed()

    def do_reject(self):
        if self.process_widget.is_running():
            self.process_widget.abort()
        else:
            self.close()

    def on_finished(self):
        if hasattr(self, 'setResult'):
            self.setResult(QtGui.QDialog.Accepted)

        self.emit(QtCore.SIGNAL("subprocessFinished(bool)"), True)
        self.emit(QtCore.SIGNAL("disableUi(bool)"), False)

        self.return_code = 0

        if not self.ui_mode:
            self.close()

    def on_failed(self):
        self.emit(QtCore.SIGNAL("subprocessFailed(bool)"), False)
        self.emit(QtCore.SIGNAL("disableUi(bool)"), False)

    def on_error(self):
        self.emit(QtCore.SIGNAL("subprocessError(bool)"), False)

    def setupUi(self, ui):
        ui.setupUi(self)
        if self._restore_size:
            self.resize(self._restore_size)


class SubProcessWindow(SubProcessWindowBase, QBzrWindow):

    def __init__(self, title,
                 name="genericsubprocess",
                 args=None,
                 dir=None,
                 default_size=None,
                 ui_mode=True,
                 dialog=True,
                 parent=None,
                 hide_progress=False):
        QBzrWindow.__init__(self, title, parent)
        self.__init_internal__(title,
                               name=name,
                               args=args,
                               dir=dir,
                               default_size=default_size,
                               ui_mode=ui_mode,
                               dialog=dialog,
                               parent=parent,
                               hide_progress=hide_progress)

    def closeEvent(self, event):
        if not self.process_widget.is_running():
            QBzrWindow.closeEvent(self, event)
        else:
            self.process_widget.abort()
            event.ignore()


class SubProcessDialog(SubProcessWindowBase, QBzrDialog):
    """An abstract base-class for all subprocess related dialogs.

    It is expected that sub-classes of this will create their own UI, and while
    doing so, will add the widgets returned by
    self.make_default_layout_widgets()
    """

    def __init__(self, title=None,
                 name="genericsubprocess",
                 args=None,
                 dir=None,
                 default_size=None,
                 ui_mode=True,
                 dialog=True,
                 parent=None,
                 hide_progress=False):
        QBzrDialog.__init__(self, title, parent)
        self.__init_internal__(title,
                               name=name,
                               args=args,
                               dir=dir,
                               default_size=default_size,
                               ui_mode=ui_mode,
                               dialog=dialog,
                               parent=parent,
                               hide_progress=hide_progress)

    def closeEvent(self, event):
        if not self.process_widget.is_running():
            QBzrDialog.closeEvent(self, event)
        else:
            self.process_widget.abort()
            event.ignore()


class SimpleSubProcessDialog(SubProcessDialog):
    """A concrete helper class of SubProcessDialog, which has a single label
    widget for displaying a simple description before executing a subprocess.
    """

    def __init__(self, title, desc,
                 name="genericsubprocess",
                 args=None,
                 dir=None,
                 default_size=None,
                 ui_mode=True,
                 dialog=True,
                 hide_progress=False,
                 auto_start_show_on_failed=False,
                 parent=None,
                 ):
        super(SimpleSubProcessDialog, self).__init__(
                               title,
                               name=name,
                               args=args,
                               dir=dir,
                               default_size=default_size,
                               ui_mode=ui_mode,
                               dialog=dialog,
                               parent=parent,
                               hide_progress=hide_progress)
        self.desc = desc
        # create a layout to hold our one label and the subprocess widgets.
        layout = QtGui.QVBoxLayout(self)
        groupbox = QtGui.QGroupBox(gettext('Description'))
        v = QtGui.QVBoxLayout(groupbox)
        label = QtGui.QLabel(self.desc)
        label.font().setBold(True)
        v.addWidget(label)
        layout.addWidget(groupbox)
        # and add the subprocess widgets.
        for w in self.make_default_layout_widgets():
            layout.addWidget(w)

        self.auto_start_show_on_failed = auto_start_show_on_failed
        QtCore.QTimer.singleShot(1, self.auto_start)

    def auto_start(self):
        if self.auto_start_show_on_failed:
            QtCore.QObject.connect(self,
                                   QtCore.SIGNAL("subprocessFailed(bool)"),
                                   self,
                                   QtCore.SLOT("setHidden(bool)"))
            QtCore.QObject.connect(self,
                                   QtCore.SIGNAL("subprocessError(bool)"),
                                   self,
                                   QtCore.SLOT("setHidden(bool)"))
            self.do_start()


class SubProcessWidget(QtGui.QWidget):

    def __init__(self, ui_mode, parent=None, hide_progress=False):
        QtGui.QGroupBox.__init__(self, parent)
        self.ui_mode = ui_mode

        layout = QtGui.QVBoxLayout(self)

        message_layout = QtGui.QHBoxLayout()

        self.progressMessage = QtGui.QLabel(self)
        #self.progressMessage.setWordWrap(True) -- this breaks minimal window size hint
        self.progressMessage.setText(gettext("Ready"))
        message_layout.addWidget(self.progressMessage, 1)

        self.transportActivity = QtGui.QLabel(self)
        message_layout.addWidget(self.transportActivity)

        layout.addLayout(message_layout)

        self.progressBar = QtGui.QProgressBar(self)
        self.progressBar.setMaximum(1000000)
        layout.addWidget(self.progressBar)

        self.console = QtGui.QTextBrowser(self)
        self.console.setFocusPolicy(QtCore.Qt.ClickFocus)
        layout.addWidget(self.console)

        self.encoding = osutils.get_user_encoding()
        self.stdout = None
        self.stderr = None

        self.process = QtCore.QProcess()
        self.connect(self.process,
            QtCore.SIGNAL("readyReadStandardOutput()"),
            self.readStdout)
        self.connect(self.process,
            QtCore.SIGNAL("readyReadStandardError()"),
            self.readStderr)
        self.connect(self.process,
            QtCore.SIGNAL("error(QProcess::ProcessError)"),
            self.reportProcessError)
        self.connect(self.process,
            QtCore.SIGNAL("finished(int, QProcess::ExitStatus)"),
            self.onFinished)

        self.defaultWorkingDir = self.process.workingDirectory ()

        self.finished = False
        self.aborting = False

        self.messageFormat = QtGui.QTextCharFormat()
        self.errorFormat = QtGui.QTextCharFormat()
        self.errorFormat.setForeground(QtGui.QColor('red'))
        self.cmdlineFormat = QtGui.QTextCharFormat()
        self.cmdlineFormat.setForeground(QtGui.QColor('blue'))

        if hide_progress:
            self.hide_progress()

        self._args_file = None  # temp file to pass arguments to qsubprocess

    def hide_progress(self):
        self.progressMessage.setHidden(True)
        self.progressBar.setHidden(True)

    def is_running(self):
        return self.process.state() == QtCore.QProcess.Running or\
               self.process.state() == QtCore.QProcess.Starting

    def do_start(self, workdir, *args):
        """Launch one bzr command.
        @param  workdir:    working directory for command.
                            Could be None to use self.defaultWorkingDir
        @param  args:   bzr command and its arguments
        @type   args:   all arguments should be unicode strings (or ascii-only).
        """
        QtGui.QApplication.processEvents() # make sure ui has caught up
        self.start_multi(((workdir, args),))

    def start_multi(self, commands):
        self.setProgress(0, [gettext("Starting...")], "")
        self.console.setFocus(QtCore.Qt.OtherFocusReason)
        self.commands = list(commands)
        self._start_next()

    def _start_next(self):
        """Start first command from self.commands queue."""
        self._delete_args_file()
        dir, args = self.commands.pop(0)

        args = bencode_unicode(args)

        # win32 has command-line length limit about 32K, but it seems 
        # problems with command-line buffer limit occurs not only on windows.
        # see bug https://bugs.launchpad.net/qbzr/+bug/396165
        # XXX make the threshold configurable in qbzr.conf?
        if len(args) > 10000:   # on Linux I believe command-line is in utf-8,
                                # so we need to have some extra space
                                # when converting unicode -> utf8
            # save the args to the file
            fname = self._create_args_file(args)
            args = "@" + fname.replace('\\', '/')

        if dir is None:
            dir = self.defaultWorkingDir

        self.process.setWorkingDirectory (dir)
        self._setup_stdout_stderr()
        if getattr(sys, "frozen", None) is not None:
            bzr_exe = sys.argv[0]
            if sys.frozen == 'windows_exe':
                # bzrw.exe
                exe = os.path.join(os.path.dirname(sys.argv[0]), 'bzr.exe')
                if os.path.isfile(exe):
                    bzr_exe = exe
            self.process.start(
                bzr_exe, ['qsubprocess', '--bencode', args])
        else:
            self.process.start(
                sys.executable, [sys.argv[0], 'qsubprocess', '--bencode', args])

    def _setup_stdout_stderr(self):
        if self.stdout is None:
            writer = codecs.getwriter(osutils.get_terminal_encoding())
            self.stdout = writer(sys.stdout, errors='replace')
            self.stderr = writer(sys.stderr, errors='replace')

    def abort(self):
        if self.is_running():
            self.abort_futher_processes()
            if not self.aborting:
                self.aborting = True
                if MS_WINDOWS:
                    # trying to send signal to our subprocess
                    signal_event(get_child_pid(self.process.pid()))
                else:
                    # be nice and try to use ^C
                    os.kill(self.process.pid(), signal.SIGINT) 
                self.setProgress(None, [gettext("Aborting...")])
            else:
                self.process.terminate()

    def abort_futher_processes(self):
        self.commands = []

    def setProgress(self, progress, messages, transport_activity=None):
        if progress is not None:
            self.progressBar.setValue(progress)
        if progress == 1000000 and not messages:
            text = gettext("Finished!")
        else:
            if isinstance(messages, unicode):
                text = messages
            else:
                text = " / ".join(messages)
        self.progressMessage.setText(text)
        if transport_activity is not None:
            self.transportActivity.setText(transport_activity)

    def readStdout(self):
        # ensure we read from subprocess plain string
        data = str(self.process.readAllStandardOutput())
        # we need unicode for all strings except bencoded streams
        for line in data.splitlines():
            if line.startswith("qbzr:PROGRESS:"):
                # but we have to ensure we have unicode after bdecode
                progress, transport_activity, messages = map(ensure_unicode, bencode.bdecode(line[14:]))
                self.setProgress(progress, messages, transport_activity)
            elif line.startswith("qbzr:GETPASS:"):
                prompt = bencode.bdecode(line[13:]).decode('utf-8')
                passwd, ok = QtGui.QInputDialog.getText(self,
                                                        gettext("Enter Password"),
                                                        prompt,
                                                        QtGui.QLineEdit.Password)
                data = unicode(passwd).encode('utf-8'), int(ok)
                self.process.write("qbzr:GETPASS:"+bencode.bencode(data)+"\n")
                if not ok:
                    self.abort_futher_processes()
            else:
                line = line.decode(self.encoding)
                self.logMessage(line)
                if not self.ui_mode:
                    self.stdout.write(line)
                    self.stdout.write("\n")

    def readStderr(self):
        data = str(self.process.readAllStandardError()).decode(self.encoding, 'replace')
        if data:
            self.emit(QtCore.SIGNAL("error()"))

        for line in data.splitlines():
            error = line.startswith("bzr: ERROR:")
            self.logMessage(line, error)
            if not self.ui_mode:
                self.stderr.write(line)
                self.stderr.write("\n")

    def logMessage(self, message, error=False):
        if error:
            format = self.errorFormat
        else:
            format = self.messageFormat
        self.console.setCurrentCharFormat(format);
        self.console.append(message);
        scrollbar = self.console.verticalScrollBar()
        scrollbar.setValue(scrollbar.maximum())

    def logMessageEx(self, message, kind="plain"):
        """Write message to console area.
        @param kind: kind of message used for selecting style of formatting.
            Possible kind values:
                * plain = usual message, written in default style;
                * error = error message, written in red;
                * cmdline = show actual command-line, written in blue.
        """
        if kind == 'error':
            format = self.errorFormat
        elif kind == 'cmdline':
            format = self.cmdlineFormat
        else:
            format = self.messageFormat
        self.console.setCurrentCharFormat(format)
        self.console.append(message)
        scrollbar = self.console.verticalScrollBar()
        scrollbar.setValue(scrollbar.maximum())

    def reportProcessError(self, error):
        self.aborting = False
        self.setProgress(1000000, [gettext("Failed!")])
        if error == QtCore.QProcess.FailedToStart:
            message = gettext("Failed to start bzr.")
        else:
            message = gettext("Error while running bzr. (error code: %d)" % error)
        self.logMessage(message, True)
        self.emit(QtCore.SIGNAL("failed()"))

    def onFinished(self, exitCode, exitStatus):
        self._delete_args_file()
        if self.aborting:
            self.aborting = False
            self.setProgress(1000000, [gettext("Aborted!")])
            self.emit(QtCore.SIGNAL("failed()"))
        elif exitCode == 0:
            if self.commands and not self.aborting:
                self._start_next()
            else:
                self.finished = True
                self.setProgress(1000000, [gettext("Finished!")])
                self.emit(QtCore.SIGNAL("finished()"))
        else:
            self.setProgress(1000000, [gettext("Failed!")])
            self.emit(QtCore.SIGNAL("failed()"))

    def _create_args_file(self, text):
        """@param text: text to write into temp file,
                        it should be unicode string
        """
        if self._args_file:
            self._delete_args_file()
        qdir = os.path.join(tempfile.gettempdir(), 'QBzr', 'qsubprocess')
        if not os.path.isdir(qdir):
            os.makedirs(qdir)
        fd, fname = tempfile.mkstemp(dir=qdir)
        f = os.fdopen(fd, "wb")
        try:
            f.write(text.encode('utf8'))
        finally:
            f.close()   # it closes fd as well
        self._args_file = fname
        return fname

    def _delete_args_file(self):
        if self._args_file:
            try:
                os.unlink(self._args_file)
            except (IOError, OSError), e:
                pass
            else:
                self._args_file = None


class SubprocessProgressView (TextProgressView):

    def __init__(self, term_file):
        TextProgressView.__init__(self, term_file)
        # The TextProgressView does not show the transport activity untill
        # there was a progress update. This changed becuse showing the
        # transport activity before a progress update would cause artifactes to
        # remain on the screen. We don't have to worry about that
        self._have_output = True

    def _repaint(self):
        if self._last_task:
            task_msg = self._format_task(self._last_task)
            progress_frac = self._last_task._overall_completion_fraction()
            if progress_frac is not None:
                progress = int(progress_frac * 1000000)
            else:
                progress = 1
        else:
            task_msg = ''
            progress = 0

        trans = self._last_transport_msg

        self._term_file.write('qbzr:PROGRESS:' + bencode.bencode((progress,
                              trans, task_msg)) + '\n')
        self._term_file.flush()

    def clear(self):
        pass


class SubprocessUIFactory(TextUIFactory):

    def make_progress_view(self):
        return SubprocessProgressView(self.stdout)
    
    # This is to be compatabile with bzr < rev 4558
    _make_progress_view = make_progress_view
    
    def clear_term(self):
        """Prepare the terminal for output.

        This will, for example, clear text progress bars, and leave the
        cursor at the leftmost position."""
        pass

    def get_password(self, prompt='', **kwargs):
        prompt = prompt % kwargs
        self.stdout.write('qbzr:GETPASS:' + bencode.bencode(prompt.encode('utf-8')) + '\n')
        self.stdout.flush()
        line = self.stdin.readline()
        if line.startswith('qbzr:GETPASS:'):
            passwd, accepted = bencode.bdecode(line[13:].rstrip('\r\n'))
            if accepted:
                return passwd
            else:
                raise KeyboardInterrupt()
        raise Exception("Did not recive a password from the main process.")


if MS_WINDOWS:
    import ctypes
    if getattr(sys, "frozen", None):
        # this is needed for custom bzr.exe builds (without TortoiseBzr inside)
        ctypes.__path__.append(os.path.normpath(
            os.path.join(os.path.dirname(__file__), '..', '_lib', 'ctypes')))
    from ctypes import cast, POINTER, Structure
    from ctypes.wintypes import DWORD, HANDLE

    class PROCESS_INFORMATION(Structure):
        _fields_ = [("hProcess", HANDLE),
                    ("hThread", HANDLE),
                    ("dwProcessID", DWORD),
                    ("dwThreadID", DWORD)]

    LPPROCESS_INFORMATION = POINTER(PROCESS_INFORMATION)

    def get_child_pid(voidptr):
        lp = cast(int(voidptr), LPPROCESS_INFORMATION)
        return lp.contents.dwProcessID

    def get_event_name(child_pid):
        return 'qbzr-qsubprocess-%d' % child_pid

    def signal_event(child_pid):
        import win32event
        ev = win32event.CreateEvent(None, 0, 0, get_event_name(child_pid))
        try:
            win32event.SetEvent(ev)
        finally:
            ev.Close()

def bencode_unicode(args):
    """Bencode list of unicode strings as list of utf-8 strings and converting
    resulting string to unicode.
    """
    args_utf8 = bencode.bencode([unicode(a).encode('utf-8') for a in args])
    return unicode(args_utf8, 'utf-8')
