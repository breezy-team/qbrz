# -*- coding: utf-8 -*-
#
# QBzr - Qt frontend to Bazaar commands
#
# Contributors:
#  Javier Derderian <javierder@gmail.com>
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

import re
from PyQt4 import QtCore, QtGui

from bzrlib import errors
from bzrlib.plugins.qbzr.lib.i18n import gettext
from bzrlib.plugins.qbzr.lib.subprocess import SubProcessDialog
from bzrlib.plugins.qbzr.lib.util import url_for_display

class QBzrExportDialog(SubProcessDialog):

    def __init__(self, dest, branch, ui_mode):
        
        
        title = "%s: %s" % (gettext("Export"), url_for_display(branch.base))
        super(QBzrExportDialog, self).__init__(
                                  title,
                                  name = "export",
                                  default_size = (400, 400),
                                  ui_mode = ui_mode,
                                  dialog = True,
                                  parent = None,
                                  hide_progress=False,
                                  )
            
            
            
            
        self.branch = branch
        
        
        gbExportDestination = QtGui.QGroupBox(gettext("Export destination"), self)
        vboxExportDestination = QtGui.QVBoxLayout(gbExportDestination)
        vboxExportDestination.addStrut(0)
        
        location_hbox = QtGui.QHBoxLayout()
        
        location_label = QtGui.QLabel(gettext("Location:"))
        location_edit = QtGui.QLineEdit()
           
        
        
        #submitbranch = branch.get_submit_branch()
        #if submitbranch != None:
        #    submit_branch_combo.addItem(submitbranch)
            
        self.location_edit = location_edit # to allow access from another function     
        browse_button = QtGui.QPushButton(gettext("Browse"))
        QtCore.QObject.connect(browse_button, QtCore.SIGNAL("clicked(bool)"), self.browse_submit_clicked)
                    
        location_hbox.addWidget(location_label)
        location_hbox.addWidget(location_edit)
        location_hbox.addWidget(browse_button)
        
        
        location_hbox.setStretchFactor(location_label,0)
        location_hbox.setStretchFactor(location_edit,1)
        location_hbox.setStretchFactor(browse_button,0)
        
        vboxExportDestination.addLayout(location_hbox)
        
        
        format_hbox = QtGui.QHBoxLayout()
        
        format_label = QtGui.QLabel(gettext("Format:"))
        format_combo = QtGui.QComboBox()   
        format_combo.addItem("dir")
        format_combo.addItem("tar")
        format_combo.addItem("tbz2")
        format_combo.addItem("tgz")
        format_combo.addItem("zip")
        
        
        """publicbranch = branch.get_public_branch()
        if publicbranch != None:
            public_branch_combo.addItem(publicbranch)"""
                
        self.format_combo = format_combo # to allow access from another function      
                    
        format_hbox.addWidget(format_label)
        format_hbox.addWidget(format_combo)
        
        format_hbox.setStretchFactor(format_label,0)
        format_hbox.setStretchFactor(format_combo,0)
        
        vboxExportDestination.addLayout(format_hbox)
        
        
        remember_check = QtGui.QCheckBox(gettext("Remember these locations as defaults"))
        self.remember_check = remember_check
        vboxExportDestination.addWidget(remember_check)
        
        
        revisions_hbox = QtGui.QHBoxLayout()
        revisions_label = QtGui.QLabel(gettext("Send revisions:"))
        revisions_edit = QtGui.QLineEdit()
        self.revisions_edit = revisions_edit
        
        revisions_hbox.addWidget(revisions_label)
        revisions_hbox.addWidget(revisions_edit)
        
        vboxExportDestination.addLayout(revisions_hbox)
        
        nobundle_check = QtGui.QCheckBox(gettext("Do not include a bundle in the merge directive"))
        self.nobundle_check = nobundle_check
        vboxExportDestination.addWidget(nobundle_check)
        nopatch_check = QtGui.QCheckBox(gettext("Do not include a preview patch in the merge directive"))
        self.nopatch_check = nopatch_check
        vboxExportDestination.addWidget(nopatch_check)
        
        message_hbox = QtGui.QHBoxLayout()
        message_label = QtGui.QLabel(gettext("Message:"))
        message_edit = QtGui.QLineEdit()
        self.message_edit = message_edit
        
        message_hbox.addWidget(message_label)
        message_hbox.addWidget(message_edit)
        
        vboxExportDestination.addLayout(message_hbox)
        
        ####
        
        gbAction = QtGui.QGroupBox(gettext("Action"), self)
        vboxAction = QtGui.QVBoxLayout(gbAction)
        
        submit_email_radio = QtGui.QRadioButton("Send e-mail")
        submit_email_radio.toggle()
        self.submit_email_radio = submit_email_radio
        vboxAction.addWidget(submit_email_radio)
        
        
        mailto_hbox = QtGui.QHBoxLayout()
        
        mailto_label = QtGui.QLabel(gettext("Mail to address:"))
        mailto_edit = QtGui.QLineEdit()
        self.mailto_edit = mailto_edit
        mailto_hbox.insertSpacing(0,50)
        mailto_hbox.addWidget(mailto_label)
        mailto_hbox.addWidget(mailto_edit)
        
        vboxAction.addLayout(mailto_hbox)
        
        
        save_file_radio = QtGui.QRadioButton("Save to file")
        self.save_file_radio = save_file_radio
        
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
        self.splitter.addWidget(gbExportDestination)
        
        self.splitter.addWidget(self.make_default_status_box())
        
        self.splitter.setStretchFactor(0, 10)
        self.restoreSplitterSizes([150, 150])
        
        layout.addWidget(self.splitter)
        layout.addWidget(self.buttonbox)
       
        
        
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
        
    
    def validate(self):
        if self.submit_email_radio.isChecked():
            location = str(self.mailto_edit.text())
            if location == '' :
                self.mailto_edit.setFocus()
                raise errors.BzrCommandError("Email address not entered.")
            if re.match("^.+\\@(\\[?)[a-zA-Z0-9\\-\\.]+\\.([a-zA-Z]{2,3}|[0-9]{1,3})(\\]?)$", location) == None:
                self.mailto_edit.setFocus()
                raise errors.BzrCommandError("Email address is not valid.")
        else:
            location = str(self.savefile_edit.text())
            if location == '':
                self.savefile_edit.setFocus()
                raise errors.BzrCommandError("Filename not entered.")
        
        submit_branch = str(self.submit_branch_combo.currentText())
        if(submit_branch == ''):
            self.submit_branch_combo.setFocus()
            raise errors.BzrCommandError("No submit branch entered.")
        return True
    
    def start(self):
        args = []
        submit_branch = str(self.submit_branch_combo.currentText())
        public_branch = str(self.public_branch_combo.currentText())
        
        if public_branch != '':
            args.append(public_branch)
            
        mylocation =  url_for_display(self.branch.base)     
        args.append("-f")
        args.append(mylocation)

        if self.submit_email_radio.isChecked():
            location = str(self.mailto_edit.text())
            args.append("--mail-to=%s" % location)
        else:
            location = str(self.savefile_edit.text())
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

    def saveSize(self):
        SubProcessDialog.saveSize(self)
        self.saveSplitterSizes()
