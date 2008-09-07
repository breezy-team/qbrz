# -*- coding: utf-8 -*-

# Form implementation generated from reading ui file 'ui/update_checkout.ui'
#
# Created: Sun Sep 07 16:12:22 2008
#      by: PyQt4 UI code generator 4.4.2
#
# WARNING! All changes made in this file will be lost!

from PyQt4 import QtCore, QtGui
from bzrlib.plugins.qbzr.lib.i18n import gettext


class Ui_UpdateCheckoutForm(object):
    def setupUi(self, UpdateCheckoutForm):
        UpdateCheckoutForm.setObjectName("UpdateCheckoutForm")
        UpdateCheckoutForm.resize(436, 169)
        self.verticalLayout = QtGui.QVBoxLayout(UpdateCheckoutForm)
        self.verticalLayout.setObjectName("verticalLayout")
        self.label = QtGui.QLabel(UpdateCheckoutForm)
        sizePolicy = QtGui.QSizePolicy(QtGui.QSizePolicy.Preferred, QtGui.QSizePolicy.Fixed)
        sizePolicy.setHorizontalStretch(0)
        sizePolicy.setVerticalStretch(0)
        sizePolicy.setHeightForWidth(self.label.sizePolicy().hasHeightForWidth())
        self.label.setSizePolicy(sizePolicy)
        self.label.setObjectName("label")
        self.verticalLayout.addWidget(self.label)
        self.groupBox = QtGui.QGroupBox(UpdateCheckoutForm)
        self.groupBox.setObjectName("groupBox")
        self.gridLayout = QtGui.QGridLayout(self.groupBox)
        self.gridLayout.setObjectName("gridLayout")
        self.location = QtGui.QComboBox(self.groupBox)
        self.location.setEnabled(False)
        sizePolicy = QtGui.QSizePolicy(QtGui.QSizePolicy.Preferred, QtGui.QSizePolicy.Fixed)
        sizePolicy.setHorizontalStretch(1)
        sizePolicy.setVerticalStretch(0)
        sizePolicy.setHeightForWidth(self.location.sizePolicy().hasHeightForWidth())
        self.location.setSizePolicy(sizePolicy)
        self.location.setObjectName("location")
        self.gridLayout.addWidget(self.location, 2, 1, 1, 2)
        self.but_pull = QtGui.QRadioButton(self.groupBox)
        self.but_pull.setEnabled(True)
        self.but_pull.setObjectName("but_pull")
        self.gridLayout.addWidget(self.but_pull, 1, 1, 1, 1)
        self.but_update = QtGui.QRadioButton(self.groupBox)
        self.but_update.setChecked(True)
        self.but_update.setObjectName("but_update")
        self.gridLayout.addWidget(self.but_update, 0, 1, 1, 1)
        self.location_picker = QtGui.QPushButton(self.groupBox)
        self.location_picker.setEnabled(False)
        self.location_picker.setObjectName("location_picker")
        self.gridLayout.addWidget(self.location_picker, 2, 3, 1, 1)
        self.but_pull_overwrite = QtGui.QCheckBox(self.groupBox)
        self.but_pull_overwrite.setEnabled(False)
        self.but_pull_overwrite.setObjectName("but_pull_overwrite")
        self.gridLayout.addWidget(self.but_pull_overwrite, 3, 1, 1, 1)
        self.verticalLayout.addWidget(self.groupBox)

        self.retranslateUi(UpdateCheckoutForm)
        QtCore.QMetaObject.connectSlotsByName(UpdateCheckoutForm)

    def retranslateUi(self, UpdateCheckoutForm):
        UpdateCheckoutForm.setWindowTitle(gettext("Update Bazaar Checkout"))
        self.label.setText(gettext("This directory is a checkout of: %s"))
        self.groupBox.setTitle(gettext("Update source"))
        self.but_pull.setText(gettext("Pull a different branch"))
        self.but_update.setText(gettext("Update the working tree from the bound branch"))
        self.location_picker.setText(gettext("Browse..."))
        self.but_pull_overwrite.setText(gettext("Overwrite differences between branches"))

