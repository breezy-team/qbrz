# -*- coding: utf-8 -*-

# Form implementation generated from reading ui file 'ui/update_checkout.ui'
#
# Created by: PyQt5 UI code generator 5.12.3
#
# WARNING! All changes made in this file will be lost!


from PyQt5 import QtCore, QtGui, QtWidgets
from breezy.plugins.qbrz.lib.i18n import gettext



class Ui_UpdateCheckoutForm(object):
    def setupUi(self, UpdateCheckoutForm):
        UpdateCheckoutForm.setObjectName("UpdateCheckoutForm")
        UpdateCheckoutForm.resize(317, 170)
        self.verticalLayout = QtWidgets.QVBoxLayout(UpdateCheckoutForm)
        self.verticalLayout.setContentsMargins(9, 9, 9, 9)
        self.verticalLayout.setObjectName("verticalLayout")
        self.label = QtWidgets.QLabel(UpdateCheckoutForm)
        sizePolicy = QtWidgets.QSizePolicy(QtWidgets.QSizePolicy.Preferred, QtWidgets.QSizePolicy.Fixed)
        sizePolicy.setHorizontalStretch(0)
        sizePolicy.setVerticalStretch(0)
        sizePolicy.setHeightForWidth(self.label.sizePolicy().hasHeightForWidth())
        self.label.setSizePolicy(sizePolicy)
        self.label.setObjectName("label")
        self.verticalLayout.addWidget(self.label)
        self.groupBox = QtWidgets.QGroupBox(UpdateCheckoutForm)
        self.groupBox.setObjectName("groupBox")
        self.gridLayout = QtWidgets.QGridLayout(self.groupBox)
        self.gridLayout.setObjectName("gridLayout")
        self.but_update = QtWidgets.QRadioButton(self.groupBox)
        self.but_update.setChecked(True)
        self.but_update.setObjectName("but_update")
        self.gridLayout.addWidget(self.but_update, 0, 0, 1, 3)
        self.but_pull = QtWidgets.QRadioButton(self.groupBox)
        self.but_pull.setEnabled(True)
        self.but_pull.setObjectName("but_pull")
        self.gridLayout.addWidget(self.but_pull, 1, 0, 1, 3)
        spacerItem = QtWidgets.QSpacerItem(18, 20, QtWidgets.QSizePolicy.Expanding, QtWidgets.QSizePolicy.Minimum)
        self.gridLayout.addItem(spacerItem, 2, 0, 1, 1)
        self.location = QtWidgets.QComboBox(self.groupBox)
        self.location.setEnabled(False)
        sizePolicy = QtWidgets.QSizePolicy(QtWidgets.QSizePolicy.Preferred, QtWidgets.QSizePolicy.Fixed)
        sizePolicy.setHorizontalStretch(1)
        sizePolicy.setVerticalStretch(0)
        sizePolicy.setHeightForWidth(self.location.sizePolicy().hasHeightForWidth())
        self.location.setSizePolicy(sizePolicy)
        self.location.setEditable(True)
        self.location.setSizeAdjustPolicy(QtWidgets.QComboBox.AdjustToMinimumContentsLength)
        self.location.setObjectName("location")
        self.gridLayout.addWidget(self.location, 2, 1, 1, 1)
        self.location_picker = QtWidgets.QPushButton(self.groupBox)
        self.location_picker.setEnabled(False)
        self.location_picker.setObjectName("location_picker")
        self.gridLayout.addWidget(self.location_picker, 2, 2, 1, 1)
        spacerItem1 = QtWidgets.QSpacerItem(18, 20, QtWidgets.QSizePolicy.Expanding, QtWidgets.QSizePolicy.Minimum)
        self.gridLayout.addItem(spacerItem1, 3, 0, 1, 1)
        self.but_pull_overwrite = QtWidgets.QCheckBox(self.groupBox)
        self.but_pull_overwrite.setEnabled(False)
        self.but_pull_overwrite.setObjectName("but_pull_overwrite")
        self.gridLayout.addWidget(self.but_pull_overwrite, 3, 1, 1, 2)
        self.verticalLayout.addWidget(self.groupBox)

        self.retranslateUi(UpdateCheckoutForm)
        self.but_pull.toggled['bool'].connect(self.location.setEnabled)
        self.but_pull.toggled['bool'].connect(self.location_picker.setEnabled)
        self.but_pull.toggled['bool'].connect(self.but_pull_overwrite.setEnabled)
        UpdateCheckoutForm.disableUi['bool'].connect(self.groupBox.setDisabled)
        QtCore.QMetaObject.connectSlotsByName(UpdateCheckoutForm)

    def retranslateUi(self, UpdateCheckoutForm):
        _translate = QtCore.QCoreApplication.translate
        UpdateCheckoutForm.setWindowTitle(_translate("UpdateCheckoutForm", "Update Checkout"))
        self.label.setText(_translate("UpdateCheckoutForm", "This directory is a checkout of: %s"))
        self.groupBox.setTitle(_translate("UpdateCheckoutForm", "Update source"))
        self.but_update.setText(_translate("UpdateCheckoutForm", "Update the working tree from the bound branch"))
        self.but_pull.setText(_translate("UpdateCheckoutForm", "Pull a different branch"))
        self.location_picker.setText(_translate("UpdateCheckoutForm", "Browse..."))
        self.but_pull_overwrite.setText(_translate("UpdateCheckoutForm", "Overwrite differences between branches"))
