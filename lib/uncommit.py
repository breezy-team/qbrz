# -*- coding: utf-8 -*-
#
# QBzr - Qt frontend to Bazaar commands
# Copyright (C) 2009 Canonical Ltd
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
from PyQt4 import QtCore, QtGui

from bzrlib import log, urlutils
from bzrlib.revisionspec import RevisionInfo, RevisionSpec

from bzrlib.plugins.qbzr.lib.html_log import log_as_html
from bzrlib.plugins.qbzr.lib.i18n import gettext
from bzrlib.plugins.qbzr.lib.subprocess import SubProcessDialog


class QBzrUncommitWindow(SubProcessDialog):

    def __init__(self, branch, dialog=True, ui_mode=True, parent=None,
            local=None, message=None):
        self.branch = branch
        super(QBzrUncommitWindow, self).__init__(
                                  gettext("Uncommit"),
                                  name="uncommit",
                                  default_size=(400, 400),
                                  ui_mode=ui_mode,
                                  dialog=dialog,
                                  parent=parent,
                                  hide_progress=True,
                                  )
    
        # Display the revision selection section. We nearly always
        # want to just uncommit the last revision (to tweak the
        # commit message say) so we make that the default.
        groupbox = QtGui.QGroupBox(gettext("Move tip to"), self)
        self.last_radio = QtGui.QRadioButton(
            gettext("Parent of current tip revision"))
        self.last_radio.setChecked(QtCore.Qt.Checked)
        self.other_radio = QtGui.QRadioButton(gettext("Other revision:"))
        self.other_revision = QtGui.QLineEdit()
        other = QtGui.QHBoxLayout()
        other.addWidget(self.other_radio)
        other.addWidget(self.other_revision)
        vbox = QtGui.QVBoxLayout(groupbox)
        vbox.addWidget(self.last_radio)
        vbox.addLayout(other)
        
        # groupbox gets disabled as we are executing.
        QtCore.QObject.connect(self,
                               QtCore.SIGNAL("subprocessStarted(bool)"),
                               groupbox,
                               QtCore.SLOT("setDisabled(bool)"))

        self.splitter = QtGui.QSplitter(QtCore.Qt.Vertical)
        self.splitter.addWidget(groupbox)
        self.splitter.addWidget(self.make_default_status_box())
        self.splitter.setStretchFactor(0, 10)
        self.restoreSplitterSizes([150, 150])

        layout = QtGui.QVBoxLayout(self)
        layout.addWidget(self.splitter)
        layout.addWidget(self.buttonbox)

    def _revision_identifier(self):
        """What revision did the user select?

        :return: None for the last revision.
          Otherwise the revision identifier as a string.
        """
        if self.other_radio.isChecked():
            # should we check something was actually entered here?
            return str(self.other_revision.text())
        # Default is the tip revision
        return None

    def get_revno(self, revision):
        """Get the revno for a revision string or None if illegal."""
        # XXX: Is there a standard way of doing this in QBzr?
        try:
            rev_spec = RevisionSpec.from_string(revision)
        except errors.NoSuchRevisionSpec:
            # TODO: popup an error dialog explaining the spec is bad
            return None
        return rev_spec.in_history(self.branch).revno

    def validate(self):
        """Check that the user really wants to uncommit the given revisions."""
        revision = self._revision_identifier()
        if revision is None:
            log_rqst = log.make_log_request_dict(limit=1)
        else:
            revno = self.get_revno(revision)
            if revno is None:
                return False
            # We need to offset the revno by +1 because we'll be uncommitting
            # *back* to revno, meaning those after it are 'deleted'
            log_rqst = log.make_log_request_dict(start_revision=revno+1)
        log_data = log_as_html(self.branch, log_rqst)
        question = gettext("Do you really want to uncommit these revisions?")
        btn = QtGui.QMessageBox.warning(self,
            "QBzr - " + gettext("Uncommit"),
            '<font color="red">%s</font><br/>%s' % (question, log_data),
            gettext("&Yes"), gettext("&No"), '',
            0, 1)
        if btn == 0: # QtGui.QMessageBox.Yes:
            return True
        return False

    def do_start(self):
        args = ['--force']
        revision = self._revision_identifier()
        if revision:
            args.append('--revision')
            args.append(revision)
        dest = self.branch.base
        cwd = urlutils.local_path_to_url(os.getcwd()) + '/'
        if cwd != dest:
            args.append(dest)
        self.process_widget.do_start(None, 'uncommit', *args)

    def saveSize(self):
        SubProcessDialog.saveSize(self)
        self.saveSplitterSizes()
