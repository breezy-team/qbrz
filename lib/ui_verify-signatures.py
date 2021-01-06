# -*- coding: utf-8 -*-

# Form implementation generated from reading ui file 'ui/verify-signatures.ui'
#
# Created by: PyQt5 UI code generator 5.12.3
#
# WARNING! All changes made in this file will be lost!


from PyQt5 import QtCore, QtGui, QtWidgets
from breezy.plugins.qbrz.lib.i18n import gettext



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
