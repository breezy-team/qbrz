# -*- coding: utf-8 -*-

# Form implementation generated from reading ui file 'ui/update_branch.ui'
#
# Created by: PyQt4 UI code generator 4.12.3
#
# WARNING! All changes made in this file will be lost!

from PyQt4 import QtCore, QtGui

try:
    _fromUtf8 = QtCore.QString.fromUtf8
except AttributeError:
    def _fromUtf8(s):
        return s

try:
    _encoding = QtGui.QApplication.UnicodeUTF8
    def _translate(context, text, disambig):
        return QtGui.QApplication.translate(context, text, disambig, _encoding)
except AttributeError:
    def _translate(context, text, disambig):
        return QtGui.QApplication.translate(context, text, disambig)

class Ui_UpdateBranchForm(object):
    def setupUi(self, UpdateBranchForm):
        UpdateBranchForm.setObjectName(_fromUtf8("UpdateBranchForm"))
        UpdateBranchForm.resize(407, 198)
        self.verticalLayout_3 = QtGui.QVBoxLayout(UpdateBranchForm)
        self.verticalLayout_3.setMargin(9)
        self.verticalLayout_3.setObjectName(_fromUtf8("verticalLayout_3"))
        self.label = QtGui.QLabel(UpdateBranchForm)
        self.label.setScaledContents(False)
        self.label.setWordWrap(False)
        self.label.setObjectName(_fromUtf8("label"))
        self.verticalLayout_3.addWidget(self.label)
        self.groupBox = QtGui.QGroupBox(UpdateBranchForm)
        sizePolicy = QtGui.QSizePolicy(QtGui.QSizePolicy.Preferred, QtGui.QSizePolicy.Preferred)
        sizePolicy.setHorizontalStretch(0)
        sizePolicy.setVerticalStretch(1)
        sizePolicy.setHeightForWidth(self.groupBox.sizePolicy().hasHeightForWidth())
        self.groupBox.setSizePolicy(sizePolicy)
        self.groupBox.setObjectName(_fromUtf8("groupBox"))
        self.gridLayout = QtGui.QGridLayout(self.groupBox)
        self.gridLayout.setObjectName(_fromUtf8("gridLayout"))
        self.location_picker = QtGui.QPushButton(self.groupBox)
        self.location_picker.setObjectName(_fromUtf8("location_picker"))
        self.gridLayout.addWidget(self.location_picker, 1, 2, 1, 1)
        self.but_pull = QtGui.QRadioButton(self.groupBox)
        self.but_pull.setChecked(True)
        self.but_pull.setObjectName(_fromUtf8("but_pull"))
        self.gridLayout.addWidget(self.but_pull, 0, 0, 1, 3)
        self.but_pull_remember = QtGui.QCheckBox(self.groupBox)
        self.but_pull_remember.setEnabled(True)
        self.but_pull_remember.setChecked(False)
        self.but_pull_remember.setObjectName(_fromUtf8("but_pull_remember"))
        self.gridLayout.addWidget(self.but_pull_remember, 2, 1, 1, 2)
        self.but_pull_overwrite = QtGui.QCheckBox(self.groupBox)
        self.but_pull_overwrite.setObjectName(_fromUtf8("but_pull_overwrite"))
        self.gridLayout.addWidget(self.but_pull_overwrite, 3, 1, 1, 2)
        spacerItem = QtGui.QSpacerItem(17, 18, QtGui.QSizePolicy.Fixed, QtGui.QSizePolicy.Minimum)
        self.gridLayout.addItem(spacerItem, 3, 0, 1, 1)
        self.location = QtGui.QComboBox(self.groupBox)
        sizePolicy = QtGui.QSizePolicy(QtGui.QSizePolicy.Preferred, QtGui.QSizePolicy.Fixed)
        sizePolicy.setHorizontalStretch(1)
        sizePolicy.setVerticalStretch(0)
        sizePolicy.setHeightForWidth(self.location.sizePolicy().hasHeightForWidth())
        self.location.setSizePolicy(sizePolicy)
        self.location.setEditable(True)
        self.location.setSizeAdjustPolicy(QtGui.QComboBox.AdjustToMinimumContentsLength)
        self.location.setObjectName(_fromUtf8("location"))
        self.location.addItem(_fromUtf8(""))
        self.gridLayout.addWidget(self.location, 1, 1, 1, 1)
        spacerItem1 = QtGui.QSpacerItem(18, 20, QtGui.QSizePolicy.Expanding, QtGui.QSizePolicy.Minimum)
        self.gridLayout.addItem(spacerItem1, 1, 0, 1, 1)
        spacerItem2 = QtGui.QSpacerItem(18, 17, QtGui.QSizePolicy.Expanding, QtGui.QSizePolicy.Minimum)
        self.gridLayout.addItem(spacerItem2, 2, 0, 1, 1)
        self.but_update = QtGui.QRadioButton(self.groupBox)
        self.but_update.setObjectName(_fromUtf8("but_update"))
        self.gridLayout.addWidget(self.but_update, 4, 0, 1, 3)
        self.location_picker.raise_()
        self.but_pull.raise_()
        self.but_pull_remember.raise_()
        self.but_pull_overwrite.raise_()
        self.location.raise_()
        self.but_update.raise_()
        self.verticalLayout_3.addWidget(self.groupBox)

        self.retranslateUi(UpdateBranchForm)
        QtCore.QObject.connect(self.but_pull, QtCore.SIGNAL(_fromUtf8("toggled(bool)")), self.but_pull_remember.setEnabled)
        QtCore.QObject.connect(self.but_pull, QtCore.SIGNAL(_fromUtf8("toggled(bool)")), self.but_pull_overwrite.setEnabled)
        QtCore.QObject.connect(self.but_pull, QtCore.SIGNAL(_fromUtf8("toggled(bool)")), self.location.setEnabled)
        QtCore.QObject.connect(self.but_pull, QtCore.SIGNAL(_fromUtf8("toggled(bool)")), self.location_picker.setEnabled)
        QtCore.QObject.connect(UpdateBranchForm, QtCore.SIGNAL(_fromUtf8("disableUi(bool)")), self.label.setDisabled)
        QtCore.QObject.connect(UpdateBranchForm, QtCore.SIGNAL(_fromUtf8("disableUi(bool)")), self.groupBox.setDisabled)
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

