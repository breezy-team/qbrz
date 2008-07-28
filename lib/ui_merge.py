# -*- coding: utf-8 -*-

# Form implementation generated from reading ui file 'ui/merge.ui'
#
# Created: Fri Aug 22 20:10:16 2008
#      by: PyQt4 UI code generator 4.3.3
#
# WARNING! All changes made in this file will be lost!

from PyQt4 import QtCore, QtGui
from bzrlib.plugins.qbzr.lib.i18n import gettext


class Ui_MergeForm(object):
    def setupUi(self, MergeForm):
        MergeForm.setObjectName("MergeForm")
        MergeForm.resize(QtCore.QSize(QtCore.QRect(0,0,382,341).size()).expandedTo(MergeForm.minimumSizeHint()))

        self.vboxlayout = QtGui.QVBoxLayout(MergeForm)
        self.vboxlayout.setObjectName("vboxlayout")

        self.groupBox = QtGui.QGroupBox(MergeForm)
        self.groupBox.setObjectName("groupBox")

        self.gridlayout = QtGui.QGridLayout(self.groupBox)
        self.gridlayout.setObjectName("gridlayout")

        self.label_2 = QtGui.QLabel(self.groupBox)
        self.label_2.setObjectName("label_2")
        self.gridlayout.addWidget(self.label_2,0,0,1,1)

        self.location = QtGui.QComboBox(self.groupBox)
        self.location.setEditable(True)
        self.location.setSizeAdjustPolicy(QtGui.QComboBox.AdjustToMinimumContentsLength)
        self.location.setObjectName("location")
        self.gridlayout.addWidget(self.location,0,1,1,2)

        self.location_picker = QtGui.QPushButton(self.groupBox)
        self.location_picker.setObjectName("location_picker")
        self.gridlayout.addWidget(self.location_picker,0,3,1,1)

        self.label_3 = QtGui.QLabel(self.groupBox)
        self.label_3.setObjectName("label_3")
        self.gridlayout.addWidget(self.label_3,1,0,1,1)

        self.revision = QtGui.QLineEdit(self.groupBox)
        self.revision.setObjectName("revision")
        self.gridlayout.addWidget(self.revision,1,1,1,1)

        spacerItem = QtGui.QSpacerItem(211,20,QtGui.QSizePolicy.Expanding,QtGui.QSizePolicy.Minimum)
        self.gridlayout.addItem(spacerItem,1,2,1,2)

        self.remember = QtGui.QCheckBox(self.groupBox)
        self.remember.setChecked(True)
        self.remember.setObjectName("remember")
        self.gridlayout.addWidget(self.remember,2,0,1,4)
        self.vboxlayout.addWidget(self.groupBox)

        self.groupBox_2 = QtGui.QGroupBox(MergeForm)
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

        self.retranslateUi(MergeForm)
        QtCore.QMetaObject.connectSlotsByName(MergeForm)

    def retranslateUi(self, MergeForm):
        self.groupBox.setTitle(gettext("Options"))
        self.label_2.setText(gettext("&Location:"))
        self.location_picker.setText(gettext("Browse..."))
        self.label_3.setText(gettext("&Revision:"))
        self.remember.setText(gettext("Remember this location as a default"))
        self.groupBox_2.setTitle(gettext("Status"))
        self.progressMessage.setText(gettext("Stopped"))

