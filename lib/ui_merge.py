# -*- coding: utf-8 -*-

# Form implementation generated from reading ui file 'ui/merge.ui'
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

class Ui_MergeForm(object):
    def setupUi(self, MergeForm):
        MergeForm.setObjectName("MergeForm")
        MergeForm.resize(448, 248)
        self.verticalLayout = QtWidgets.QVBoxLayout(MergeForm)
        self.verticalLayout.setContentsMargins(9, 9, 9, 9)
        self.verticalLayout.setObjectName("verticalLayout")
        self.groupBox = QtWidgets.QGroupBox(MergeForm)
        self.groupBox.setObjectName("groupBox")
        self.gridLayout = QtWidgets.QGridLayout(self.groupBox)
        self.gridLayout.setObjectName("gridLayout")
        self.label_4 = QtWidgets.QLabel(self.groupBox)
        self.label_4.setObjectName("label_4")
        self.gridLayout.addWidget(self.label_4, 0, 0, 1, 1)
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
        spacerItem = QtWidgets.QSpacerItem(107, 20, QtWidgets.QSizePolicy.Expanding, QtWidgets.QSizePolicy.Minimum)
        self.gridLayout.addItem(spacerItem, 1, 2, 1, 2)
        self.remember = QtWidgets.QCheckBox(self.groupBox)
        self.remember.setObjectName("remember")
        self.gridLayout.addWidget(self.remember, 2, 0, 1, 4)
        self.force = QtWidgets.QCheckBox(self.groupBox)
        self.force.setObjectName("force")
        self.gridLayout.addWidget(self.force, 3, 0, 1, 4)
        self.uncommitted = QtWidgets.QCheckBox(self.groupBox)
        self.uncommitted.setObjectName("uncommitted")
        self.gridLayout.addWidget(self.uncommitted, 4, 0, 1, 4)
        self.verticalLayout.addWidget(self.groupBox)
        self.label_4.setBuddy(self.revision)
        self.label_3.setBuddy(self.revision)

        self.retranslateUi(MergeForm)
        MergeForm.disableUi[bool].connect(self.groupBox.setDisabled)
        QtCore.QMetaObject.connectSlotsByName(MergeForm)

    def retranslateUi(self, MergeForm):
        MergeForm.setWindowTitle(_translate("MergeForm", "Merge", None))
        self.groupBox.setTitle(_translate("MergeForm", "Options", None))
        self.label_4.setText(_translate("MergeForm", "&Location:", None))
        self.location_picker.setText(_translate("MergeForm", "Browse...", None))
        self.label_3.setText(_translate("MergeForm", "&Revision:", None))
        self.remember.setText(_translate("MergeForm", "Remember this location as a default", None))
        self.force.setText(_translate("MergeForm", "Merge even if the working tree has uncommitted changes", None))
        self.uncommitted.setText(_translate("MergeForm", "Merge uncommitted changes instead of committed ones", None))

