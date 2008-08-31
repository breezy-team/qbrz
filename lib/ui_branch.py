# -*- coding: utf-8 -*-

# Form implementation generated from reading ui file 'ui/branch.ui'
#
# Created: Wed Jul 30 14:20:50 2008
#      by: PyQt4 UI code generator 4.4.2
#
# WARNING! All changes made in this file will be lost!

from PyQt4 import QtCore, QtGui
from bzrlib.plugins.qbzr.lib.i18n import gettext


class Ui_BranchForm(object):
    def setupUi(self, BranchForm):
        BranchForm.setObjectName("BranchForm")
        BranchForm.resize(420,112)
        self.gridLayout = QtGui.QGridLayout(BranchForm)
        self.gridLayout.setObjectName("gridLayout")
        self.label_2 = QtGui.QLabel(BranchForm)
        self.label_2.setObjectName("label_2")
        self.gridLayout.addWidget(self.label_2,0,0,1,1)
        self.from_location = QtGui.QComboBox(BranchForm)
        self.from_location.setEditable(True)
        self.from_location.setSizeAdjustPolicy(QtGui.QComboBox.AdjustToMinimumContentsLength)
        self.from_location.setObjectName("from_location")
        self.gridLayout.addWidget(self.from_location,0,1,1,2)
        self.from_picker = QtGui.QPushButton(BranchForm)
        self.from_picker.setObjectName("from_picker")
        self.gridLayout.addWidget(self.from_picker,0,3,1,1)
        self.label_3 = QtGui.QLabel(BranchForm)
        self.label_3.setObjectName("label_3")
        self.gridLayout.addWidget(self.label_3,1,0,1,1)
        self.revision = QtGui.QLineEdit(BranchForm)
        self.revision.setObjectName("revision")
        self.gridLayout.addWidget(self.revision,1,1,1,1)
        spacerItem = QtGui.QSpacerItem(211,20,QtGui.QSizePolicy.Expanding,QtGui.QSizePolicy.Minimum)
        self.gridLayout.addItem(spacerItem,1,2,1,2)
        self.label_4 = QtGui.QLabel(BranchForm)
        self.label_4.setObjectName("label_4")
        self.gridLayout.addWidget(self.label_4,2,0,1,1)
        self.to_location = QtGui.QComboBox(BranchForm)
        self.to_location.setEditable(True)
        self.to_location.setSizeAdjustPolicy(QtGui.QComboBox.AdjustToMinimumContentsLength)
        self.to_location.setObjectName("to_location")
        self.gridLayout.addWidget(self.to_location,2,1,1,2)
        self.to_picker = QtGui.QPushButton(BranchForm)
        self.to_picker.setObjectName("to_picker")
        self.gridLayout.addWidget(self.to_picker,2,3,1,1)
        self.label_2.setBuddy(self.from_location)
        self.label_3.setBuddy(self.revision)
        self.label_4.setBuddy(self.to_location)

        self.retranslateUi(BranchForm)
        QtCore.QMetaObject.connectSlotsByName(BranchForm)

    def retranslateUi(self, BranchForm):
        BranchForm.setTitle(gettext("Options"))
        self.label_2.setText(gettext("&Location:"))
        self.from_picker.setText(gettext("Browse..."))
        self.label_3.setText(gettext("&Revision:"))
        self.label_4.setText(gettext("&To:"))
        self.to_picker.setText(gettext("Browse..."))

