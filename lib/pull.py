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
    urlutils,
    )
from bzrlib.errors import BzrError, NoSuchRevision
from bzrlib.option import Option
from bzrlib.commands import Command, register_command
from bzrlib.commit import ReportCommitToLog
from bzrlib.workingtree import WorkingTree

from bzrlib.plugins.qbzr.lib.diff import DiffWindow
from bzrlib.plugins.qbzr.lib.i18n import gettext, N_
from bzrlib.plugins.qbzr.lib.ui_branch import Ui_BranchForm
from bzrlib.plugins.qbzr.lib.ui_pull import Ui_PullForm
from bzrlib.plugins.qbzr.lib.ui_push import Ui_PushForm
from bzrlib.plugins.qbzr.lib.ui_merge import Ui_MergeForm
from bzrlib.plugins.qbzr.lib.util import (
    BTN_CANCEL,
    BTN_OK,
    QBzrWindow,
    StandardButton,
    )


class QBzrPullWindow(QBzrWindow):

    TITLE = N_("Pull")
    NAME = "pull"
    PICKER_CAPTION = N_("Select Source Location")
    DEFAULT_SIZE = (400, 420)

    def __init__(self, branch, parent=None):
        QBzrWindow.__init__(self, [gettext(self.TITLE)], parent)
        self.restoreSize(self.NAME, self.DEFAULT_SIZE)
        self.branch = branch

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

        self.finished = False
        self.aborting = False

        self.messageFormat = QtGui.QTextCharFormat()
        self.errorFormat = QtGui.QTextCharFormat()
        self.errorFormat.setForeground(QtGui.QColor('red'))

        self.okButton = StandardButton(BTN_OK)
        self.cancelButton = StandardButton(BTN_CANCEL)

        self.buttonbox = QtGui.QDialogButtonBox(self.centralwidget)
        self.buttonbox.addButton(self.okButton,
            QtGui.QDialogButtonBox.AcceptRole)
        self.buttonbox.addButton(self.cancelButton,
            QtGui.QDialogButtonBox.RejectRole)
        self.connect(self.buttonbox, QtCore.SIGNAL("accepted()"), self.accept)
        self.connect(self.buttonbox, QtCore.SIGNAL("rejected()"), self.reject)

        self.setupUi()

    def get_stored_location(self, branch):
        return branch.get_parent()

    def add_related_locations(self, locations, branch):
        def add_location(location):
            if location and location not in locations:
                locations.append(location)
        add_location(branch.get_parent())
        add_location(branch.get_bound_location())
        add_location(branch.get_push_location())

    def get_related_locations(self, branch):
        # Add the stored location, if it's not set make it empty
        locations = [self.get_stored_location(branch) or u'']
        # Add other related locations to the combo box
        self.add_related_locations(locations, branch)
        return locations

    def setupUi(self):
        self.ui = self.create_ui()
        self.ui.setupUi(self.centralwidget)
        self.ui.vboxlayout.addWidget(self.buttonbox)
        locations = self.get_related_locations(self.branch)
        for location in locations:
            if location:
                location = urlutils.unescape_for_display(location, 'utf-8')
                self.ui.location.addItem(location)
        self.ui.location.setEditText(locations[0])
        # One directory picker for the pull location.
        self.connect(self.ui.location_picker, QtCore.SIGNAL("clicked()"),
                     self.location_picker_clicked)

    def location_picker_clicked(self):
        self._do_directory_picker(self.ui.location, gettext(self.PICKER_CAPTION))

    def _do_directory_picker(self, widget, caption):
        """Called by the clicked() signal for the various directory pickers"""
        dir = widget.currentText()
        if not os.path.isdir(dir):
            dir = ""
        dir = QtGui.QFileDialog.getExistingDirectory(self, caption, dir)
        if dir:
            widget.setEditText(dir)

    def create_ui(self):
        return Ui_PullForm()

    def start(self, *args):
        self.setProgress(0, [gettext("Starting...")])
        self.ui.console.setFocus(QtCore.Qt.OtherFocusReason)
        self.okButton.setEnabled(False)
        args = ' '.join('"%s"' % a.replace('"', '\"') for a in args)
        if getattr(sys, "frozen", None) is not None:
            self.process.start(
                sys.argv[0], ['qsubprocess', args])
        else:
            self.process.start(
                sys.executable, [sys.argv[0], 'qsubprocess', args])

    def show(self):
        QBzrWindow.show(self)

    def accept(self):
        if self.finished:
            self.close()
        else:
            args = ['--directory', self.branch.base]
            if self.ui.overwrite.isChecked():
                args.append('--overwrite')
            if self.ui.remember.isChecked():
                args.append('--remember')
            revision = str(self.ui.revision.text())
            if revision:
                args.append('--revision')
                args.append(revision)
            location = str(self.ui.location.currentText())
            self.start('pull', location, *args)

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
        if not self.aborting:
            # be nice and try to use ^C
            self.aborting = True
            self.setProgress(None, [gettext("Aborting...")])
        else:
            self.process.terminate()

    def setProgress(self, progress, messages):
        if progress is not None:
            self.ui.progressBar.setValue(progress)
        if progress == 1000000 and not messages:
            text = gettext("Finished!")
        else:
            text = " / ".join(messages)
        self.ui.progressMessage.setText(text)

    def readStdout(self):
        data = str(self.process.readAllStandardOutput())
        for line in data.splitlines():
            if line.startswith("qbzr:PROGRESS:"):
                progress, messages = bencode.bdecode(line[14:])
                self.setProgress(progress, messages)
            else:
                self.logMessage(line)
        if self.aborting:
            self.process.close()

    def readStderr(self):
        data = str(self.process.readAllStandardError())
        for line in data.splitlines():
            error = line.startswith("bzr: ERROR:")
            self.logMessage(line, error)
        if self.aborting:
            self.process.close()

    def logMessage(self, message, error=False):
        if error:
            format = self.errorFormat
        else:
            format = self.messageFormat
        cursor = self.ui.console.textCursor()
        cursor.insertText(message + "\n", format)
        scrollbar = self.ui.console.verticalScrollBar()
        scrollbar.setValue(scrollbar.maximum())

    def reportProcessError(self, error):
        if self.aborting == True:
            self.close()
            return
        self.aborting = False
        self.setProgress(1000000, [gettext("Failed!")])
        if error == QtCore.QProcess.FailedToStart:
            message = gettext("Failed to start bzr.")
        else:
            message = gettext("Error while running bzr. (error code: %d)" % error)
        self.logMessage(message, True)

    def onFinished(self, exitCode, exitStatus):
        if self.aborting == True:
            self.close()
            return
        self.aborting = False
        if exitCode == 0:
            self.finished = True
            self.cancelButton.setEnabled(False)
        else:
            self.setProgress(1000000, [gettext("Failed!")])
        self.okButton.setEnabled(True)


class QBzrPushWindow(QBzrPullWindow):

    TITLE = N_("Push")
    NAME = "push"
    PICKER_CAPTION = N_("Select Target Location")
    DEFAULT_SIZE = (400, 420)

    def get_stored_location(self, branch):
        return branch.get_push_location()

    def create_ui(self):
        return Ui_PushForm()

    def accept(self):
        if self.finished:
            self.close()
        else:
            args = ['--directory', self.branch.base]
            if self.ui.overwrite.isChecked():
                args.append('--overwrite')
            if self.ui.remember.isChecked():
                args.append('--remember')
            if self.ui.create_prefix.isChecked():
                args.append('--create-prefix')
            if self.ui.use_existing_dir.isChecked():
                args.append('--use-existing-dir')
            location = str(self.ui.location.currentText())
            self.start('push', location, *args)


class QBzrBranchWindow(QBzrPullWindow):

    TITLE = N_("Branch")
    NAME = "branch"
    DEFAULT_SIZE = (400, 420)

    def setupUi(self):
        self.ui = Ui_BranchForm()
        self.ui.setupUi(self.centralwidget)
        self.ui.vboxlayout.addWidget(self.buttonbox)
        #print urlutils.local_path_to_url('.')
        #location = self.get_stored_location(branch)
        #if location is not None:
        #    location = urlutils.unescape(location)
        #    self.ui.location.setEditText(location)
        #    self.ui.location.lineEdit().setCursorPosition(0)

        # Our 2 directory pickers hook up to our combos.
        self.connect(self.ui.from_picker, QtCore.SIGNAL("clicked()"),
                     self.from_picker_clicked)
        self.connect(self.ui.to_picker, QtCore.SIGNAL("clicked()"),
                     self.to_picker_clicked)

    def to_picker_clicked(self):
        self._do_directory_picker(self.ui.to_location,
                                  gettext("Select Target Location"))

    def from_picker_clicked(self):
        self._do_directory_picker(self.ui.from_location,
                                  gettext("Select Source Location"))

    def accept(self):
        if self.finished:
            self.close()
        else:
            args = []
            revision = str(self.ui.revision.text())
            if revision:
                args.append('--revision')
                args.append(revision)
            from_location = str(self.ui.from_location.currentText())
            to_location = str(self.ui.to_location.currentText())
            self.start('branch', from_location, to_location, *args)


class QBzrMergeWindow(QBzrPullWindow):

    TITLE = N_("Merge")
    NAME = "pull"
    PICKER_CAPTION = N_("Select Source Location")
    DEFAULT_SIZE = (400, 420)

    def create_ui(self):
        return Ui_MergeForm()

    def accept(self):
        if self.finished:
            self.close()
        else:
            args = ['--directory', self.branch.base]
            if self.ui.remember.isChecked():
                args.append('--remember')
            location = str(self.ui.location.currentText())
            self.start('merge', location, *args)
