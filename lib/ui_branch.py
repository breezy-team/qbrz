# -*- coding: utf-8 -*-

# Form implementation generated from reading ui file 'ui/branch.ui'
#
# Created: Wed Mar 23 17:07:09 2011
#      by: PyQt4 UI code generator 4.8.2
#
# WARNING! All changes made in this file will be lost!

from PyQt4 import QtCore, QtGui
from bzrlib.plugins.qbzr.lib.i18n import gettext


try:
    _fromUtf8 = QtCore.QString.fromUtf8
except AttributeError:
    _fromUtf8 = lambda s: s

class Ui_BranchForm(object):
    def setupUi(self, BranchForm):
        BranchForm.setObjectName(_fromUtf8("BranchForm"))
        BranchForm.resize(349, 245)
        self.verticalLayout = QtGui.QVBoxLayout(BranchForm)
        self.verticalLayout.setObjectName(_fromUtf8("verticalLayout"))
        self.groupBox = QtGui.QGroupBox(BranchForm)
        self.groupBox.setObjectName(_fromUtf8("groupBox"))
        self.formLayout = QtGui.QFormLayout(self.groupBox)
        self.formLayout.setFieldGrowthPolicy(QtGui.QFormLayout.AllNonFixedFieldsGrow)
        self.formLayout.setObjectName(_fromUtf8("formLayout"))
        self.from_label = QtGui.QLabel(self.groupBox)
        self.from_label.setObjectName(_fromUtf8("from_label"))
        self.formLayout.setWidget(0, QtGui.QFormLayout.LabelRole, self.from_label)
        self.horizontalLayout_2 = QtGui.QHBoxLayout()
        self.horizontalLayout_2.setObjectName(_fromUtf8("horizontalLayout_2"))
        self.from_location = QtGui.QComboBox(self.groupBox)
        sizePolicy = QtGui.QSizePolicy(QtGui.QSizePolicy.MinimumExpanding, QtGui.QSizePolicy.Fixed)
        sizePolicy.setHorizontalStretch(0)
        sizePolicy.setVerticalStretch(0)
        sizePolicy.setHeightForWidth(self.from_location.sizePolicy().hasHeightForWidth())
        self.from_location.setSizePolicy(sizePolicy)
        self.from_location.setEditable(True)
        self.from_location.setSizeAdjustPolicy(QtGui.QComboBox.AdjustToContentsOnFirstShow)
        self.from_location.setObjectName(_fromUtf8("from_location"))
        self.horizontalLayout_2.addWidget(self.from_location)
        self.from_picker = QtGui.QPushButton(self.groupBox)
        self.from_picker.setObjectName(_fromUtf8("from_picker"))
        self.horizontalLayout_2.addWidget(self.from_picker)
        self.horizontalLayout_2.setStretch(0, 1)
        self.formLayout.setLayout(0, QtGui.QFormLayout.FieldRole, self.horizontalLayout_2)
        self.to_label = QtGui.QLabel(self.groupBox)
        self.to_label.setObjectName(_fromUtf8("to_label"))
        self.formLayout.setWidget(1, QtGui.QFormLayout.LabelRole, self.to_label)
        self.horizontalLayout_3 = QtGui.QHBoxLayout()
        self.horizontalLayout_3.setObjectName(_fromUtf8("horizontalLayout_3"))
        self.to_location = QtGui.QComboBox(self.groupBox)
        sizePolicy = QtGui.QSizePolicy(QtGui.QSizePolicy.MinimumExpanding, QtGui.QSizePolicy.Fixed)
        sizePolicy.setHorizontalStretch(0)
        sizePolicy.setVerticalStretch(0)
        sizePolicy.setHeightForWidth(self.to_location.sizePolicy().hasHeightForWidth())
        self.to_location.setSizePolicy(sizePolicy)
        self.to_location.setEditable(True)
        self.to_location.setSizeAdjustPolicy(QtGui.QComboBox.AdjustToContentsOnFirstShow)
        self.to_location.setObjectName(_fromUtf8("to_location"))
        self.horizontalLayout_3.addWidget(self.to_location)
        self.to_picker = QtGui.QPushButton(self.groupBox)
        self.to_picker.setObjectName(_fromUtf8("to_picker"))
        self.horizontalLayout_3.addWidget(self.to_picker)
        self.horizontalLayout_3.setStretch(0, 1)
        self.formLayout.setLayout(1, QtGui.QFormLayout.FieldRole, self.horizontalLayout_3)
        self.verticalLayout.addWidget(self.groupBox)
        self.groupBox_2 = QtGui.QGroupBox(BranchForm)
        self.groupBox_2.setObjectName(_fromUtf8("groupBox_2"))
        self.verticalLayout_2 = QtGui.QVBoxLayout(self.groupBox_2)
        self.verticalLayout_2.setObjectName(_fromUtf8("verticalLayout_2"))
        self.bind = QtGui.QCheckBox(self.groupBox_2)
        self.bind.setObjectName(_fromUtf8("bind"))
        self.verticalLayout_2.addWidget(self.bind)
        self.horizontalLayout = QtGui.QHBoxLayout()
        self.horizontalLayout.setObjectName(_fromUtf8("horizontalLayout"))
        self.revision_label = QtGui.QLabel(self.groupBox_2)
        self.revision_label.setObjectName(_fromUtf8("revision_label"))
        self.horizontalLayout.addWidget(self.revision_label)
        self.revision = QtGui.QLineEdit(self.groupBox_2)
        self.revision.setObjectName(_fromUtf8("revision"))
        self.horizontalLayout.addWidget(self.revision)
        spacerItem = QtGui.QSpacerItem(78, 37, QtGui.QSizePolicy.Expanding, QtGui.QSizePolicy.Minimum)
        self.horizontalLayout.addItem(spacerItem)
        self.verticalLayout_2.addLayout(self.horizontalLayout)
        self.verticalLayout.addWidget(self.groupBox_2)
        self.from_label.setBuddy(self.from_location)
        self.to_label.setBuddy(self.to_location)
        self.revision_label.setBuddy(self.revision)

        self.retranslateUi(BranchForm)
        QtCore.QObject.connect(BranchForm, QtCore.SIGNAL(_fromUtf8("disableUi(bool)")), self.groupBox.setDisabled)
        QtCore.QMetaObject.connectSlotsByName(BranchForm)

    def retranslateUi(self, BranchForm):
        BranchForm.setWindowTitle(gettext("Branch"))
        self.groupBox.setTitle(gettext("Locations"))
        self.from_label.setText(gettext("&From:"))
        self.from_picker.setText(gettext("Browse..."))
        self.to_label.setText(gettext("&To:"))
        self.to_picker.setText(gettext("Browse..."))
        self.groupBox_2.setTitle(gettext("Options"))
        self.bind.setText(gettext("Bind new branch to parent location"))
        self.revision_label.setText(gettext("&Revision:"))

