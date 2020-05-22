# -*- coding: utf-8 -*-

# Form implementation generated from reading ui file 'ui/merge.ui'
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

class Ui_MergeForm(object):
    def setupUi(self, MergeForm):
        MergeForm.setObjectName(_fromUtf8("MergeForm"))
        MergeForm.resize(448, 248)
        self.verticalLayout = QtGui.QVBoxLayout(MergeForm)
        self.verticalLayout.setMargin(9)
        self.verticalLayout.setObjectName(_fromUtf8("verticalLayout"))
        self.groupBox = QtGui.QGroupBox(MergeForm)
        self.groupBox.setObjectName(_fromUtf8("groupBox"))
        self.gridLayout = QtGui.QGridLayout(self.groupBox)
        self.gridLayout.setObjectName(_fromUtf8("gridLayout"))
        self.label_4 = QtGui.QLabel(self.groupBox)
        self.label_4.setObjectName(_fromUtf8("label_4"))
        self.gridLayout.addWidget(self.label_4, 0, 0, 1, 1)
        self.location = QtGui.QComboBox(self.groupBox)
        self.location.setEditable(True)
        self.location.setSizeAdjustPolicy(QtGui.QComboBox.AdjustToMinimumContentsLength)
        self.location.setObjectName(_fromUtf8("location"))
        self.gridLayout.addWidget(self.location, 0, 1, 1, 2)
        self.location_picker = QtGui.QPushButton(self.groupBox)
        self.location_picker.setObjectName(_fromUtf8("location_picker"))
        self.gridLayout.addWidget(self.location_picker, 0, 3, 1, 1)
        self.label_3 = QtGui.QLabel(self.groupBox)
        self.label_3.setObjectName(_fromUtf8("label_3"))
        self.gridLayout.addWidget(self.label_3, 1, 0, 1, 1)
        self.revision = QtGui.QLineEdit(self.groupBox)
        self.revision.setObjectName(_fromUtf8("revision"))
        self.gridLayout.addWidget(self.revision, 1, 1, 1, 1)
        spacerItem = QtGui.QSpacerItem(107, 20, QtGui.QSizePolicy.Expanding, QtGui.QSizePolicy.Minimum)
        self.gridLayout.addItem(spacerItem, 1, 2, 1, 2)
        self.remember = QtGui.QCheckBox(self.groupBox)
        self.remember.setObjectName(_fromUtf8("remember"))
        self.gridLayout.addWidget(self.remember, 2, 0, 1, 4)
        self.force = QtGui.QCheckBox(self.groupBox)
        self.force.setObjectName(_fromUtf8("force"))
        self.gridLayout.addWidget(self.force, 3, 0, 1, 4)
        self.uncommitted = QtGui.QCheckBox(self.groupBox)
        self.uncommitted.setObjectName(_fromUtf8("uncommitted"))
        self.gridLayout.addWidget(self.uncommitted, 4, 0, 1, 4)
        self.verticalLayout.addWidget(self.groupBox)
        self.label_4.setBuddy(self.revision)
        self.label_3.setBuddy(self.revision)

        self.retranslateUi(MergeForm)
        QtCore.QObject.connect(MergeForm, QtCore.SIGNAL(_fromUtf8("disableUi(bool)")), self.groupBox.setDisabled)
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

