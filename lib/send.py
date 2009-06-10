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
            
        groupbox = QtGui.QGroupBox(gettext("Branch to submit:")+str(branch), self)
        vbox = QtGui.QVBoxLayout(groupbox)
        vbox.addStrut(0)
    
        
        self.branch = branch
        
        target_hbox = QtGui.QHBoxLayout()
        
        target_branch_label = QtGui.QLabel(gettext("Target Branch:"))
        target_branch_combo = QtGui.QComboBox()
        self.target_branch_combo = target_branch_combo
        target_branch_combo.setEditable(True)
        target_hbox.addWidget(target_branch_label)
        target_hbox.addWidget(target_branch_combo)
        
        target_hbox.setStretchFactor(target_branch_combo,1)
        
        vbox.addLayout(target_hbox)
        
        
        groupbox_submit = QtGui.QGroupBox(gettext("Enter submit location:"))
        hbox_submit = QtGui.QHBoxLayout(groupbox_submit)
        vbox.addWidget(groupbox_submit)
        
        
        submit_email_radio = QtGui.QRadioButton("Send to email")
        self.submit_email_radio = submit_email_radio
        submit_email_radio.toggle()
        
        
        location_save_radio = QtGui.QRadioButton("Save to location")
        self.location_save_radio = location_save_radio
        
        
        
        hbox_submit.addWidget(submit_email_radio)
        hbox_submit.addWidget(location_save_radio)
        hbox_submit.setStretchFactor(submit_email_radio,0)
        hbox_submit.setStretchFactor(location_save_radio,1)
        
        
        hbox_location_edit = QtGui.QHBoxLayout()
        
        submit_location_edit = QtGui.QLineEdit()
        hbox_location_edit.addWidget(submit_location_edit)
        self.browse_location_button = QtGui.QPushButton("Browse")
        
        self.sendtype_presed() # to set the browse button disabled as default
        
        hbox_location_edit.addWidget(self.browse_location_button)
        
        self.submit_location_edit = submit_location_edit

        vbox.addLayout(hbox_location_edit)
        
        label_message = QtGui.QLabel(gettext("Message:"))
        vbox.addWidget(label_message)
        self.message_edit = QtGui.QLineEdit()
        vbox.addWidget(self.message_edit)
        
        
        
        
        
        options_group = QtGui.QGroupBox("Options")
        vbox.addWidget(options_group)
        options_vbox = QtGui.QHBoxLayout(options_group)
        
        self.remember_check = QtGui.QCheckBox("Remember")
        options_vbox.addWidget(self.remember_check)
        options_vbox.setStretchFactor(self.remember_check,0)

        self.nobundle_check = QtGui.QCheckBox("No bundle")
        options_vbox.addWidget(self.nobundle_check)
        options_vbox.setStretchFactor(self.nobundle_check,0)
        
        self.nopatch_check = QtGui.QCheckBox("No patch")
        options_vbox.addWidget(self.nopatch_check)
        options_vbox.setStretchFactor(self.nopatch_check,1)

        # groupbox gets disabled as we are executing.
        QtCore.QObject.connect(self,
                               QtCore.SIGNAL("subprocessStarted(bool)"),
                               vbox,
                               QtCore.SLOT("setDisabled(bool)"))
        
        # connect submit type to enable/disable browse button.
        QtCore.QObject.connect(self.submit_email_radio, QtCore.SIGNAL("toggled(bool)"), self.sendtype_presed)
        
        # connect "browse" button with dialog
        QtCore.QObject.connect(self.browse_location_button, QtCore.SIGNAL("clicked(bool)"), self.browse_location_clicked)

        self.splitter = QtGui.QSplitter(QtCore.Qt.Vertical)
        self.splitter.addWidget(groupbox)
        #self.splitter.addWidget(self.make_default_status_box())
        
        self.splitter.setStretchFactor(0, 10)
        self.restoreSplitterSizes([150, 150])
        
        
        layout = QtGui.QVBoxLayout(self)
        #layout.addWidget(vbox)
        layout.addWidget(self.splitter)
        layout.addWidget(self.buttonbox)

    
    def sendtype_presed(self):
        if self.submit_email_radio.isChecked():
            self.browse_location_button.setDisabled(True)
        else:
            self.browse_location_button.setDisabled(False)
        
    def browse_location_clicked(self):
        fileName = QtGui.QFileDialog.getSaveFileName(self, ("Select destination"));
        self.submit_location_edit.setText(fileName)
        
    def start(self):        
        
        
        
     
     
        target_branch = str(self.target_branch_combo.currentText())
        location = str(self.submit_location_edit.text())
        
        if target_branch == '':
            pass
            # error
        
        if location == '':
            pass
            # error
            
            
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
