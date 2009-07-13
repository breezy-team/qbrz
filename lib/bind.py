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

from bzrlib.plugins.qbzr.lib.wtlist import (
    ChangeDesc,
    WorkingTreeFileList,
    closure_in_selected_list,
    )
from bzrlib.plugins.qbzr.lib.util import url_for_display, QBzrWindow, BTN_CLOSE, BTN_OK

from bzrlib.branch import Branch

class QBzrBindWindow(QBzrWindow):

    
    def accept(self):
        pass
    
    def __init__(self, branch, ui_mode=False):#tree, selected_list, dialog=True, ui_mode=True, parent=None, local=None, message=None):
        
        self._window_name = "bind"
        
        title = "%s: %s" % (gettext("Bind branch"), url_for_display(branch.base))
        QBzrWindow.__init__(self, title)
        
        self.resize(500,-1)

        
        self.buttonbox = self.create_button_box(BTN_CLOSE, BTN_OK)

        self.vbox = QtGui.QVBoxLayout(self.centralwidget)
        
        
        self.branch = branch
        
        gbBind = QtGui.QGroupBox(gettext("Bind branch"), self)
        
        bind_hbox = QtGui.QHBoxLayout(gbBind)
        
        branch_label = QtGui.QLabel(gettext("Branch:"))
        branch_combo = QtGui.QComboBox()   
        branch_combo.setEditable(True)
        
        self.branch_combo = branch_combo
        
        repo = branch.bzrdir.find_repository()
        
        boundloc = branch.get_old_bound_location()
        if boundloc != None:
            branch_combo.addItem(url_for_display(boundloc))
            
        """if repo != None:
            branches = repo.find_branches()
            for br in branches:
                branch_combo.addItem(url_for_display(br.base))"""
                
        if boundloc == None:
            branch_combo.clearEditText()
            
        
        browse_button = QtGui.QPushButton(gettext("Browse"))
        QtCore.QObject.connect(browse_button, QtCore.SIGNAL("clicked(bool)"), self.browse_clicked)
        
                
        bind_hbox.addWidget(branch_label)
        bind_hbox.addWidget(branch_combo)
        bind_hbox.addWidget(browse_button)
        
        bind_hbox.setStretchFactor(branch_label,0)
        bind_hbox.setStretchFactor(branch_combo,1)
        bind_hbox.setStretchFactor(browse_button,0)
        
        self.vbox.addWidget(gbBind)
        self.vbox.addStretch()
        self.vbox.addWidget(self.buttonbox)
        
    def browse_clicked(self):
        fileName = QtGui.QFileDialog.getExistingDirectory(self, ("Select branch location"));
        self.branch_combo.insertItem(0,fileName)
        self.branch_combo.setCurrentIndex(0)
        
                
    def accept(self):        
        error = []      
        
        args = []
        location = str(self.branch_combo.currentText())
        
        if(location == ''):
            error.append("Fill in branch location")
            
        mylocation =  url_for_display(self.branch.base)
                            
        if len(error) > 0:            
            msgBox = QtGui.QMessageBox(self)
            msgBox.setText("There are errors.\nPlease do the following actions in order to fix them.")
            msgBox.setInformativeText("\n".join(error))
            msgBox.setStandardButtons(QtGui.QMessageBox.Ok)
            msgBox.setDefaultButton(QtGui.QMessageBox.Ok)
            msgBox.setIcon(QtGui.QMessageBox.Critical)
            ret = msgBox.exec_()
            return False

        
        b, relpath = Branch.open_containing(mylocation)
        b_other = Branch.open(location)
        try:
            b.bind(b_other)
        except errors.DivergedBranches:
            msgBox = QtGui.QMessageBox(self)
            msgBox.setText('These branches have diverged.'
                           ' Try merging, and then bind again.')
            msgBox.setStandardButtons(QtGui.QMessageBox.Ok)
            msgBox.setDefaultButton(QtGui.QMessageBox.Ok)
            msgBox.setIcon(QtGui.QMessageBox.Critical)
            ret = msgBox.exec_()
            return False

        if b.get_config().has_explicit_nickname():
            b.nick = b_other.nick
            
            
        self.close()

                


