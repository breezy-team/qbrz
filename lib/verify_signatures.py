# -*- coding: utf-8 -*-
#
# QBzr - Qt frontend to Bazaar commands
# Copyright (C) 2011 Canonical Ltd
# Author Jonathan Riddell <jriddell@ubuntu.com>
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

from bzrlib import bzrdir, osutils

from bzrlib.info import show_bzrdir_info

from bzrlib.plugins.qbzr.lib.i18n import gettext
from bzrlib.plugins.qbzr.lib.ui_verify_signatures import Ui_VerifyForm
from bzrlib.plugins.qbzr.lib.util import (
    BTN_CLOSE,
    QBzrWindow, QBzrDialog,
    url_for_display,
    ThrobberWidget,
    )
from bzrlib import (
    bzrdir as _mod_bzrdir,
    errors,
    gpg,
    revision as _mod_revision,
    )

from PyQt4.QtCore import *
from PyQt4.QtGui import *

from StringIO import StringIO


class QBzrVerifySignaturesWindow(QBzrDialog):
    """Show the user information on the status of digital signatures for the
    commits on this branch"""

    def __init__(self, acceptable_keys, revision, location, parent=None):
        """load UI file, add buttons and throbber, run refresh"""
        QBzrDialog.__init__(self, [gettext("Verify Signatures")], parent)
        self.restoreSize("verify-signatures", (580, 250))
        self.buttonbox = self.create_button_box(BTN_CLOSE)
        self.ui = Ui_VerifyForm()
        self.ui.setupUi(self)
        self.ui.verticalLayout.addWidget(self.buttonbox)
        self.throbber = ThrobberWidget(self)
        self.ui.verticalLayout.insertWidget(0, self.throbber)
        
        self.acceptable_keys = acceptable_keys
        self.revision = revision
        self.location = location
        QTimer.singleShot(0, self.refresh_view)

    def refresh_view(self):
        """get the revisions wanted by the user, do the verifications and
        popular the tree widget with the results"""
        self.throbber.show()
        bzrdir = _mod_bzrdir.BzrDir.open_containing(self.location)[0]
        branch = bzrdir.open_branch()
        repo = branch.repository
        branch_config = branch.get_config()
        gpg_strategy = gpg.GPGStrategy(branch_config)
        gpg_strategy.set_acceptable_keys(self.acceptable_keys)

        if branch.name is None:
            header = branch.user_url
        else:
            header = branch.name
        self.ui.treeWidget.setHeaderLabels([str(header)])

        #get our list of revisions
        revisions = []
        if self.revision is not None:
            if len(self.revision) == 1:
                revno, rev_id = self.revision[0].in_history(branch)
                revisions.append(rev_id)
            elif len(sel.revision) == 2:
                from_revno, from_revid = self.revision[0].in_history(branch)
                to_revno, to_revid = self.revision[1].in_history(branch)
                if to_revid is None:
                    to_revno = branch.revno()
                if from_revno is None or to_revno is None:
                    raise errors.BzrCommandError('Cannot verify a range of '\
                                               'non-revision-history revisions')
                for revno in range(from_revno, to_revno + 1):
                    revisions.append(branch.get_rev_id(revno))
        else:
            #all revisions by default including merges
            graph = repo.get_graph()
            revisions = []
            repo.lock_read()
            for rev_id, parents in graph.iter_ancestry(
                    [branch.last_revision()]):
                if _mod_revision.is_null(rev_id):
                    continue
                if parents is None:
                    # Ignore ghosts
                    continue
                revisions.append(rev_id)
            repo.unlock()
        count, result, all_verifiable =\
                                gpg_strategy.do_verifications(revisions, repo,
                                                     QApplication.processEvents)
        if all_verifiable:
            message = QTreeWidgetItem( [gettext(
                            "All commits signed with verifiable keys")] )
            self.ui.treeWidget.addTopLevelItem(message)
            for verbose_message in gpg_strategy.verbose_valid_message(result):
                QTreeWidgetItem(message, [verbose_message])
        else:
            valid_commit_message = QTreeWidgetItem(
                            [gpg_strategy.valid_commits_message(count)] )
            self.ui.treeWidget.addTopLevelItem(valid_commit_message)
            for verbose_message in gpg_strategy.verbose_valid_message(result):
                QTreeWidgetItem(valid_commit_message, [verbose_message])

            expired_key_message = QTreeWidgetItem(
                            [gpg_strategy.expired_commit_message(count)] )
            self.ui.treeWidget.addTopLevelItem(expired_key_message)
            for verbose_message in \
                              gpg_strategy.verbose_expired_key_message(result,
                                                                         repo):
                QTreeWidgetItem(expired_key_message, [verbose_message])

            unknown_key_message = QTreeWidgetItem(
                            [gpg_strategy.unknown_key_message(count)] )
            self.ui.treeWidget.addTopLevelItem(unknown_key_message)
            for verbose_message in gpg_strategy.verbose_missing_key_message(
                                                                        result):
                QTreeWidgetItem(unknown_key_message, [verbose_message])

            commit_not_valid_message = QTreeWidgetItem(
                            [gpg_strategy.commit_not_valid_message(count)] )
            self.ui.treeWidget.addTopLevelItem(commit_not_valid_message)
            for verbose_message in gpg_strategy.verbose_not_valid_message(
                                                                result, repo):
                QTreeWidgetItem(commit_not_valid_message, [verbose_message])

            commit_not_signed_message = QTreeWidgetItem(
                            [gpg_strategy.commit_not_signed_message(count)] )
            self.ui.treeWidget.addTopLevelItem(commit_not_signed_message)
            for verbose_message in gpg_strategy.verbose_not_signed_message(
                                                                result, repo):
                QTreeWidgetItem(commit_not_signed_message, [verbose_message])
        self.throbber.hide()
