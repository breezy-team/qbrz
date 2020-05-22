# -*- coding: utf-8 -*-

# Form implementation generated from reading ui file 'ui/update_checkout.ui'
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

class Ui_UpdateCheckoutForm(object):
    def setupUi(self, UpdateCheckoutForm):
        UpdateCheckoutForm.setObjectName(_fromUtf8("UpdateCheckoutForm"))
        UpdateCheckoutForm.resize(317, 170)
        self.verticalLayout = QtGui.QVBoxLayout(UpdateCheckoutForm)
        self.verticalLayout.setMargin(9)
        self.verticalLayout.setObjectName(_fromUtf8("verticalLayout"))
        self.label = QtGui.QLabel(UpdateCheckoutForm)
        sizePolicy = QtGui.QSizePolicy(QtGui.QSizePolicy.Preferred, QtGui.QSizePolicy.Fixed)
        sizePolicy.setHorizontalStretch(0)
        sizePolicy.setVerticalStretch(0)
        sizePolicy.setHeightForWidth(self.label.sizePolicy().hasHeightForWidth())
        self.label.setSizePolicy(sizePolicy)
        self.label.setObjectName(_fromUtf8("label"))
        self.verticalLayout.addWidget(self.label)
        self.groupBox = QtGui.QGroupBox(UpdateCheckoutForm)
        self.groupBox.setObjectName(_fromUtf8("groupBox"))
        self.gridLayout = QtGui.QGridLayout(self.groupBox)
        self.gridLayout.setObjectName(_fromUtf8("gridLayout"))
        self.but_update = QtGui.QRadioButton(self.groupBox)
        self.but_update.setChecked(True)
        self.but_update.setObjectName(_fromUtf8("but_update"))
        self.gridLayout.addWidget(self.but_update, 0, 0, 1, 3)
        self.but_pull = QtGui.QRadioButton(self.groupBox)
        self.but_pull.setEnabled(True)
        self.but_pull.setObjectName(_fromUtf8("but_pull"))
        self.gridLayout.addWidget(self.but_pull, 1, 0, 1, 3)
        spacerItem = QtGui.QSpacerItem(18, 20, QtGui.QSizePolicy.Expanding, QtGui.QSizePolicy.Minimum)
        self.gridLayout.addItem(spacerItem, 2, 0, 1, 1)
        self.location = QtGui.QComboBox(self.groupBox)
        self.location.setEnabled(False)
        sizePolicy = QtGui.QSizePolicy(QtGui.QSizePolicy.Preferred, QtGui.QSizePolicy.Fixed)
        sizePolicy.setHorizontalStretch(1)
        sizePolicy.setVerticalStretch(0)
        sizePolicy.setHeightForWidth(self.location.sizePolicy().hasHeightForWidth())
        self.location.setSizePolicy(sizePolicy)
        self.location.setEditable(True)
        self.location.setSizeAdjustPolicy(QtGui.QComboBox.AdjustToMinimumContentsLength)
        self.location.setObjectName(_fromUtf8("location"))
        self.gridLayout.addWidget(self.location, 2, 1, 1, 1)
        self.location_picker = QtGui.QPushButton(self.groupBox)
        self.location_picker.setEnabled(False)
        self.location_picker.setObjectName(_fromUtf8("location_picker"))
        self.gridLayout.addWidget(self.location_picker, 2, 2, 1, 1)
        spacerItem1 = QtGui.QSpacerItem(18, 20, QtGui.QSizePolicy.Expanding, QtGui.QSizePolicy.Minimum)
        self.gridLayout.addItem(spacerItem1, 3, 0, 1, 1)
        self.but_pull_overwrite = QtGui.QCheckBox(self.groupBox)
        self.but_pull_overwrite.setEnabled(False)
        self.but_pull_overwrite.setObjectName(_fromUtf8("but_pull_overwrite"))
        self.gridLayout.addWidget(self.but_pull_overwrite, 3, 1, 1, 2)
        self.verticalLayout.addWidget(self.groupBox)

        self.retranslateUi(UpdateCheckoutForm)
        QtCore.QObject.connect(self.but_pull, QtCore.SIGNAL(_fromUtf8("toggled(bool)")), self.location.setEnabled)
        QtCore.QObject.connect(self.but_pull, QtCore.SIGNAL(_fromUtf8("toggled(bool)")), self.location_picker.setEnabled)
        QtCore.QObject.connect(self.but_pull, QtCore.SIGNAL(_fromUtf8("toggled(bool)")), self.but_pull_overwrite.setEnabled)
        QtCore.QObject.connect(UpdateCheckoutForm, QtCore.SIGNAL(_fromUtf8("disableUi(bool)")), self.groupBox.setDisabled)
        QtCore.QMetaObject.connectSlotsByName(UpdateCheckoutForm)

    def retranslateUi(self, UpdateCheckoutForm):
        UpdateCheckoutForm.setWindowTitle(_translate("UpdateCheckoutForm", "Update Checkout", None))
        self.label.setText(_translate("UpdateCheckoutForm", "This directory is a checkout of: %s", None))
        self.groupBox.setTitle(_translate("UpdateCheckoutForm", "Update source", None))
        self.but_update.setText(_translate("UpdateCheckoutForm", "Update the working tree from the bound branch", None))
        self.but_pull.setText(_translate("UpdateCheckoutForm", "Pull a different branch", None))
        self.location_picker.setText(_translate("UpdateCheckoutForm", "Browse...", None))
        self.but_pull_overwrite.setText(_translate("UpdateCheckoutForm", "Overwrite differences between branches", None))

