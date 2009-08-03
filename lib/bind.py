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

from bzrlib import errors

from bzrlib.plugins.qbzr.lib.i18n import gettext
from bzrlib.plugins.qbzr.lib.subprocess import SubProcessDialog
from bzrlib.plugins.qbzr.lib.util import (
    url_for_display,
    QBzrDialog,
    runs_in_loading_queue,
    ThrobberWidget,
    StandardButton,
    BTN_CANCEL
    )
from bzrlib.plugins.qbzr.lib.uifactory import ui_current_widget
from bzrlib.plugins.qbzr.lib.trace import (
   reports_exception,
   SUB_LOAD_METHOD)

class QBzrBindDialog(SubProcessDialog):

    actionButton = None
    
    def __init__(self, branch, ui_mode = None, unbind=False):
        
        super(QBzrBindDialog, self).__init__(
                                  gettext("Bind/Unbind branch"),
                                  name = "bind",
                                  default_size = (400, 400),
                                  ui_mode = ui_mode,
                                  dialog = True,
                                  parent = None,
                                  hide_progress=False,
                                  )
            
        self.branch = branch
        
        gbBind = QtGui.QGroupBox(gettext("Bind/Unbind branch"), self)
        
        bind_hbox = QtGui.QHBoxLayout(gbBind)
        
        branch_label = QtGui.QLabel(gettext("Bind to:"))
        branch_combo = QtGui.QComboBox()   
        branch_combo.setEditable(True)
        
        self.branch_combo = branch_combo
        
        QtCore.QObject.connect(branch_combo, QtCore.SIGNAL("textChanged(QString)"), self.combo_changed)
        
        repo = branch.bzrdir.find_repository()
        
        currboundloc = branch.get_bound_location()
        
        if unbind and currboundloc != None:
            branch_combo.addItem(url_for_display(currboundloc))
        elif unbind == False:
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
        
        layout = QtGui.QVBoxLayout(self)
        
        layout.addWidget(gbBind)
        
        layout.addWidget(self.make_default_status_box())
        layout.addWidget(self.buttonbox)

        for but in self.buttonbox.buttons(): 
            self.buttonbox.removeButton(but)
            
        cancelButton = StandardButton(BTN_CANCEL)
        
        
        
        
        
        
        if unbind:
            self.actionButton = QtGui.QPushButton("Unbind")
        else:
            self.actionButton = QtGui.QPushButton("Bind")


        self.buttonbox.addButton(self.actionButton,
                                 QtGui.QDialogButtonBox.AcceptRole)
                
        self.buttonbox.addButton(cancelButton,
                                 QtGui.QDialogButtonBox.RejectRole)

        
        self.combo_changed(branch_combo.currentText())
        """self.connect(self.buttonbox, QtCore.SIGNAL("accepted()"), self.do_accept)
        self.connect(self.buttonbox, QtCore.SIGNAL("rejected()"), self.do_reject)"""

        

    def combo_changed(self, stri):
        if self.actionButton != None:
            if str(stri) == "":
                self.actionButton.setText("Unbind")
            else:
                self.actionButton.setText("Bind")
        
    def browse_clicked(self):
        fileName = QtGui.QFileDialog.getExistingDirectory(self, gettext("Select branch location"));
        if fileName != '':
            self.branch_combo.insertItem(0,fileName)
            self.branch_combo.setCurrentIndex(0)
        
    @reports_exception(type=SUB_LOAD_METHOD)
    @ui_current_widget   
    def validate(self):
        return True
        location = str(self.branch_combo.currentText())
       
        if(location == ''):
            raise errors.BzrCommandError("Branch location not entered.")
        
        return True
    
    def do_start(self):        
        args = []
        
        location = str(self.branch_combo.currentText())
        mylocation =  url_for_display(self.branch.base)     
        
        if location == "":
            self.process_widget.do_start(None, 'unbind')
        else:
            self.process_widget.do_start(None, 'bind', location, *args)
        
