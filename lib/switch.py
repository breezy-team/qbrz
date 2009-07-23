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

import os
import re
from PyQt4 import QtCore, QtGui

from bzrlib.plugins.qbzr.lib.i18n import gettext
from bzrlib.plugins.qbzr.lib.subprocess import SubProcessDialog
from bzrlib.plugins.qbzr.lib.wtlist import (
    ChangeDesc,
    WorkingTreeFileList,
    closure_in_selected_list,
    )
from bzrlib.plugins.qbzr.lib.util import url_for_display

from bzrlib.branch import Branch

from bzrlib.plugins.qbzr.lib.uifactory import ui_current_widget

from bzrlib.plugins.qbzr.lib.trace import (

   reports_exception,

   SUB_LOAD_METHOD)

from bzrlib import errors, osutils

class QBzrSwitchWindow(SubProcessDialog):

    def __init__(self, branch, ui_mode = None):#tree, selected_list, dialog=True, ui_mode=True, parent=None, local=None, message=None):
        
        
        
        super(QBzrSwitchWindow, self).__init__(
                                  gettext("Switch Checkout to"),
                                  name = "switch",
                                  default_size = (400, 400),
                                  ui_mode = ui_mode,
                                  dialog = True,
                                  parent = None,
                                  hide_progress=False,
                                  )
            
        self.branch = branch
        
        gbSwitch = QtGui.QGroupBox(gettext("Switch Checkout to"), self)
        
        switch_hbox = QtGui.QHBoxLayout(gbSwitch)
        
        branch_label = QtGui.QLabel(gettext("Branch:"))
        branch_combo = QtGui.QComboBox()   
        branch_combo.setEditable(True)
        
        self.branch_combo = branch_combo
        
        repo = branch.bzrdir.find_repository()


        repo = branch.bzrdir.find_repository()
        
        boundloc = branch.get_bound_location()
        if boundloc != None:
            branch_combo.addItem(url_for_display(boundloc))
            
        if repo != None:
            branches = repo.find_branches()
            for br in branches:
                branch_combo.addItem(url_for_display(br.base))
             
        if boundloc == None:
            branch_combo.clearEditText()

        browse_button = QtGui.QPushButton(gettext("Browse"))
        QtCore.QObject.connect(browse_button, QtCore.SIGNAL("clicked(bool)"), self.browse_clicked)
        
                
        switch_hbox.addWidget(branch_label)
        switch_hbox.addWidget(branch_combo)
        switch_hbox.addWidget(browse_button)
        
        switch_hbox.setStretchFactor(branch_label,0)
        switch_hbox.setStretchFactor(branch_combo,1)
        switch_hbox.setStretchFactor(browse_button,0)
        
        layout = QtGui.QVBoxLayout(self)
        
        layout.addWidget(gbSwitch)
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
            raise errors.BzrCommandError("Branch location not entered.")
        
        return True
            
    def start(self):        

        
        args = []
        
        location = str(self.branch_combo.currentText())
        mylocation =  url_for_display(self.branch.base)     
                            
        self.process_widget.start(None, 'switch', location, *args)
        

    def saveSize(self):
        SubProcessDialog.saveSize(self)
        #self.saveSplitterSizes()
