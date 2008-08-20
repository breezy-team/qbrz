# -*- coding: utf-8 -*-

# Form implementation generated from reading ui file 'ui/pull.ui'
#
# Created: Wed Aug 20 14:47:53 2008
#      by: PyQt4 UI code generator 4.4.3
#
# WARNING! All changes made in this file will be lost!

from PyQt4 import QtCore, QtGui
from bzrlib.plugins.qbzr.lib.i18n import gettext


class Ui_PullForm(object):
    def setupUi(self, PullForm):
        PullForm.setObjectName("PullForm")
        PullForm.resize(382, 340)
        self.vboxlayout = QtGui.QVBoxLayout(PullForm)
        self.vboxlayout.setObjectName("vboxlayout")
        self.groupBox = QtGui.QGroupBox(PullForm)
        self.groupBox.setObjectName("groupBox")
        self.gridlayout = QtGui.QGridLayout(self.groupBox)
        self.gridlayout.setObjectName("gridlayout")
        self.label_2 = QtGui.QLabel(self.groupBox)
        self.label_2.setObjectName("label_2")
        self.gridlayout.addWidget(self.label_2, 0, 0, 1, 1)
        self.location = QtGui.QComboBox(self.groupBox)
        self.location.setEditable(True)
        self.location.setObjectName("location")
        self.gridlayout.addWidget(self.location, 0, 1, 1, 2)
        self.location_picker = QtGui.QPushButton(self.groupBox)
        self.location_picker.setObjectName("location_picker")
        self.gridlayout.addWidget(self.location_picker, 0, 3, 1, 1)
        self.label_3 = QtGui.QLabel(self.groupBox)
        self.label_3.setObjectName("label_3")
        self.gridlayout.addWidget(self.label_3, 1, 0, 1, 1)
        self.revision = QtGui.QLineEdit(self.groupBox)
        self.revision.setObjectName("revision")
        self.gridlayout.addWidget(self.revision, 1, 1, 1, 1)
        spacerItem = QtGui.QSpacerItem(211, 20, QtGui.QSizePolicy.Expanding, QtGui.QSizePolicy.Minimum)
        self.gridlayout.addItem(spacerItem, 1, 2, 1, 1)
        self.remember = QtGui.QCheckBox(self.groupBox)
        self.remember.setChecked(True)
        self.remember.setObjectName("remember")
        self.gridlayout.addWidget(self.remember, 2, 0, 1, 3)
        self.overwrite = QtGui.QCheckBox(self.groupBox)
        self.overwrite.setObjectName("overwrite")
        self.gridlayout.addWidget(self.overwrite, 3, 0, 1, 3)
        self.vboxlayout.addWidget(self.groupBox)
        self.groupBox_2 = QtGui.QGroupBox(PullForm)
        self.groupBox_2.setObjectName("groupBox_2")
        self.vboxlayout1 = QtGui.QVBoxLayout(self.groupBox_2)
        self.vboxlayout1.setObjectName("vboxlayout1")
        self.progressMessage = QtGui.QLabel(self.groupBox_2)
        self.progressMessage.setWordWrap(True)
        self.progressMessage.setObjectName("progressMessage")
        self.vboxlayout1.addWidget(self.progressMessage)
        self.progressBar = QtGui.QProgressBar(self.groupBox_2)
        self.progressBar.setMaximum(1000000)
        self.progressBar.setObjectName("progressBar")
        self.vboxlayout1.addWidget(self.progressBar)
        self.console = QtGui.QTextBrowser(self.groupBox_2)
        self.console.setObjectName("console")
        self.vboxlayout1.addWidget(self.console)
        self.vboxlayout.addWidget(self.groupBox_2)
        self.label_2.setBuddy(self.location)
        self.label_3.setBuddy(self.revision)

        self.retranslateUi(PullForm)
        QtCore.QMetaObject.connectSlotsByName(PullForm)

    def retranslateUi(self, PullForm):
        self.groupBox.setTitle(gettext("Options"))
        self.label_2.setText(gettext("&Location:"))
        self.location_picker.setText(gettext("Browse..."))
        self.label_3.setText(gettext("&Revision:"))
        self.remember.setText(gettext("Remember this location as a default"))
        self.overwrite.setText(gettext("Overwrite differences between branches"))
        self.groupBox_2.setTitle(gettext("Status"))
        self.progressMessage.setText(gettext("Stopped"))

