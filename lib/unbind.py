# -*- coding: utf-8 -*-
#
# QBzr - Qt frontend to Bazaar commands
#
# Contributors:
#  Javier Der Derian <javierder@gmail.com>
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


from PyQt4 import QtGui

from bzrlib.plugins.qbzr.lib.i18n import gettext
from bzrlib.plugins.qbzr.lib.subprocess import SubProcessDialog
from bzrlib.plugins.qbzr.lib.util import (
    url_for_display,
    StandardButton,
    BTN_CANCEL
    )

class QBzrUnbindDialog(SubProcessDialog):
     
    def __init__(self, branch, ui_mode = None):

        super(QBzrUnbindDialog, self).__init__(
                                  gettext("Unbind branch"),
                                  name = "unbind",
                                  default_size = (200, 200),
                                  ui_mode = ui_mode,
                                  dialog = True,
                                  parent = None,
                                  hide_progress=False,
                                  )
        
        self.branch = branch
        
        gbBind = QtGui.QGroupBox(gettext("Unbind branch %s") % url_for_display(branch.base), self)
        
        bind_vbox = QtGui.QVBoxLayout(gbBind)
        
        self.currbound = branch.get_bound_location()
        if self.currbound != None:
            curr_hbox = QtGui.QHBoxLayout()
            
            curr_label = QtGui.QLabel(gettext("Currently bound to: %s") % url_for_display(self.currbound))
                    
            curr_hbox.addWidget(curr_label)
            bind_vbox.addLayout(curr_hbox)    
                    
        layout = QtGui.QVBoxLayout(self)
        
        layout.addWidget(gbBind)
        
        self.buttonbox.clear()
        
        cancelButton = StandardButton(BTN_CANCEL)
        
        self.unbindButton = QtGui.QPushButton(gettext("Unbind"))
        self.buttonbox.addButton(self.unbindButton,
                                 QtGui.QDialogButtonBox.AcceptRole)     
        
        self.buttonbox.addButton(cancelButton,
                                 QtGui.QDialogButtonBox.RejectRole)
                
        layout.addWidget(self.make_default_status_box())
        layout.addWidget(self.buttonbox)
            
    def do_start(self):        
        
        self.process_widget.do_start(None, 'unbind')
