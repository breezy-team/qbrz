# -*- coding: utf-8 -*-

# Form implementation generated from reading ui file 'ui/branch.ui'
#
# Created: Thu Sep 18 20:58:12 2008
#      by: PyQt4 UI code generator 4.4.2
#
# WARNING! All changes made in this file will be lost!

from PyQt4 import QtCore, QtGui
from bzrlib.plugins.qbzr.lib.i18n import gettext


class Ui_BranchForm(object):
    def setupUi(self, BranchForm):
        BranchForm.setObjectName("BranchForm")
        BranchForm.resize(349, 130)
        self.verticalLayout = QtGui.QVBoxLayout(BranchForm)
        self.verticalLayout.setMargin(9)
        self.verticalLayout.setObjectName("verticalLayout")
        self.groupBox = QtGui.QGroupBox(BranchForm)
        self.groupBox.setObjectName("groupBox")
        self.gridLayout = QtGui.QGridLayout(self.groupBox)
        self.gridLayout.setObjectName("gridLayout")
        self.label_2 = QtGui.QLabel(self.groupBox)
        self.label_2.setObjectName("label_2")
        self.gridLayout.addWidget(self.label_2, 0, 0, 1, 1)
        self.from_location = QtGui.QComboBox(self.groupBox)
        self.from_location.setEditable(True)
        self.from_location.setSizeAdjustPolicy(QtGui.QComboBox.AdjustToMinimumContentsLength)
        self.from_location.setObjectName("from_location")
        self.gridLayout.addWidget(self.from_location, 0, 1, 1, 2)
        self.from_picker = QtGui.QPushButton(self.groupBox)
        self.from_picker.setObjectName("from_picker")
        self.gridLayout.addWidget(self.from_picker, 0, 3, 1, 1)
        self.label_3 = QtGui.QLabel(self.groupBox)
        self.label_3.setObjectName("label_3")
        self.gridLayout.addWidget(self.label_3, 1, 0, 1, 1)
        self.revision = QtGui.QLineEdit(self.groupBox)
        self.revision.setObjectName("revision")
        self.gridLayout.addWidget(self.revision, 1, 1, 1, 1)
        spacerItem = QtGui.QSpacerItem(83, 20, QtGui.QSizePolicy.Expanding, QtGui.QSizePolicy.Minimum)
        self.gridLayout.addItem(spacerItem, 1, 2, 1, 2)
        self.label_4 = QtGui.QLabel(self.groupBox)
        self.label_4.setObjectName("label_4")
        self.gridLayout.addWidget(self.label_4, 2, 0, 1, 1)
        self.to_location = QtGui.QComboBox(self.groupBox)
        self.to_location.setEditable(True)
        self.to_location.setSizeAdjustPolicy(QtGui.QComboBox.AdjustToMinimumContentsLength)
        self.to_location.setObjectName("to_location")
        self.gridLayout.addWidget(self.to_location, 2, 1, 1, 2)
        self.to_picker = QtGui.QPushButton(self.groupBox)
        self.to_picker.setObjectName("to_picker")
        self.gridLayout.addWidget(self.to_picker, 2, 3, 1, 1)
        self.verticalLayout.addWidget(self.groupBox)
        self.label_2.setBuddy(self.from_location)
        self.label_3.setBuddy(self.revision)
        self.label_4.setBuddy(self.to_location)

        self.retranslateUi(BranchForm)
        QtCore.QMetaObject.connectSlotsByName(BranchForm)

    def retranslateUi(self, BranchForm):
        BranchForm.setWindowTitle(gettext("Branch"))
        self.groupBox.setTitle(gettext("Options"))
        self.label_2.setText(gettext("&Location:"))
        self.from_picker.setText(gettext("Browse..."))
        self.label_3.setText(gettext("&Revision:"))
        self.label_4.setText(gettext("&To:"))
        self.to_picker.setText(gettext("Browse..."))

