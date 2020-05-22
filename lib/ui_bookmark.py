# -*- coding: utf-8 -*-

# Form implementation generated from reading ui file 'ui/bookmark.ui'
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

class Ui_BookmarkDialog(object):
    def setupUi(self, BookmarkDialog):
        BookmarkDialog.setObjectName(_fromUtf8("BookmarkDialog"))
        BookmarkDialog.resize(354, 90)
        self.vboxlayout = QtGui.QVBoxLayout(BookmarkDialog)
        self.vboxlayout.setObjectName(_fromUtf8("vboxlayout"))
        self.gridlayout = QtGui.QGridLayout()
        self.gridlayout.setObjectName(_fromUtf8("gridlayout"))
        self.label = QtGui.QLabel(BookmarkDialog)
        self.label.setObjectName(_fromUtf8("label"))
        self.gridlayout.addWidget(self.label, 0, 0, 1, 1)
        self.name = QtGui.QLineEdit(BookmarkDialog)
        self.name.setObjectName(_fromUtf8("name"))
        self.gridlayout.addWidget(self.name, 0, 1, 1, 1)
        self.label_2 = QtGui.QLabel(BookmarkDialog)
        self.label_2.setObjectName(_fromUtf8("label_2"))
        self.gridlayout.addWidget(self.label_2, 1, 0, 1, 1)
        self.location = QtGui.QLineEdit(BookmarkDialog)
        self.location.setObjectName(_fromUtf8("location"))
        self.gridlayout.addWidget(self.location, 1, 1, 1, 1)
        self.vboxlayout.addLayout(self.gridlayout)
        spacerItem = QtGui.QSpacerItem(336, 16, QtGui.QSizePolicy.Minimum, QtGui.QSizePolicy.Expanding)
        self.vboxlayout.addItem(spacerItem)
        self.buttonBox = QtGui.QDialogButtonBox(BookmarkDialog)
        self.buttonBox.setOrientation(QtCore.Qt.Horizontal)
        self.buttonBox.setObjectName(_fromUtf8("buttonBox"))
        self.vboxlayout.addWidget(self.buttonBox)
        self.label.setBuddy(self.name)
        self.label_2.setBuddy(self.location)

        self.retranslateUi(BookmarkDialog)
        QtCore.QObject.connect(self.buttonBox, QtCore.SIGNAL(_fromUtf8("accepted()")), BookmarkDialog.accept)
        QtCore.QObject.connect(self.buttonBox, QtCore.SIGNAL(_fromUtf8("rejected()")), BookmarkDialog.reject)
        QtCore.QMetaObject.connectSlotsByName(BookmarkDialog)

    def retranslateUi(self, BookmarkDialog):
        self.label.setText(_translate("BookmarkDialog", "&Name:", None))
        self.label_2.setText(_translate("BookmarkDialog", "&Location:", None))

