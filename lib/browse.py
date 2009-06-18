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

from PyQt4 import QtCore, QtGui
from bzrlib import (
    osutils,
    errors,
    )
from bzrlib.bzrdir import BzrDir
from bzrlib.revisionspec import RevisionSpec

from bzrlib.plugins.qbzr.lib.i18n import gettext
from bzrlib.plugins.qbzr.lib.treewidget import TreeWidget
from bzrlib.plugins.qbzr.lib.util import (
    BTN_CLOSE,
    QBzrWindow,
    ThrobberWidget,
    runs_in_loading_queue,
    url_for_display,
    )
from bzrlib.plugins.qbzr.lib.uifactory import ui_current_widget
from bzrlib.plugins.qbzr.lib.trace import reports_exception


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
        self.root_file_id = None

        QBzrWindow.__init__(self,
            [gettext("Browse"), self.location], parent)
        self.restoreSize("browse", (780, 580))

        vbox = QtGui.QVBoxLayout(self.centralwidget)
        
        self.throbber = ThrobberWidget(self)
        vbox.addWidget(self.throbber)

        hbox = QtGui.QHBoxLayout()
        hbox.addWidget(QtGui.QLabel(gettext("Location:")))
        self.location_edit = QtGui.QLineEdit()
        self.location_edit.setReadOnly(True)
        self.location_edit.setText(self.location)
        hbox.addWidget(self.location_edit, 7)
        hbox.addWidget(QtGui.QLabel(gettext("Revision:")))
        self.revision_edit = QtGui.QLineEdit()
        hbox.addWidget(self.revision_edit, 1)
        self.show_button = QtGui.QPushButton(gettext("Show"))
        self.connect(self.show_button, QtCore.SIGNAL("clicked()"), self.reload_tree)
        hbox.addWidget(self.show_button, 0)
        vbox.addLayout(hbox)
        
        self.file_tree = TreeWidget(self)
        self.file_tree.throbber = self.throbber
        vbox.addWidget(self.file_tree)

        buttonbox = self.create_button_box(BTN_CLOSE)
        vbox.addWidget(buttonbox)

        self.windows = []

    def show(self):
        # we show the bare form as soon as possible.
        QBzrWindow.show(self)
        QtCore.QTimer.singleShot(1, self.load)
   
    @runs_in_loading_queue
    @ui_current_widget
    @reports_exception()
    def load(self):
        self.throbber.show()
        self.processEvents()
        try:
            self.revno_map = None
            if not self.branch:
                (self.workingtree,
                 self.branch,
                 repo, path) = BzrDir.open_containing_tree_branch_or_repository(self.location)
            
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
            # XXX make this operation lazy? how?
            self.revno_map = self.branch.get_revision_id_to_revno_map()
            self.file_tree.tree_model.set_revno_map(self.revno_map)
            
        finally:
            self.throbber.hide()

    
    @ui_current_widget
    def set_revision(self, revspec=None, revision_id=None, text=None):
        if text=="wt:":
            self.workingtree.lock_read()
            try:
                self.tree = self.workingtree
                self.file_tree.set_tree(self.workingtree, self.branch)
            finally:
                self.workingtree.unlock()
        else:
            branch = self.branch
            branch.lock_read()
            self.processEvents()
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
                if self.revno_map is not None:
                    self.file_tree.tree_model.set_revno_map(self.revno_map)
            finally:
                branch.unlock()
        self.revision_edit.setText(text)


    @ui_current_widget
    def reload_tree(self):
        revstr = unicode(self.revision_edit.text())
        if not revstr:
            if self.workingtree is not None:
                revision_spec = "wt:"
                revision_id = None
            else:
                revno, revision_id = self.branch.last_revision_info()
                self.revision_spec = str(revno)
            self.set_revision(revision_id=revision_id, text=revision_spec)
        else:
            if revstr == "wt:":
                revision_spec = "wt:"
                revision_id = None                
                self.set_revision(revision_id=revision_id, text=revision_spec)
            else:
                try:
                    revspec = RevisionSpec.from_string(revstr)
                except errors.NoSuchRevisionSpec, e:
                    QtGui.QMessageBox.warning(self,
                        gettext("Browse"), str(e),
                        QtGui.QMessageBox.Ok)
                    return
                self.set_revision(revspec)
