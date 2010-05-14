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
    )

class QBzrUnbindDialog(SubProcessDialog):
     
    def __init__(self, branch, ui_mode=None, immediate=False):

        super(QBzrUnbindDialog, self).__init__(
                                  gettext("Unbind branch"),
                                  name = "unbind",
                                  default_size = (200, 200),
                                  ui_mode = ui_mode,
                                  dialog = True,
                                  parent = None,
                                  hide_progress=False,
                                  immediate = immediate
                                  )
        self.branch = branch
        
        gbBind = QtGui.QGroupBox(gettext("Unbind"), self)
        bind_box = QtGui.QFormLayout(gbBind)
        info_label = QtGui.QLabel(url_for_display(branch.base))
        bind_box.addRow(gettext("Branch:"), info_label)

        self.currbound = branch.get_bound_location()
        if self.currbound != None:
            curr_label = QtGui.QLabel(url_for_display(self.currbound))
            bind_box.addRow(gettext("Bound to:"), curr_label)  
                    
        layout = QtGui.QVBoxLayout(self)
        layout.addWidget(gbBind)
        layout.addWidget(self.make_default_status_box())
        layout.addWidget(self.buttonbox)
            
    def do_start(self):        
        self.process_widget.do_start(None, 'unbind')
