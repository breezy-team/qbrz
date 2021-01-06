# -*- coding: utf-8 -*-

# Form implementation generated from reading ui file 'ui/branch.ui'
#
# Created by: PyQt5 UI code generator 5.12.3
#
# WARNING! All changes made in this file will be lost!


from PyQt5 import QtCore, QtGui, QtWidgets
from breezy.plugins.qbrz.lib.i18n import gettext



class Ui_BranchForm(object):
    def setupUi(self, BranchForm):
        BranchForm.setObjectName("BranchForm")
        BranchForm.resize(349, 245)
        self.verticalLayout = QtWidgets.QVBoxLayout(BranchForm)
        self.verticalLayout.setObjectName("verticalLayout")
        self.groupBox = QtWidgets.QGroupBox(BranchForm)
        self.groupBox.setObjectName("groupBox")
        self.formLayout = QtWidgets.QFormLayout(self.groupBox)
        self.formLayout.setFieldGrowthPolicy(QtWidgets.QFormLayout.AllNonFixedFieldsGrow)
        self.formLayout.setObjectName("formLayout")
        self.from_label = QtWidgets.QLabel(self.groupBox)
        self.from_label.setObjectName("from_label")
        self.formLayout.setWidget(0, QtWidgets.QFormLayout.LabelRole, self.from_label)
        self.horizontalLayout_2 = QtWidgets.QHBoxLayout()
        self.horizontalLayout_2.setObjectName("horizontalLayout_2")
        self.from_location = QtWidgets.QComboBox(self.groupBox)
        sizePolicy = QtWidgets.QSizePolicy(QtWidgets.QSizePolicy.MinimumExpanding, QtWidgets.QSizePolicy.Fixed)
        sizePolicy.setHorizontalStretch(0)
        sizePolicy.setVerticalStretch(0)
        sizePolicy.setHeightForWidth(self.from_location.sizePolicy().hasHeightForWidth())
        self.from_location.setSizePolicy(sizePolicy)
        self.from_location.setEditable(True)
        self.from_location.setSizeAdjustPolicy(QtWidgets.QComboBox.AdjustToContentsOnFirstShow)
        self.from_location.setObjectName("from_location")
        self.horizontalLayout_2.addWidget(self.from_location)
        self.from_picker = QtWidgets.QPushButton(self.groupBox)
        self.from_picker.setObjectName("from_picker")
        self.horizontalLayout_2.addWidget(self.from_picker)
        self.horizontalLayout_2.setStretch(0, 1)
        self.formLayout.setLayout(0, QtWidgets.QFormLayout.FieldRole, self.horizontalLayout_2)
        self.to_label = QtWidgets.QLabel(self.groupBox)
        self.to_label.setObjectName("to_label")
        self.formLayout.setWidget(1, QtWidgets.QFormLayout.LabelRole, self.to_label)
        self.horizontalLayout_3 = QtWidgets.QHBoxLayout()
        self.horizontalLayout_3.setObjectName("horizontalLayout_3")
        self.to_location = QtWidgets.QComboBox(self.groupBox)
        sizePolicy = QtWidgets.QSizePolicy(QtWidgets.QSizePolicy.MinimumExpanding, QtWidgets.QSizePolicy.Fixed)
        sizePolicy.setHorizontalStretch(0)
        sizePolicy.setVerticalStretch(0)
        sizePolicy.setHeightForWidth(self.to_location.sizePolicy().hasHeightForWidth())
        self.to_location.setSizePolicy(sizePolicy)
        self.to_location.setEditable(True)
        self.to_location.setSizeAdjustPolicy(QtWidgets.QComboBox.AdjustToContentsOnFirstShow)
        self.to_location.setObjectName("to_location")
        self.horizontalLayout_3.addWidget(self.to_location)
        self.to_picker = QtWidgets.QPushButton(self.groupBox)
        self.to_picker.setObjectName("to_picker")
        self.horizontalLayout_3.addWidget(self.to_picker)
        self.horizontalLayout_3.setStretch(0, 1)
        self.formLayout.setLayout(1, QtWidgets.QFormLayout.FieldRole, self.horizontalLayout_3)
        self.verticalLayout.addWidget(self.groupBox)
        self.groupBox_2 = QtWidgets.QGroupBox(BranchForm)
        self.groupBox_2.setObjectName("groupBox_2")
        self.verticalLayout_2 = QtWidgets.QVBoxLayout(self.groupBox_2)
        self.verticalLayout_2.setObjectName("verticalLayout_2")
        self.bind = QtWidgets.QCheckBox(self.groupBox_2)
        self.bind.setObjectName("bind")
        self.verticalLayout_2.addWidget(self.bind)
        self.horizontalLayout = QtWidgets.QHBoxLayout()
        self.horizontalLayout.setObjectName("horizontalLayout")
        self.revision_label = QtWidgets.QLabel(self.groupBox_2)
        self.revision_label.setObjectName("revision_label")
        self.horizontalLayout.addWidget(self.revision_label)
        self.revision = QtWidgets.QLineEdit(self.groupBox_2)
        self.revision.setObjectName("revision")
        self.horizontalLayout.addWidget(self.revision)
        spacerItem = QtWidgets.QSpacerItem(78, 37, QtWidgets.QSizePolicy.Expanding, QtWidgets.QSizePolicy.Minimum)
        self.horizontalLayout.addItem(spacerItem)
        self.verticalLayout_2.addLayout(self.horizontalLayout)
        self.verticalLayout.addWidget(self.groupBox_2)
        self.from_label.setBuddy(self.from_location)
        self.to_label.setBuddy(self.to_location)
        self.revision_label.setBuddy(self.revision)

        self.retranslateUi(BranchForm)
        BranchForm.disableUi['bool'].connect(self.groupBox.setDisabled)
        QtCore.QMetaObject.connectSlotsByName(BranchForm)

    def retranslateUi(self, BranchForm):
        _translate = QtCore.QCoreApplication.translate
        BranchForm.setWindowTitle(_translate("BranchForm", "Branch"))
        self.groupBox.setTitle(_translate("BranchForm", "Locations"))
        self.from_label.setText(_translate("BranchForm", "&From:"))
        self.from_picker.setText(_translate("BranchForm", "Browse..."))
        self.to_label.setText(_translate("BranchForm", "&To:"))
        self.to_picker.setText(_translate("BranchForm", "Browse..."))
        self.groupBox_2.setTitle(_translate("BranchForm", "Options"))
        self.bind.setText(_translate("BranchForm", "Bind new branch to parent location"))
        self.revision_label.setText(_translate("BranchForm", "&Revision:"))
