# -*- coding: utf-8 -*-

# Form implementation generated from reading ui file 'ui/info.ui'
#
# Created: Fri Aug 22 22:07:12 2008
#      by: PyQt4 UI code generator 4.3.3
#
# WARNING! All changes made in this file will be lost!

from PyQt4 import QtCore, QtGui
from bzrlib.plugins.qbzr.lib.i18n import gettext


class Ui_InfoForm(object):
    def setupUi(self, InfoForm):
        InfoForm.setObjectName("InfoForm")
        InfoForm.resize(QtCore.QSize(QtCore.QRect(0,0,469,289).size()).expandedTo(InfoForm.minimumSizeHint()))

        self.vboxlayout = QtGui.QVBoxLayout(InfoForm)
        self.vboxlayout.setObjectName("vboxlayout")

        self.tabWidget = QtGui.QTabWidget(InfoForm)
        self.tabWidget.setObjectName("tabWidget")

        self.tab = QtGui.QWidget()
        self.tab.setObjectName("tab")

        self.vboxlayout1 = QtGui.QVBoxLayout(self.tab)
        self.vboxlayout1.setObjectName("vboxlayout1")

        self.label_2 = QtGui.QLabel(self.tab)
        self.label_2.setObjectName("label_2")
        self.vboxlayout1.addWidget(self.label_2)

        self.local_location = QtGui.QLabel(self.tab)
        self.local_location.setWordWrap(True)
        self.local_location.setTextInteractionFlags(QtCore.Qt.LinksAccessibleByMouse|QtCore.Qt.TextSelectableByKeyboard|QtCore.Qt.TextSelectableByMouse)
        self.local_location.setObjectName("local_location")
        self.vboxlayout1.addWidget(self.local_location)

        self.label_4 = QtGui.QLabel(self.tab)
        self.label_4.setObjectName("label_4")
        self.vboxlayout1.addWidget(self.label_4)

        self.public_branch_location = QtGui.QLabel(self.tab)
        self.public_branch_location.setWordWrap(True)
        self.public_branch_location.setTextInteractionFlags(QtCore.Qt.LinksAccessibleByMouse|QtCore.Qt.TextSelectableByKeyboard|QtCore.Qt.TextSelectableByMouse)
        self.public_branch_location.setObjectName("public_branch_location")
        self.vboxlayout1.addWidget(self.public_branch_location)

        spacerItem = QtGui.QSpacerItem(20,132,QtGui.QSizePolicy.Minimum,QtGui.QSizePolicy.Expanding)
        self.vboxlayout1.addItem(spacerItem)
        self.tabWidget.addTab(self.tab,"")

        self.tab_2 = QtGui.QWidget()
        self.tab_2.setGeometry(QtCore.QRect(0,0,447,241))
        self.tab_2.setObjectName("tab_2")

        self.vboxlayout2 = QtGui.QVBoxLayout(self.tab_2)
        self.vboxlayout2.setObjectName("vboxlayout2")

        self.label = QtGui.QLabel(self.tab_2)
        self.label.setObjectName("label")
        self.vboxlayout2.addWidget(self.label)

        self.push_branch = QtGui.QLabel(self.tab_2)
        self.push_branch.setWordWrap(True)
        self.push_branch.setTextInteractionFlags(QtCore.Qt.LinksAccessibleByMouse|QtCore.Qt.TextSelectableByKeyboard|QtCore.Qt.TextSelectableByMouse)
        self.push_branch.setObjectName("push_branch")
        self.vboxlayout2.addWidget(self.push_branch)

        self.label_3 = QtGui.QLabel(self.tab_2)
        self.label_3.setObjectName("label_3")
        self.vboxlayout2.addWidget(self.label_3)

        self.parent_branch = QtGui.QLabel(self.tab_2)
        self.parent_branch.setWordWrap(True)
        self.parent_branch.setTextInteractionFlags(QtCore.Qt.LinksAccessibleByMouse|QtCore.Qt.TextSelectableByKeyboard|QtCore.Qt.TextSelectableByMouse)
        self.parent_branch.setObjectName("parent_branch")
        self.vboxlayout2.addWidget(self.parent_branch)

        self.label_6 = QtGui.QLabel(self.tab_2)
        self.label_6.setObjectName("label_6")
        self.vboxlayout2.addWidget(self.label_6)

        self.submit_branch = QtGui.QLabel(self.tab_2)
        self.submit_branch.setWordWrap(True)
        self.submit_branch.setTextInteractionFlags(QtCore.Qt.LinksAccessibleByMouse|QtCore.Qt.TextSelectableByKeyboard|QtCore.Qt.TextSelectableByMouse)
        self.submit_branch.setObjectName("submit_branch")
        self.vboxlayout2.addWidget(self.submit_branch)

        spacerItem1 = QtGui.QSpacerItem(20,88,QtGui.QSizePolicy.Minimum,QtGui.QSizePolicy.Expanding)
        self.vboxlayout2.addItem(spacerItem1)
        self.tabWidget.addTab(self.tab_2,"")

        self.tab_3 = QtGui.QWidget()
        self.tab_3.setObjectName("tab_3")

        self.gridlayout = QtGui.QGridLayout(self.tab_3)
        self.gridlayout.setObjectName("gridlayout")

        self.label_11 = QtGui.QLabel(self.tab_3)

        sizePolicy = QtGui.QSizePolicy(QtGui.QSizePolicy.Maximum,QtGui.QSizePolicy.Preferred)
        sizePolicy.setHorizontalStretch(0)
        sizePolicy.setVerticalStretch(0)
        sizePolicy.setHeightForWidth(self.label_11.sizePolicy().hasHeightForWidth())
        self.label_11.setSizePolicy(sizePolicy)
        self.label_11.setObjectName("label_11")
        self.gridlayout.addWidget(self.label_11,0,0,1,1)

        self.tree_format = QtGui.QLabel(self.tab_3)
        self.tree_format.setWordWrap(True)
        self.tree_format.setTextInteractionFlags(QtCore.Qt.LinksAccessibleByMouse|QtCore.Qt.TextSelectableByKeyboard|QtCore.Qt.TextSelectableByMouse)
        self.tree_format.setObjectName("tree_format")
        self.gridlayout.addWidget(self.tree_format,0,1,1,1)

        self.label_8 = QtGui.QLabel(self.tab_3)

        sizePolicy = QtGui.QSizePolicy(QtGui.QSizePolicy.Maximum,QtGui.QSizePolicy.Preferred)
        sizePolicy.setHorizontalStretch(0)
        sizePolicy.setVerticalStretch(0)
        sizePolicy.setHeightForWidth(self.label_8.sizePolicy().hasHeightForWidth())
        self.label_8.setSizePolicy(sizePolicy)
        self.label_8.setObjectName("label_8")
        self.gridlayout.addWidget(self.label_8,1,0,1,1)

        self.branch_format = QtGui.QLabel(self.tab_3)
        self.branch_format.setWordWrap(True)
        self.branch_format.setTextInteractionFlags(QtCore.Qt.LinksAccessibleByMouse|QtCore.Qt.TextSelectableByKeyboard|QtCore.Qt.TextSelectableByMouse)
        self.branch_format.setObjectName("branch_format")
        self.gridlayout.addWidget(self.branch_format,1,1,1,1)

        self.label_14 = QtGui.QLabel(self.tab_3)

        sizePolicy = QtGui.QSizePolicy(QtGui.QSizePolicy.Maximum,QtGui.QSizePolicy.Preferred)
        sizePolicy.setHorizontalStretch(0)
        sizePolicy.setVerticalStretch(0)
        sizePolicy.setHeightForWidth(self.label_14.sizePolicy().hasHeightForWidth())
        self.label_14.setSizePolicy(sizePolicy)
        self.label_14.setObjectName("label_14")
        self.gridlayout.addWidget(self.label_14,2,0,1,1)

        self.repository_format = QtGui.QLabel(self.tab_3)
        self.repository_format.setWordWrap(True)
        self.repository_format.setTextInteractionFlags(QtCore.Qt.LinksAccessibleByMouse|QtCore.Qt.TextSelectableByKeyboard|QtCore.Qt.TextSelectableByMouse)
        self.repository_format.setObjectName("repository_format")
        self.gridlayout.addWidget(self.repository_format,2,1,1,1)

        self.label_7 = QtGui.QLabel(self.tab_3)

        sizePolicy = QtGui.QSizePolicy(QtGui.QSizePolicy.Maximum,QtGui.QSizePolicy.Preferred)
        sizePolicy.setHorizontalStretch(0)
        sizePolicy.setVerticalStretch(0)
        sizePolicy.setHeightForWidth(self.label_7.sizePolicy().hasHeightForWidth())
        self.label_7.setSizePolicy(sizePolicy)
        self.label_7.setObjectName("label_7")
        self.gridlayout.addWidget(self.label_7,3,0,1,1)

        self.bzrdir_format = QtGui.QLabel(self.tab_3)
        self.bzrdir_format.setWordWrap(True)
        self.bzrdir_format.setTextInteractionFlags(QtCore.Qt.LinksAccessibleByMouse|QtCore.Qt.TextSelectableByKeyboard|QtCore.Qt.TextSelectableByMouse)
        self.bzrdir_format.setObjectName("bzrdir_format")
        self.gridlayout.addWidget(self.bzrdir_format,3,1,1,1)

        spacerItem2 = QtGui.QSpacerItem(298,132,QtGui.QSizePolicy.Minimum,QtGui.QSizePolicy.Expanding)
        self.gridlayout.addItem(spacerItem2,4,0,1,2)
        self.tabWidget.addTab(self.tab_3,"")
        self.vboxlayout.addWidget(self.tabWidget)

        self.retranslateUi(InfoForm)
        self.tabWidget.setCurrentIndex(0)
        QtCore.QMetaObject.connectSlotsByName(InfoForm)

    def retranslateUi(self, InfoForm):
        self.label_2.setText(gettext("Local location:"))
        self.local_location.setText(gettext("..."))
        self.label_4.setText(gettext("Public branch location:"))
        self.public_branch_location.setText(gettext("..."))
        self.tabWidget.setTabText(self.tabWidget.indexOf(self.tab), gettext("&Location"))
        self.label.setText(gettext("Push branch:"))
        self.push_branch.setText(gettext("..."))
        self.label_3.setText(gettext("Parent branch:"))
        self.parent_branch.setText(gettext("..."))
        self.label_6.setText(gettext("Submit branch:"))
        self.submit_branch.setText(gettext("..."))
        self.tabWidget.setTabText(self.tabWidget.indexOf(self.tab_2), gettext("&Related Branches"))
        self.label_11.setText(gettext("Working tree format:"))
        self.tree_format.setText(gettext("..."))
        self.label_8.setText(gettext("Branch format:"))
        self.branch_format.setText(gettext("..."))
        self.label_14.setText(gettext("Repository format:"))
        self.repository_format.setText(gettext("..."))
        self.label_7.setText(gettext("Control directory format:"))
        self.bzrdir_format.setText(gettext("..."))
        self.tabWidget.setTabText(self.tabWidget.indexOf(self.tab_3), gettext("&Format"))

