# -*- coding: utf-8 -*-

# Form implementation generated from reading ui file 'ui/info.ui'
#
# Created: Wed May 11 11:25:59 2011
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
        self.horizontalLayout = QtGui.QHBoxLayout()
        self.horizontalLayout.setObjectName(_fromUtf8("horizontalLayout"))
        self.label_2 = QtGui.QLabel(InfoForm)
        self.label_2.setObjectName(_fromUtf8("label_2"))
        self.horizontalLayout.addWidget(self.label_2)
        self.local_location = QtGui.QLabel(InfoForm)
        self.local_location.setWordWrap(False)
        self.local_location.setTextInteractionFlags(QtCore.Qt.LinksAccessibleByMouse|QtCore.Qt.TextSelectableByKeyboard|QtCore.Qt.TextSelectableByMouse)
        self.local_location.setObjectName(_fromUtf8("local_location"))
        self.horizontalLayout.addWidget(self.local_location)
        spacerItem = QtGui.QSpacerItem(40, 20, QtGui.QSizePolicy.Expanding, QtGui.QSizePolicy.Minimum)
        self.horizontalLayout.addItem(spacerItem)
        self.verticalLayout.addLayout(self.horizontalLayout)
        self.tabWidget = QtGui.QTabWidget(InfoForm)
        self.tabWidget.setObjectName(_fromUtf8("tabWidget"))
        self.tab_basic = QtGui.QWidget()
        self.tab_basic.setObjectName(_fromUtf8("tab_basic"))
        self.verticalLayout_5 = QtGui.QVBoxLayout(self.tab_basic)
        self.verticalLayout_5.setObjectName(_fromUtf8("verticalLayout_5"))
        self.frame = QtGui.QFrame(self.tab_basic)
        self.frame.setFrameShape(QtGui.QFrame.NoFrame)
        self.frame.setFrameShadow(QtGui.QFrame.Plain)
        self.frame.setLineWidth(1)
        self.frame.setObjectName(_fromUtf8("frame"))
        self.verticalLayout_3 = QtGui.QVBoxLayout(self.frame)
        self.verticalLayout_3.setObjectName(_fromUtf8("verticalLayout_3"))
        self.basic_info = QtGui.QLabel(self.frame)
        self.basic_info.setAlignment(QtCore.Qt.AlignLeading|QtCore.Qt.AlignLeft|QtCore.Qt.AlignTop)
        self.basic_info.setObjectName(_fromUtf8("basic_info"))
        self.verticalLayout_3.addWidget(self.basic_info)
        self.verticalLayout_5.addWidget(self.frame)
        self.tabWidget.addTab(self.tab_basic, _fromUtf8(""))
        self.tab_detailed = QtGui.QWidget()
        self.tab_detailed.setObjectName(_fromUtf8("tab_detailed"))
        self.verticalLayout_6 = QtGui.QVBoxLayout(self.tab_detailed)
        self.verticalLayout_6.setObjectName(_fromUtf8("verticalLayout_6"))
        self.scrollArea = QtGui.QScrollArea(self.tab_detailed)
        self.scrollArea.setFrameShape(QtGui.QFrame.NoFrame)
        self.scrollArea.setFrameShadow(QtGui.QFrame.Plain)
        self.scrollArea.setLineWidth(1)
        self.scrollArea.setWidgetResizable(True)
        self.scrollArea.setObjectName(_fromUtf8("scrollArea"))
        self.scrollAreaWidgetContents = QtGui.QWidget(self.scrollArea)
        self.scrollAreaWidgetContents.setGeometry(QtCore.QRect(0, 0, 539, 179))
        self.scrollAreaWidgetContents.setObjectName(_fromUtf8("scrollAreaWidgetContents"))
        self.verticalLayout_2 = QtGui.QVBoxLayout(self.scrollAreaWidgetContents)
        self.verticalLayout_2.setObjectName(_fromUtf8("verticalLayout_2"))
        self.detailed_info = QtGui.QLabel(self.scrollAreaWidgetContents)
        self.detailed_info.setAlignment(QtCore.Qt.AlignLeading|QtCore.Qt.AlignLeft|QtCore.Qt.AlignTop)
        self.detailed_info.setObjectName(_fromUtf8("detailed_info"))
        self.verticalLayout_2.addWidget(self.detailed_info)
        self.scrollArea.setWidget(self.scrollAreaWidgetContents)
        self.verticalLayout_6.addWidget(self.scrollArea)
        self.tabWidget.addTab(self.tab_detailed, _fromUtf8(""))
        self.verticalLayout.addWidget(self.tabWidget)

        self.retranslateUi(InfoForm)
        self.tabWidget.setCurrentIndex(1)
        QtCore.QMetaObject.connectSlotsByName(InfoForm)

    def retranslateUi(self, InfoForm):
        self.label_2.setText(gettext("Location:"))
        self.local_location.setText(gettext("..."))
        self.basic_info.setText(gettext("Info"))
        self.tabWidget.setTabText(self.tabWidget.indexOf(self.tab_basic), gettext("&Basic"))
        self.detailed_info.setText(gettext("Info"))
        self.tabWidget.setTabText(self.tabWidget.indexOf(self.tab_detailed), gettext("&Detailed"))

