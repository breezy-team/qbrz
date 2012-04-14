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

from PyQt4 import QtCore, QtGui
from contextlib import contextmanager

from bzrlib.plugins.qbzr.lib import MS_WINDOWS
from bzrlib.plugins.qbzr.lib.i18n import gettext, N_
from bzrlib.plugins.qbzr.lib.util import (
    BTN_CANCEL,
    BTN_CLOSE,
    BTN_OK,
    QBzrDialog,
    QBzrWindow,
    StandardButton,
    ensure_unicode,
    InfoWidget,
    )

from bzrlib.ui.text import TextProgressView, TextUIFactory
from bzrlib.plugins.qbzr.lib.trace import (
   report_exception,
   SUB_LOAD_METHOD)

from bzrlib.lazy_import import lazy_import
lazy_import(globals(), '''
import codecs
import re
import shlex
import signal
import tempfile
import thread

from bzrlib import (
    bencode,
    commands,
    errors,
    osutils,
    ui,
    )

from bzrlib.bzrdir import BzrDir

from bzrlib.plugins.qbzr.lib.commit import CommitWindow
from bzrlib.plugins.qbzr.lib.revert import RevertWindow
from bzrlib.plugins.qbzr.lib.shelvewindow import ShelveWindow
from bzrlib.plugins.qbzr.lib.conflicts import ConflictsWindow
''')


# Subprocess service messages markers
SUB_PROGRESS = "qbzr:PROGRESS:"
SUB_GETPASS = "qbzr:GETPASS:"
SUB_GETUSER = "qbzr:GETUSER:"
SUB_GETBOOL = "qbzr:GETBOOL:"
SUB_CHOOSE = "qbzr:CHOOSE:"
SUB_ERROR = "qbzr:ERROR:"
SUB_NOTIFY = "qbzr:NOTIFY:"

NOTIFY_CONFLICT = "conflict:"


class WarningInfoWidget(InfoWidget):
    def __init__(self, parent):
        InfoWidget.__init__(self, parent)
        layout = QtGui.QVBoxLayout(self)
        label_layout = QtGui.QHBoxLayout()
        
        icon = QtGui.QLabel()
        icon.setPixmap(self.style().standardPixmap(
                       QtGui.QStyle.SP_MessageBoxWarning))
        label_layout.addWidget(icon)
        self.label = QtGui.QLabel()
        label_layout.addWidget(self.label, 2)
        layout.addLayout(label_layout)
        self.button_layout = QtGui.QHBoxLayout()
        self.button_layout.addStretch(1)
        layout.addLayout(self.button_layout)

        self.buttons = []

    def add_button(self, text, on_click):
        button = QtGui.QPushButton(gettext(text))
        self.connect(button, QtCore.SIGNAL("clicked(bool)"), on_click)
        self.button_layout.addWidget(button)
        self.buttons.append((button, on_click))

    def remove_all_buttons(self):
        for button, on_click in self.buttons:
            self.disconnect(button, QtCore.SIGNAL("clicked(bool)"), on_click)
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
        self.connect(self.process_widget,
            QtCore.SIGNAL("finished()"),
            self.on_finished)
        self.connect(self.process_widget,
            QtCore.SIGNAL("failed(QString)"),
            self.on_failed)
        self.connect(self.process_widget,
            QtCore.SIGNAL("error()"),
            self.on_error)
        self.connect(self.process_widget,
            QtCore.SIGNAL("conflicted(QString)"),
            self.on_conflicted)

        self.closeButton = StandardButton(BTN_CLOSE)
        self.okButton = StandardButton(BTN_OK)
        self.cancelButton = StandardButton(BTN_CANCEL)

        # ok button gets disabled when we start.
        QtCore.QObject.connect(self,
                               QtCore.SIGNAL("subprocessStarted(bool)"),
                               self.okButton,
                               QtCore.SLOT("setDisabled(bool)"))

        # ok button gets hidden when we finish.
        QtCore.QObject.connect(self,
                               QtCore.SIGNAL("subprocessFinished(bool)"),
                               self.okButton,
                               QtCore.SLOT("setHidden(bool)"))

        # close button gets shown when we finish.
        QtCore.QObject.connect(self,
                               QtCore.SIGNAL("subprocessFinished(bool)"),
                               self.closeButton,
                               QtCore.SLOT("setShown(bool)"))

        # cancel button gets disabled when finished.
        QtCore.QObject.connect(self,
                               QtCore.SIGNAL("subprocessFinished(bool)"),
                               self.cancelButton,
                               QtCore.SLOT("setDisabled(bool)"))

        # ok button gets enabled when we fail.
        QtCore.QObject.connect(self,
                               QtCore.SIGNAL("subprocessFailed(bool)"),
                               self.okButton,
                               QtCore.SLOT("setDisabled(bool)"))

        # Change the ok button to 'retry' if we fail.
        QtCore.QObject.connect(self,
                               QtCore.SIGNAL("subprocessFailed(bool)"),
                               lambda failed: self.okButton.setText(
                                              gettext('&Retry')))

        self.buttonbox = QtGui.QDialogButtonBox(self)
        self.buttonbox.addButton(self.okButton,
            QtGui.QDialogButtonBox.AcceptRole)
        self.buttonbox.addButton(self.closeButton,
            QtGui.QDialogButtonBox.AcceptRole)
        self.buttonbox.addButton(self.cancelButton,
            QtGui.QDialogButtonBox.RejectRole)
        self.connect(self.buttonbox, QtCore.SIGNAL("accepted()"), self.do_accept)
        self.connect(self.buttonbox, QtCore.SIGNAL("rejected()"), self.do_reject)
        self.closeButton.setHidden(True) # but 'close' starts as hidden.

        self.infowidget = WarningInfoWidget(self)
        self.infowidget.hide()
        QtCore.QObject.connect(self,
                               QtCore.SIGNAL("subprocessStarted(bool)"),
                               self.infowidget,
                               QtCore.SLOT("setHidden(bool)"))

        if immediate:
            self.do_accept()

    def make_default_status_box(self):
        panel = QtGui.QWidget()
        vbox = QtGui.QVBoxLayout(panel)
        vbox.setContentsMargins(0, 0, 0, 0)
        vbox.addWidget(self.infowidget)
        status_group_box = QtGui.QGroupBox(gettext("Status"))
        status_layout = QtGui.QVBoxLayout(status_group_box)
        status_layout.setContentsMargins(0, 0, 0, 0)
        status_layout.addWidget(self.process_widget)
        vbox.addWidget(status_group_box)
        return panel

    def make_process_panel(self):
        panel = QtGui.QWidget()
        vbox = QtGui.QVBoxLayout(panel)
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
            self.on_failed('CheckArgsFailed')

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

        if not self.ui_mode and not self.infowidget.isVisible():
            self.close()

    def on_conflicted(self, tree_path):
        if tree_path:
            self.action_url = unicode(tree_path) # QString -> unicode
            self.infowidget.setup_for_conflicted(self.open_conflicts_win,
                                                 self.open_revert_win)
            self.infowidget.show()

    def on_failed(self, error):
        self.emit(QtCore.SIGNAL("subprocessFailed(bool)"), False)
        self.emit(QtCore.SIGNAL("disableUi(bool)"), False)
        
        if error=='UncommittedChanges':
            self.action_url = self.process_widget.error_data['display_url']
            self.infowidget.setup_for_uncommitted(self.open_commit_win, 
                                                  self.open_revert_win,
                                                  self.open_shelve_win)
            self.infowidget.show()

        elif error=='LockContention':
            self.infowidget.setup_for_locked(self.do_accept)
            self.infowidget.show()

    def on_error(self):
        self.emit(QtCore.SIGNAL("subprocessError(bool)"), False)

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
        QtCore.QObject.connect(window,
                               QtCore.SIGNAL("allResolved(bool)"),
                               self.infowidget,
                               QtCore.SLOT("setHidden(bool)")) 

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

        self.force_passing_args_via_file = False
        self._args_file = None  # temp file to pass arguments to qsubprocess
        self.error_class = ''
        self.error_data = {}
        self.conflicted = False

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
        self._setup_stdout_stderr()
        self._delete_args_file()
        dir, args = self.commands.pop(0)

        # Log the command we about to execute
        def format_args_for_log(args):
            r = ['bzr']
            for a in args:
                a = unicode(a).translate({
                        ord(u'\n'): u'\\n',
                        ord(u'\r'): u'\\r',
                        ord(u'\t'): u'\\t',
                        })
                if " " in a:
                    r.append('"%s"' % a)
                else:
                    r.append(a)
            s = ' '.join(r)
            if len(s) > 128:  # XXX make it configurable?
                s = s[:128] + '...'
            return s
        self.logMessageEx("Run command: "+format_args_for_log(args), "cmdline", self.stderr)

        args = bencode_unicode(args)

        # win32 has command-line length limit about 32K, but it seems 
        # problems with command-line buffer limit occurs not only on windows.
        # see bug https://bugs.launchpad.net/qbzr/+bug/396165
        # on Linux I believe command-line is in utf-8,
        # so we need to have some extra space
        # when converting unicode -> utf8
        if (len(args) > 10000       # XXX make the threshold configurable in qbzr.conf?
            or re.search(r"(?:"
                r"\n|\r"            # workaround for bug #517420
                r"|\\\\"            # workaround for bug #528944
                r")", args) is not None
            or self.force_passing_args_via_file     # workaround for bug #936587
            ):
            # save the args to the file
            fname = self._create_args_file(args)
            args = "@" + fname.replace('\\', '/')

        if dir is None:
            dir = self.defaultWorkingDir

        self.error_class = ''
        self.error_data = {}

        self.process.setWorkingDirectory(dir)
        if getattr(sys, "frozen", None) is not None:
            bzr_exe = sys.executable
            if os.path.basename(bzr_exe) != "bzr.exe":
                # Was run from bzrw.exe or tbzrcommand.
                bzr_exe = os.path.join(os.path.dirname(sys.executable), "bzr.exe")
                if not os.path.isfile(bzr_exe):
                    self.reportProcessError(
                        None, gettext('Could not locate "bzr.exe".'))
            self.process.start(
                bzr_exe, ['qsubprocess', '--bencode', args])
        else:
            # otherwise running as python script.
            # ensure run from bzr, and not others, e.g. tbzrcommand.py
            script = sys.argv[0]
            # make absolute, because we may be running in a different
            # dir.
            script = os.path.abspath(script)
            if os.path.basename(script) != "bzr":
                import bzrlib
                # are we running directly from a bzr directory?
                script = os.path.join(bzrlib.__path__[0], "..", "bzr")
                if not os.path.isfile(script):
                    # maybe from an installed bzr?
                    script = os.path.join(sys.prefix, "scripts", "bzr")
                if not os.path.isfile(script):
                    self.reportProcessError(
                        None, gettext('Could not locate "bzr" script.'))
            self.process.start(
                sys.executable, [script, 'qsubprocess', '--bencode', args])

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
            text = " / ".join(messages)
        self.progressMessage.setText(text)
        if transport_activity is not None:
            self.transportActivity.setText(transport_activity)

    def readStdout(self):
        # ensure we read from subprocess plain string
        data = str(self.process.readAllStandardOutput())
        # we need unicode for all strings except bencoded streams
        for line in data.splitlines():
            if line.startswith(SUB_PROGRESS):
                try:
                    progress, transport_activity, task_info = bencode.bdecode(
                        line[len(SUB_PROGRESS):])
                    messages = [b.decode("utf-8") for b in task_info]
                except ValueError, e:
                    # we got malformed data from qsubprocess (bencode failed to decode)
                    # so just show it in the status console
                    self.logMessageEx("qsubprocess error: "+str(e), "error", self.stderr)
                    self.logMessageEx(line.decode(self.encoding), "error", self.stderr)
                else:
                    self.setProgress(progress, messages, transport_activity)
            elif line.startswith(SUB_GETPASS):
                prompt = bdecode_prompt(line[len(SUB_GETPASS):])
                passwd, ok = QtGui.QInputDialog.getText(self,
                                                        gettext("Enter Password"),
                                                        prompt,
                                                        QtGui.QLineEdit.Password)
                data = unicode(passwd).encode('utf-8'), int(ok)
                self.process.write(SUB_GETPASS + bencode.bencode(data) + "\n")
                if not ok:
                    self.abort_futher_processes()
            elif line.startswith(SUB_GETUSER):
                prompt = bdecode_prompt(line[len(SUB_GETUSER):])
                passwd, ok = QtGui.QInputDialog.getText(self,
                                                        gettext("Enter Username"),
                                                        prompt)
                data = unicode(passwd).encode('utf-8'), int(ok)
                self.process.write(SUB_GETUSER + bencode.bencode(data) + "\n")
                if not ok:
                    self.abort_futher_processes()
            elif line.startswith(SUB_GETBOOL):
                prompt = bdecode_prompt(line[len(SUB_GETBOOL):])
                button = QtGui.QMessageBox.question(
                    self, "Bazaar", prompt,
                    QtGui.QMessageBox.Yes, QtGui.QMessageBox.No)
                
                data = (button == QtGui.QMessageBox.Yes)
                self.process.write(SUB_GETBOOL + bencode.bencode(data) + "\n")
            elif line.startswith(SUB_CHOOSE):
                msg, choices, default = bdecode_choose_args(line[len(SUB_CHOOSE):])
                mbox = QtGui.QMessageBox(parent=self)
                mbox.setText(msg)
                mbox.setIcon(QtGui.QMessageBox.Question)
                choices = choices.split('\n')
                index = 0
                for c in choices:
                    button = mbox.addButton(c, QtGui.QMessageBox.AcceptRole)
                    if index == default:
                        mbox.setDefaultButton(button)
                    index += 1
                index = mbox.exec_()
                self.process.write(SUB_CHOOSE + bencode.bencode(index) + "\n")
            elif line.startswith(SUB_ERROR):
                self.error_class, self.error_data = bdecode_exception_instance(
                    line[len(SUB_ERROR):])
            elif line.startswith(SUB_NOTIFY):
                msg = line[len(SUB_NOTIFY):]
                if msg.startswith(NOTIFY_CONFLICT):
                    self.conflicted = True
                    self.conflict_tree_path = bdecode_prompt(msg[len(NOTIFY_CONFLICT):])
            else:
                line = line.decode(self.encoding, 'replace')
                self.logMessageEx(line, 'plain', self.stdout)

    def readStderr(self):
        data = str(self.process.readAllStandardError()).decode(self.encoding, 'replace')
        if data:
            self.emit(QtCore.SIGNAL("error()"))

        for line in data.splitlines():
            error = line.startswith("bzr: ERROR:")
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
                message = gettext("Failed to start bzr.")
            else:
                message = gettext("Error while running bzr. (error code: %d)" % error)
        self.logMessage(message, True)
        self.emit(QtCore.SIGNAL("failed(QString)"), self.error_class)

    def onFinished(self, exitCode, exitStatus):
        self._delete_args_file()
        if self.aborting:
            self.aborting = False
            self.setProgress(1000000, [gettext("Aborted!")])
            self.emit(QtCore.SIGNAL("failed(QString)"), 'Aborted')
        elif exitCode < 3:
            if self.commands and not self.aborting:
                self._start_next()
            else:
                self.finished = True
                self.setProgress(1000000, [gettext("Finished!")])
                if self.conflicted:
                    self.emit(QtCore.SIGNAL("conflicted(QString)"), 
                              self.conflict_tree_path)
                self.emit(QtCore.SIGNAL("finished()"))
        else:
            self.setProgress(1000000, [gettext("Failed!")])
            self.emit(QtCore.SIGNAL("failed(QString)"), self.error_class)

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
            except (IOError, OSError):
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

        trans = self._last_transport_msg

        self._term_file.write(
            SUB_PROGRESS + bencode.bencode((progress, trans, task_info)) + '\n')
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

    def _get_answer_from_main(self, name, arg):
        self.stdout.write(name + bencode_prompt(arg) + '\n')
        self.stdout.flush()
        line = self.stdin.readline()
        if line.startswith(name):
            return bencode.bdecode(line[len(name):].rstrip('\r\n'))
        raise Exception("Did not recive a answer from the main process.")
    
    def _choose_from_main(self, msg, choices, default):
        name = SUB_CHOOSE
        self.stdout.write(name + bencode_choose_args(msg, choices, default) + '\n')
        self.stdout.flush()
        line = self.stdin.readline()
        if line.startswith(name):
            return bencode.bdecode(line[len(name):].rstrip('\r\n'))
        raise Exception("Did not recive a answer from the main process.")
    
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
#     bzr qannotate commands.py -r1117

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
        from bzrlib.merge import Merger
        Merger.hooks.install_named_hook('post_merge', post_merge, hook_name)
        yield
    finally:
        Merger.hooks.uninstall_named_hook('post_merge', hook_name)

def run_subprocess_command(cmd, bencoded=False):
    """The actual body of qsubprocess.
    Running specified bzr command in the subprocess.
    @param cmd: string with command line to run.
    @param bencoded: either cmd_str is bencoded list or not.

    NOTE: if cmd starts with @ sign then it used as name of the file
    where actual command line string is saved (utf-8 encoded).
    """
    if MS_WINDOWS:
        thread.start_new_thread(windows_emulate_ctrl_c, ())
    else:
        signal.signal(signal.SIGINT, sigabrt_handler)
    ui.ui_factory = SubprocessUIFactory(stdin=sys.stdin,
                                        stdout=sys.stdout,
                                        stderr=sys.stderr)
    if cmd.startswith('@'):
        fname = cmd[1:]
        f = open(fname, 'rb')
        try:
            cmd_utf8 = f.read()
        finally:
            f.close()
    else:
        cmd_utf8 = cmd.encode('utf8')
    if not bencoded:
        argv = [unicode(p, 'utf-8') for p in shlex.split(cmd_utf8)]
    else:
        argv = [unicode(p, 'utf-8') for p in bencode.bdecode(cmd_utf8)]
    try:
        def on_conflicted(wtpath):
            print "%s%s%s" % (SUB_NOTIFY, NOTIFY_CONFLICT, bencode_prompt(wtpath))
        with watch_conflicts(on_conflicted):
            return commands.run_bzr(argv)
    except (KeyboardInterrupt, SystemExit):
        raise
    except Exception, e:
        print "%s%s" % (SUB_ERROR, bencode_exception_instance(e))
        raise


def sigabrt_handler(signum, frame):
    raise KeyboardInterrupt()


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


def bencode_unicode(args):
    """Bencode list of unicode strings as list of utf-8 strings and converting
    resulting string to unicode.
    """
    args_utf8 = bencode.bencode([unicode(a).encode('utf-8') for a in args])
    return unicode(args_utf8, 'utf-8')

def bencode_prompt(arg):
    return bencode.bencode(arg.encode('unicode-escape'))

def bdecode_prompt(s):
    return bencode.bdecode(s).decode('unicode-escape')

def bencode_choose_args(msg, choices, default):
    if default is None:
        default = -1
    return bencode.bencode([
        msg.encode('unicode-escape'),
        choices.encode('unicode-escape'),
        default
    ])

def bdecode_choose_args(s):
    msg, choices, default = bencode.bdecode(s)
    msg = msg.decode('unicode-escape')
    choices = choices.decode('unicode-escape')
    return msg, choices, default

def bencode_exception_instance(e):
    """Serialise the main information about an exception instance with bencode

    For now, nearly all exceptions just give the exception name as a string,
    but a dictionary is also given that may contain unicode-escaped attributes.
    """
    # GZ 2011-04-15: Could use bzrlib.trace._qualified_exception_name in 2.4
    ename = e.__class__.__name__
    d = {}
    # For now be conservative and only serialise attributes that will get used
    keys = []
    if isinstance(e, errors.UncommittedChanges):
        keys.append("display_url")
    for key in keys:
        # getattr and __repr__ can break in lots of ways, so catch everything
        # but exceptions that occur as interrupts, allowing for Python 2.4
        try:
            val = getattr(e, key)
            if not isinstance(val, unicode):
                if not isinstance(val, str):
                    val = repr(val)
                val = val.decode("ascii", "replace")
        except (KeyboardInterrupt, SystemExit):
            raise
        except:
            val = "[QBzr could not serialize this attribute]"
        d[key] = val.encode("unicode-escape")
    return bencode.bencode((ename, d))


def bdecode_exception_instance(s):
    """Deserialise information about an exception instance with bdecode"""
    ename, d = bencode.bdecode(s)
    for k in d:
        d[k] = d[k].decode("unicode-escape")
    return ename, d


# GZ 2011-04-15: Remove or deprecate these functions if they remain unused?
def encode_unicode_escape(obj):
    if isinstance(obj, dict):
        result = {}
        for k,v in obj.iteritems():
            result[k] = v.encode('unicode-escape')
        return result
    else:
        raise TypeError('encode_unicode_escape: unsupported type: %r' % type(obj))

def decode_unicode_escape(obj):
    if isinstance(obj, dict):
        result = {}
        for k,v in obj.iteritems():
            result[k] = v.decode('unicode-escape')
        return result
    else:
        raise TypeError('decode_unicode_escape: unsupported type: %r' % type(obj))
