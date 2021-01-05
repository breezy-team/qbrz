# -*- coding: utf-8 -*-

# Form implementation generated from reading ui file 'ui/bookmark.ui'
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

class Ui_BookmarkDialog(object):
    def setupUi(self, BookmarkDialog):
        BookmarkDialog.setObjectName("BookmarkDialog")
        BookmarkDialog.resize(354, 90)
        self.vboxlayout = QtWidgets.QVBoxLayout(BookmarkDialog)
        self.vboxlayout.setObjectName("vboxlayout")
        self.gridlayout = QtWidgets.QGridLayout()
        self.gridlayout.setObjectName("gridlayout")
        self.label = QtWidgets.QLabel(BookmarkDialog)
        self.label.setObjectName("label")
        self.gridlayout.addWidget(self.label, 0, 0, 1, 1)
        self.name = QtWidgets.QLineEdit(BookmarkDialog)
        self.name.setObjectName("name")
        self.gridlayout.addWidget(self.name, 0, 1, 1, 1)
        self.label_2 = QtWidgets.QLabel(BookmarkDialog)
        self.label_2.setObjectName("label_2")
        self.gridlayout.addWidget(self.label_2, 1, 0, 1, 1)
        self.location = QtWidgets.QLineEdit(BookmarkDialog)
        self.location.setObjectName("location")
        self.gridlayout.addWidget(self.location, 1, 1, 1, 1)
        self.vboxlayout.addLayout(self.gridlayout)
        spacerItem = QtWidgets.QSpacerItem(336, 16, QtWidgets.QSizePolicy.Minimum, QtWidgets.QSizePolicy.Expanding)
        self.vboxlayout.addItem(spacerItem)
        self.buttonBox = QtWidgets.QDialogButtonBox(BookmarkDialog)
        self.buttonBox.setOrientation(QtCore.Qt.Horizontal)
        self.buttonBox.setObjectName("buttonBox")
        self.vboxlayout.addWidget(self.buttonBox)
        self.label.setBuddy(self.name)
        self.label_2.setBuddy(self.location)

        self.retranslateUi(BookmarkDialog)
        self.buttonBox.accepted.connect(BookmarkDialog.accept)
        self.buttonBox.rejected.connect(BookmarkDialog.reject)
        QtCore.QMetaObject.connectSlotsByName(BookmarkDialog)

    def retranslateUi(self, BookmarkDialog):
        self.label.setText(_translate("BookmarkDialog", "&Name:", None))
        self.label_2.setText(_translate("BookmarkDialog", "&Location:", None))

