# -*- coding: utf-8 -*-

# Form implementation generated from reading ui file 'ui/merge_config.ui'
#
# Created by: PyQt5 UI code generator 5.12.3
#
# WARNING! All changes made in this file will be lost!


from PyQt5 import QtCore, QtGui, QtWidgets
from breezy.plugins.qbrz.lib.i18n import gettext



class Ui_MergeConfig(object):
    def setupUi(self, MergeConfig):
        MergeConfig.setObjectName("MergeConfig")
        MergeConfig.resize(544, 330)
        self.verticalLayout = QtWidgets.QVBoxLayout(MergeConfig)
        self.verticalLayout.setObjectName("verticalLayout")
        self.groupBox = QtWidgets.QGroupBox(MergeConfig)
        self.groupBox.setObjectName("groupBox")
        self.verticalLayout_2 = QtWidgets.QVBoxLayout(self.groupBox)
        self.verticalLayout_2.setObjectName("verticalLayout_2")
        self.tools = QtWidgets.QTableView(self.groupBox)
        self.tools.setSelectionBehavior(QtWidgets.QAbstractItemView.SelectRows)
        self.tools.setShowGrid(False)
        self.tools.setObjectName("tools")
        self.tools.horizontalHeader().setHighlightSections(False)
        self.tools.horizontalHeader().setStretchLastSection(True)
        self.tools.verticalHeader().setVisible(False)
        self.tools.verticalHeader().setDefaultSectionSize(15)
        self.tools.verticalHeader().setMinimumSectionSize(15)
        self.verticalLayout_2.addWidget(self.tools)
        self.widget = QtWidgets.QWidget(self.groupBox)
        self.widget.setObjectName("widget")
        self.horizontalLayout = QtWidgets.QHBoxLayout(self.widget)
        self.horizontalLayout.setObjectName("horizontalLayout")
        spacerItem = QtWidgets.QSpacerItem(40, 20, QtWidgets.QSizePolicy.Expanding, QtWidgets.QSizePolicy.Minimum)
        self.horizontalLayout.addItem(spacerItem)
        self.add = QtWidgets.QPushButton(self.widget)
        self.add.setObjectName("add")
        self.horizontalLayout.addWidget(self.add)
        self.remove = QtWidgets.QPushButton(self.widget)
        self.remove.setObjectName("remove")
        self.horizontalLayout.addWidget(self.remove)
        self.set_default = QtWidgets.QPushButton(self.widget)
        self.set_default.setObjectName("set_default")
        self.horizontalLayout.addWidget(self.set_default)
        spacerItem1 = QtWidgets.QSpacerItem(40, 20, QtWidgets.QSizePolicy.Expanding, QtWidgets.QSizePolicy.Minimum)
        self.horizontalLayout.addItem(spacerItem1)
        self.verticalLayout_2.addWidget(self.widget)
        self.verticalLayout.addWidget(self.groupBox)

        self.retranslateUi(MergeConfig)
        QtCore.QMetaObject.connectSlotsByName(MergeConfig)

    def retranslateUi(self, MergeConfig):
        _translate = QtCore.QCoreApplication.translate
        MergeConfig.setWindowTitle(_translate("MergeConfig", "Form"))
        self.groupBox.setTitle(_translate("MergeConfig", "External Merge Tools"))
        self.add.setText(_translate("MergeConfig", "Add"))
        self.remove.setText(_translate("MergeConfig", "Remove"))
        self.set_default.setToolTip(_translate("MergeConfig", "Sets the selected merge tool as the default to use in qconflicts."))
        self.set_default.setText(_translate("MergeConfig", "Set Default"))
