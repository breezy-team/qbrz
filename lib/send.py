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

class SendWindow(SubProcessDialog):

    def __init__(self, branch, ui_mode=False, parent=None):
        
        title = "%s: %s" % (gettext("Send"), url_for_display(branch.base))
        super(SendWindow, self).__init__(
                                  title,
                                  name = "send",
                                  default_size = (400, 400),
                                  ui_mode = ui_mode,
                                  dialog = True,
                                  parent = parent,
                                  hide_progress=False,
                                  )

        self.branch = branch
        
        gbMergeDirective = QtGui.QGroupBox(gettext("Merge Directive Options"), self)
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
        self.remember_check = remember_check
        vboxMergeDirective.addWidget(remember_check)

        bundle_check = QtGui.QCheckBox(gettext("Include a bundle in the merge directive"))
        bundle_check.setChecked(True)
        self.bundle_check = bundle_check
        vboxMergeDirective.addWidget(bundle_check)
        patch_check = QtGui.QCheckBox(gettext("Include a preview patch in the merge directive"))
        patch_check.setChecked(True)
        self.patch_check = patch_check
        vboxMergeDirective.addWidget(patch_check)
        
        gbAction = QtGui.QGroupBox(gettext("Action"), self)
        vboxAction = QtGui.QVBoxLayout(gbAction)
        
        submit_email_radio = QtGui.QRadioButton("Send e-mail")
        submit_email_radio.toggle()
        self.submit_email_radio = submit_email_radio
        vboxAction.addWidget(submit_email_radio)
        
        mailto_hbox = QtGui.QHBoxLayout()
        
        mailto_label = QtGui.QLabel(gettext("Address:"))
        mailto_edit = QtGui.QLineEdit()
        self.mailto_edit = mailto_edit
        mailto_hbox.insertSpacing(0,50)
        mailto_hbox.addWidget(mailto_label)
        mailto_hbox.addWidget(mailto_edit)
        
        vboxAction.addLayout(mailto_hbox)
        
        message_hbox = QtGui.QHBoxLayout()
        message_label = QtGui.QLabel(gettext("Message:"))
        message_edit = QtGui.QLineEdit()
        self.message_edit = message_edit
        
        message_hbox.insertSpacing(0,50)
        message_hbox.addWidget(message_label)
        message_hbox.addWidget(message_edit)

        vboxAction.addLayout(message_hbox)
        
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
                
        revisions_hbox = QtGui.QHBoxLayout()
        revisions_label = QtGui.QLabel(gettext("Revisions:"))
        revisions_edit = QtGui.QLineEdit()
        self.revisions_edit = revisions_edit
        
        revisions_hbox.addWidget(revisions_label)
        revisions_hbox.addWidget(revisions_edit)

        vboxAction.addLayout(revisions_hbox)
        
        layout = QtGui.QVBoxLayout(self)
        
        self.splitter = QtGui.QSplitter(QtCore.Qt.Vertical)
        self.splitter.addWidget(gbAction)
        self.splitter.addWidget(gbMergeDirective)
        
        self.splitter.addWidget(self.make_default_status_box())
        
        self.splitter.setStretchFactor(0, 10)
        self.restoreSplitterSizes([150, 150])
        
        layout.addWidget(self.splitter)
        layout.addWidget(self.buttonbox)
       
    def savefile_button_clicked(self):
        fileName = QtGui.QFileDialog.getSaveFileName(self, ("Select save location"));
        if fileName != '':
            self.savefile_edit.setText(fileName)
                
    def browse_submit_clicked(self):
        fileName = QtGui.QFileDialog.getExistingDirectory(self, ("Select Submit branch"));
        if fileName != '':
            self.submit_branch_combo.insertItem(0,fileName)
            self.submit_branch_combo.setCurrentIndex(0)

    def browse_public_clicked(self):
        fileName = QtGui.QFileDialog.getExistingDirectory(self, ("Select Public branch"));
        if fileName != '':
            self.public_branch_combo.insertItem(0,fileName)
            self.public_branch_combo.setCurrentIndex(0)

    def validate(self):
        if self.submit_email_radio.isChecked():
            location = str(self.mailto_edit.text())
            if not location:
                self.mailto_edit.setFocus()
                self.operation_blocked(gettext("Email address not entered."))
                return False
            if re.match("^.+\\@(\\[?)[a-zA-Z0-9\\-\\.]+\\.([a-zA-Z]{2,3}|[0-9]{1,3})(\\]?)$", location) is None:
                self.mailto_edit.setFocus()
                self.operation_blocked(gettext("Email address is not valid."))
                return False
        else:
            location = unicode(self.savefile_edit.text())
            if not location:
                self.savefile_edit.setFocus()
                self.operation_blocked(gettext("Filename not entered."))
                return False

        submit_branch = unicode(self.submit_branch_combo.currentText())
        if not submit_branch:
            self.submit_branch_combo.setFocus()
            self.operation_blocked(gettext("No submit branch entered."))
            return False
        return True

    def do_start(self):
        args = []
        submit_branch = unicode(self.submit_branch_combo.currentText())
        public_branch = unicode(self.public_branch_combo.currentText())
        
        if public_branch:
            args.append(public_branch)

        mylocation = url_for_display(self.branch.base)
        args.append("-f")
        args.append(mylocation)

        if self.submit_email_radio.isChecked():
            location = str(self.mailto_edit.text())
            args.append("--mail-to=%s" % location)
        else:
            location = unicode(self.savefile_edit.text())
            args.append("-o")
            args.append(location)

        if self.remember_check.isChecked():
            args.append("--remember")

        if not self.patch_check.isChecked():
            args.append("--no-patch")

        if not self.bundle_check.isChecked():
            args.append("--no-bundle")

        if unicode(self.message_edit.text()):
            args.append("--message=%s" % unicode(self.message_edit.text()))

        revision = str(self.revisions_edit.text())
        if revision == '':
            args.append("--revision=-1")
        else:
            args.append("--revision=%s" % revision)

        self.process_widget.do_start(None, 'send', submit_branch, *args)

    def _saveSize(self, config):
        SubProcessDialog._saveSize(self, config)
        self._saveSplitterSizes(config, self.splitter)
