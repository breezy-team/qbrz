# -*- coding: utf-8 -*-

# Form implementation generated from reading ui file 'ui/info.ui'
#
# Created by: PyQt5 UI code generator 5.12.3
#
# WARNING! All changes made in this file will be lost!


from PyQt5 import QtCore, QtGui, QtWidgets
from breezy.plugins.qbrz.lib.i18n import gettext



class Ui_InfoForm(object):
    def setupUi(self, InfoForm):
        InfoForm.setObjectName("InfoForm")
        InfoForm.resize(579, 266)
        self.verticalLayout = QtWidgets.QVBoxLayout(InfoForm)
        self.verticalLayout.setObjectName("verticalLayout")
        self.horizontalLayout = QtWidgets.QHBoxLayout()
        self.horizontalLayout.setObjectName("horizontalLayout")
        self.label_2 = QtWidgets.QLabel(InfoForm)
        self.label_2.setObjectName("label_2")
        self.horizontalLayout.addWidget(self.label_2)
        self.local_location = QtWidgets.QLabel(InfoForm)
        self.local_location.setWordWrap(False)
        self.local_location.setTextInteractionFlags(QtCore.Qt.LinksAccessibleByMouse|QtCore.Qt.TextSelectableByKeyboard|QtCore.Qt.TextSelectableByMouse)
        self.local_location.setObjectName("local_location")
        self.horizontalLayout.addWidget(self.local_location)
        spacerItem = QtWidgets.QSpacerItem(40, 20, QtWidgets.QSizePolicy.Expanding, QtWidgets.QSizePolicy.Minimum)
        self.horizontalLayout.addItem(spacerItem)
        self.verticalLayout.addLayout(self.horizontalLayout)
        self.tabWidget = QtWidgets.QTabWidget(InfoForm)
        self.tabWidget.setObjectName("tabWidget")
        self.tab_basic = QtWidgets.QWidget()
        self.tab_basic.setObjectName("tab_basic")
        self.verticalLayout_5 = QtWidgets.QVBoxLayout(self.tab_basic)
        self.verticalLayout_5.setObjectName("verticalLayout_5")
        self.frame = QtWidgets.QFrame(self.tab_basic)
        self.frame.setFrameShape(QtWidgets.QFrame.NoFrame)
        self.frame.setFrameShadow(QtWidgets.QFrame.Plain)
        self.frame.setLineWidth(1)
        self.frame.setObjectName("frame")
        self.verticalLayout_3 = QtWidgets.QVBoxLayout(self.frame)
        self.verticalLayout_3.setObjectName("verticalLayout_3")
        self.basic_info = QtWidgets.QLabel(self.frame)
        self.basic_info.setAlignment(QtCore.Qt.AlignLeading|QtCore.Qt.AlignLeft|QtCore.Qt.AlignTop)
        self.basic_info.setObjectName("basic_info")
        self.verticalLayout_3.addWidget(self.basic_info)
        self.verticalLayout_5.addWidget(self.frame)
        self.tabWidget.addTab(self.tab_basic, "")
        self.tab_detailed = QtWidgets.QWidget()
        self.tab_detailed.setObjectName("tab_detailed")
        self.verticalLayout_6 = QtWidgets.QVBoxLayout(self.tab_detailed)
        self.verticalLayout_6.setObjectName("verticalLayout_6")
        self.scrollArea = QtWidgets.QScrollArea(self.tab_detailed)
        self.scrollArea.setFrameShape(QtWidgets.QFrame.NoFrame)
        self.scrollArea.setFrameShadow(QtWidgets.QFrame.Plain)
        self.scrollArea.setLineWidth(1)
        self.scrollArea.setWidgetResizable(True)
        self.scrollArea.setObjectName("scrollArea")
        self.scrollAreaWidgetContents = QtWidgets.QWidget()
        self.scrollAreaWidgetContents.setGeometry(QtCore.QRect(0, 0, 539, 179))
        self.scrollAreaWidgetContents.setObjectName("scrollAreaWidgetContents")
        self.verticalLayout_2 = QtWidgets.QVBoxLayout(self.scrollAreaWidgetContents)
        self.verticalLayout_2.setObjectName("verticalLayout_2")
        self.detailed_info = QtWidgets.QLabel(self.scrollAreaWidgetContents)
        self.detailed_info.setAlignment(QtCore.Qt.AlignLeading|QtCore.Qt.AlignLeft|QtCore.Qt.AlignTop)
        self.detailed_info.setObjectName("detailed_info")
        self.verticalLayout_2.addWidget(self.detailed_info)
        self.scrollArea.setWidget(self.scrollAreaWidgetContents)
        self.verticalLayout_6.addWidget(self.scrollArea)
        self.tabWidget.addTab(self.tab_detailed, "")
        self.verticalLayout.addWidget(self.tabWidget)

        self.retranslateUi(InfoForm)
        self.tabWidget.setCurrentIndex(1)
        QtCore.QMetaObject.connectSlotsByName(InfoForm)

    def retranslateUi(self, InfoForm):
        _translate = QtCore.QCoreApplication.translate
        self.label_2.setText(_translate("InfoForm", "Location:"))
        self.local_location.setText(_translate("InfoForm", "..."))
        self.basic_info.setText(_translate("InfoForm", "Info"))
        self.tabWidget.setTabText(self.tabWidget.indexOf(self.tab_basic), _translate("InfoForm", "&Basic"))
        self.detailed_info.setText(_translate("InfoForm", "Info"))
        self.tabWidget.setTabText(self.tabWidget.indexOf(self.tab_detailed), _translate("InfoForm", "&Detailed"))
