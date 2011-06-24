# -*- coding: utf-8 -*-
#
# QBzr - Qt frontend to Bazaar commands
# Copyright (C) 2008 Lukáš Lalinský <lalinsky@gmail.com>
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
    )
from bzrlib import (
    bzrdir as _mod_bzrdir,
    errors,
    gpg,
    revision as _mod_revision,
    )

from PyQt4.QtGui import QTreeWidgetItem

from StringIO import StringIO


class QBzrVerifySignaturesWindow(QBzrDialog):

    def __init__(self, location, parent=None):
        QBzrDialog.__init__(self, [gettext("Verify Signatures")], parent)
        self.restoreSize("verify-signatures", (580, 250))
        self.buttonbox = self.create_button_box(BTN_CLOSE)
        self.ui = Ui_VerifyForm()
        self.ui.setupUi(self)
        self.ui.verticalLayout.addWidget(self.buttonbox)
        self.refresh_view(location)

    def refresh_view(self, location):
        directory = u"."
        revision = None
        acceptable_keys = None
        verbose = None
        self.outf = StringIO()

        bzrdir = _mod_bzrdir.BzrDir.open_containing(directory)[0]
        branch = bzrdir.open_branch()
        repo = branch.repository
        branch_config = branch.get_config()
        gpg_strategy = gpg.GPGStrategy(branch_config)

        gpg_strategy.set_acceptable_keys(acceptable_keys)

        #get our list of revisions
        revisions = []
        if revision is not None:
            if len(revision) == 1:
                revno, rev_id = revision[0].in_history(branch)
                revisions.append(rev_id)
            elif len(revision) == 2:
                from_revno, from_revid = revision[0].in_history(branch)
                to_revno, to_revid = revision[1].in_history(branch)
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
                                gpg_strategy.do_verifications(revisions, repo)
        if all_verifiable:
            message = QTreeWidgetItem( [gettext(
                            "All commits signed with verifiable keys\n")] )
            self.ui.treeWidget.addTopLevelItem(message)
            QTreeWidgetItem(message, 
                            [gpg_strategy.verbose_valid_message(result)])
        else:
            valid_commit_message = QTreeWidgetItem(
                            [gpg_strategy.valid_commits_message(count)] )
            self.ui.treeWidget.addTopLevelItem(valid_commit_message)
            QTreeWidgetItem(valid_commit_message, 
                            [gpg_strategy.verbose_valid_message(result)])

            unknown_key_message = QTreeWidgetItem(
                            [gpg_strategy.unknown_key_message(count)] )
            self.ui.treeWidget.addTopLevelItem(unknown_key_message)
            QTreeWidgetItem(unknown_key_message, 
                            [gpg_strategy.verbose_missing_key_message(result)])

            commit_not_valid_message = QTreeWidgetItem(
                            [gpg_strategy.commit_not_valid_message(count)] )
            self.ui.treeWidget.addTopLevelItem(commit_not_valid_message)
            QTreeWidgetItem(commit_not_valid_message, 
                            [gpg_strategy.verbose_not_valid_message(result,
                                                                        repo)])

            commit_not_signed_message = QTreeWidgetItem(
                            [gpg_strategy.commit_not_signed_message(count)] )
            self.ui.treeWidget.addTopLevelItem(commit_not_signed_message)
            QTreeWidgetItem(commit_not_signed_message, 
                            [gpg_strategy.verbose_not_signed_message(result,
                                                                        repo)])
