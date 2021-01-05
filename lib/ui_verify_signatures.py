# -*- coding: utf-8 -*-

# Form implementation generated from reading ui file 'ui/verify-signatures.ui'
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

class Ui_VerifyForm(object):
    def setupUi(self, VerifyForm):
        VerifyForm.setObjectName("VerifyForm")
        VerifyForm.resize(560, 230)
        self.verticalLayout = QtWidgets.QVBoxLayout(VerifyForm)
        self.verticalLayout.setObjectName("verticalLayout")
        self.treeWidget = QtWidgets.QTreeWidget(VerifyForm)
        self.treeWidget.setObjectName("treeWidget")
        self.treeWidget.headerItem().setText(0, "1")
        self.verticalLayout.addWidget(self.treeWidget)

        self.retranslateUi(VerifyForm)
        QtCore.QMetaObject.connectSlotsByName(VerifyForm)

    def retranslateUi(self, VerifyForm):
        pass

