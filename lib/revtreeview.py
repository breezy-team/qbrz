# -*- coding: utf-8 -*-
#
# QBzr - Qt frontend to Bazaar commands
# Copyright (C) 2006-2007 Gary van der Merwe <garyvdm@gmail.com> 
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

from bzrlib.plugins.qbzr.lib.util import runs_in_loading_queue
from bzrlib.plugins.qbzr.lib.lazycachedrevloader import load_revisions
from bzrlib.transport.local import LocalTransport

RevIdRole = QtCore.Qt.UserRole + 1

class RevisionTreeView(QtGui.QTreeView):
    """TreeView widget to shows revisions.
    
    Only revisions that are visible on screen are loaded."""

    def __init__(self, parent=None):
        QtGui.QTreeView.__init__(self, parent)
        self.connect(self.verticalScrollBar(), QtCore.SIGNAL("valueChanged (int)"),
                     self.scroll_changed)
        self.load_revisions_call_count = 0
        self.load_revisions_throbber_shown = False
        self.rev_tree_rev_tree_model = None
    
    def set_rev_tree_model(self, rev_tree_model):
        self.rev_tree_model = rev_tree_model
        rev_tree_model.connect(rev_tree_model,
            QtCore.SIGNAL("dataChanged(QModelIndex, QModelIndex)"),
            self.model_data_changed)
    
    def scroll_changed(self, value):
        self.load_visible_revisions()
    
    def model_data_changed(self, start_index, end_index):
        self.load_visible_revisions()
    
    def resizeEvent(self, e):
        self.load_visible_revisions()
        QtGui.QTreeView.resizeEvent(self, e)
    
    def get_repo(self):
        """Returns a repository to be passed to load_revisions"""
        raise NotImplementedError()
    
    def on_revisions_loaded(self, revisions, last_call):
        """Called once revisions are availible
        
        Typicaly you will want to pass this on to your rev_tree_model so that it can
        emit a dataChanged signal.
        """
        pass
    
    def get_row_revid(self, row):
        """Get the revision id for a row"""
    
    @runs_in_loading_queue
    def load_visible_revisions(self):
        rev_tree_model = self.rev_tree_model
        top_index = self.indexAt(self.viewport().rect().topLeft()).row()
        bottom_index = self.indexAt(self.viewport().rect().bottomLeft()).row()
        row_count = rev_tree_model.rowCount(QtCore.QModelIndex())
        if top_index == -1:
            #Nothing is visible
            return
        if bottom_index == -1:
            bottom_index = row_count
        # The + 2 is so that the rev that is off screen due to the throbber
        # is loaded.
        bottom_index = min((bottom_index + 2, row_count))
        revids = set()
        for row in xrange(top_index, bottom_index):
            revids.add(rev_tree_model.get_revid(row))
        revids = list(revids)
        
        self.load_revisions_call_count += 1
        current_call_count = self.load_revisions_call_count

        def before_batch_load(repo, revids):
            if current_call_count < self.load_revisions_call_count:
                return True
            
            repo_is_local = isinstance(repo.bzrdir.transport, LocalTransport)
            if not repo_is_local:
                if not self.load_revisions_throbber_shown \
                            and hasattr(self, "throbber"):
                    self.throbber.show()
                    self.load_revisions_throbber_shown = True
                # Allow for more scrolling to happen.
                self.delay(0.5)
            
            return False

        try:
            load_revisions(revids, self.get_repo(),
                           revisions_loaded = self.on_revisions_loaded,
                           before_batch_load = before_batch_load)
        finally:
            self.load_revisions_call_count -=1
            if self.load_revisions_call_count == 0:
                # This is the last running method
                if self.load_revisions_throbber_shown:
                    self.load_revisions_throbber_shown = False
                    self.throbber.hide()
    
    def delay(self, timeout):
        
        def null():
            pass
        
        QtCore.QTimer.singleShot(timeout, null)
        QtCore.QCoreApplication.processEvents(
                            QtCore.QEventLoop.WaitForMoreEvents)
