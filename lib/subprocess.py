# -*- coding: utf-8 -*-
#
# QBzr - Qt frontend to Bazaar commands
# Copyright (C) 2006 Lukáš Lalinský <lalinsky@gmail.com>
# Copyright (C) 2008 Gary van der Merwe <garyvdm@gmail.com>
# Copyright (C) 2009 Alexander Belchenko
# Copyright (C) 2010 QBzr Developers
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

import os
import sys
import time

from PyQt5 import QtCore, QtGui, QtWidgets
from contextlib import contextmanager

from breezy.plugins.qbrz.lib import MS_WINDOWS
from breezy.plugins.qbrz.lib.i18n import gettext, N_
from breezy.plugins.qbrz.lib.util import (
    BTN_CANCEL,
    BTN_CLOSE,
    BTN_OK,
    QBzrDialog,
    QBzrWindow,
    StandardButton,
    ensure_unicode,
    InfoWidget,
    )

from breezy.ui.text import TextProgressView, TextUIFactory
from breezy.plugins.qbrz.lib.trace import (
   report_exception,
   SUB_LOAD_METHOD)

from breezy.lazy_import import lazy_import
try:
    QString = unicode
except NameError:
    # Python 3
    QString = str

import fastbencode as bencode

lazy_import(globals(), '''
import codecs
import re
import shlex
import signal
import tempfile
import thread

from breezy import (
    commands,
    errors,
    osutils,
    ui,
    )

from breezy.controldir import ControlDir

from breezy.plugins.qbrz.lib.commit import CommitWindow
from breezy.plugins.qbrz.lib.revert import RevertWindow
from breezy.plugins.qbrz.lib.shelvewindow import ShelveWindow
from breezy.plugins.qbrz.lib.conflicts import ConflictsWindow
''')


# Subprocess service messages markers
SUB_PROGRESS = "qbrz:PROGRESS:"
SUB_GETPASS = "qbrz:GETPASS:"
SUB_GETUSER = "qbrz:GETUSER:"
SUB_GETBOOL = "qbrz:GETBOOL:"
SUB_CHOOSE = "qbrz:CHOOSE:"
SUB_ERROR = "qbrz:ERROR:"
SUB_NOTIFY = "qbrz:NOTIFY:"

NOTIFY_CONFLICT = "conflict:"


class WarningInfoWidget(InfoWidget):
    def __init__(self, parent):
        InfoWidget.__init__(self, parent)
        layout = QtWidgets.QVBoxLayout(self)
        label_layout = QtWidgets.QHBoxLayout()

        icon = QtWidgets.QLabel()
        icon.setPixmap(self.style().standardPixmap(QtWidgets.QStyle.SP_MessageBoxWarning))
        label_layout.addWidget(icon)
        self.label = QtWidgets.QLabel()
        label_layout.addWidget(self.label, 2)
        layout.addLayout(label_layout)
        self.button_layout = QtWidgets.QHBoxLayout()
        self.button_layout.addStretch(1)
        layout.addLayout(self.button_layout)

        self.buttons = []

    def add_button(self, text, on_click):
        button = QtWidgets.QPushButton(gettext(text))
        button.clicked[bool].connect(on_click)
        self.button_layout.addWidget(button)
        self.buttons.append((button, on_click))

    def remove_all_buttons(self):
        for button, on_click in self.buttons:
            button.clicked[bool].disconnect(on_click)
            self.button_layout.removeWidget(button)
            button.close()
        del(self.buttons[:])

    def set_label(self, text):
        self.label.setText(gettext(text))

    def setup_for_uncommitted(self, on_commit, on_revert, on_shelve):
        self.remove_all_buttons()
        self.set_label(N_('Working tree has uncommitted changes.'))
        self.add_button(N_('Commit'), on_commit)
        self.add_button(N_('Revert'), on_revert)
        self.add_button(N_('Shelve'), on_shelve)

    def setup_for_conflicted(self, on_conflict, on_revert):
        self.remove_all_buttons()
        self.set_label(N_('Working tree has conflicts.'))
        self.add_button(N_('Resolve'), on_conflict)
        self.add_button(N_('Revert'), on_revert)


    def setup_for_locked(self, on_retry):
        self.remove_all_buttons()
        self.set_label(N_('Could not acquire lock. Please retry later.'))
        self.add_button(N_('Retry'), on_retry)


class SubProcessWindowBase(object):

    subprocessStarted = QtCore.pyqtSignal(bool)
    disableUi = QtCore.pyqtSignal(bool)
    subprocessFinished = QtCore.pyqtSignal(bool)
    subprocessFailed = QtCore.pyqtSignal(bool)
    subprocessError = QtCore.pyqtSignal(bool)

    def __init_internal__(self, title,
                          name="genericsubprocess",
                          args=None,
                          dir=None,
                          default_size=None,
                          ui_mode=True,
                          dialog=True,
                          parent=None,
                          hide_progress=False,
                          immediate=False):
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
        self.process_widget.finished.connect(self.on_finished)
        self.process_widget.failed['QString'].connect(self.on_failed)
        self.process_widget.error.connect(self.on_error)
        self.process_widget.conflicted['QString'].connect(self.on_conflicted)

        self.closeButton = StandardButton(BTN_CLOSE)
        self.okButton = StandardButton(BTN_OK)
        self.cancelButton = StandardButton(BTN_CANCEL)

        # ok button gets disabled when we start.
        self.subprocessStarted[bool].connect(self.okButton.setDisabled)

        # ok button gets hidden when we finish.
        self.subprocessFinished[bool].connect(self.okButton.setHidden)

        # close button gets shown when we finish.
        self.subprocessFinished[bool].connect(self.closeButton.setVisible)

        # cancel button gets disabled when finished.
        self.subprocessFinished[bool].connect(self.cancelButton.setDisabled)

        # ok button gets enabled when we fail.
        self.subprocessFailed[bool].connect(self.okButton.setDisabled)

        # Change the ok button to 'retry' if we fail.
        self.subprocessFailed[bool].connect(lambda failed: self.okButton.setText(gettext('&Retry')))

        self.buttonbox = QtWidgets.QDialogButtonBox(self)
        self.buttonbox.addButton(self.okButton, QtWidgets.QDialogButtonBox.AcceptRole)
        self.buttonbox.addButton(self.closeButton, QtWidgets.QDialogButtonBox.AcceptRole)
        self.buttonbox.addButton(self.cancelButton, QtWidgets.QDialogButtonBox.RejectRole)
        self.buttonbox.accepted.connect(self.do_accept)
        self.buttonbox.rejected.connect(self.do_reject)
        self.closeButton.setHidden(True) # but 'close' starts as hidden.

        self.infowidget = WarningInfoWidget(self)
        self.infowidget.hide()
        self.subprocessStarted[bool].connect(self.infowidget.setHidden)

        if immediate:
            self.do_accept()

    def make_default_status_box(self):
        panel = QtWidgets.QWidget()
        vbox = QtWidgets.QVBoxLayout(panel)
        vbox.setContentsMargins(0, 0, 0, 0)
        vbox.addWidget(self.infowidget)
        status_group_box = QtWidgets.QGroupBox(gettext("Status"))
        status_layout = QtWidgets.QVBoxLayout(status_group_box)
        status_layout.setContentsMargins(0, 0, 0, 0)
        status_layout.addWidget(self.process_widget)
        vbox.addWidget(status_group_box)
        return panel

    def make_process_panel(self):
        panel = QtWidgets.QWidget()
        vbox = QtWidgets.QVBoxLayout(panel)
        vbox.setContentsMargins(0, 0, 0, 0)
        vbox.addWidget(self.infowidget)
        vbox.addWidget(self.process_widget)
        return panel

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
        if self.process_widget.is_finished:
            self.close()
        else:
            try:
                if not self.validate():
                    return
            except:
                report_exception(type=SUB_LOAD_METHOD, window=self.window())
                return

            self.subprocessStarted.emit(True)
            self.disableUi.emit(True)
            self.do_start()

    def do_start(self):
        if self._check_args():
            self.process_widget.do_start(self.dir, *self.args)
        else:
            self.on_failed('CheckArgsFailed')

    def do_reject(self):
        if self.process_widget.is_running():
            self.process_widget.abort()
        else:
            self.close()

    def on_finished(self):
        if hasattr(self, 'setResult'):
            self.setResult(QtWidgets.QDialog.Accepted)

        self.subprocessFinished.emit(True)
        self.disableUi.emit(False)

        self.return_code = 0

        if not self.ui_mode and not self.infowidget.isVisible():
            self.close()

    def on_conflicted(self, tree_path):
        if tree_path:
            self.action_url = str(tree_path) # QString -> unicode
            self.infowidget.setup_for_conflicted(self.open_conflicts_win, self.open_revert_win)
            self.infowidget.show()

    def on_failed(self, error):
        self.subprocessFailed.emit(False)
        self.disableUi.emit(False)

        if error == 'UncommittedChanges':
            self.action_url = self.process_widget.error_data['display_url']
            self.infowidget.setup_for_uncommitted(self.open_commit_win,
                                                  self.open_revert_win,
                                                  self.open_shelve_win)
            self.infowidget.show()

        elif error == 'LockContention':
            self.infowidget.setup_for_locked(self.do_accept)
            self.infowidget.show()

    def on_error(self):
        self.subprocessError.emit(False)

    def setupUi(self, ui):
        ui.setupUi(self)
        if self._restore_size:
            self.resize(self._restore_size)

    def open_commit_win(self, b):
        # XXX refactor so that the tree can be opened by the window
        tree, branch = BzrDir.open_tree_or_branch(self.action_url)
        commit_window = CommitWindow(tree, None, parent=self)
        self.windows.append(commit_window)
        commit_window.show()

    def open_revert_win(self, b):
        # XXX refactor so that the tree can be opened by the window
        tree, branch = BzrDir.open_tree_or_branch(self.action_url)
        revert_window = RevertWindow(tree, None, parent=self)
        self.windows.append(revert_window)
        revert_window.show()

    def open_shelve_win(self, b):
        shelve_window = ShelveWindow(directory=self.action_url, parent=self)
        self.windows.append(shelve_window)
        shelve_window.show()

    def open_conflicts_win(self, b):
        window = ConflictsWindow(self.action_url, parent=self)
        self.windows.append(window)
        window.show()
        window.allResolved[bool].connect(self.infowidget.setHidden)

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
                 hide_progress=False,
                 immediate=False):
        QBzrDialog.__init__(self, title, parent)
        self.__init_internal__(title,
                               name=name,
                               args=args,
                               dir=dir,
                               default_size=default_size,
                               ui_mode=ui_mode,
                               dialog=dialog,
                               parent=parent,
                               hide_progress=hide_progress,
                               immediate=immediate)

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
                 immediate=False
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
                               hide_progress=hide_progress,
                               immediate=immediate)
        self.desc = desc
        # create a layout to hold our one label and the subprocess widgets.
        layout = QtWidgets.QVBoxLayout(self)
        groupbox = QtWidgets.QGroupBox(gettext('Description'))
        v = QtWidgets.QVBoxLayout(groupbox)
        label = QtWidgets.QLabel(self.desc)
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
            self.subprocessFailed[bool].connect(self.setHidden)
            self.subprocessError[bool].connect(self.setHidden)
            self.do_start()


class SubProcessWidget(QtWidgets.QWidget):
    # RJLRJL moved to class members to handle connects to Qt5
    #  'a signal needs to be defined on class level'
    failed = QtCore.pyqtSignal('QString')
    conflicted = QtCore.pyqtSignal('QString')
    finished = QtCore.pyqtSignal(bool)
    error = QtCore.pyqtSignal(bool)

    def __init__(self, ui_mode, parent=None, hide_progress=False):
        QtWidgets.QGroupBox.__init__(self, parent)
        self.ui_mode = ui_mode

        layout = QtWidgets.QVBoxLayout(self)

        message_layout = QtWidgets.QHBoxLayout()

        self.progressMessage = QtWidgets.QLabel(self)
        #self.progressMessage.setWordWrap(True) -- this breaks minimal window size hint
        self.progressMessage.setText(gettext("Ready"))
        message_layout.addWidget(self.progressMessage, 1)

        self.transportActivity = QtWidgets.QLabel(self)
        message_layout.addWidget(self.transportActivity)

        layout.addLayout(message_layout)

        self.progressBar = QtWidgets.QProgressBar(self)
        self.progressBar.setMaximum(1000000)
        layout.addWidget(self.progressBar)

        self.console = QtWidgets.QTextBrowser(self)
        self.console.setFocusPolicy(QtCore.Qt.ClickFocus)
        layout.addWidget(self.console)

        self.encoding = osutils.get_user_encoding()
        self.stdout = None
        self.stderr = None

        self.process = QtCore.QProcess()
        self.process.readyReadStandardOutput.connect(self.readStdout)
        self.process.readyReadStandardError.connect(self.readStderr)
        self.process.error[QtCore.QProcess.ProcessError].connect(self.reportProcessError)
        self.process.finished[int, QtCore.QProcess.ExitStatus].connect(self.onFinished)

        self.defaultWorkingDir = self.process.workingDirectory()

        self.is_finished = False
        self.aborting = False

        self.messageFormat = QtGui.QTextCharFormat()
        self.errorFormat = QtGui.QTextCharFormat()
        self.errorFormat.setForeground(QtGui.QColor('red'))
        self.cmdlineFormat = QtGui.QTextCharFormat()
        self.cmdlineFormat.setForeground(QtGui.QColor('blue'))

        if hide_progress:
            self.hide_progress()

        self.force_passing_args_via_file = False
        self._args_file = None  # temp file to pass arguments to qsubprocess
        self.error_class = ''
        self.error_data = {}
        self.is_conflicted = False

    def hide_progress(self):
        self.progressMessage.setHidden(True)
        self.progressBar.setHidden(True)

    def is_running(self):
        return self.process.state() == QtCore.QProcess.Running or self.process.state() == QtCore.QProcess.Starting

    def do_start(self, workdir, *args):
        """Launch one bzr command.
        @param  workdir:    working directory for command.
                            Could be None to use self.defaultWorkingDir
        @param  args:   bzr command and its arguments
        @type   args:   all arguments should be unicode strings (or ascii-only).
        """
        QtWidgets.QApplication.processEvents()  # make sure ui has caught up
        self.start_multi(((workdir, args),))

    def start_multi(self, commands):
        self.setProgress(0, [gettext("Starting...")], "")
        self.console.setFocus(QtCore.Qt.OtherFocusReason)
        self.commands = list(commands)
        self._start_next()

    def _start_next(self):
        """Start first command from self.commands queue."""
        self._setup_stdout_stderr()
        self._delete_args_file()
        directory, args = self.commands.pop(0)

        # Log the command we about to execute
        # Interestingly, this puts quotes around any strings in r
        # but this is not done in the body of the kirk, for some reason
        def format_args_for_log(args):
            # r = ['bzr']
            r = ['brz']
            for a in args:
                a = str(a).translate({
                        ord('\n'): '\\n',
                        ord('\r'): '\\r',
                        ord('\t'): '\\t',
                        })
                if " " in a:
                    r.append('"%s"' % a)
                else:
                    r.append(a)
            s = ' '.join(r)
            if len(s) > 128:  # XXX make it configurable?
                s = s[:128] + '...'
            return s
        self.logMessageEx("Run command: " + format_args_for_log(args), "cmdline", self.stderr)

        # RJLRJL: these are encoded, just to be decoded again in run_subprocess_command
        args = bittorrent_b_encode_unicode(args)

        # win32 has command-line length limit about 32K, but it seems
        # problems with command-line buffer limit occurs not only on windows.
        # see bug https://bugs.launchpad.net/qbrz/+bug/396165
        # on Linux I believe command-line is in utf-8,
        # so we need to have some extra space
        # when converting unicode -> utf8
        # XXX make the threshold configurable in qbrz.conf?
        #
        # RJL: at this point, args is now a byte string (bencoded)
        if (len(args) > 10000 or re.search(rb"(?:"
                rb"\n|\r"            # workaround for bug #517420 multi-line comments
                rb"|\\\\"            # workaround for bug #528944 eating backslashes
                rb")", args) is not None
            or self.force_passing_args_via_file     # workaround for bug #936587 quoted regular expressions
            ):
            # save the args to the file
            fname = self._create_args_file(args)
            # This:
            #
            #  args = "@" + fname.replace('\\', '/')
            #
            # was bad and caused a bug: args was now no longer a bencoded string... but
            # the code below would pass it to qsubprocess telling the lie that it was. Tsk.
            # In Python 2 this sort-of worked: more correctly, nobody noticed the bad behaviour
            # (bug) for 10 or 12 years.
            #
            # Instead, we'll pass a properly constructed, bencoded string
            #
            args = "@" + fname.replace('\\', '/')
            args = bencode.bencode(bytes(args, 'utf-8'))

        if directory is None:
            directory = self.defaultWorkingDir

        self.error_class = ''
        # failed = QtCore.pyqtSignal('QString')
        # conflicted = QtCore.pyqtSignal('QString')
        # finished = QtCore.pyqtSignal()
        self.error_data = {}

        self.process.setWorkingDirectory(directory)
        if getattr(sys, "frozen", None) is not None:
            brz_exe = sys.executable
            if os.path.basename(brz_exe) != "brz.exe":
                # Was run from bzrw.exe or tbzrcommand.
                brz_exe = os.path.join(os.path.dirname(sys.executable), "brz.exe")
                if not os.path.isfile(brz_exe):
                    self.reportProcessError(None, gettext('Could not locate "brz.exe".'))
            self.process.start(brz_exe, ['qsubprocess', '--bencode', args])
        else:
            # otherwise running as python script.
            # ensure run from bzr, and not others, e.g. tbzrcommand.py
            script = sys.argv[0]
            # make absolute, because we may be running in a different
            # dir.
            script = os.path.abspath(script)
            # allow for bzr or brz with optional extension (such as bzr.py)
            if os.path.splitext(os.path.basename(script))[0] not in ("brz", "bzr"):
                import breezy
                # are we running directly from a bzr directory?
                script = os.path.join(breezy.__path__[0], "..", "brz")
                if not os.path.isfile(script):
                    # maybe from an installed bzr?
                    script = os.path.join(sys.prefix, "scripts", "brz")
                if not os.path.isfile(script):
                    self.reportProcessError(None, gettext('Could not locate "brz" script.'))
            self.process.start(sys.executable, [script, 'qsubprocess', '--bencode', str(args, 'utf-8')])

    def _setup_stdout_stderr(self):
        if self.stdout is None:
            writer = codecs.getwriter(osutils.get_terminal_encoding())
            self.stdout = writer(sys.stdout.buffer, errors='replace')
            self.stderr = writer(sys.stderr.buffer, errors='replace')

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
            text = " / ".join(messages)
        self.progressMessage.setText(text)
        if transport_activity is not None:
            self.transportActivity.setText(transport_activity)

    def readStdout(self):
        # TODO: This will almost certainly fail - see TestSubprocessProgressView in test_subprocess
        # ensure we read from subprocess plain string.
        #
        # ``run_subprocess_command`` seems to end up here
        #
        # ``readAllStandardOutput`` is a PyQt4 routine. The docs state that it returns a QByteArray:
        # testing shows that it does and that its ``.data()`` method returns bytes
        #
        data = self.process.readAllStandardOutput().data().decode(self.encoding)

        for line in data.splitlines():
            # Note that bdecode needs bytes so we encode() once we've snipped off the leading SUB_PROGRESS or whatever
            if line.startswith(SUB_PROGRESS):
                try:
                    progress, transport_activity, task_info = bencode.bdecode(line[len(SUB_PROGRESS):].encode(self.encoding))
                    messages = [b.decode("utf-8") for b in task_info]
                except ValueError as e:
                    # we got malformed data from qsubprocess (bencode failed to decode)
                    # so just show it in the status console
                    self.logMessageEx("qsubprocess error: " + str(e), "error", self.stderr)
                    self.logMessageEx(line, "error", self.stderr)
                else:
                    self.setProgress(progress, messages, transport_activity.decode("utf-8"))
            elif line.startswith(SUB_GETPASS):
                prompt = bittorrent_b_decode_prompt(line[len(SUB_GETPASS):].encode(self.encoding))
                passwd, ok = QtWidgets.QInputDialog.getText(self, gettext("Enter Password"), prompt, QtWidgets.QLineEdit.Password)
                data = str(passwd).encode('utf-8'), int(ok)
                self.process.write(SUB_GETPASS + bencode.bencode(data) + "\n")
                if not ok:
                    self.abort_futher_processes()
            elif line.startswith(SUB_GETUSER):
                prompt = bittorrent_b_decode_prompt(line[len(SUB_GETUSER):].encode(self.encoding))
                passwd, ok = QtWidgets.QInputDialog.getText(self, gettext("Enter Username"), prompt)
                data = str(passwd).encode('utf-8'), int(ok)
                self.process.write(SUB_GETUSER + bencode.bencode(data) + "\n")
                if not ok:
                    self.abort_futher_processes()
            elif line.startswith(SUB_GETBOOL):
                prompt = bittorrent_b_decode_prompt(line[len(SUB_GETBOOL):].encode(self.encoding))
                button = QtWidgets.QMessageBox.question(self, "Bazaar", prompt, QtWidgets.QMessageBox.Yes, QtWidgets.QMessageBox.No)
                data = (button == QtWidgets.QMessageBox.Yes)
                self.process.write(SUB_GETBOOL + bencode.bencode(data) + "\n")
            elif line.startswith(SUB_CHOOSE):
                msg, choices, default = bittorrent_b_decode_choose_args(line[len(SUB_CHOOSE):].encode(self.encoding))
                mbox = QtWidgets.QMessageBox(parent=self)
                mbox.setText(msg)
                mbox.setIcon(QtWidgets.QMessageBox.Question)
                choices = choices.split('\n')
                index = 0
                for c in choices:
                    button = mbox.addButton(c, QtWidgets.QMessageBox.AcceptRole)
                    if index == default:
                        mbox.setDefaultButton(button)
                    index += 1
                index = mbox.exec_()
                self.process.write(SUB_CHOOSE + bencode.bencode(index) + "\n")
            elif line.startswith(SUB_ERROR):
                self.error_class, self.error_data = bittorrent_b_decode_exception_instance(line[len(SUB_ERROR):].encode(self.encoding))
            elif line.startswith(SUB_NOTIFY):
                msg = line[len(SUB_NOTIFY):]
                if msg.startswith(NOTIFY_CONFLICT):
                    self.is_conflicted = True
                    self.conflict_tree_path = bittorrent_b_decode_prompt(msg[len(NOTIFY_CONFLICT):].encode(self.encoding))
            else:
                self.logMessageEx(line, 'plain', self.stdout)

    def readStderr(self):
        data = bytes(self.process.readAllStandardError()).decode(self.encoding, 'replace')
        if data:
            self.error.emit(True)

        for line in data.splitlines():
            # RJLRJL this should be brz, I think
            # error = line.startswith("bzr: ERROR:")
            error = line.startswith("brz: ERROR:")
            self.logMessage(line, error, self.stderr)

    def logMessage(self, message, error=False, terminal_stream=None):
        kind = 'plain'
        if error:
            kind = 'error'
        self.logMessageEx(message, kind, terminal_stream)

    def logMessageEx(self, message, kind="plain", terminal_stream=None):
        """Write message to console area.
        @param kind: kind of message used for selecting style of formatting.
            Possible kind values:
                * plain = usual message, written in default style;
                * error = error message, written in red;
                * cmdline = show actual command-line, written in blue.
        @param terminal_stream: if we working in non --ui-mode
            the message can be echoed to real terminal via specified
            terminal_stream (e.g. sys.stdout or sys.stderr)
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
        if not self.ui_mode and terminal_stream:
            terminal_stream.write(message)
            terminal_stream.write('\n')

    def reportProcessError(self, error, message=None):
        self.aborting = False
        self.setProgress(1000000, [gettext("Failed!")])
        if message is None:
            if error == QtCore.QProcess.FailedToStart:
                message = gettext("Failed to start brz.")
            else:
                message = gettext("Error while running brz. (error code: %d)" % error)
        self.logMessage(message, True)
        self.failed.emit(self.error_class)

    def onFinished(self, exitCode, exitStatus):
        self._delete_args_file()
        if self.aborting:
            self.aborting = False
            self.setProgress(1000000, [gettext("Aborted!")])
            self.failed.emit('Aborted')
        elif exitCode < 3:
            if self.commands and not self.aborting:
                self._start_next()
            else:
                self.is_finished = True
                self.setProgress(1000000, [gettext("Finished!")])
                if self.is_conflicted:
                    self.conflicted.emit(self.conflict_tree_path)
                time.sleep(2)
                self.finished.emit(True)
        else:
            self.setProgress(1000000, [gettext("Failed!")])
            self.failed.emit(self.error_class)

    def _create_args_file(self, text:bytes):
        """@param text: text to write into temp file,
                        it should be unicode string
        """
        if self._args_file:
            self._delete_args_file()
        # RJLRJL check QBzr vs QBrz
        # qdir = os.path.join(tempfile.gettempdir(), 'QBzr', 'qsubprocess')
        qdir = os.path.join(tempfile.gettempdir(), 'QBrz', 'qsubprocess')
        if not os.path.isdir(qdir):
            os.makedirs(qdir)
        fd, fname = tempfile.mkstemp(dir=qdir)
        with os.fdopen(fd, "wb") as f:
            # f.write(text.decode('utf8'))
            f.write(text)
        self._args_file = fname
        return fname

    def _delete_args_file(self):
        if self._args_file:
            try:
                os.unlink(self._args_file)
            except (IOError, OSError):
                pass
            else:
                self._args_file = None


class SubprocessProgressView (TextProgressView):

    def __init__(self, term_file):
        TextProgressView.__init__(self, term_file)
        # The TextProgressView does not show the transport activity untill
        # there was a progress update. This changed because showing the
        # transport activity before a progress update would cause artifacts to
        # remain on the screen. We don't have to worry about that
        self._have_output = True

    def _repaint(self):
        if self._last_task:
            # Since bzr 2.2 _format_task returns a 2-tuple of unicode
            text, counter = self._format_task(self._last_task)
            task_info = (text.encode("utf-8"), counter.encode("utf-8"))
            progress_frac = self._last_task._overall_completion_fraction()
            if progress_frac is not None:
                progress = int(progress_frac * 1000000)
            else:
                progress = 1
        else:
            task_info = ()
            progress = 0

        trans = self._last_transport_msg.encode("utf-8")

        bdata = bencode.bencode((progress, trans, task_info))
        self._term_file.write(SUB_PROGRESS + bdata.decode("utf-8") + '\n')
        self._term_file.flush()

    def clear(self):
        pass


class SubprocessUIFactory(TextUIFactory):

    def make_progress_view(self):
        return SubprocessProgressView(self.stdout)

    # This is to be compatabile with bzr less rev 4558
    _make_progress_view = make_progress_view

    def clear_term(self):
        """
        # Prepare the terminal for output.

        # This will, for example, clear text progress bars, and leave the
        # cursor at the leftmost position.
        """
        pass

    def _get_answer_from_main(self, name, arg):
        self.stdout.write(name + bittorrent_b_encode_prompt(arg) + '\n')
        self.stdout.flush()
        line = self.stdin.readline()
        if line.startswith(name):
            return bencode.bdecode(line[len(name):].rstrip('\r\n'))
        raise Exception("Did not receive a answer from the main process.")

    def _choose_from_main(self, msg, choices, default):
        name = SUB_CHOOSE
        self.stdout.write(name + bittorrent_b_encode_choose_args(msg, choices, default) + '\n')
        self.stdout.flush()
        line = self.stdin.readline()
        if line.startswith(name):
            return bencode.bdecode(line[len(name):].rstrip('\r\n'))
        raise Exception("Did not receive a answer from the main process.")

    def get_password(self, prompt='', **kwargs):
        prompt = prompt % kwargs
        passwd, accepted = self._get_answer_from_main(SUB_GETPASS, prompt)
        if accepted:
            return passwd
        else:
            raise KeyboardInterrupt()

    def get_username(self, prompt='', **kwargs):
        prompt = prompt % kwargs
        username, accepted = self._get_answer_from_main(SUB_GETUSER, prompt)
        if accepted:
            return username
        else:
            raise KeyboardInterrupt()

    def get_boolean(self, prompt):
        return self._get_answer_from_main(SUB_GETBOOL, prompt+'?')

    def choose(self, msg, choices, default=None):
        if default is None:
            default = -1
        index = self._choose_from_main(msg, choices, default)
        return index


# [bialix 2010/02/04] body of cmd_qsubprocess has moved from commands.py
# to see annotation of cmd_qsubprocess before move use:
#
#  bzr qannotate commands.py -r1117

@contextmanager
def watch_conflicts(on_conflicted):
    """
    Call on_conflicted when conflicts generated in the context.
    :on_conflicted: callable with 1 argument(abspath of wt).
    """
    from uuid import uuid1
    hook_name = uuid1().hex

    def post_merge(m):
        if len(m.cooked_conflicts) > 0:
            try:
                abspath = m.this_tree.abspath('')
            except AttributeError:
                abspath = ""
            on_conflicted(abspath)

    try:
        from breezy.merge import Merger
        Merger.hooks.install_named_hook('post_merge', post_merge, hook_name)
        yield
    finally:
        Merger.hooks.uninstall_named_hook('post_merge', hook_name)

def run_subprocess_command(cmd, bencoded=False):
    """The actual body of qsubprocess.
    Running specified bzr command in the subprocess.
    @param cmd: string with command line to run.
    @param bencoded: either cmd_str is bencoded list or not.

    (RJL: No, I don't know if that means it's always a list that's
    either bencoded or a list that's not, or it's either a bencoded-list
    or something else bencoded, or something else not bencoded.)

    NOTE: if cmd starts with @ sign then it used as name of the file
    where actual command line string is saved (utf-8 encoded)...BUT
    see below.

    RJLRJL: Because of the joy of python2 -> python3, but more because nobody
    bothered to make a class for bencoded, we have to fanny about with bytes
    and strings - what larks!. So, one day, we'll make bencoded a class.
    Strictly, bencoded (python3) *should* be bytes, but you never can tell.
    Particularly in this code. And don't get me started on rev_ids.

    Also, the 'starts with @' means it's **NOT BENCODED** (sometimes).
    How can you tell?
    Try passing cmd to bdecode: you'll probably get an error about 'identifier 64'.
    You *can* strip off the leading '@' but what's left behind might or might not
    be bencoded.

    Standards, we've heard of them. I've fixed some of the passing code so that it
    actually passes bencoded('@'+filename) not '@'+filename, but don't know if I've
    found it all.

    Breezy's ``run_bzr`` says we should pass 'valid' strings so we need to
    get rid of any lurking bytes. Unfortunately, we can no longer trust the
    bencoded flag as passed. Also, run_bzr is lying: if you read the code it actually calls
    ``_specified_or_unicode_argv()`` which will:

      raise errors.BzrError("argv should be list of unicode strings.")

    so it *actually wants a list of strings*. Grr.
    """
    if MS_WINDOWS:
        thread.start_new_thread(windows_emulate_ctrl_c, ())
    else:
        signal.signal(signal.SIGINT, sigabrt_handler)
    ui.ui_factory = SubprocessUIFactory(stdin=sys.stdin, stdout=sys.stdout, stderr=sys.stderr)

    if not isinstance(cmd, str) and not isinstance(cmd, bytes):
        raise TypeError('Only string or bytes accepted ({0}, {1})'.format(cmd, type(cmd)))

    # Right, here we go, we could be a string or bytes
    # and bencoded might be actually true (it's bytes) or just
    # pretending (it's not bytes but is bencoded). Also, the cmd might
    # result in a list once decoded, even though this is not supposed to
    # be called with one... or perhaps it is (it seems to vary)
    # Eventually, we need a list in argv to pass to breezy's run_bzr
    argv = []
    if bencoded:
        # if we are bytes AND bencoded (perhaps), decode properly
        if isinstance(cmd, bytes):
            s_cmd = bencode.bdecode(cmd)
        elif isinstance(cmd, str):
            # Force to bytes to decode it properly from bencoded format
            # SOMETIMES it's NOT really bencoded, even when it says it is
            # in which case we will probably get a ValueError
            b = bytes(cmd, 'utf-8')
            s_cmd = bencode.bdecode(b)
    else:
        if isinstance(cmd, bytes):
            s_cmd = cmd.decode('utf-8')
        else:
            s_cmd = cmd

    # Sometimes we get a list, decode each line
    # Note that each LINE might be bencoded too
    if isinstance(s_cmd, list):
        for i, s in enumerate(s_cmd):
            if isinstance(s, bytes):
                argv.append(s.decode('utf-8'))
    else:
        # just put the string into it
        argv.append(s_cmd)

    # Now we are looking for '@' at the start
    if s_cmd[0][0] == '@':
        fname = s_cmd[1:]
        # Changed this: it's written in 'b' so must be read that way too
        with open(fname, 'rb') as f:
            s_cmd = f.read()
        # We stored a bencoded string like b'l6:ignore18:qbrz-setup-iss.loge', so...:
        s_cmd = bencode.bdecode(s_cmd)
        # ...and again, sometimes we get a list like [b'ignore', b'qbrz-setup-iss.log'], so...
        argv = []
        if isinstance(s_cmd, list):
            for i, s in enumerate(s_cmd):
                if isinstance(s, bytes):
                    argv.append(s.decode('utf-8'))
        else:
            # just put the string into it
            argv.append(s_cmd)

    try:
        def on_conflicted(wtpath):
            # See comment re: frankenstrings below for why we cast to string
            print("%s%s%s" % (SUB_NOTIFY, NOTIFY_CONFLICT, str(bittorrent_b_encode_prompt(wtpath), 'utf-8')))
        with watch_conflicts(on_conflicted):
            # _specified_or_unicode_argv should raise a BzrError here
            # if we pass a string
            return commands.run_bzr(argv)
    except (KeyboardInterrupt, SystemExit):
        raise
    except errors.BzrError as e:
        print("%s%s" % (SUB_ERROR, str(bittorrent_b_encode_exception_instance(e), 'utf-8')))
        raise
    except Exception as e:
        # The problem with the original code is that it sends a Frankenstring, for example:
        #
        #   qbrz:ERROR:b'l18:AlreadyBranchErrordee'
        #
        # which is a str, but with a byte-marked string (b'...') inside it, so
        # force it to be properly bytes OR force the bittorrent to string and let
        # the receiver sort it out: strictly speaking, it's not really b-encoded
        # if it has a prefix so make it a string
        print("%s%s" % (SUB_ERROR, str(bittorrent_b_encode_exception_instance(e), 'utf-8')))
        raise


def sigabrt_handler(signum, frame):
    raise KeyboardInterrupt()


if MS_WINDOWS:
    import ctypes
    if getattr(sys, "frozen", None):
        # this is needed for custom brz.exe builds (without TortoiseBzr inside)
        ctypes.__path__.append(os.path.normpath(os.path.join(os.path.dirname(__file__), '..', '_lib', 'ctypes')))
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
        return 'qbrz-qsubprocess-%d' % child_pid

    def signal_event(child_pid):
        import win32event
        ev = win32event.CreateEvent(None, 0, 0, get_event_name(child_pid))
        try:
            win32event.SetEvent(ev)
        finally:
            ev.Close()

    def windows_emulate_ctrl_c():
        """To emulate Ctrl+C on Windows we have to wait some global event,
        and once it will trigger we will try to interrupt main thread.
        IMPORTANT: This function should be invoked as separate thread!
        """
        import win32event
        ev = win32event.CreateEvent(None, 0, 0, get_event_name(os.getpid()))
        try:
            win32event.WaitForSingleObject(ev, win32event.INFINITE)
        finally:
            ev.Close()
        thread.interrupt_main()

# === Bncode / Bdecode (B-Encode)

# Bencode (pronounced _B-Encode_, not _Ben Code_) is a serialization encoding format used in torrent files for
# the BitTorrent protocol. It consists of a series of strings, integers, lists, and dictionaries; since
# lists and dictionaries contain multiple elements of the Bencode types, they can be nested hierarchically,
# encapsulating complex data structures.
#
# <https://wiki.theory.org/index.php/BitTorrentSpecification#Bencoding>
#
# The elements are:-
#
#   * Strings: coded as a decimal number giving the length of the string, then a colon,
#   then the string itself; e.g., ``5:stuff``. The empty string is ``0:``
#
#   * Integers: coded as the letter ``i``, then the integer
#      as a series of decimal digits), then the letter ``e``. E.g., ``i42e`` is 42.
#      Leading zeroes (e.g. ``i-04e``) are invalid, except for zero itself: ``i0e``.
#
#   * Lists: coded as the letter ``l`` (lower-case L), then the list elements
#      (each encoded as one of the Bencode types, which can include other lists), then the
#       letter ``e``. E.g.,
#
#       ``li42e5:stuffi666ee``
#
#     which contains ``42``, ``stuff`` (strictly ``5:stuff``) and ``666``
#      as its elements)
#
#   * Dictionaries: pairs of keys and values, where the key is a string
#     and the value can be any Bencode type; surrounded by an opening letter ``d``
#     and closing letter ``e``; keys must appear in alphabetic order; e.g.,
#
#     ``d4:testi42e3:zzz4:junke``
#
#     is a dictionary where key ``test`` has value ``42`` and key ``zzz`` has value ``junk``.


def bittorrent_b_encode_unicode(args: list) -> bytes:
    """
    Bencode list of unicode strings as list of utf-8 strings and converting
    resulting string to unicode.
    Bencode will only accept bytes
    """
    if isinstance(args, str) or isinstance(args, bytes):
        raise TypeError('bittorrent_b_encode_unicode only accepts an iterable got ', type(args))
    args_utf8 = bencode.bencode([a.encode('utf-8') for a in args])
    return args_utf8


def bittorrent_b_encode_prompt(utf_string: str or bytes) -> bytes:
    # The brz.bencode returns bytes but can be passed
    # integer, list, bytes, and dictionaries
    # BUT only those (so NO strings, even in dictionaries)
    # The problem is that the original code called bencode like so:
    #
    # ``bencode.bencode(arg.encode('unicode-escape'))``
    #
    # ...and you can only do encode() with bytes
    # What we *can* do is insist we only get strings sent to us
    if not isinstance(utf_string, str) and not isinstance(utf_string, bytes):
        raise TypeError('bittorrent_b_encode_prompt accepts only strings or bytes')
    return bencode.bencode(utf_string.encode('utf-8'))


def bittorrent_b_decode_prompt(bencoded_bytes: bytes) -> str:
    # bdecode requires an already bittorrent-encoded bytes
    # (it'll give a TypeError for plain strings)
    # So we can insist that we have bytes
    if not isinstance(bencoded_bytes, bytes):
        raise TypeError('bittorrent_b_decode_prompt accepts only bytes')
    # However, it can return bytes, integer, list or dictionary, but here we assume
    # bytes... and we convert them to a string
    return bencode.bdecode(bencoded_bytes).decode('utf-8')


def bittorrent_b_encode_choose_args(msg, choices, default):
    if default is None:
        default = -1
    return bencode.bencode([msg.encode('utf-8'), choices.encode('utf-8'), default])


def bittorrent_b_decode_choose_args(s):
    msg, choices, default = bencode.bdecode(s)
    msg = msg.decode('utf-8')
    choices = choices.decode('utf-8')
    return msg, choices, default


def bittorrent_b_encode_exception_instance(e: Exception) -> bytes:
    """
    Serialise the main information about an exception instance with bencode

    For now, nearly all exceptions just give the exception name as a string,
    but a dictionary is also given that may contain unicode-escaped attributes.

    RJLRJL: actually, one has to pass bytes as both dictionary keys and values.
    For example:

      ``bencode.bencode((b'something', {b'somekey':b'fred'}))``

    gives

      ``b'l9:somethingd7:somekey4:fredee'``

    but if either is a plain string, bencode will choke. b-encoded keys and values
    are accepted too, so:

      ``bencode.bencode((b'something', {b'7:somekey':b'4:fred'}))``
      ``bencode.bencode((b'something', {b'somekey':b'4:fred'}))``
      ``bencode.bencode((b'something', {b'7:somekey':b'fred'}))``

    would all work, as does, perhaps unsurprisingly:

      ``bencode.bencode((b'9:something', {b'7:somekey':b'4:fred'}))``

    """
    if not isinstance(e, Exception):
        raise TypeError('Passed {0} instead of exception'.format(type(e)))
    # GZ 2011-04-15: Could use breezy.trace._qualified_exception_name in 2.4
    # Convert to bytes...
    ename = e.__class__.__name__.encode('utf-8')
    d = {}
    # For now be conservative and only serialise attributes that will get used
    # RJL: in 2020 nothing has yet been added! However, we'll keep the same code
    keys = []
    if isinstance(e, errors.UncommittedChanges):
        # Keys need to be bytes: however, when we use getattr, we need to use
        # a string (not bytes). What larks!
        keys.append("display_url")
    for key in keys:
        # getattr and __repr__ can break in lots of ways, so catch everything
        # but exceptions that occur as interrupts, allowing for Python 2.4
        try:
            # Fetch (presumably) a string
            val = getattr(e, key)
            # RJL: the following is to get the representation as a string
            # the problem is that bytes will get wrapped in ".." which is probably not
            # what is wanted.
            # ``if not isinstance(val, str):
            #     val = repr(val)
            #   val = val.decode("ascii", "replace")``
            #
            # We only need to convert other things than bytes
            if not isinstance(val, bytes):
                if not isinstance(val, str):
                    val = repr(val)
                # Now convert to bytes...
                val = val.encode('utf-8')
        except (KeyboardInterrupt, SystemExit):
            raise
        except KeyError:
            val = b'[Qbrz could not find the key [{0}] to serialize this attribute]'.format(key)
        except:
            val = b"[QBrz could not serialize this attribute]"
        # The key needs to be bytes too
        d[key.encode('utf-8')] = val
    return bencode.bencode((ename, d))


def bittorrent_b_decode_exception_instance(bencoded_bytes: bytes) -> (str, list):
    """
    Deserialise information about an exception instance with bdecode

    Returns a string and a list of strings
    """
    # We'll have something in b-encoded form, such as, for example:
    #
    #  ``b'l15:PermissionErrordee'``
    #
    # which is 'PermissionError' string and {} (an empty dictionary)
    # b-decode will return bytes so, from the above example, we'd get:
    #
    #  ``[b'PermissionError', {}]``
    if not isinstance(bencoded_bytes, bytes):
        raise TypeError('Bytes required for bittorrent_b_decode_exception_instance')

    ename, d = bencode.bdecode(bencoded_bytes)

    #
    # The returned list needs to have entries with strings, not bytes.
    # **However**, the orignal code didn't try to convert the keys.
    # Instead, we now create a new_d of the same type as d.
    #
    # Get the type via type(d) and then instantiate id via () - hence
    # new_d = type(d)()
    #
    new_d = type(d)()
    for k in d:
        # Convert the key and the value to a string from bytes
        # and put the results into new_d
        new_d[k.decode('utf-8')] = d[k].decode('utf-8')
    # And convert the exception name to a string too
    return ename.decode('utf-8'), new_d


# GZ 2011-04-15: Remove or deprecate these functions if they remain unused?
# def bittorrent_b_encode_unicode_escape(obj):
#     if isinstance(obj, dict):
#         result = {}
#         for k,v in obj.items():
#             result[k] = v.encode('unicode-escape')
#         return result
#     else:
#         raise TypeError('bittorrent_b_encode_unicode_escape: unsupported type: %r' % type(obj))

# def bittorrent_b_decode_unicode_escape(a_dict:dict) -> dict:
#     # Receives a dictionary that has been bittorrent encoded
#     if isinstance(obj, dict):
#         result = {}
#         for k,v in obj.items():
#             result[k] = v.decode('unicode-escape')
#         return result
#     else:
#         raise TypeError('bittorrent_b_decode_unicode_escape: unsupported type: %r' % type(obj))
