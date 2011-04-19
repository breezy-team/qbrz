# -*- coding: utf-8 -*-

# Form implementation generated from reading ui file 'ui/info.ui'
#
# Created: Tue Apr 19 11:26:26 2011
#      by: PyQt4 UI code generator 4.8.1
#
# WARNING! All changes made in this file will be lost!

from PyQt4 import QtCore, QtGui
from bzrlib.plugins.qbzr.lib.i18n import gettext


try:
    _fromUtf8 = QtCore.QString.fromUtf8
except AttributeError:
    _fromUtf8 = lambda s: s

class Ui_InfoForm(object):
    def setupUi(self, InfoForm):
        InfoForm.setObjectName(_fromUtf8("InfoForm"))
        InfoForm.resize(579, 266)
        self.verticalLayout = QtGui.QVBoxLayout(InfoForm)
        self.verticalLayout.setObjectName(_fromUtf8("verticalLayout"))
        self.formLayout = QtGui.QFormLayout()
        self.formLayout.setFieldGrowthPolicy(QtGui.QFormLayout.AllNonFixedFieldsGrow)
        self.formLayout.setObjectName(_fromUtf8("formLayout"))
        self.label_2 = QtGui.QLabel(InfoForm)
        self.label_2.setObjectName(_fromUtf8("label_2"))
        self.formLayout.setWidget(0, QtGui.QFormLayout.FieldRole, self.label_2)
        self.local_location = QtGui.QLabel(InfoForm)
        self.local_location.setWordWrap(True)
        self.local_location.setTextInteractionFlags(QtCore.Qt.LinksAccessibleByMouse|QtCore.Qt.TextSelectableByKeyboard|QtCore.Qt.TextSelectableByMouse)
        self.local_location.setObjectName(_fromUtf8("local_location"))
        self.formLayout.setWidget(0, QtGui.QFormLayout.LabelRole, self.local_location)
        self.verticalLayout.addLayout(self.formLayout)
        self.tabWidget = QtGui.QTabWidget(InfoForm)
        self.tabWidget.setObjectName(_fromUtf8("tabWidget"))
        self.tab_basic = QtGui.QWidget()
        self.tab_basic.setObjectName(_fromUtf8("tab_basic"))
        self.verticalLayout_5 = QtGui.QVBoxLayout(self.tab_basic)
        self.verticalLayout_5.setObjectName(_fromUtf8("verticalLayout_5"))
        self.basic_info = QtGui.QLabel(self.tab_basic)
        self.basic_info.setAlignment(QtCore.Qt.AlignLeading|QtCore.Qt.AlignLeft|QtCore.Qt.AlignTop)
        self.basic_info.setObjectName(_fromUtf8("basic_info"))
        self.verticalLayout_5.addWidget(self.basic_info)
        self.tabWidget.addTab(self.tab_basic, _fromUtf8(""))
        self.tab_detailed = QtGui.QWidget()
        self.tab_detailed.setObjectName(_fromUtf8("tab_detailed"))
        self.verticalLayout_6 = QtGui.QVBoxLayout(self.tab_detailed)
        self.verticalLayout_6.setObjectName(_fromUtf8("verticalLayout_6"))
        self.detailed_info = QtGui.QLabel(self.tab_detailed)
        self.detailed_info.setAlignment(QtCore.Qt.AlignLeading|QtCore.Qt.AlignLeft|QtCore.Qt.AlignTop)
        self.detailed_info.setObjectName(_fromUtf8("detailed_info"))
        self.verticalLayout_6.addWidget(self.detailed_info)
        self.tabWidget.addTab(self.tab_detailed, _fromUtf8(""))
        self.verticalLayout.addWidget(self.tabWidget)

        self.retranslateUi(InfoForm)
        self.tabWidget.setCurrentIndex(0)
        QtCore.QMetaObject.connectSlotsByName(InfoForm)

    def retranslateUi(self, InfoForm):
        self.label_2.setText(gettext("Location:"))
        self.local_location.setText(gettext("..."))
        self.basic_info.setText(gettext("Info"))
        self.tabWidget.setTabText(self.tabWidget.indexOf(self.tab_basic), gettext("&Basic"))
        self.detailed_info.setText(gettext("Info"))
        self.tabWidget.setTabText(self.tabWidget.indexOf(self.tab_detailed), gettext("&Detailed"))

