# -*- coding: utf-8 -*-
#
# QBzr - Qt frontend to Bazaar commands
#
# Contributors:
#  Mark Hammond <mhammond@skippinet.com.au>
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

class SendWindow(SubProcessDialog):

    def __init__(self, branch):#tree, selected_list, dialog=True, ui_mode=True, parent=None, local=None, message=None):
        """self.tree = tree
        self.initial_selected_list = selected_list"""
        
        super(SendWindow, self).__init__(
                                  gettext("Send"),
                                  name = "send",
                                  default_size = (400, 400),
                                  ui_mode = None,
                                  dialog = True,
                                  parent = None,
                                  hide_progress=False,
                                  )
            
            
            
            
        self.branch = branch
        
        
        gbMergeDirective = QtGui.QGroupBox(gettext("Merge Directive"), self)
        vboxMergeDirective = QtGui.QVBoxLayout(gbMergeDirective)
        vboxMergeDirective.addStrut(0)
        
        submit_hbox = QtGui.QHBoxLayout()
        
        submit_branch_label = QtGui.QLabel(gettext("Submit Branch:"))
        submit_branch_combo = QtGui.QComboBox()   
        submit_branch_combo.setEditable(True)
        
        submitbranch = branch.get_submit_branch()
        if submitbranch != None:
            submit_branch_combo.addItem(submitbranch)
            
        self.submit_branch_combo = submit_branch_combo # to allow access from another function     
        browse_submit_button = QtGui.QPushButton(gettext("Browse"))
        QtCore.QObject.connect(browse_submit_button, QtCore.SIGNAL("clicked(bool)"), self.browse_submit_clicked)
                    
        submit_hbox.addWidget(submit_branch_label)
        submit_hbox.addWidget(submit_branch_combo)
        submit_hbox.addWidget(browse_submit_button)
        
        
        submit_hbox.setStretchFactor(submit_branch_label,0)
        submit_hbox.setStretchFactor(submit_branch_combo,1)
        submit_hbox.setStretchFactor(browse_submit_button,0)
        
        vboxMergeDirective.addLayout(submit_hbox)
        
        
        public_hbox = QtGui.QHBoxLayout()
        
        public_branch_label = QtGui.QLabel(gettext("Public Branch:"))
        public_branch_combo = QtGui.QComboBox()   
        public_branch_combo.setEditable(True)
        
        publicbranch = branch.get_public_branch()
        if publicbranch != None:
            public_branch_combo.addItem(publicbranch)
                
        self.public_branch_combo = public_branch_combo # to allow access from another function      
        browse_public_button = QtGui.QPushButton(gettext("Browse"))
        QtCore.QObject.connect(browse_public_button, QtCore.SIGNAL("clicked(bool)"), self.browse_public_clicked)
                    
        public_hbox.addWidget(public_branch_label)
        public_hbox.addWidget(public_branch_combo)
        public_hbox.addWidget(browse_public_button)
        
        public_hbox.setStretchFactor(public_branch_label,0)
        public_hbox.setStretchFactor(public_branch_combo,1)
        public_hbox.setStretchFactor(browse_public_button,0)
        
        vboxMergeDirective.addLayout(public_hbox)
        
        
        remember_check = QtGui.QCheckBox(gettext("Remember these locations as defaults"))
        vboxMergeDirective.addWidget(remember_check)
        
        
        revisions_hbox = QtGui.QHBoxLayout()
        revisions_label = QtGui.QLabel(gettext("Send revisions:"))
        revisions_edit = QtGui.QLineEdit()
        
        revisions_hbox.addWidget(revisions_label)
        revisions_hbox.addWidget(revisions_edit)
        
        vboxMergeDirective.addLayout(revisions_hbox)
        
        nobundle_check = QtGui.QCheckBox(gettext("Do not include a bundle in the merge directive"))
        vboxMergeDirective.addWidget(nobundle_check)
        nopatch_check = QtGui.QCheckBox(gettext("Do not include a preview patch in the merge directive"))
        vboxMergeDirective.addWidget(nopatch_check)
        
        ####
        
        gbAction = QtGui.QGroupBox(gettext("Action"), self)
        vboxAction = QtGui.QVBoxLayout(gbAction)
        
        submit_email_radio = QtGui.QRadioButton("Send e-mail")
        submit_email_radio.toggle()
        vboxAction.addWidget(submit_email_radio)
        
        
        mailto_hbox = QtGui.QHBoxLayout()
        
        mailto_label = QtGui.QLabel(gettext("Mail to address:"))
        mailto_edit = QtGui.QLineEdit()
        mailto_hbox.insertSpacing(0,50)
        mailto_hbox.addWidget(mailto_label)
        mailto_hbox.addWidget(mailto_edit)
        
        vboxAction.addLayout(mailto_hbox)
        
        
        save_file_radio = QtGui.QRadioButton("Save to file")
        vboxAction.addWidget(save_file_radio)
        
        savefile_hbox = QtGui.QHBoxLayout()
        
        
        savefile_label = QtGui.QLabel(gettext("Filename:"))
        savefile_edit = QtGui.QLineEdit()
        self.savefile_edit = savefile_edit # to allow access from callback function
        savefile_button = QtGui.QPushButton(gettext("Browse"))
        QtCore.QObject.connect(savefile_button, QtCore.SIGNAL("clicked(bool)"), self.savefile_button_clicked)
        
        savefile_hbox.insertSpacing(0,50)
        savefile_hbox.addWidget(savefile_label)
        savefile_hbox.addWidget(savefile_edit)
        savefile_hbox.addWidget(savefile_button)
        
        vboxAction.addLayout(savefile_hbox)
                
        
        layout = QtGui.QVBoxLayout(self)
        
        
        self.splitter = QtGui.QSplitter(QtCore.Qt.Vertical)
        self.splitter.addWidget(gbAction)
        self.splitter.addWidget(gbMergeDirective)
        
        self.splitter.addWidget(self.make_default_status_box())
        
        self.splitter.setStretchFactor(0, 10)
        self.restoreSplitterSizes([150, 150])
        
        layout.addWidget(self.splitter)
        layout.addWidget(self.buttonbox)

    
    def sendtype_presed(self):
        if self.submit_email_radio.isChecked():
            self.browse_location_button.setDisabled(True)
        else:
            self.browse_location_button.setDisabled(False)
        
        
        
    def savefile_button_clicked(self):
        fileName = QtGui.QFileDialog.getSaveFileName(self, ("Select save location"));
        self.savefile_edit.setText(fileName)
                
    def browse_submit_clicked(self):
        fileName = QtGui.QFileDialog.getExistingDirectory(self, ("Select Submit branch"));
        self.submit_branch_combo.insertItem(0,fileName)
        self.submit_branch_combo.setCurrentIndex(0)        


    def browse_public_clicked(self):
        fileName = QtGui.QFileDialog.getExistingDirectory(self, ("Select Public branch"));
        self.public_branch_combo.insertItem(0,fileName)
        self.public_branch_combo.setCurrentIndex(0)
        
                
    def start(self):        
        target_branch = str(self.target_branch_combo.currentText())
        location = str(self.submit_location_edit.text())
        
        error = []
        
        if target_branch == '':
            error.append("Please fill in target branch")
        
        if location == '':
            error.append("Please fill in target location")
        else:
            if self.submit_email_radio.isChecked():
                if re.match("^.+\\@(\\[?)[a-zA-Z0-9\\-\\.]+\\.([a-zA-Z]{2,3}|[0-9]{1,3})(\\]?)$", location) == None:
                    error.append("Please enter a valid email address")
            
        if len(error) > 0:            
            msgBox = QtGui.QMessageBox(self)
            msgBox.setText("There are erros in your request.")
            msgBox.setInformativeText("\n".join(error))
            msgBox.setStandardButtons(QtGui.QMessageBox.Ok)
            msgBox.setDefaultButton(QtGui.QMessageBox.Ok)
            msgBox.setIcon(QtGui.QMessageBox.Critical)
            ret = msgBox.exec_()
            return
            
            
        mylocation =  url_for_display(self.branch.base)    
        
        args = ["-f", mylocation]
        
        
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
            
        args.append("--revision=-1")
        
            
        
        
        
        self.process_widget.start(None, 'send', target_branch, *args)
        

    def saveSize(self):
        SubProcessDialog.saveSize(self)
        self.saveSplitterSizes()
