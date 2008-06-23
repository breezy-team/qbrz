# -*- coding: utf-8 -*-

# Form implementation generated from reading ui file 'ui/push.ui'
#
# Created: Wed Jun 18 15:52:44 2008
#      by: PyQt4 UI code generator 4.3.1
#
# WARNING! All changes made in this file will be lost!

from PyQt4 import QtCore, QtGui
from bzrlib.plugins.qbzr.lib.i18n import gettext


class Ui_PushForm(object):
    def setupUi(self, PushForm):
        PushForm.setObjectName("PushForm")
        PushForm.resize(QtCore.QSize(QtCore.QRect(0,0,429,400).size()).expandedTo(PushForm.minimumSizeHint()))

        self.vboxlayout = QtGui.QVBoxLayout(PushForm)
        self.vboxlayout.setObjectName("vboxlayout")

        self.groupBox = QtGui.QGroupBox(PushForm)
        self.groupBox.setObjectName("groupBox")

        self.gridlayout = QtGui.QGridLayout(self.groupBox)
        self.gridlayout.setObjectName("gridlayout")

        self.label_2 = QtGui.QLabel(self.groupBox)
        self.label_2.setObjectName("label_2")
        self.gridlayout.addWidget(self.label_2,0,0,1,1)

        self.location = QtGui.QComboBox(self.groupBox)

        sizePolicy = QtGui.QSizePolicy(QtGui.QSizePolicy.Expanding,QtGui.QSizePolicy.Fixed)
        sizePolicy.setHorizontalStretch(0)
        sizePolicy.setVerticalStretch(0)
        sizePolicy.setHeightForWidth(self.location.sizePolicy().hasHeightForWidth())
        self.location.setSizePolicy(sizePolicy)
        self.location.setEditable(True)
        self.location.setObjectName("location")
        self.gridlayout.addWidget(self.location,0,1,1,1)

        self.remember = QtGui.QCheckBox(self.groupBox)
        self.remember.setChecked(True)
        self.remember.setObjectName("remember")
        self.gridlayout.addWidget(self.remember,1,0,1,2)

        self.overwrite = QtGui.QCheckBox(self.groupBox)
        self.overwrite.setObjectName("overwrite")
        self.gridlayout.addWidget(self.overwrite,2,0,1,2)

        self.use_existing_dir = QtGui.QCheckBox(self.groupBox)
        self.use_existing_dir.setObjectName("use_existing_dir")
        self.gridlayout.addWidget(self.use_existing_dir,3,0,1,2)

        self.create_prefix = QtGui.QCheckBox(self.groupBox)
        self.create_prefix.setObjectName("create_prefix")
        self.gridlayout.addWidget(self.create_prefix,4,0,1,2)
        self.vboxlayout.addWidget(self.groupBox)

        self.groupBox_2 = QtGui.QGroupBox(PushForm)
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

        self.retranslateUi(PushForm)
        QtCore.QMetaObject.connectSlotsByName(PushForm)

    def retranslateUi(self, PushForm):
        self.groupBox.setTitle(gettext("Options"))
        self.label_2.setText(gettext("&Location:"))
        self.remember.setText(gettext("Remember this location as a default"))
        self.overwrite.setText(gettext("Overwrite differences between branches"))
        self.use_existing_dir.setText(gettext("Use existing directory"))
        self.create_prefix.setText(gettext("Create the path up to the branch if it does not exist"))
        self.groupBox_2.setTitle(gettext("Status"))
        self.progressMessage.setText(gettext("Stopped"))

