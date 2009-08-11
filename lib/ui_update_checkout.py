# -*- coding: utf-8 -*-

# Form implementation generated from reading ui file 'ui/update_checkout.ui'
#
# Created: Thu Jul 30 12:22:19 2009
#      by: PyQt4 UI code generator 4.4.3
#
# WARNING! All changes made in this file will be lost!

from PyQt4 import QtCore, QtGui
from bzrlib.plugins.qbzr.lib.i18n import gettext


class Ui_UpdateCheckoutForm(object):
    def setupUi(self, UpdateCheckoutForm):
        UpdateCheckoutForm.setObjectName("UpdateCheckoutForm")
        UpdateCheckoutForm.resize(317, 170)
        self.verticalLayout = QtGui.QVBoxLayout(UpdateCheckoutForm)
        self.verticalLayout.setMargin(9)
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
        self.but_update = QtGui.QRadioButton(self.groupBox)
        self.but_update.setChecked(True)
        self.but_update.setObjectName("but_update")
        self.gridLayout.addWidget(self.but_update, 0, 0, 1, 3)
        self.but_pull = QtGui.QRadioButton(self.groupBox)
        self.but_pull.setEnabled(True)
        self.but_pull.setObjectName("but_pull")
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
        self.location.setObjectName("location")
        self.gridLayout.addWidget(self.location, 2, 1, 1, 1)
        self.location_picker = QtGui.QPushButton(self.groupBox)
        self.location_picker.setEnabled(False)
        self.location_picker.setObjectName("location_picker")
        self.gridLayout.addWidget(self.location_picker, 2, 2, 1, 1)
        spacerItem1 = QtGui.QSpacerItem(18, 20, QtGui.QSizePolicy.Expanding, QtGui.QSizePolicy.Minimum)
        self.gridLayout.addItem(spacerItem1, 3, 0, 1, 1)
        self.but_pull_overwrite = QtGui.QCheckBox(self.groupBox)
        self.but_pull_overwrite.setEnabled(False)
        self.but_pull_overwrite.setObjectName("but_pull_overwrite")
        self.gridLayout.addWidget(self.but_pull_overwrite, 3, 1, 1, 2)
        self.verticalLayout.addWidget(self.groupBox)

        self.retranslateUi(UpdateCheckoutForm)
        QtCore.QObject.connect(self.but_pull, QtCore.SIGNAL("toggled(bool)"), self.location.setEnabled)
        QtCore.QObject.connect(self.but_pull, QtCore.SIGNAL("toggled(bool)"), self.location_picker.setEnabled)
        QtCore.QObject.connect(self.but_pull, QtCore.SIGNAL("toggled(bool)"), self.but_pull_overwrite.setEnabled)
        QtCore.QObject.connect(UpdateCheckoutForm, QtCore.SIGNAL("disableUi(bool)"), self.groupBox.setDisabled)
        QtCore.QMetaObject.connectSlotsByName(UpdateCheckoutForm)

    def retranslateUi(self, UpdateCheckoutForm):
        UpdateCheckoutForm.setWindowTitle(gettext("Update Checkout"))
        self.label.setText(gettext("This directory is a checkout of: %s"))
        self.groupBox.setTitle(gettext("Update source"))
        self.but_update.setText(gettext("Update the working tree from the bound branch"))
        self.but_pull.setText(gettext("Pull a different branch"))
        self.location_picker.setText(gettext("Browse..."))
        self.but_pull_overwrite.setText(gettext("Overwrite differences between branches"))

