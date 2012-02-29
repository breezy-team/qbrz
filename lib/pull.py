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

import os

from PyQt4 import QtCore, QtGui

from bzrlib import (
    errors,
    osutils,
    urlutils,
    )
from bzrlib.commands import get_cmd_object

from bzrlib.plugins.qbzr.lib.i18n import gettext
from bzrlib.plugins.qbzr.lib.subprocess import SubProcessDialog
from bzrlib.plugins.qbzr.lib.ui_pull import Ui_PullForm
from bzrlib.plugins.qbzr.lib.ui_push import Ui_PushForm
from bzrlib.plugins.qbzr.lib.ui_merge import Ui_MergeForm
from bzrlib.plugins.qbzr.lib.util import (
    iter_branch_related_locations,
    save_pull_location,
    fill_pull_combo,
    fill_combo_with,
    hookup_directory_picker,
    DIRECTORYPICKER_SOURCE,
    DIRECTORYPICKER_TARGET,
    url_for_display,
    )


class QBzrPullWindow(SubProcessDialog):

    NAME = "pull"

    def __init__(self, branch, tree=None, location=None, revision=None, remember=None,
                 overwrite=None, ui_mode=True, parent=None):
        self.branch = branch
        self.tree = tree
        super(QBzrPullWindow, self).__init__(name = self.NAME,
                                             ui_mode = ui_mode,
                                             parent = parent)
        self.ui = Ui_PullForm()
        self.setupUi(self.ui)
        # add the subprocess widgets.
        for w in self.make_default_layout_widgets():
            self.layout().addWidget(w)

        self.default_location = fill_pull_combo(self.ui.location, self.branch)
        if location:
            self.ui.location.setEditText(location)
        else:
            self.ui.location.setFocus()

        if remember:
            self.ui.remember.setCheckState(QtCore.Qt.Checked)
        if overwrite:
            self.ui.overwrite.setCheckState(QtCore.Qt.Checked)
        if revision:
            self.ui.revision.setText(revision)

        # One directory picker for the pull location.
        hookup_directory_picker(self,
                                self.ui.location_picker,
                                self.ui.location,
                                DIRECTORYPICKER_SOURCE)

    def do_start(self):
        if self.tree:
            dest = self.tree.basedir
        else:
            dest = self.branch.base
        args = []
        if dest != osutils.getcwd():
            args.extend(('--directory', dest))
        if self.ui.overwrite.isChecked():
            args.append('--overwrite')
        if self.ui.remember.isChecked():
            args.append('--remember')
        revision = str(self.ui.revision.text())
        if revision:
            args.append('--revision')
            args.append(revision)
        location = unicode(self.ui.location.currentText())
        if location and location != self.default_location:
            args.insert(0, location)
        self.process_widget.do_start(None, 'pull', *args)
        save_pull_location(self.branch, location)


class QBzrPushWindow(SubProcessDialog):

    NAME = "push"

    def __init__(self, branch, tree=None, location=None,
                 create_prefix=None, use_existing_dir=None,
                 remember=None, overwrite=None, ui_mode=True, parent=None):

        self.branch = branch
        self.tree = tree
        self._no_strict = None
        super(QBzrPushWindow, self).__init__(name = self.NAME,
                                             ui_mode = ui_mode,
                                             parent = parent)

        self.ui = Ui_PushForm()
        self.setupUi(self.ui)
        # and add the subprocess widgets.
        for w in self.make_default_layout_widgets():
            self.layout().addWidget(w)

        self.default_location = self.branch.get_push_location()
        df = url_for_display(self.default_location or 
            self._suggested_push_location())
        fill_combo_with(self.ui.location, df,
                        iter_branch_related_locations(self.branch))
        if location:
            self.ui.location.setEditText(location)
        else:
            self.ui.location.setFocus()

        if remember:
            self.ui.remember.setCheckState(QtCore.Qt.Checked)
        if overwrite:
            self.ui.overwrite.setCheckState(QtCore.Qt.Checked)
        if create_prefix:
            self.ui.create_prefix.setCheckState(QtCore.Qt.Checked)
        if use_existing_dir:
            self.ui.use_existing_dir.setCheckState(QtCore.Qt.Checked)

        # One directory picker for the push location.
        hookup_directory_picker(self,
                                self.ui.location_picker,
                                self.ui.location,
                                DIRECTORYPICKER_TARGET)

    def _suggested_push_location(self):
        """Suggest a push location when one is not already defined.

        @return: a sensible location as a string or '' if none.
        """
        # If this is a feature branch and its parent exists locally,
        # its grandparent is likely to be the hosted master branch.
        # If so, suggest a push location, otherwise don't.
        parent_url = self.branch.get_parent()
        if parent_url and parent_url.startswith("file://"):
            from bzrlib.branch import Branch
            try:
                parent_branch = Branch.open(parent_url)
            except errors.NotBranchError:
                return ''
            master_url = (parent_branch.get_parent() or
                parent_branch.get_bound_location())
            if master_url and not master_url.startswith("file://"):
                if master_url.find("launchpad") >= 0:
                    suggest_url = self._build_lp_push_suggestion(master_url)
                    if suggest_url:
                        return suggest_url
                # XXX we can hook in there even more specific suggesters
                # XXX maybe we need registry?
                suggest_url = self._build_generic_push_suggestion(master_url)
                if suggest_url:
                    return suggest_url
        return ''

    def _build_lp_push_suggestion(self, master_url):
        try:
            from bzrlib.plugins.launchpad import account
        except ImportError:
            # yes, ImportError is possible with bzr.exe,
            # because user has option to not install launchpad plugin at all
            return ''
        from bzrlib.plugins.qbzr.lib.util import launchpad_project_from_url
        user_name = account.get_lp_login()
        project_name = launchpad_project_from_url(master_url)
        branch_name = urlutils.basename(self.branch.base)
        if user_name and project_name and branch_name:
            return "lp:~%s/%s/%s" % (user_name, project_name, branch_name)
        else:
            return ''

    def _build_generic_push_suggestion(self, master_url):
        master_parent = urlutils.dirname(master_url)
        branch_name = urlutils.basename(self.branch.base)
        return urlutils.join(master_parent, branch_name)

    def do_start(self):
        if self.tree:
            dest = self.tree.basedir
        else:
            dest = self.branch.base
        args = []
        if dest != osutils.getcwd():
            args.extend(('--directory', dest))
        if self.ui.overwrite.isChecked():
            args.append('--overwrite')
        if self.ui.remember.isChecked():
            args.append('--remember')
        if self.ui.create_prefix.isChecked():
            args.append('--create-prefix')
        if self.ui.use_existing_dir.isChecked():
            args.append('--use-existing-dir')
        if 'strict' in get_cmd_object('push').options() and self._no_strict:
            # force --no-strict because we checking blocking conditions
            # in validate method (see below).
            args.append('--no-strict')
        location = unicode(self.ui.location.currentText())
        if location and location != self.default_location:
            args.insert(0, location)
        self.process_widget.do_start(None, 'push', *args)

    def validate(self):
        """Check working tree for blocking conditions (such as uncommitted
        changes or out of date) and return True if we can push anyway
        or False if push operation should be aborted.
        """
        if self._no_strict:
            return True
        # check blocking conditions in the tree
        if self.tree is None:
            return True     # no tree - no check
        cfg = self.branch.get_config()
        strict = cfg.get_user_option('push_strict')
        if strict is not None:
            bools = dict(yes=True, no=False, on=True, off=False,
                         true=True, false=False)
            strict = bools.get(strict.lower(), None)
        if strict == False:
            return True     # don't check blocking conditions
        # the code below based on check in from bzrlib/builtins.py: cmd_push
        tree = self.tree
        blocker = None
        if (tree.has_changes(tree.basis_tree())
            or len(tree.get_parent_ids()) > 1):
                blocker = gettext('Working tree has uncommitted changes.')
        if tree.last_revision() != tree.branch.last_revision():
            # The tree has lost sync with its branch, there is little
            # chance that the user is aware of it but he can still force
            # the push with --no-strict
            blocker = gettext("Working tree is out of date, "
                "please run 'bzr update'.")
        #
        if blocker is None:
            return True
        if self.ask_confirmation(blocker + "\n\n" +
            gettext("Do you want to continue anyway?"),
            type='warning'):
                self._no_strict = True
                return True
        return False


class QBzrMergeWindow(SubProcessDialog):

    NAME = "merge"

    def __init__(self, branch, tree=None, location=None, revision=None, remember=None,
                 force=None, uncommitted=None, ui_mode=True, parent=None):
        super(QBzrMergeWindow, self).__init__(name = self.NAME,
                                             ui_mode = ui_mode,
                                             parent = parent)
        self.branch = branch
        self.tree = tree
        self.ui = Ui_MergeForm()
        self.setupUi(self.ui)
        # and add the subprocess widgets.
        for w in self.make_default_layout_widgets():
            self.layout().addWidget(w)

        fill_pull_combo(self.ui.location, self.branch)
        if location:
            self.ui.location.setEditText(location)
        else:
            self.ui.location.setFocus()

        if remember:
            self.ui.remember.setCheckState(QtCore.Qt.Checked)
        if force:
            self.ui.force.setCheckState(QtCore.Qt.Checked)
        if uncommitted:
            self.ui.uncommitted.setCheckState(QtCore.Qt.Checked)
        if revision:
            self.ui.revision.setText(revision)
    
        # One directory picker for the pull location.
        hookup_directory_picker(self,
                                self.ui.location_picker,
                                self.ui.location,
                                DIRECTORYPICKER_SOURCE)

    def do_start(self):
        if self.tree:
            dest = self.tree.basedir
        else:
            dest = self.branch.base
        if dest == os.getcwdu():
            args = []
        else:
            args = ['--directory', dest]
        if self.ui.remember.isChecked():
            args.append('--remember')
        if self.ui.force.isChecked():
            args.append('--force')
        if self.ui.uncommitted.isChecked():
            args.append('--uncommitted')
        rev = unicode(self.ui.revision.text()).strip()
        if rev:
            args.extend(['--revision', rev])
        location = unicode(self.ui.location.currentText())
        self.process_widget.do_start(None, 'merge', location, *args)
        save_pull_location(None, location)
