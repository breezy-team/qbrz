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


from PyQt4 import QtCore, QtGui

from bzrlib import errors, osutils

from bzrlib.plugins.qbzr.lib.i18n import gettext
from bzrlib.plugins.qbzr.lib.subprocess import SubProcessDialog
from bzrlib.plugins.qbzr.lib.util import (
    url_for_display,
    StandardButton,
    BTN_CANCEL
    )
from bzrlib.plugins.qbzr.lib.uifactory import ui_current_widget
from bzrlib.plugins.qbzr.lib.trace import (
   reports_exception,
   SUB_LOAD_METHOD)

class QBzrBindDialog(SubProcessDialog):

    def __init__(self, branch, location=None, ui_mode = None):
        
        super(QBzrBindDialog, self).__init__(
                                  gettext("Bind branch"),
                                  name = "bind",
                                  default_size = (400, 400),
                                  ui_mode = ui_mode,
                                  dialog = True,
                                  parent = None,
                                  hide_progress=False,
                                  )
            
        self.branch = branch
        
        gbBind = QtGui.QGroupBox(gettext("Bind"), self)
        
        bind_box = QtGui.QFormLayout(gbBind)
        
        bind_box.addRow(gettext("Branch location:"),QtGui.QLabel(url_for_display(branch.base)))
        
        bind_hbox = QtGui.QHBoxLayout()
        
        branch_label = QtGui.QLabel(gettext("Bind to:"))
        branch_combo = QtGui.QComboBox()   
        branch_combo.setEditable(True)
        
        self.branch_combo = branch_combo
        
        repo = branch.bzrdir.find_repository()
        
        if location != None:
            branch_combo.addItem(osutils.abspath(location))
            
        self.currbound = branch.get_bound_location()
        if self.currbound != None:
            bind_box.addRow(gettext("Currently bound to:"),QtGui.QLabel(url_for_display(self.currbound)))
                     
        
        boundloc = branch.get_old_bound_location()
        if boundloc != None:
            branch_combo.addItem(url_for_display(boundloc))
            
        browse_button = QtGui.QPushButton(gettext("Browse"))
        QtCore.QObject.connect(browse_button, QtCore.SIGNAL("clicked(bool)"), self.browse_clicked)
        
                
        bind_hbox.addWidget(branch_label)
        bind_hbox.addWidget(branch_combo)
        bind_hbox.addWidget(browse_button)
        
        bind_hbox.setStretchFactor(branch_label,0)
        bind_hbox.setStretchFactor(branch_combo,1)
        bind_hbox.setStretchFactor(browse_button,0)
        bind_box.addRow(bind_hbox)
        
        layout = QtGui.QVBoxLayout(self)
        
        layout.addWidget(gbBind)
        
        self.buttonbox.clear()
        
        cancelButton = StandardButton(BTN_CANCEL)
        
        self.bindButton = QtGui.QPushButton(gettext("Bind"))
        self.buttonbox.addButton(self.bindButton,
                                 QtGui.QDialogButtonBox.AcceptRole)      
        
        self.buttonbox.addButton(cancelButton,
                                 QtGui.QDialogButtonBox.RejectRole)
                
        layout.addWidget(self.make_default_status_box())
        layout.addWidget(self.buttonbox)
        
        
    def browse_clicked(self):
        fileName = QtGui.QFileDialog.getExistingDirectory(self, gettext("Select branch location"));
        if fileName != '':
            self.branch_combo.insertItem(0,fileName)
            self.branch_combo.setCurrentIndex(0)
        
    @reports_exception(type=SUB_LOAD_METHOD)
    @ui_current_widget   
    def validate(self):
        location = str(self.branch_combo.currentText())
       
        if(location == ''):
            raise errors.BzrCommandError(gettext("Master branch location not specified."))
        
        return True
    
    def do_start(self):        
        args = []
        
        location = str(self.branch_combo.currentText())
        mylocation =  url_for_display(self.branch.base)     
                            
        self.process_widget.do_start(None, 'bind', location, *args)
