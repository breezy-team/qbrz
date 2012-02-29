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

from PyQt4 import QtCore, QtGui

from bzrlib import bzrdir, errors, log
from bzrlib.revisionspec import RevisionSpec

from bzrlib.plugins.qbzr.lib.html_log import log_as_html
from bzrlib.plugins.qbzr.lib.i18n import gettext
from bzrlib.plugins.qbzr.lib.subprocess import SubProcessDialog
from bzrlib.plugins.qbzr.lib.trace import (
   reports_exception,
   SUB_LOAD_METHOD,
   )
from bzrlib.plugins.qbzr.lib.util import url_for_display


class QBzrUncommitWindow(SubProcessDialog):

    def __init__(self, location, dialog=True, ui_mode=True, parent=None,
            local=None, message=None):
        super(QBzrUncommitWindow, self).__init__(
                                  gettext("Uncommit"),
                                  name="uncommit",
                                  default_size=(400, 400),
                                  ui_mode=ui_mode,
                                  dialog=dialog,
                                  parent=parent,
                                  hide_progress=True,
                                  )
        self.tree, self.branch = bzrdir.BzrDir.open_tree_or_branch(location)
 
        # Display the branch
        branch_label = QtGui.QLabel(gettext("Branch: %s") %
            url_for_display(self.branch.base))

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
 
        # If the user starts entering a value in the 'other revision' field,
        # set the matching radio button implicitly
        QtCore.QObject.connect(self.other_revision,
                               QtCore.SIGNAL("textChanged(QString)"),
                               self.do_other_revision_changed)
        
        # groupbox gets disabled as we are executing.
        QtCore.QObject.connect(self,
                               QtCore.SIGNAL("subprocessStarted(bool)"),
                               groupbox,
                               QtCore.SLOT("setDisabled(bool)"))

        # Put the form together
        layout = QtGui.QVBoxLayout(self)
        layout.addWidget(branch_label)
        layout.addWidget(groupbox)
        layout.addWidget(self.make_default_status_box())
        layout.addWidget(self.buttonbox)

    def do_other_revision_changed(self, text):
        if text and not self.other_radio.isChecked():
            self.other_radio.setChecked(True)

    def _revision_identifier(self):
        """What revision did the user select?

        :return: None for the last revision.
          Otherwise the revision identifier as a string.
        """
        if self.other_radio.isChecked():
            result = unicode(self.other_revision.text())
            if result:
                return result
            else:
                msg = gettext("No other revision specified.")
                raise errors.BzrError(msg)
        # Default is the tip revision
        return None

    @reports_exception(type=SUB_LOAD_METHOD)
    def validate(self):
        """Check that the user really wants to uncommit the given revisions."""
        revision = self._revision_identifier()
        if revision is None:
            log_rqst = log.make_log_request_dict(limit=1)
        else:
            rev_spec = RevisionSpec.from_string(revision)
            revno = rev_spec.in_history(self.branch).revno
            # We need to offset the revno by +1 because we'll be uncommitting
            # *back* to revno, meaning those after it are 'deleted'
            log_rqst = log.make_log_request_dict(start_revision=revno+1)
        log_data = log_as_html(self.branch, log_rqst)
        question = gettext("Do you really want to uncommit these revisions?")
        if self.ask_confirmation(
            '<font color="red">%s</font><br/>%s' % (question, log_data),
            type='warning'):
                return True
        return False

    def do_start(self):
        args = ['--force']
        revision = self._revision_identifier()
        if revision:
            args.append('--revision')
            args.append(revision)
        if self.tree:
            dest = self.tree.basedir
        else:
            dest = self.branch.base
        args.append(dest)
        self.process_widget.do_start(None, 'uncommit', *args)
