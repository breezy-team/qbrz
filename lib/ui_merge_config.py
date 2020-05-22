# -*- coding: utf-8 -*-

# Form implementation generated from reading ui file 'ui/merge_config.ui'
#
# Created by: PyQt4 UI code generator 4.12.3
#
# WARNING! All changes made in this file will be lost!

from PyQt4 import QtCore, QtGui

try:
    _fromUtf8 = QtCore.QString.fromUtf8
except AttributeError:
    def _fromUtf8(s):
        return s

try:
    _encoding = QtGui.QApplication.UnicodeUTF8
    def _translate(context, text, disambig):
        return QtGui.QApplication.translate(context, text, disambig, _encoding)
except AttributeError:
    def _translate(context, text, disambig):
        return QtGui.QApplication.translate(context, text, disambig)

class Ui_MergeConfig(object):
    def setupUi(self, MergeConfig):
        MergeConfig.setObjectName(_fromUtf8("MergeConfig"))
        MergeConfig.resize(544, 330)
        self.verticalLayout = QtGui.QVBoxLayout(MergeConfig)
        self.verticalLayout.setObjectName(_fromUtf8("verticalLayout"))
        self.groupBox = QtGui.QGroupBox(MergeConfig)
        self.groupBox.setObjectName(_fromUtf8("groupBox"))
        self.verticalLayout_2 = QtGui.QVBoxLayout(self.groupBox)
        self.verticalLayout_2.setObjectName(_fromUtf8("verticalLayout_2"))
        self.tools = QtGui.QTableView(self.groupBox)
        self.tools.setSelectionBehavior(QtGui.QAbstractItemView.SelectRows)
        self.tools.setShowGrid(False)
        self.tools.setObjectName(_fromUtf8("tools"))
        self.tools.horizontalHeader().setHighlightSections(False)
        self.tools.horizontalHeader().setStretchLastSection(True)
        self.tools.verticalHeader().setVisible(False)
        self.tools.verticalHeader().setDefaultSectionSize(15)
        self.tools.verticalHeader().setMinimumSectionSize(15)
        self.verticalLayout_2.addWidget(self.tools)
        self.widget = QtGui.QWidget(self.groupBox)
        self.widget.setObjectName(_fromUtf8("widget"))
        self.horizontalLayout = QtGui.QHBoxLayout(self.widget)
        self.horizontalLayout.setMargin(0)
        self.horizontalLayout.setObjectName(_fromUtf8("horizontalLayout"))
        spacerItem = QtGui.QSpacerItem(40, 20, QtGui.QSizePolicy.Expanding, QtGui.QSizePolicy.Minimum)
        self.horizontalLayout.addItem(spacerItem)
        self.add = QtGui.QPushButton(self.widget)
        self.add.setObjectName(_fromUtf8("add"))
        self.horizontalLayout.addWidget(self.add)
        self.remove = QtGui.QPushButton(self.widget)
        self.remove.setObjectName(_fromUtf8("remove"))
        self.horizontalLayout.addWidget(self.remove)
        self.set_default = QtGui.QPushButton(self.widget)
        self.set_default.setObjectName(_fromUtf8("set_default"))
        self.horizontalLayout.addWidget(self.set_default)
        spacerItem1 = QtGui.QSpacerItem(40, 20, QtGui.QSizePolicy.Expanding, QtGui.QSizePolicy.Minimum)
        self.horizontalLayout.addItem(spacerItem1)
        self.verticalLayout_2.addWidget(self.widget)
        self.verticalLayout.addWidget(self.groupBox)

        self.retranslateUi(MergeConfig)
        QtCore.QMetaObject.connectSlotsByName(MergeConfig)

    def retranslateUi(self, MergeConfig):
        MergeConfig.setWindowTitle(_translate("MergeConfig", "Form", None))
        self.groupBox.setTitle(_translate("MergeConfig", "External Merge Tools", None))
        self.add.setText(_translate("MergeConfig", "Add", None))
        self.remove.setText(_translate("MergeConfig", "Remove", None))
        self.set_default.setToolTip(_translate("MergeConfig", "Sets the selected merge tool as the default to use in qconflicts.", None))
        self.set_default.setText(_translate("MergeConfig", "Set Default", None))

