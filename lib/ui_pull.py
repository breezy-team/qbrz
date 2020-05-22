# -*- coding: utf-8 -*-

# Form implementation generated from reading ui file 'ui/pull.ui'
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

class Ui_PullForm(object):
    def setupUi(self, PullForm):
        PullForm.setObjectName(_fromUtf8("PullForm"))
        PullForm.resize(404, 194)
        self.verticalLayout = QtGui.QVBoxLayout(PullForm)
        self.verticalLayout.setMargin(9)
        self.verticalLayout.setObjectName(_fromUtf8("verticalLayout"))
        self.groupBox = QtGui.QGroupBox(PullForm)
        self.groupBox.setObjectName(_fromUtf8("groupBox"))
        self.gridLayout = QtGui.QGridLayout(self.groupBox)
        self.gridLayout.setObjectName(_fromUtf8("gridLayout"))
        self.label_2 = QtGui.QLabel(self.groupBox)
        self.label_2.setObjectName(_fromUtf8("label_2"))
        self.gridLayout.addWidget(self.label_2, 0, 0, 1, 1)
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
        spacerItem = QtGui.QSpacerItem(211, 20, QtGui.QSizePolicy.Expanding, QtGui.QSizePolicy.Minimum)
        self.gridLayout.addItem(spacerItem, 1, 2, 1, 2)
        self.remember = QtGui.QCheckBox(self.groupBox)
        self.remember.setChecked(False)
        self.remember.setObjectName(_fromUtf8("remember"))
        self.gridLayout.addWidget(self.remember, 2, 0, 1, 4)
        self.overwrite = QtGui.QCheckBox(self.groupBox)
        self.overwrite.setObjectName(_fromUtf8("overwrite"))
        self.gridLayout.addWidget(self.overwrite, 3, 0, 1, 4)
        self.verticalLayout.addWidget(self.groupBox)
        self.label_2.setBuddy(self.location)
        self.label_3.setBuddy(self.revision)

        self.retranslateUi(PullForm)
        QtCore.QObject.connect(PullForm, QtCore.SIGNAL(_fromUtf8("disableUi(bool)")), self.groupBox.setDisabled)
        QtCore.QMetaObject.connectSlotsByName(PullForm)

    def retranslateUi(self, PullForm):
        PullForm.setWindowTitle(_translate("PullForm", "Pull", None))
        self.groupBox.setTitle(_translate("PullForm", "Options", None))
        self.label_2.setText(_translate("PullForm", "&Location:", None))
        self.location_picker.setText(_translate("PullForm", "Browse...", None))
        self.label_3.setText(_translate("PullForm", "&Revision:", None))
        self.remember.setText(_translate("PullForm", "Remember this location as a default", None))
        self.overwrite.setText(_translate("PullForm", "Overwrite differences between branches", None))

