# -*- coding: utf-8 -*-

# Form implementation generated from reading ui file 'ui/verify-signatures.ui'
#
# Created: Fri Jun 24 11:51:55 2011
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
        VerifyForm.resize(560, 230)
        self.verticalLayout = QtGui.QVBoxLayout(VerifyForm)
        self.verticalLayout.setObjectName(_fromUtf8("verticalLayout"))
        self.treeWidget = QtGui.QTreeWidget(VerifyForm)
        self.treeWidget.setObjectName(_fromUtf8("treeWidget"))
        self.treeWidget.headerItem().setText(0, _fromUtf8("1"))
        self.verticalLayout.addWidget(self.treeWidget)

        self.retranslateUi(VerifyForm)
        QtCore.QMetaObject.connectSlotsByName(VerifyForm)

    def retranslateUi(self, VerifyForm):
        pass

