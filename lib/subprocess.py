# -*- coding: utf-8 -*-
#
# QBzr - Qt frontend to Bazaar commands
# Copyright (C) 2006 Lukáš Lalinský <lalinsky@gmail.com>
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

import sys
from PyQt4 import QtCore, QtGui
from bzrlib import progress
from bzrlib.util import bencode
from bzrlib.plugins.qbzr.lib.i18n import gettext, N_
from bzrlib.plugins.qbzr.lib.util import (
    BTN_CANCEL,
    BTN_OK,
    BTN_CLOSE,
    QBzrWindow,
    QBzrDialog,
    StandardButton,
    )


class SubProcessWindowBase:

    def __init_internal__(self, title,
                          name="genericsubprocess",
                          args=None,
                          dir=None,
                          default_size=None,
                          ui_mode=True,
                          dialog=True,
                          parent=None):
        self.restoreSize(name, default_size)
        self.args = args
        self.dir = dir
        self.ui_mode = ui_mode

        if dialog:
            flags = (self.windowFlags() & ~QtCore.Qt.Window) | QtCore.Qt.Dialog
            self.setWindowFlags(flags)

        self.process_widget = SubProcessWidget(self.ui_mode, self)
        self.connect(self.process_widget,
            QtCore.SIGNAL("finished()"),
            self.finished)
        self.connect(self.process_widget,
            QtCore.SIGNAL("failed()"),
            self.failed)

        closeButton = StandardButton(BTN_CLOSE)
        okButton = StandardButton(BTN_OK)
        cancelButton = StandardButton(BTN_CANCEL)

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

        self.buttonbox = QtGui.QDialogButtonBox(self)
        self.buttonbox.addButton(okButton,
            QtGui.QDialogButtonBox.AcceptRole)
        self.buttonbox.addButton(closeButton,
            QtGui.QDialogButtonBox.AcceptRole)
        self.buttonbox.addButton(cancelButton,
            QtGui.QDialogButtonBox.RejectRole)
        self.connect(self.buttonbox, QtCore.SIGNAL("accepted()"), self.accept)
        self.connect(self.buttonbox, QtCore.SIGNAL("rejected()"), self.reject)
        closeButton.setHidden(True) # but 'close' starts as hidden.

    def make_default_layout_widgets(self):
        status_group_box = QtGui.QGroupBox(gettext("Status"), self)
        status_layout = QtGui.QVBoxLayout(status_group_box)
        status_layout.addWidget(self.process_widget)
        yield status_group_box
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
        if self.args is not None:
            return True
        QtGui.QMessageBox.critical(self, gettext('Internal Error'),
            gettext(
                'Sorry, subprocess action (%s) cannot be started\n'
                'because self.args is None.\n'
                'Please, report bug at:\n'
                'https://bugs.launchpad.net/qbzr/+filebug'),
            gettext('&Close'))
        return False

    def accept(self):
        if self.process_widget.finished:
            self.close()
        else:
            if not (self.validate() and self._check_args()):
                return
            self.emit(QtCore.SIGNAL("subprocessStarted(bool)"), True)
            self.start()
    
    def start(self):
        self.process_widget.start(self.dir, *self.args)
    
    def reject(self):
        if self.process_widget.is_running():
            self.process_widget.abort()
        else:
            self.close()

    def finished(self):
        if hasattr(self, 'setResult'):
            self.setResult(QtGui.QDialog.Accepted)
        
        self.emit(QtCore.SIGNAL("subprocessFinished(bool)"), True)

        if not self.ui_mode:
            self.close()

    def failed(self):
        self.emit(QtCore.SIGNAL("subprocessStarted(bool)"), False)
    
    def closeEvent(self, event):
        if not self.process_widget.is_running():
            QBzrWindow.closeEvent(self, event)
        else:
            self.process_widget.abort()
            event.ignore()


class SubProcessWindow(QBzrWindow, SubProcessWindowBase):

    def __init__(self, title,
                 name="genericsubprocess",
                 args=None,
                 dir=None,
                 default_size=None,
                 ui_mode=True,
                 dialog=True,
                 parent=None):
        QBzrWindow.__init__(self, title, parent)
        self.__init_internal__(title,
                               name=name,
                               args=args,
                               dir=dir,
                               default_size=default_size,
                               ui_mode=ui_mode,
                               dialog=dialog,
                               parent=parent)


class SubProcessDialog(QBzrDialog, SubProcessWindowBase):
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
                 parent=None):
        QBzrDialog.__init__(self, title, parent)
        self.__init_internal__(title,
                               name=name,
                               args=args,
                               dir=dir,
                               default_size=default_size,
                               ui_mode=ui_mode,
                               dialog=dialog,
                               parent=parent)


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
                 parent=None):
        super(SimpleSubProcessDialog, self).__init__(
                               title,
                               name=name,
                               args=args,
                               dir=dir,
                               default_size=default_size,
                               ui_mode=ui_mode,
                               dialog=dialog,
                               parent=parent)           
        self.desc = desc
        # create a layout to hold our one label and the subprocess widgets.
        layout = QtGui.QVBoxLayout(self)
        label = QtGui.QLabel(self.desc, self)
        label.font().setBold(True)
        layout.addWidget(label)
        # and add the subprocess widgets.
        for w in self.make_default_layout_widgets():
            layout.addWidget(w)

class SubProcessWidget(QtGui.QWidget):

    def __init__(self, ui_mode, parent = None):
        QtGui.QGroupBox.__init__(self, parent)
        self.ui_mode = ui_mode

        layout = QtGui.QVBoxLayout(self)

        self.progressMessage = QtGui.QLabel(self)
        #self.progressMessage.setWordWrap(True) -- this breaks minimal window size hint
        self.progressMessage.setText(gettext("Stopped"))
        layout.addWidget(self.progressMessage)

        self.progressBar = QtGui.QProgressBar(self)
        self.progressBar.setMaximum(1000000)
        layout.addWidget(self.progressBar)

        self.console = QtGui.QTextBrowser(self)
        layout.addWidget(self.console)

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
    
    def hide_progress(self):
        self.progressMessage.setHidden(True)
        self.progressBar.setHidden(True)
    
    def is_running(self):
        return self.process.state() == QtCore.QProcess.Running or\
               self.process.state() == QtCore.QProcess.Starting
    
    def start(self, dir, *args):
        QtGui.QApplication.processEvents() # make sure ui has caught up
        self.start_multi(((dir, args),))
    
    def start_multi(self, commands):
        self.setProgress(0, [gettext("Starting...")])
        self.console.setFocus(QtCore.Qt.OtherFocusReason)
        self.commands = list(commands)
        self._start_next()
    
    def _start_next(self):
        dir, args = self.commands.pop(0)
        args = ' '.join('"%s"' % a.replace('"', '\\"') for a in args)
        if dir is None:
            dir = self.defaultWorkingDir
        
        self.process.setWorkingDirectory (dir)
        if getattr(sys, "frozen", None) is not None:
            self.process.start(
                sys.argv[0], ['qsubprocess', args])
        else:
            self.process.start(
                sys.executable, [sys.argv[0], 'qsubprocess', args])
    
    def abort(self):
        if self.is_running():
            if not self.aborting:
                # be nice and try to use ^C
                self.process.close()
                self.aborting = True
                self.setProgress(None, [gettext("Aborting...")])
            else:
                self.process.terminate()
    
    def setProgress(self, progress, messages):
        if progress is not None:
            self.progressBar.setValue(progress)
        if progress == 1000000 and not messages:
            text = gettext("Finished!")
        else:
            text = " / ".join(messages)
        self.progressMessage.setText(text)
    
    def readStdout(self):
        data = str(self.process.readAllStandardOutput())
        for line in data.splitlines():
            if line.startswith("qbzr:PROGRESS:"):
                progress, messages = bencode.bdecode(line[14:])
                self.setProgress(progress, messages)
            else:
                self.logMessage(line)
                if not self.ui_mode:
                    sys.stdout.write(line)
                    sys.stdout.write("\n")

    def readStderr(self):
        data = str(self.process.readAllStandardError())
        for line in data.splitlines():
            error = line.startswith("bzr: ERROR:")
            self.logMessage(line, error)
            if not self.ui_mode:
                sys.stderr.write(line)
                sys.stderr.write("\n")

    def logMessage(self, message, error=False):
        if error:
            format = self.errorFormat
        else:
            format = self.messageFormat
        self.console.setCurrentCharFormat(format);
        self.console.append(message);
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
        #self.emit(QtCore.SIGNAL("failed()"))

    def onFinished(self, exitCode, exitStatus):
        self.aborting = False
        if exitCode == 0:
            if self.commands:
                self._start_next()
            else:
                self.finished = True
                self.emit(QtCore.SIGNAL("finished()"))
        else:
            self.setProgress(1000000, [gettext("Failed!")])
            self.emit(QtCore.SIGNAL("failed()"))


class SubprocessChildProgress(progress._BaseProgressBar):

    def __init__(self, _stack, **kwargs):
        super(SubprocessChildProgress, self).__init__(_stack=_stack, **kwargs)
        self.parent = _stack.top()
        self.message = None
        self.current = 0
        self.total = 0

    def tick(self, messages, progress):
        self.parent.child_update(messages, progress)

    def child_update(self, messages, progress):
        if self.current is not None and self.total:
            progress = (self.current + progress) / self.total
        else:
            progress = 0.0
        if self.message:
            messages = [self.message] + messages
        self.tick(messages, progress)

    def update(self, message, current=None, total=None):
        if current is not None:
            if total is not None:
                self.message = '%s (%s/%s)' % (message, current, total)
            else:
                self.message = '%s (%s)' % (message, current)
        else:
            self.message = message
        self.current = current
        self.total = total
        self.child_update([], 0.0)

    def clear(self):
        pass

    def note(self, *args, **kwargs):
        self.parent.note(*args, **kwargs)

    def child_progress(self, **kwargs):
        return SubprocessChildProgress(**kwargs)


class SubprocessProgress(SubprocessChildProgress):

    def __init__(self, **kwargs):
        super(SubprocessProgress, self).__init__(**kwargs)

    def _report(self, progress, messages=()):
        data = int(progress * 1000000), messages
        sys.stdout.write('qbzr:PROGRESS:' + bencode.bencode(data) + '\n')
        sys.stdout.flush()

    def tick(self, messages, progress):
        self._report(progress, messages)

    def finished(self):
        self._report(1.0)
