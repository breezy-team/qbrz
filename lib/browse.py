# -*- coding: utf-8 -*-
#
# QBzr - Qt frontend to Bazaar commands
# Copyright (C) 2006 Lukáš Lalinský <lalinsky@gmail.com>
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

from PyQt5 import QtCore, QtGui, QtWidgets
from breezy.plugins.qbrz.lib.util import (
    BTN_CLOSE,
    BTN_REFRESH,
    StandardButton,
    QBzrWindow,
    ThrobberWidget,
    runs_in_loading_queue,
    url_for_display,
    )
from breezy.plugins.qbrz.lib.uifactory import ui_current_widget
from breezy.plugins.qbrz.lib.trace import reports_exception

from breezy.lazy_import import lazy_import
lazy_import(globals(), '''
from breezy import (
    osutils,
    errors,
    )
from breezy.controldir import ControlDir
from breezy.revisionspec import RevisionSpec

from breezy.plugins.qbrz.lib.i18n import gettext
from breezy.plugins.qbrz.lib.treewidget import TreeWidget, TreeFilterMenu
from breezy.plugins.qbrz.lib.diff import DiffButtons
''')
class BrowseWindow(QBzrWindow):

    def __init__(self, branch=None, location=None, revision=None,
                 revision_id=None, revision_spec=None, parent=None):
        if branch:
            self.branch = branch
            self.location = url_for_display(branch.base)
        else:
            self.branch = None
            if location is None:
                location = osutils.getcwd()
            self.location = location

        self.workingtree = None
        self.revision_id = revision_id
        self.revision_spec = revision_spec
        self.revision = revision

        QBzrWindow.__init__(self, [gettext("Browse"), self.location], parent)
        self.restoreSize("browse", (780, 580))

        vbox = QtWidgets.QVBoxLayout(self.centralwidget)

        self.throbber = ThrobberWidget(self)
        vbox.addWidget(self.throbber)

        hbox = QtWidgets.QHBoxLayout()
        hbox.addWidget(QtWidgets.QLabel(gettext("Location:")))
        self.location_edit = QtWidgets.QLineEdit()
        self.location_edit.setReadOnly(True)
        self.location_edit.setText(self.location)
        hbox.addWidget(self.location_edit, 7)
        hbox.addWidget(QtWidgets.QLabel(gettext("Revision:")))
        self.revision_edit = QtWidgets.QLineEdit()
        self.revision_edit.returnPressed.connect(self.reload_tree)
        hbox.addWidget(self.revision_edit, 1)
        self.show_button = QtWidgets.QPushButton(gettext("Show"))
        self.show_button.clicked.connect(self.reload_tree)
        hbox.addWidget(self.show_button, 0)

        self.filter_menu = TreeFilterMenu(self)
        self.filter_button = QtWidgets.QPushButton(gettext("&Filter"))
        self.filter_button.setMenu(self.filter_menu)
        hbox.addWidget(self.filter_button, 0)
        self.filter_menu.triggered[int, bool].connect(self.filter_triggered)

        vbox.addLayout(hbox)

        self.file_tree = TreeWidget(self)
        self.file_tree.throbber = self.throbber
        vbox.addWidget(self.file_tree)

        self.filter_menu.set_filters(self.file_tree.tree_filter_model.filters)

        buttonbox = self.create_button_box(BTN_CLOSE)

        self.refresh_button = StandardButton(BTN_REFRESH)
        buttonbox.addButton(self.refresh_button, QtWidgets.QDialogButtonBox.ActionRole)
        self.refresh_button.clicked.connect(self.file_tree.refresh)

        self.diffbuttons = DiffButtons(self.centralwidget)
        self.diffbuttons._triggered['QString'].connect(self.file_tree.show_differences)

        hbox = QtWidgets.QHBoxLayout()
        hbox.addWidget(self.diffbuttons)
        hbox.addWidget(buttonbox)
        vbox.addLayout(hbox)

        self.windows = []

        self.file_tree.setFocus()   # set focus so keyboard navigation will work from the beginning

    def show(self):
        # we show the bare form as soon as possible.
        # QBzrWindow.show(self)
        super().show()
        # QtCore.QTimer.singleShot(1, self.load)
        self.load()
        self.file_tree.refresh()

    # @runs_in_loading_queue
    @ui_current_widget
    @reports_exception()
    def load(self):
        self.throbber.show()
        self.processEvents()
        try:
            self.revno_map = None
            if not self.branch:
                (self.workingtree, self.branch, repo, path) = ControlDir.open_containing_tree_branch_or_repository(self.location)

            if self.revision is None:
                if self.revision_id is None:
                    if self.workingtree is not None:
                        self.revision_spec = "wt:"
                    else:
                        revno, self.revision_id = self.branch.last_revision_info()
                        self.revision_spec = str(revno)
                self.set_revision(revision_id=self.revision_id, text=self.revision_spec)
            else:
                self.set_revision(self.revision)
            self.processEvents()
        finally:
            self.throbber.hide()
            self.processEvents()

    # @runs_in_loading_queue
    @ui_current_widget
    def set_revision(self, revspec=None, revision_id=None, text=None):
        self.throbber.show()
        try:
            buttons = (self.filter_button,
                       self.diffbuttons,
                       self.refresh_button)
            state = self.file_tree.get_state()
            if text=="wt:":
                self.tree = self.workingtree
                self.tree.lock_read()
                try:
                    self.file_tree.set_tree(self.workingtree, self.branch)
                    self.file_tree.restore_state(state)
                finally:
                    self.tree.unlock()
                for button in buttons:
                    button.setEnabled(True)
            else:
                branch = self.branch
                branch.lock_read()
                self.processEvents()

                for button in buttons:
                    button.setEnabled(False)
                fmodel = self.file_tree.tree_filter_model
                fmodel.setFilter(fmodel.UNCHANGED, True)
                self.filter_menu.set_filters(fmodel.filters)

                try:
                    if revision_id is None:
                        text = revspec.spec or ''
                        if revspec.in_branch == revspec.in_history:
                            args = [branch]
                        else:
                            args = [branch, False]

                        revision_id = revspec.in_branch(*args).rev_id

                    self.revision_id = revision_id
                    self.tree = branch.repository.revision_tree(revision_id)
                    self.processEvents()
                    self.file_tree.set_tree(self.tree, self.branch)
                    self.file_tree.restore_state(state)
                    if self.revno_map is None:
                        self.processEvents()
                        # XXX make this operation lazy? how?
                        self.revno_map = self.branch.get_revision_id_to_revno_map()
                    self.file_tree.tree_model.set_revno_map(self.revno_map)
                finally:
                    branch.unlock()
            self.revision_edit.setText(text)
        finally:
            self.throbber.hide()

    # @ui_current_widget
    def reload_tree(self):
        revstr = str(self.revision_edit.text())
        if not revstr:
            if self.workingtree is not None:
                self.revision_spec = "wt:"
                revision_id = None
            else:
                revno, revision_id = self.branch.last_revision_info()
                self.revision_spec = str(revno)
            self.set_revision(revision_id=revision_id, text=self.revision_spec)
        else:
            if revstr == "wt:":
                self.revision_spec = "wt:"
                revision_id = None
                self.set_revision(revision_id=revision_id, text=self.revision_spec)
            else:
                try:
                    revspec = RevisionSpec.from_string(revstr)
                except errors.NoSuchRevisionSpec as e:
                    QtWidgets.QMessageBox.warning(self, gettext("Browse"), str(e), QtWidgets.QMessageBox.Ok)
                    return
                self.set_revision(revspec)

    def filter_triggered(self, filter, checked):
        self.file_tree.tree_filter_model.setFilter(filter, checked)
