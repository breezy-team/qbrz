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
        
        title = "%s: %s" % (gettext("Switch Checkout"), url_for_display(branch.base))
        QBzrWindow.__init__(self, title)
        

        
        self.buttonbox = self.create_button_box(BTN_CLOSE, BTN_OK)

        self.vbox = QtGui.QVBoxLayout(self.centralwidget)
        
        
        self.branch = branch
        
        gbBind = QtGui.QGroupBox(gettext("Switch Checkout To"), self)
        
        bind_hbox = QtGui.QHBoxLayout(gbBind)
        
        branch_label = QtGui.QLabel(gettext("Branch:"))
        branch_combo = QtGui.QComboBox()   
        branch_combo.setEditable(True)
        
        self.branch_combo = branch_combo
        
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
        
                
    def start(self):        

        error = []
        
        
        args = []
        submit_branch = str(self.submit_branch_combo.currentText())
        public_branch = str(self.public_branch_combo.currentText())
        
        if(submit_branch == ''):
            error.append("Fill in submit branch")
        #else:
        #    args.append(submit_branch)
            
        if public_branch != '':
            args.append(public_branch)
            
        mylocation =  url_for_display(self.branch.base)     
        args.append("-f")
        args.append(mylocation)

        
        if self.submit_email_radio.isChecked():
            location = str(self.mailto_edit.text())
            if location == '' or re.match("^.+\\@(\\[?)[a-zA-Z0-9\\-\\.]+\\.([a-zA-Z]{2,3}|[0-9]{1,3})(\\]?)$", location) == None:
                error.append("Enter a valid email address")
        else:
            location = str(self.savefile_edit.text())
            if location == '':
                error.append("Enter a valid filename to save.")
                            
        if len(error) > 0:            
            msgBox = QtGui.QMessageBox(self)
            msgBox.setText("There are errors.\nPlease do the following actions in order to fix them.")
            msgBox.setInformativeText("\n".join(error))
            msgBox.setStandardButtons(QtGui.QMessageBox.Ok)
            msgBox.setDefaultButton(QtGui.QMessageBox.Ok)
            msgBox.setIcon(QtGui.QMessageBox.Critical)
            ret = msgBox.exec_()
            return False

        if self.submit_email_radio.isChecked():
            args.append("--mail-to=%s" % location)
        else:
            args.append("-o")
            args.append(location)
            
        
        if self.remember_check.isChecked():
            args.append("--remember")

        if self.nopatch_check.isChecked():
            args.append("--no-patch")
            
        if self.nobundle_check.isChecked():
            args.append("--no-bundle")
                    
        if self.message_edit.text() != '':
            args.append("--message=%s" % str(self.message_edit.text()))
        
        
        revision = str(self.revisions_edit.text())
        if revision == '':
            args.append("--revision=-1")
        else:
            args.append("--revision=%s" % revision)

        self.process_widget.start(None, 'send', submit_branch, *args)
        


