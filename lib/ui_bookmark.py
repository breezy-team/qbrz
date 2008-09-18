# -*- coding: utf-8 -*-

# Form implementation generated from reading ui file 'ui/bookmark.ui'
#
# Created: Thu Sep 18 20:58:12 2008
#      by: PyQt4 UI code generator 4.4.2
#
# WARNING! All changes made in this file will be lost!

from PyQt4 import QtCore, QtGui
from bzrlib.plugins.qbzr.lib.i18n import gettext


class Ui_BookmarkDialog(object):
    def setupUi(self, BookmarkDialog):
        BookmarkDialog.setObjectName("BookmarkDialog")
        BookmarkDialog.resize(354, 90)
        self.vboxlayout = QtGui.QVBoxLayout(BookmarkDialog)
        self.vboxlayout.setObjectName("vboxlayout")
        self.gridlayout = QtGui.QGridLayout()
        self.gridlayout.setObjectName("gridlayout")
        self.label = QtGui.QLabel(BookmarkDialog)
        self.label.setObjectName("label")
        self.gridlayout.addWidget(self.label, 0, 0, 1, 1)
        self.name = QtGui.QLineEdit(BookmarkDialog)
        self.name.setObjectName("name")
        self.gridlayout.addWidget(self.name, 0, 1, 1, 1)
        self.label_2 = QtGui.QLabel(BookmarkDialog)
        self.label_2.setObjectName("label_2")
        self.gridlayout.addWidget(self.label_2, 1, 0, 1, 1)
        self.location = QtGui.QLineEdit(BookmarkDialog)
        self.location.setObjectName("location")
        self.gridlayout.addWidget(self.location, 1, 1, 1, 1)
        self.vboxlayout.addLayout(self.gridlayout)
        spacerItem = QtGui.QSpacerItem(336, 16, QtGui.QSizePolicy.Minimum, QtGui.QSizePolicy.Expanding)
        self.vboxlayout.addItem(spacerItem)
        self.buttonBox = QtGui.QDialogButtonBox(BookmarkDialog)
        self.buttonBox.setOrientation(QtCore.Qt.Horizontal)
        self.buttonBox.setObjectName("buttonBox")
        self.vboxlayout.addWidget(self.buttonBox)
        self.label.setBuddy(self.name)
        self.label_2.setBuddy(self.location)

        self.retranslateUi(BookmarkDialog)
        QtCore.QObject.connect(self.buttonBox, QtCore.SIGNAL("accepted()"), BookmarkDialog.accept)
        QtCore.QObject.connect(self.buttonBox, QtCore.SIGNAL("rejected()"), BookmarkDialog.reject)
        QtCore.QMetaObject.connectSlotsByName(BookmarkDialog)

    def retranslateUi(self, BookmarkDialog):
        self.label.setText(gettext("&Name:"))
        self.label_2.setText(gettext("&Location:"))

