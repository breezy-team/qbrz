# -*- coding: utf-8 -*-

# Form implementation generated from reading ui file 'ui/merge.ui'
#
# Created: Wed Jul 30 14:20:50 2008
#      by: PyQt4 UI code generator 4.4.2
#
# WARNING! All changes made in this file will be lost!

from PyQt4 import QtCore, QtGui
from bzrlib.plugins.qbzr.lib.i18n import gettext


class Ui_MergeForm(object):
    def setupUi(self, MergeForm):
        MergeForm.setObjectName("MergeForm")
        MergeForm.resize(420,107)
        self.gridLayout = QtGui.QGridLayout(MergeForm)
        self.gridLayout.setObjectName("gridLayout")
        self.label_2 = QtGui.QLabel(MergeForm)
        self.label_2.setObjectName("label_2")
        self.gridLayout.addWidget(self.label_2,0,0,1,1)
        self.location = QtGui.QComboBox(MergeForm)
        self.location.setEditable(True)
        self.location.setSizeAdjustPolicy(QtGui.QComboBox.AdjustToMinimumContentsLength)
        self.location.setObjectName("location")
        self.gridLayout.addWidget(self.location,0,1,1,2)
        self.location_picker = QtGui.QPushButton(MergeForm)
        self.location_picker.setObjectName("location_picker")
        self.gridLayout.addWidget(self.location_picker,0,3,1,1)
        self.label_3 = QtGui.QLabel(MergeForm)
        self.label_3.setObjectName("label_3")
        self.gridLayout.addWidget(self.label_3,1,0,1,1)
        self.revision = QtGui.QLineEdit(MergeForm)
        self.revision.setObjectName("revision")
        self.gridLayout.addWidget(self.revision,1,1,1,1)
        spacerItem = QtGui.QSpacerItem(211,20,QtGui.QSizePolicy.Expanding,QtGui.QSizePolicy.Minimum)
        self.gridLayout.addItem(spacerItem,1,2,1,2)
        self.remember = QtGui.QCheckBox(MergeForm)
        self.remember.setChecked(True)
        self.remember.setObjectName("remember")
        self.gridLayout.addWidget(self.remember,2,0,1,4)
        self.label_2.setBuddy(self.location)
        self.label_3.setBuddy(self.revision)

        self.retranslateUi(MergeForm)
        QtCore.QMetaObject.connectSlotsByName(MergeForm)

    def retranslateUi(self, MergeForm):
        MergeForm.setTitle(gettext("Options"))
        self.label_2.setText(gettext("&Location:"))
        self.location_picker.setText(gettext("Browse..."))
        self.label_3.setText(gettext("&Revision:"))
        self.remember.setText(gettext("Remember this location as a default"))

