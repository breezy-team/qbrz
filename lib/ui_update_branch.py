# -*- coding: utf-8 -*-

# Form implementation generated from reading ui file 'ui/update_branch.ui'
#
# Created: Thu Jul 30 12:22:19 2009
#      by: PyQt4 UI code generator 4.4.3
#
# WARNING! All changes made in this file will be lost!

from PyQt4 import QtCore, QtGui
from bzrlib.plugins.qbzr.lib.i18n import gettext


class Ui_UpdateBranchForm(object):
    def setupUi(self, UpdateBranchForm):
        UpdateBranchForm.setObjectName("UpdateBranchForm")
        UpdateBranchForm.resize(407, 198)
        self.verticalLayout_3 = QtGui.QVBoxLayout(UpdateBranchForm)
        self.verticalLayout_3.setMargin(9)
        self.verticalLayout_3.setObjectName("verticalLayout_3")
        self.label = QtGui.QLabel(UpdateBranchForm)
        self.label.setScaledContents(False)
        self.label.setWordWrap(False)
        self.label.setObjectName("label")
        self.verticalLayout_3.addWidget(self.label)
        self.groupBox = QtGui.QGroupBox(UpdateBranchForm)
        sizePolicy = QtGui.QSizePolicy(QtGui.QSizePolicy.Preferred, QtGui.QSizePolicy.Preferred)
        sizePolicy.setHorizontalStretch(0)
        sizePolicy.setVerticalStretch(1)
        sizePolicy.setHeightForWidth(self.groupBox.sizePolicy().hasHeightForWidth())
        self.groupBox.setSizePolicy(sizePolicy)
        self.groupBox.setObjectName("groupBox")
        self.gridLayout = QtGui.QGridLayout(self.groupBox)
        self.gridLayout.setObjectName("gridLayout")
        self.location_picker = QtGui.QPushButton(self.groupBox)
        self.location_picker.setObjectName("location_picker")
        self.gridLayout.addWidget(self.location_picker, 1, 2, 1, 1)
        self.but_pull = QtGui.QRadioButton(self.groupBox)
        self.but_pull.setChecked(True)
        self.but_pull.setObjectName("but_pull")
        self.gridLayout.addWidget(self.but_pull, 0, 0, 1, 3)
        self.but_pull_remember = QtGui.QCheckBox(self.groupBox)
        self.but_pull_remember.setEnabled(True)
        self.but_pull_remember.setChecked(False)
        self.but_pull_remember.setObjectName("but_pull_remember")
        self.gridLayout.addWidget(self.but_pull_remember, 2, 1, 1, 2)
        self.but_pull_overwrite = QtGui.QCheckBox(self.groupBox)
        self.but_pull_overwrite.setObjectName("but_pull_overwrite")
        self.gridLayout.addWidget(self.but_pull_overwrite, 3, 1, 1, 2)
        spacerItem = QtGui.QSpacerItem(17, 18, QtGui.QSizePolicy.Fixed, QtGui.QSizePolicy.Minimum)
        self.gridLayout.addItem(spacerItem, 3, 0, 1, 1)
        self.location = QtGui.QComboBox(self.groupBox)
        sizePolicy = QtGui.QSizePolicy(QtGui.QSizePolicy.Preferred, QtGui.QSizePolicy.Fixed)
        sizePolicy.setHorizontalStretch(1)
        sizePolicy.setVerticalStretch(0)
        sizePolicy.setHeightForWidth(self.location.sizePolicy().hasHeightForWidth())
        self.location.setSizePolicy(sizePolicy)
        self.location.setEditable(True)
        self.location.setSizeAdjustPolicy(QtGui.QComboBox.AdjustToMinimumContentsLength)
        self.location.setObjectName("location")
        self.location.addItem(QtCore.QString())
        self.gridLayout.addWidget(self.location, 1, 1, 1, 1)
        spacerItem1 = QtGui.QSpacerItem(18, 20, QtGui.QSizePolicy.Expanding, QtGui.QSizePolicy.Minimum)
        self.gridLayout.addItem(spacerItem1, 1, 0, 1, 1)
        spacerItem2 = QtGui.QSpacerItem(18, 17, QtGui.QSizePolicy.Expanding, QtGui.QSizePolicy.Minimum)
        self.gridLayout.addItem(spacerItem2, 2, 0, 1, 1)
        self.but_update = QtGui.QRadioButton(self.groupBox)
        self.but_update.setObjectName("but_update")
        self.gridLayout.addWidget(self.but_update, 4, 0, 1, 3)
        self.verticalLayout_3.addWidget(self.groupBox)

        self.retranslateUi(UpdateBranchForm)
        QtCore.QObject.connect(self.but_pull, QtCore.SIGNAL("toggled(bool)"), self.but_pull_remember.setEnabled)
        QtCore.QObject.connect(self.but_pull, QtCore.SIGNAL("toggled(bool)"), self.but_pull_overwrite.setEnabled)
        QtCore.QObject.connect(self.but_pull, QtCore.SIGNAL("toggled(bool)"), self.location.setEnabled)
        QtCore.QObject.connect(self.but_pull, QtCore.SIGNAL("toggled(bool)"), self.location_picker.setEnabled)
        QtCore.QObject.connect(UpdateBranchForm, QtCore.SIGNAL("disableUi(bool)"), self.label.setDisabled)
        QtCore.QObject.connect(UpdateBranchForm, QtCore.SIGNAL("disableUi(bool)"), self.groupBox.setDisabled)
        QtCore.QMetaObject.connectSlotsByName(UpdateBranchForm)

    def retranslateUi(self, UpdateBranchForm):
        UpdateBranchForm.setWindowTitle(gettext("Update Branch"))
        self.label.setText(gettext("This directory is a branch.  Please select what you would like to update"))
        self.groupBox.setTitle(gettext("Update source"))
        self.location_picker.setText(gettext("Browse..."))
        self.but_pull.setText(gettext("Pull most recent changes from:"))
        self.but_pull_remember.setText(gettext("Remember this as the new parent branch"))
        self.but_pull_overwrite.setText(gettext("Overwrite differences between branches"))
        self.location.setItemText(0, gettext("<Parent Branch shown here>"))
        self.but_update.setText(gettext("Update working tree to the latest changes in the branch"))

