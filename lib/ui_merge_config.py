# -*- coding: utf-8 -*-

# Form implementation generated from reading ui file 'ui/merge_config.ui'
#
# Created: Sun Nov 07 17:00:49 2010
#      by: PyQt4 UI code generator 4.7.2
#
# WARNING! All changes made in this file will be lost!

from PyQt4 import QtCore, QtGui
from bzrlib.plugins.qbzr.lib.i18n import gettext


class Ui_MergeConfig(object):
    def setupUi(self, MergeConfig):
        MergeConfig.setObjectName("MergeConfig")
        MergeConfig.resize(626, 297)
        self.verticalLayout_2 = QtGui.QVBoxLayout(MergeConfig)
        self.verticalLayout_2.setObjectName("verticalLayout_2")
        self.groupBox = QtGui.QGroupBox(MergeConfig)
        self.groupBox.setObjectName("groupBox")
        self.verticalLayout_3 = QtGui.QVBoxLayout(self.groupBox)
        self.verticalLayout_3.setObjectName("verticalLayout_3")
        self.splitter = QtGui.QSplitter(self.groupBox)
        self.splitter.setOrientation(QtCore.Qt.Horizontal)
        self.splitter.setChildrenCollapsible(False)
        self.splitter.setObjectName("splitter")
        self.layoutWidget = QtGui.QWidget(self.splitter)
        self.layoutWidget.setObjectName("layoutWidget")
        self.verticalLayout = QtGui.QVBoxLayout(self.layoutWidget)
        self.verticalLayout.setObjectName("verticalLayout")
        self.merge_tools_list = QtGui.QListView(self.layoutWidget)
        self.merge_tools_list.setObjectName("merge_tools_list")
        self.verticalLayout.addWidget(self.merge_tools_list)
        self.merge_tools_buttons = QtGui.QWidget(self.layoutWidget)
        self.merge_tools_buttons.setObjectName("merge_tools_buttons")
        self.horizontalLayout = QtGui.QHBoxLayout(self.merge_tools_buttons)
        self.horizontalLayout.setObjectName("horizontalLayout")
        spacerItem = QtGui.QSpacerItem(40, 20, QtGui.QSizePolicy.Expanding, QtGui.QSizePolicy.Minimum)
        self.horizontalLayout.addItem(spacerItem)
        self.merge_tools_add = QtGui.QPushButton(self.merge_tools_buttons)
        self.merge_tools_add.setObjectName("merge_tools_add")
        self.horizontalLayout.addWidget(self.merge_tools_add)
        self.merge_tools_remove = QtGui.QPushButton(self.merge_tools_buttons)
        self.merge_tools_remove.setObjectName("merge_tools_remove")
        self.horizontalLayout.addWidget(self.merge_tools_remove)
        self.merge_tools_detect = QtGui.QPushButton(self.merge_tools_buttons)
        self.merge_tools_detect.setObjectName("merge_tools_detect")
        self.horizontalLayout.addWidget(self.merge_tools_detect)
        spacerItem1 = QtGui.QSpacerItem(40, 20, QtGui.QSizePolicy.Expanding, QtGui.QSizePolicy.Minimum)
        self.horizontalLayout.addItem(spacerItem1)
        self.verticalLayout.addWidget(self.merge_tools_buttons)
        self.merge_tool_details = QtGui.QWidget(self.splitter)
        self.merge_tool_details.setMinimumSize(QtCore.QSize(300, 0))
        self.merge_tool_details.setObjectName("merge_tool_details")
        self.gridLayout = QtGui.QGridLayout(self.merge_tool_details)
        self.gridLayout.setContentsMargins(-1, 0, -1, 0)
        self.gridLayout.setObjectName("gridLayout")
        self.label = QtGui.QLabel(self.merge_tool_details)
        self.label.setObjectName("label")
        self.gridLayout.addWidget(self.label, 0, 0, 1, 1)
        self.merge_tool_name = QtGui.QLineEdit(self.merge_tool_details)
        self.merge_tool_name.setObjectName("merge_tool_name")
        self.gridLayout.addWidget(self.merge_tool_name, 1, 0, 1, 1)
        self.label_2 = QtGui.QLabel(self.merge_tool_details)
        self.label_2.setObjectName("label_2")
        self.gridLayout.addWidget(self.label_2, 2, 0, 1, 1)
        self.merge_tool_commandline = QtGui.QLineEdit(self.merge_tool_details)
        self.merge_tool_commandline.setObjectName("merge_tool_commandline")
        self.gridLayout.addWidget(self.merge_tool_commandline, 3, 0, 1, 1)
        self.merge_tool_browse = QtGui.QToolButton(self.merge_tool_details)
        self.merge_tool_browse.setObjectName("merge_tool_browse")
        self.gridLayout.addWidget(self.merge_tool_browse, 3, 1, 1, 1)
        spacerItem2 = QtGui.QSpacerItem(248, 130, QtGui.QSizePolicy.Minimum, QtGui.QSizePolicy.Expanding)
        self.gridLayout.addItem(spacerItem2, 6, 0, 1, 1)
        self.merge_tool_default = QtGui.QCheckBox(self.merge_tool_details)
        self.merge_tool_default.setObjectName("merge_tool_default")
        self.gridLayout.addWidget(self.merge_tool_default, 4, 0, 1, 1)
        self.verticalLayout_3.addWidget(self.splitter)
        self.verticalLayout_2.addWidget(self.groupBox)
        self.label.setBuddy(self.merge_tool_name)
        self.label_2.setBuddy(self.merge_tool_commandline)

        self.retranslateUi(MergeConfig)
        QtCore.QMetaObject.connectSlotsByName(MergeConfig)

    def retranslateUi(self, MergeConfig):
        MergeConfig.setWindowTitle(gettext("External Merge Tools"))
        self.groupBox.setTitle(gettext("External Merge Tools"))
        self.merge_tools_add.setText(gettext("Add"))
        self.merge_tools_remove.setText(gettext("Remove"))
        self.merge_tools_detect.setText(gettext("Detect"))
        self.label.setText(gettext("Name:"))
        self.label_2.setText(gettext("Command line:"))
        self.merge_tool_browse.setText(gettext("..."))
        self.merge_tool_default.setText(gettext("Default"))

