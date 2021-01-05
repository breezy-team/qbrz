# -*- coding: utf-8 -*-

# Form implementation generated from reading ui file 'ui/update_branch.ui'
#
# Created by: PyQt4 UI code generator 4.12.3
#
# WARNING! All changes made in this file will be lost!

from PyQt5 import QtCore, QtGui, QtWidgets

try:
    _encoding = QtWidgets.QApplication.UnicodeUTF8
    def _translate(context, text, disambig):
        return QtCore.QCoreApplication.translate(context, text, disambig, _encoding)
except AttributeError:
    def _translate(context, text, disambig):
        return QtCore.QCoreApplication.translate(context, text, disambig)

class Ui_UpdateBranchForm(object):
    def setupUi(self, UpdateBranchForm):
        UpdateBranchForm.setObjectName("UpdateBranchForm")
        UpdateBranchForm.resize(407, 198)
        self.verticalLayout_3 = QtWidgets.QVBoxLayout(UpdateBranchForm)
        self.verticalLayout_3.setContentsMargins(9, 9, 9, 9)
        self.verticalLayout_3.setObjectName("verticalLayout_3")
        self.label = QtWidgets.QLabel(UpdateBranchForm)
        self.label.setScaledContents(False)
        self.label.setWordWrap(False)
        self.label.setObjectName("label")
        self.verticalLayout_3.addWidget(self.label)
        self.groupBox = QtWidgets.QGroupBox(UpdateBranchForm)
        sizePolicy = QtWidgets.QSizePolicy(QtWidgets.QSizePolicy.Preferred, QtWidgets.QSizePolicy.Preferred)
        sizePolicy.setHorizontalStretch(0)
        sizePolicy.setVerticalStretch(1)
        sizePolicy.setHeightForWidth(self.groupBox.sizePolicy().hasHeightForWidth())
        self.groupBox.setSizePolicy(sizePolicy)
        self.groupBox.setObjectName("groupBox")
        self.gridLayout = QtWidgets.QGridLayout(self.groupBox)
        self.gridLayout.setObjectName("gridLayout")
        self.location_picker = QtWidgets.QPushButton(self.groupBox)
        self.location_picker.setObjectName("location_picker")
        self.gridLayout.addWidget(self.location_picker, 1, 2, 1, 1)
        self.but_pull = QtWidgets.QRadioButton(self.groupBox)
        self.but_pull.setChecked(True)
        self.but_pull.setObjectName("but_pull")
        self.gridLayout.addWidget(self.but_pull, 0, 0, 1, 3)
        self.but_pull_remember = QtWidgets.QCheckBox(self.groupBox)
        self.but_pull_remember.setEnabled(True)
        self.but_pull_remember.setChecked(False)
        self.but_pull_remember.setObjectName("but_pull_remember")
        self.gridLayout.addWidget(self.but_pull_remember, 2, 1, 1, 2)
        self.but_pull_overwrite = QtWidgets.QCheckBox(self.groupBox)
        self.but_pull_overwrite.setObjectName("but_pull_overwrite")
        self.gridLayout.addWidget(self.but_pull_overwrite, 3, 1, 1, 2)
        spacerItem = QtWidgets.QSpacerItem(17, 18, QtWidgets.QSizePolicy.Fixed, QtWidgets.QSizePolicy.Minimum)
        self.gridLayout.addItem(spacerItem, 3, 0, 1, 1)
        self.location = QtWidgets.QComboBox(self.groupBox)
        sizePolicy = QtWidgets.QSizePolicy(QtWidgets.QSizePolicy.Preferred, QtWidgets.QSizePolicy.Fixed)
        sizePolicy.setHorizontalStretch(1)
        sizePolicy.setVerticalStretch(0)
        sizePolicy.setHeightForWidth(self.location.sizePolicy().hasHeightForWidth())
        self.location.setSizePolicy(sizePolicy)
        self.location.setEditable(True)
        self.location.setSizeAdjustPolicy(QtWidgets.QComboBox.AdjustToMinimumContentsLength)
        self.location.setObjectName("location")
        self.location.addItem("")
        self.gridLayout.addWidget(self.location, 1, 1, 1, 1)
        spacerItem1 = QtWidgets.QSpacerItem(18, 20, QtWidgets.QSizePolicy.Expanding, QtWidgets.QSizePolicy.Minimum)
        self.gridLayout.addItem(spacerItem1, 1, 0, 1, 1)
        spacerItem2 = QtWidgets.QSpacerItem(18, 17, QtWidgets.QSizePolicy.Expanding, QtWidgets.QSizePolicy.Minimum)
        self.gridLayout.addItem(spacerItem2, 2, 0, 1, 1)
        self.but_update = QtWidgets.QRadioButton(self.groupBox)
        self.but_update.setObjectName("but_update")
        self.gridLayout.addWidget(self.but_update, 4, 0, 1, 3)
        self.location_picker.raise_()
        self.but_pull.raise_()
        self.but_pull_remember.raise_()
        self.but_pull_overwrite.raise_()
        self.location.raise_()
        self.but_update.raise_()
        self.verticalLayout_3.addWidget(self.groupBox)

        self.retranslateUi(UpdateBranchForm)
        self.but_pull.toggled[bool].connect(self.but_pull_remember.setEnabled)
        self.but_pull.toggled[bool].connect(self.but_pull_overwrite.setEnabled)
        self.but_pull.toggled[bool].connect(self.location.setEnabled)
        self.but_pull.toggled[bool].connect(self.location_picker.setEnabled)
        UpdateBranchForm.disableUi[bool].connect(self.label.setDisabled)
        UpdateBranchForm.disableUi[bool].connect(self.groupBox.setDisabled)
        QtCore.QMetaObject.connectSlotsByName(UpdateBranchForm)

    def retranslateUi(self, UpdateBranchForm):
        UpdateBranchForm.setWindowTitle(_translate("UpdateBranchForm", "Update Branch", None))
        self.label.setText(_translate("UpdateBranchForm", "This directory is a branch.  Please select what you would like to update", None))
        self.groupBox.setTitle(_translate("UpdateBranchForm", "Update source", None))
        self.location_picker.setText(_translate("UpdateBranchForm", "Browse...", None))
        self.but_pull.setText(_translate("UpdateBranchForm", "Pull most recent changes from:", None))
        self.but_pull_remember.setText(_translate("UpdateBranchForm", "Remember this as the new parent branch", None))
        self.but_pull_overwrite.setText(_translate("UpdateBranchForm", "Overwrite differences between branches", None))
        self.location.setItemText(0, _translate("UpdateBranchForm", "<Parent Branch shown here>", None))
        self.but_update.setText(_translate("UpdateBranchForm", "Update working tree to the latest changes in the branch", None))

