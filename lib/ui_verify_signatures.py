# -*- coding: utf-8 -*-

# Form implementation generated from reading ui file 'ui/verify-signatures.ui'
#
# Created: Thu Jun 23 15:53:22 2011
#      by: PyQt4 UI code generator 4.8.3
#
# WARNING! All changes made in this file will be lost!

from PyQt4 import QtCore, QtGui

try:
    _fromUtf8 = QtCore.QString.fromUtf8
except AttributeError:
    _fromUtf8 = lambda s: s

class Ui_VerifyForm(object):
    def setupUi(self, VerifyForm):
        VerifyForm.setObjectName(_fromUtf8("VerifyForm"))
        VerifyForm.resize(579, 266)
        self.verticalLayout = QtGui.QVBoxLayout(VerifyForm)
        self.verticalLayout.setObjectName(_fromUtf8("verticalLayout"))
        self.label = QtGui.QLabel(VerifyForm)
        self.label.setObjectName(_fromUtf8("label"))
        self.verticalLayout.addWidget(self.label)

        self.retranslateUi(VerifyForm)
        QtCore.QMetaObject.connectSlotsByName(VerifyForm)

    def retranslateUi(self, VerifyForm):
        self.label.setText(QtGui.QApplication.translate("VerifyForm", "TextLabel", None, QtGui.QApplication.UnicodeUTF8))

