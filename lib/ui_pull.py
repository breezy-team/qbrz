# -*- coding: utf-8 -*-

# Form implementation generated from reading ui file 'ui/pull.ui'
#
# Created by: PyQt5 UI code generator 5.12.3
#
# WARNING! All changes made in this file will be lost!


from PyQt5 import QtCore, QtGui, QtWidgets
from breezy.plugins.qbrz.lib.i18n import gettext



class Ui_PullForm(object):
    def setupUi(self, PullForm):
        PullForm.setObjectName("PullForm")
        PullForm.resize(404, 194)
        self.verticalLayout = QtWidgets.QVBoxLayout(PullForm)
        self.verticalLayout.setContentsMargins(9, 9, 9, 9)
        self.verticalLayout.setObjectName("verticalLayout")
        self.groupBox = QtWidgets.QGroupBox(PullForm)
        self.groupBox.setObjectName("groupBox")
        self.gridLayout = QtWidgets.QGridLayout(self.groupBox)
        self.gridLayout.setObjectName("gridLayout")
        self.label_2 = QtWidgets.QLabel(self.groupBox)
        self.label_2.setObjectName("label_2")
        self.gridLayout.addWidget(self.label_2, 0, 0, 1, 1)
        self.location = QtWidgets.QComboBox(self.groupBox)
        self.location.setEditable(True)
        self.location.setSizeAdjustPolicy(QtWidgets.QComboBox.AdjustToMinimumContentsLength)
        self.location.setObjectName("location")
        self.gridLayout.addWidget(self.location, 0, 1, 1, 2)
        self.location_picker = QtWidgets.QPushButton(self.groupBox)
        self.location_picker.setObjectName("location_picker")
        self.gridLayout.addWidget(self.location_picker, 0, 3, 1, 1)
        self.label_3 = QtWidgets.QLabel(self.groupBox)
        self.label_3.setObjectName("label_3")
        self.gridLayout.addWidget(self.label_3, 1, 0, 1, 1)
        self.revision = QtWidgets.QLineEdit(self.groupBox)
        self.revision.setObjectName("revision")
        self.gridLayout.addWidget(self.revision, 1, 1, 1, 1)
        spacerItem = QtWidgets.QSpacerItem(211, 20, QtWidgets.QSizePolicy.Expanding, QtWidgets.QSizePolicy.Minimum)
        self.gridLayout.addItem(spacerItem, 1, 2, 1, 2)
        self.remember = QtWidgets.QCheckBox(self.groupBox)
        self.remember.setChecked(False)
        self.remember.setObjectName("remember")
        self.gridLayout.addWidget(self.remember, 2, 0, 1, 4)
        self.overwrite = QtWidgets.QCheckBox(self.groupBox)
        self.overwrite.setObjectName("overwrite")
        self.gridLayout.addWidget(self.overwrite, 3, 0, 1, 4)
        self.verticalLayout.addWidget(self.groupBox)
        self.label_2.setBuddy(self.location)
        self.label_3.setBuddy(self.revision)

        self.retranslateUi(PullForm)
        PullForm.disableUi['bool'].connect(self.groupBox.setDisabled)
        QtCore.QMetaObject.connectSlotsByName(PullForm)

    def retranslateUi(self, PullForm):
        _translate = QtCore.QCoreApplication.translate
        PullForm.setWindowTitle(_translate("PullForm", "Pull"))
        self.groupBox.setTitle(_translate("PullForm", "Options"))
        self.label_2.setText(_translate("PullForm", "&Location:"))
        self.location_picker.setText(_translate("PullForm", "Browse..."))
        self.label_3.setText(_translate("PullForm", "&Revision:"))
        self.remember.setText(_translate("PullForm", "Remember this location as a default"))
        self.overwrite.setText(_translate("PullForm", "Overwrite differences between branches"))
