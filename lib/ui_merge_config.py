# -*- coding: utf-8 -*-

# Form implementation generated from reading ui file 'ui/merge_config.ui'
#
# Created: Tue Dec 07 00:17:33 2010
#      by: PyQt4 UI code generator 4.7.2
#
# WARNING! All changes made in this file will be lost!

from PyQt4 import QtCore, QtGui
from bzrlib.plugins.qbzr.lib.i18n import gettext


class Ui_MergeConfig(object):
    def setupUi(self, MergeConfig):
        MergeConfig.setObjectName("MergeConfig")
        MergeConfig.resize(544, 330)
        self.verticalLayout = QtGui.QVBoxLayout(MergeConfig)
        self.verticalLayout.setObjectName("verticalLayout")
        self.groupBox = QtGui.QGroupBox(MergeConfig)
        self.groupBox.setObjectName("groupBox")
        self.verticalLayout_2 = QtGui.QVBoxLayout(self.groupBox)
        self.verticalLayout_2.setObjectName("verticalLayout_2")
        self.tools = QtGui.QTableView(self.groupBox)
        self.tools.setSelectionBehavior(QtGui.QAbstractItemView.SelectRows)
        self.tools.setShowGrid(False)
        self.tools.setObjectName("tools")
        self.tools.horizontalHeader().setHighlightSections(False)
        self.tools.horizontalHeader().setStretchLastSection(True)
        self.tools.verticalHeader().setVisible(False)
        self.tools.verticalHeader().setDefaultSectionSize(15)
        self.tools.verticalHeader().setMinimumSectionSize(15)
        self.verticalLayout_2.addWidget(self.tools)
        self.widget = QtGui.QWidget(self.groupBox)
        self.widget.setObjectName("widget")
        self.horizontalLayout = QtGui.QHBoxLayout(self.widget)
        self.horizontalLayout.setObjectName("horizontalLayout")
        spacerItem = QtGui.QSpacerItem(40, 20, QtGui.QSizePolicy.Expanding, QtGui.QSizePolicy.Minimum)
        self.horizontalLayout.addItem(spacerItem)
        self.add = QtGui.QPushButton(self.widget)
        self.add.setObjectName("add")
        self.horizontalLayout.addWidget(self.add)
        self.remove = QtGui.QPushButton(self.widget)
        self.remove.setObjectName("remove")
        self.horizontalLayout.addWidget(self.remove)
        self.set_default = QtGui.QPushButton(self.widget)
        self.set_default.setObjectName("set_default")
        self.horizontalLayout.addWidget(self.set_default)
        spacerItem1 = QtGui.QSpacerItem(40, 20, QtGui.QSizePolicy.Expanding, QtGui.QSizePolicy.Minimum)
        self.horizontalLayout.addItem(spacerItem1)
        self.verticalLayout_2.addWidget(self.widget)
        self.verticalLayout.addWidget(self.groupBox)

        self.retranslateUi(MergeConfig)
        QtCore.QMetaObject.connectSlotsByName(MergeConfig)

    def retranslateUi(self, MergeConfig):
        MergeConfig.setWindowTitle(gettext("Form"))
        self.groupBox.setTitle(gettext("External Merge Tools"))
        self.add.setText(gettext("Add"))
        self.remove.setText(gettext("Remove"))
        self.set_default.setToolTip(gettext("Sets the selected merge tool as the default to use in qconflicts."))
        self.set_default.setText(gettext("Set Default"))

