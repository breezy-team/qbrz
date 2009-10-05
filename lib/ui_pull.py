# -*- coding: utf-8 -*-

# Form implementation generated from reading ui file 'ui/pull.ui'
#
# Created: Mon Oct 05 19:41:19 2009
#      by: PyQt4 UI code generator 4.4.3
#
# WARNING! All changes made in this file will be lost!

from PyQt4 import QtCore, QtGui
from bzrlib.plugins.qbzr.lib.i18n import gettext


class Ui_PullForm(object):
    def setupUi(self, PullForm):
        PullForm.setObjectName("PullForm")
        PullForm.resize(404, 194)
        self.verticalLayout = QtGui.QVBoxLayout(PullForm)
        self.verticalLayout.setMargin(9)
        self.verticalLayout.setObjectName("verticalLayout")
        self.groupBox = QtGui.QGroupBox(PullForm)
        self.groupBox.setObjectName("groupBox")
        self.gridLayout = QtGui.QGridLayout(self.groupBox)
        self.gridLayout.setObjectName("gridLayout")
        self.label_2 = QtGui.QLabel(self.groupBox)
        self.label_2.setObjectName("label_2")
        self.gridLayout.addWidget(self.label_2, 0, 0, 1, 1)
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
        spacerItem = QtGui.QSpacerItem(211, 20, QtGui.QSizePolicy.Expanding, QtGui.QSizePolicy.Minimum)
        self.gridLayout.addItem(spacerItem, 1, 2, 1, 2)
        self.remember = QtGui.QCheckBox(self.groupBox)
        self.remember.setChecked(False)
        self.remember.setObjectName("remember")
        self.gridLayout.addWidget(self.remember, 2, 0, 1, 4)
        self.overwrite = QtGui.QCheckBox(self.groupBox)
        self.overwrite.setObjectName("overwrite")
        self.gridLayout.addWidget(self.overwrite, 3, 0, 1, 4)
        self.verticalLayout.addWidget(self.groupBox)
        self.label_2.setBuddy(self.location)
        self.label_3.setBuddy(self.revision)

        self.retranslateUi(PullForm)
        QtCore.QObject.connect(PullForm, QtCore.SIGNAL("disableUi(bool)"), self.groupBox.setDisabled)
        QtCore.QMetaObject.connectSlotsByName(PullForm)

    def retranslateUi(self, PullForm):
        PullForm.setWindowTitle(gettext("Pull"))
        self.groupBox.setTitle(gettext("Options"))
        self.label_2.setText(gettext("&Location:"))
        self.location_picker.setText(gettext("Browse..."))
        self.label_3.setText(gettext("&Revision:"))
        self.remember.setText(gettext("Remember this location as a default"))
        self.overwrite.setText(gettext("Overwrite differences between branches"))

