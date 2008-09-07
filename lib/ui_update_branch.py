# -*- coding: utf-8 -*-

# Form implementation generated from reading ui file 'ui/update_branch.ui'
#
# Created: Sat Sep 06 10:28:50 2008
#      by: PyQt4 UI code generator 4.4.2
#
# WARNING! All changes made in this file will be lost!

from PyQt4 import QtCore, QtGui
from bzrlib.plugins.qbzr.lib.i18n import gettext


class Ui_UpdateBranchForm(object):
    def setupUi(self, UpdateBranchForm):
        UpdateBranchForm.setObjectName("UpdateBranchForm")
        UpdateBranchForm.resize(640, 220)
        self.verticalLayout_3 = QtGui.QVBoxLayout(UpdateBranchForm)
        self.verticalLayout_3.setObjectName("verticalLayout_3")
        self.label = QtGui.QLabel(UpdateBranchForm)
        self.label.setScaledContents(False)
        self.label.setWordWrap(True)
        self.label.setObjectName("label")
        self.verticalLayout_3.addWidget(self.label)
        self.groupBox = QtGui.QGroupBox(UpdateBranchForm)
        sizePolicy = QtGui.QSizePolicy(QtGui.QSizePolicy.Preferred, QtGui.QSizePolicy.Preferred)
        sizePolicy.setHorizontalStretch(0)
        sizePolicy.setVerticalStretch(1)
        sizePolicy.setHeightForWidth(self.groupBox.sizePolicy().hasHeightForWidth())
        self.groupBox.setSizePolicy(sizePolicy)
        self.groupBox.setObjectName("groupBox")
        self.verticalLayout_2 = QtGui.QVBoxLayout(self.groupBox)
        self.verticalLayout_2.setObjectName("verticalLayout_2")
        self.but_pull = QtGui.QRadioButton(self.groupBox)
        self.but_pull.setChecked(True)
        self.but_pull.setObjectName("but_pull")
        self.verticalLayout_2.addWidget(self.but_pull)
        self.horizontalLayout_2 = QtGui.QHBoxLayout()
        self.horizontalLayout_2.setObjectName("horizontalLayout_2")
        spacerItem = QtGui.QSpacerItem(13, 98, QtGui.QSizePolicy.Fixed, QtGui.QSizePolicy.Minimum)
        self.horizontalLayout_2.addItem(spacerItem)
        self.verticalLayout = QtGui.QVBoxLayout()
        self.verticalLayout.setObjectName("verticalLayout")
        self.horizontalLayout = QtGui.QHBoxLayout()
        self.horizontalLayout.setObjectName("horizontalLayout")
        self.location = QtGui.QComboBox(self.groupBox)
        sizePolicy = QtGui.QSizePolicy(QtGui.QSizePolicy.Preferred, QtGui.QSizePolicy.Fixed)
        sizePolicy.setHorizontalStretch(1)
        sizePolicy.setVerticalStretch(0)
        sizePolicy.setHeightForWidth(self.location.sizePolicy().hasHeightForWidth())
        self.location.setSizePolicy(sizePolicy)
        self.location.setEditable(True)
        self.location.setObjectName("location")
        self.location.addItem(QtCore.QString())
        self.horizontalLayout.addWidget(self.location)
        self.location_picker = QtGui.QPushButton(self.groupBox)
        self.location_picker.setObjectName("location_picker")
        self.horizontalLayout.addWidget(self.location_picker)
        self.verticalLayout.addLayout(self.horizontalLayout)
        self.but_pull_remember = QtGui.QCheckBox(self.groupBox)
        self.but_pull_remember.setEnabled(True)
        self.but_pull_remember.setChecked(False)
        self.but_pull_remember.setObjectName("but_pull_remember")
        self.verticalLayout.addWidget(self.but_pull_remember)
        self.but_pull_overwrite = QtGui.QCheckBox(self.groupBox)
        self.but_pull_overwrite.setObjectName("but_pull_overwrite")
        self.verticalLayout.addWidget(self.but_pull_overwrite)
        self.horizontalLayout_2.addLayout(self.verticalLayout)
        self.verticalLayout_2.addLayout(self.horizontalLayout_2)
        self.but_update = QtGui.QRadioButton(self.groupBox)
        self.but_update.setObjectName("but_update")
        self.verticalLayout_2.addWidget(self.but_update)
        self.verticalLayout_3.addWidget(self.groupBox)

        self.retranslateUi(UpdateBranchForm)
        QtCore.QMetaObject.connectSlotsByName(UpdateBranchForm)

    def retranslateUi(self, UpdateBranchForm):
        UpdateBranchForm.setWindowTitle(gettext("Update Bazaar Branch"))
        self.label.setText(gettext("This directory is a branch.  Please select what you would like to update"))
        self.groupBox.setTitle(gettext("Update source"))
        self.but_pull.setText(gettext("Pull most recent changes from:"))
        self.location.setItemText(0, gettext("<Parent Branch shown here>"))
        self.location_picker.setText(gettext("Browse..."))
        self.but_pull_remember.setText(gettext("Remember this as the new parent branch"))
        self.but_pull_overwrite.setText(gettext("Overwrite differences between branches"))
        self.but_update.setText(gettext("Update working tree to the latest changes in the branch"))

