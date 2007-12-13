# -*- coding: utf-8 -*-
#
# QBzr - Qt frontend to Bazaar commands
# Copyright (C) 2007 Lukáš Lalinský <lalinsky@gmail.com>
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

import os.path
import re
import sys
from PyQt4 import QtCore, QtGui

from bzrlib.util import bencode
from bzrlib import (
    bugtracker,
    errors,
    osutils,
    )
from bzrlib.errors import BzrError, NoSuchRevision
from bzrlib.option import Option
from bzrlib.commands import Command, register_command
from bzrlib.commit import ReportCommitToLog
from bzrlib.workingtree import WorkingTree
from bzrlib.plugins.qbzr.diff import DiffWindow
from bzrlib.plugins.qbzr.i18n import gettext
from bzrlib.plugins.qbzr.util import (
    BTN_CANCEL,
    BTN_OK,
    QBzrWindow,
    StandardButton,
    )


class QBzrPullWindow(QBzrWindow):

    def __init__(self, location, parent=None):
        QBzrWindow.__init__(self, [gettext("Pull")], parent)
        self.restoreSize("progress", (450, 250))
        self.location = location

        self.progressMessage = QtGui.QLabel("Foo")

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
            self.finished)
        self.aborting = False

        self.progressBar = QtGui.QProgressBar()
        self.progressBar.setValue(0)
        self.progressBar.setMinimum(0)
        self.progressBar.setMaximum(1000000)

        self.consoleDocument = QtGui.QTextDocument()
        self.console = QtGui.QTextBrowser()
        self.console.setDocument(self.consoleDocument)

        self.messageFormat = QtGui.QTextCharFormat()
        self.errorFormat = QtGui.QTextCharFormat()
        self.errorFormat.setForeground(QtGui.QColor('red'))

        self.okButton = StandardButton(BTN_OK)
        self.cancelButton = StandardButton(BTN_CANCEL)

        buttonbox = QtGui.QDialogButtonBox(self.centralwidget)
        buttonbox.addButton(self.okButton,
            QtGui.QDialogButtonBox.AcceptRole)
        buttonbox.addButton(self.cancelButton,
            QtGui.QDialogButtonBox.RejectRole)
        self.connect(buttonbox, QtCore.SIGNAL("accepted()"), self.accept)
        self.connect(buttonbox, QtCore.SIGNAL("rejected()"), self.reject)


        vbox = QtGui.QVBoxLayout(self.centralwidget)
        vbox.addWidget(self.progressMessage)
        vbox.addWidget(self.progressBar)
        vbox.addWidget(self.console)
        vbox.addWidget(buttonbox)

    def start(self):
        args = ['pull']
        if self.location:
            args.append(self.location)
        args = ' '.join('"%s"' % a.replace('"', '\"') for a in args)
        if sys.argv[0].endswith('.exe'):
            self.process.start(
                sys.argv[0], ['qsubprocess', args])
        else:
            self.process.start(
                sys.executable, [sys.argv[0], 'qsubprocess', args])

    def show(self):
        QBzrWindow.show(self)
        self.start()
        self.setProgress(0, [gettext("Starting...")])
        self.okButton.setEnabled(False)
        self.cancelButton.setEnabled(True)

    def accept(self):
        if self.process.state() == QtCore.QProcess.NotRunning:
            self.close()

    def reject(self):
        if self.process.state() == QtCore.QProcess.NotRunning:
            self.close()
        else:
            self.abort()

    def closeEvent(self, event):
        if self.process.state() == QtCore.QProcess.NotRunning:
            QBzrWindow.closeEvent(self, event)
        else:
            self.abort()
            event.ignore()

    def abort(self):
        self.aborting = True
        self.setProgress(None, [gettext("Aborting...")])

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
                if self.aborting:
                    self.process.write("ABORT\n")
                else:
                    self.process.write("OK\n")
            else:
                self.logMessage(line)

    def readStderr(self):
        data = str(self.process.readAllStandardError())
        for line in data.splitlines():
            error = line.startswith("bzr: ERROR:")
            self.logMessage(line, error)

    def logMessage(self, message, error=False):
        if error:
            format = self.errorFormat
        else:
            format = self.messageFormat
        cursor = self.console.textCursor()
        cursor.insertText(message + "\n", format)
        scrollbar = self.console.verticalScrollBar()
        scrollbar.setValue(scrollbar.maximum())

    def reportProcessError(self, error):
        self.setProgress(1000000, [gettext("Failed")])
        if error == QtCore.QProcess.FailedToStart:
            message = gettext("Failed to start bzr.")
        else:
            message = gettext("Error while running bzr. (error code: %d)" % error)
        self.logMessage(message, True)

    def finished(self, exitCode, exitStatus):
        if self.aborting == True:
            self.close()
        self.okButton.setEnabled(True)
        self.cancelButton.setEnabled(False)
