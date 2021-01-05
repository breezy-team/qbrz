# -*- coding: utf-8 -*-

# Form implementation generated from reading ui file 'ui/push.ui'
#
# Created: Mon Oct 05 19:41:19 2009
#      by: PyQt4 UI code generator 4.4.3
#
# WARNING! All changes made in this file will be lost!

from PyQt5 import QtCore, QtGui, QtWidgets
from breezy.plugins.qbrz.lib.i18n import gettext


class Ui_PushForm(object):
    def setupUi(self, PushForm):
        PushForm.setObjectName("PushForm")
        PushForm.resize(349, 175)
        self.verticalLayout = QtWidgets.QVBoxLayout(PushForm)
        self.verticalLayout.setContentsMargins(9, 9, 9, 9)
        self.verticalLayout.setObjectName("verticalLayout")
        self.groupBox = QtWidgets.QGroupBox(PushForm)
        self.groupBox.setObjectName("groupBox")
        self.gridLayout = QtWidgets.QGridLayout(self.groupBox)
        self.gridLayout.setObjectName("gridLayout")
        self.label_2 = QtWidgets.QLabel(self.groupBox)
        self.label_2.setObjectName("label_2")
        self.gridLayout.addWidget(self.label_2, 0, 0, 1, 1)
        self.location = QtWidgets.QComboBox(self.groupBox)
        sizePolicy = QtWidgets.QSizePolicy(QtWidgets.QSizePolicy.Expanding,
                                           QtWidgets.QSizePolicy.Fixed)
        sizePolicy.setHorizontalStretch(0)
        sizePolicy.setVerticalStretch(0)
        sizePolicy.setHeightForWidth(self.location.sizePolicy().hasHeightForWidth())
        self.location.setSizePolicy(sizePolicy)
        self.location.setEditable(True)
        self.location.setSizeAdjustPolicy(QtWidgets.QComboBox.AdjustToMinimumContentsLength)
        self.location.setObjectName("location")
        self.gridLayout.addWidget(self.location, 0, 1, 1, 1)
        self.location_picker = QtWidgets.QPushButton(self.groupBox)
        self.location_picker.setObjectName("location_picker")
        self.gridLayout.addWidget(self.location_picker, 0, 2, 1, 1)
        self.remember = QtWidgets.QCheckBox(self.groupBox)
        self.remember.setChecked(False)
        self.remember.setObjectName("remember")
        self.gridLayout.addWidget(self.remember, 1, 0, 1, 3)
        self.overwrite = QtWidgets.QCheckBox(self.groupBox)
        self.overwrite.setObjectName("overwrite")
        self.gridLayout.addWidget(self.overwrite, 2, 0, 1, 3)
        self.use_existing_dir = QtWidgets.QCheckBox(self.groupBox)
        self.use_existing_dir.setObjectName("use_existing_dir")
        self.gridLayout.addWidget(self.use_existing_dir, 3, 0, 1, 3)
        self.create_prefix = QtWidgets.QCheckBox(self.groupBox)
        self.create_prefix.setObjectName("create_prefix")
        self.gridLayout.addWidget(self.create_prefix, 4, 0, 1, 3)
        self.verticalLayout.addWidget(self.groupBox)
        self.label_2.setBuddy(self.location)

        self.retranslateUi(PushForm)
        PushForm.disableUi[bool].connect(self.groupBox.setDisabled)
        QtCore.QMetaObject.connectSlotsByName(PushForm)

    def retranslateUi(self, PushForm):
        PushForm.setWindowTitle(gettext("Push"))
        self.groupBox.setTitle(gettext("Options"))
        self.label_2.setText(gettext("&Location:"))
        self.location_picker.setText(gettext("Browse..."))
        self.remember.setText(gettext("Remember this location as a default"))
        self.overwrite.setText(gettext("Overwrite differences between branches"))
        self.use_existing_dir.setText(gettext("Use existing directory"))
        self.create_prefix.setText(gettext("Create the path up to the branch if it does not exist"))

