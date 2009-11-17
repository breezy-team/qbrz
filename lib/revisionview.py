# QBzr - Qt frontend to Bazaar commands
#
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

from bzrlib.plugins.qbzr.lib.diffwindow import DiffWindow
from bzrlib.plugins.qbzr.lib.diff_arg import InternalDiffArgProvider
from bzrlib.plugins.qbzr.lib.revisionmessagebrowser import RevisionMessageBrowser
from bzrlib.plugins.qbzr.lib.i18n import gettext

# DiffWindow has alot of stuff that we need, so we just extend it.
class RevisionView(DiffWindow):
    """Shows information, and a diff for a revision, in a window."""
    
    def __init__(self, revision, branch, parent=None):
        self.branch = branch
        self.revision = revision
        
        args = InternalDiffArgProvider(revision.parent_ids[0],
                                       revision.revision_id,
                                       branch, branch)
        DiffWindow.__init__(self, args, parent)
        
        self.message_browser = RevisionMessageBrowser(self)
        self.message_browser.set_display_revids([revision.revision_id], 
                                                branch.repository)
        
        vsplitter = QtGui.QSplitter(QtCore.Qt.Vertical)
        vsplitter.addWidget(self.message_browser)
        vsplitter.addWidget(self.stack)
        vsplitter.setStretchFactor(0, 1)
        vsplitter.setStretchFactor(1, 3)
        
        self.centralwidget.layout().insertWidget(1, vsplitter)
        self.centralwidget.layout().removeWidget(self.stack)
        
        self.refresh_button.setVisible(False)
        self.set_diff_title()
    
    def set_diff_title(self):
        title = [gettext("Revision"), self.revision.revision_id]
        self.set_title_and_icon(title)

    def restoreSize(self, name, defaultSize):
        super(RevisionView, self).restoreSize("revisionview", defaultSize)