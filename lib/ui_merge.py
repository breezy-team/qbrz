# -*- coding: utf-8 -*-

# Form implementation generated from reading ui file 'ui/merge.ui'
#
# Created: Tue Aug 18 15:10:52 2009
#      by: PyQt4 UI code generator 4.4.4
#
# WARNING! All changes made in this file will be lost!

from PyQt4 import QtCore, QtGui
from bzrlib.plugins.qbzr.lib.i18n import gettext


class Ui_MergeForm(object):
    def setupUi(self, MergeForm):
        MergeForm.setObjectName("MergeForm")
        MergeForm.resize(448, 248)
        self.verticalLayout = QtGui.QVBoxLayout(MergeForm)
        self.verticalLayout.setMargin(9)
        self.verticalLayout.setObjectName("verticalLayout")
        self.groupBox = QtGui.QGroupBox(MergeForm)
        self.groupBox.setObjectName("groupBox")
        self.gridLayout = QtGui.QGridLayout(self.groupBox)
        self.gridLayout.setObjectName("gridLayout")
        self.label_4 = QtGui.QLabel(self.groupBox)
        self.label_4.setObjectName("label_4")
        self.gridLayout.addWidget(self.label_4, 0, 0, 1, 1)
        self.location = QtGui.QComboBox(self.groupBox)
        self.location.setEditable(True)
        self.location.setSizeAdjustPolicy(QtGui.QComboBox.AdjustToMinimumContentsLength)
        self.location.setObjectName("location")
        self.gridLayout.addWidget(self.location, 0, 1, 1, 2)
        self.location_picker = QtGui.QPushButton(self.groupBox)
        self.location_picker.setObjectName("location_picker")
        self.gridLayout.addWidget(self.location_picker, 0, 3, 1, 1)
        self.label_3 = QtGui.QLabel(self.groupBox)
        self.label_3.setObjectName("label_3")
        self.gridLayout.addWidget(self.label_3, 1, 0, 1, 1)
        self.revision = QtGui.QLineEdit(self.groupBox)
        self.revision.setObjectName("revision")
        self.gridLayout.addWidget(self.revision, 1, 1, 1, 1)
        spacerItem = QtGui.QSpacerItem(107, 20, QtGui.QSizePolicy.Expanding, QtGui.QSizePolicy.Minimum)
        self.gridLayout.addItem(spacerItem, 1, 2, 1, 2)
        self.remember = QtGui.QCheckBox(self.groupBox)
        self.remember.setObjectName("remember")
        self.gridLayout.addWidget(self.remember, 2, 0, 1, 4)
        self.force = QtGui.QCheckBox(self.groupBox)
        self.force.setObjectName("force")
        self.gridLayout.addWidget(self.force, 3, 0, 1, 4)
        self.uncommitted = QtGui.QCheckBox(self.groupBox)
        self.uncommitted.setObjectName("uncommitted")
        self.gridLayout.addWidget(self.uncommitted, 4, 0, 1, 4)
        self.verticalLayout.addWidget(self.groupBox)
        self.label_4.setBuddy(self.revision)
        self.label_3.setBuddy(self.revision)

        self.retranslateUi(MergeForm)
        QtCore.QObject.connect(MergeForm, QtCore.SIGNAL("disableUi(bool)"), self.groupBox.setDisabled)
        QtCore.QMetaObject.connectSlotsByName(MergeForm)

    def retranslateUi(self, MergeForm):
        MergeForm.setWindowTitle(gettext("Merge"))
        self.groupBox.setTitle(gettext("Options"))
        self.label_4.setText(gettext("&Location:"))
        self.location_picker.setText(gettext("Browse..."))
        self.label_3.setText(gettext("&Revision:"))
        self.remember.setText(gettext("Remember this location as a default"))
        self.force.setText(gettext("Merge even if the working tree has uncommitted changes"))
        self.uncommitted.setText(gettext("Merge uncommitted changes instead of committed ones"))

