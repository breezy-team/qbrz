# -*- coding: utf-8 -*-

# Form implementation generated from reading ui file 'ui/push.ui'
#
# Created: Wed Jul 30 14:20:50 2008
#      by: PyQt4 UI code generator 4.4.2
#
# WARNING! All changes made in this file will be lost!

from PyQt4 import QtCore, QtGui
from bzrlib.plugins.qbzr.lib.i18n import gettext


class Ui_PushForm(object):
    def setupUi(self, PushForm):
        PushForm.setObjectName("PushForm")
        PushForm.resize(294,153)
        self.gridLayout = QtGui.QGridLayout(PushForm)
        self.gridLayout.setObjectName("gridLayout")
        self.label_2 = QtGui.QLabel(PushForm)
        self.label_2.setObjectName("label_2")
        self.gridLayout.addWidget(self.label_2,0,0,1,1)
        self.location = QtGui.QComboBox(PushForm)
        sizePolicy = QtGui.QSizePolicy(QtGui.QSizePolicy.Expanding,QtGui.QSizePolicy.Fixed)
        sizePolicy.setHorizontalStretch(0)
        sizePolicy.setVerticalStretch(0)
        sizePolicy.setHeightForWidth(self.location.sizePolicy().hasHeightForWidth())
        self.location.setSizePolicy(sizePolicy)
        self.location.setEditable(True)
        self.location.setSizeAdjustPolicy(QtGui.QComboBox.AdjustToMinimumContentsLength)
        self.location.setObjectName("location")
        self.gridLayout.addWidget(self.location,0,1,1,1)
        self.location_picker = QtGui.QPushButton(PushForm)
        self.location_picker.setObjectName("location_picker")
        self.gridLayout.addWidget(self.location_picker,0,2,1,1)
        self.remember = QtGui.QCheckBox(PushForm)
        self.remember.setChecked(True)
        self.remember.setObjectName("remember")
        self.gridLayout.addWidget(self.remember,1,0,1,3)
        self.overwrite = QtGui.QCheckBox(PushForm)
        self.overwrite.setObjectName("overwrite")
        self.gridLayout.addWidget(self.overwrite,2,0,1,3)
        self.use_existing_dir = QtGui.QCheckBox(PushForm)
        self.use_existing_dir.setObjectName("use_existing_dir")
        self.gridLayout.addWidget(self.use_existing_dir,3,0,1,3)
        self.create_prefix = QtGui.QCheckBox(PushForm)
        self.create_prefix.setObjectName("create_prefix")
        self.gridLayout.addWidget(self.create_prefix,4,0,1,3)
        self.label_2.setBuddy(self.location)

        self.retranslateUi(PushForm)
        QtCore.QMetaObject.connectSlotsByName(PushForm)

    def retranslateUi(self, PushForm):
        PushForm.setTitle(gettext("Options"))
        self.label_2.setText(gettext("&Location:"))
        self.location_picker.setText(gettext("Browse..."))
        self.remember.setText(gettext("Remember this location as a default"))
        self.overwrite.setText(gettext("Overwrite differences between branches"))
        self.use_existing_dir.setText(gettext("Use existing directory"))
        self.create_prefix.setText(gettext("Create the path up to the branch if it does not exist"))

