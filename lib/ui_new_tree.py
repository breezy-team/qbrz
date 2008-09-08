# -*- coding: utf-8 -*-

# Form implementation generated from reading ui file 'ui/new_tree.ui'
#
# Created: Mon Sep 08 16:37:30 2008
#      by: PyQt4 UI code generator 4.4.2
#
# WARNING! All changes made in this file will be lost!

from PyQt4 import QtCore, QtGui
from bzrlib.plugins.qbzr.lib.i18n import gettext


class Ui_NewWorkingTreeForm(object):
    def setupUi(self, NewWorkingTreeForm):
        NewWorkingTreeForm.setObjectName("NewWorkingTreeForm")
        NewWorkingTreeForm.resize(435, 391)
        self.verticalLayout = QtGui.QVBoxLayout(NewWorkingTreeForm)
        self.verticalLayout.setObjectName("verticalLayout")
        self.groupBox = QtGui.QGroupBox(NewWorkingTreeForm)
        self.groupBox.setObjectName("groupBox")
        self.gridLayout = QtGui.QGridLayout(self.groupBox)
        self.gridLayout.setObjectName("gridLayout")
        self.label_4 = QtGui.QLabel(self.groupBox)
        self.label_4.setObjectName("label_4")
        self.gridLayout.addWidget(self.label_4, 0, 0, 1, 2)
        self.from_location = QtGui.QComboBox(self.groupBox)
        self.from_location.setEditable(True)
        self.from_location.setSizeAdjustPolicy(QtGui.QComboBox.AdjustToMinimumContentsLength)
        self.from_location.setObjectName("from_location")
        self.gridLayout.addWidget(self.from_location, 1, 0, 1, 1)
        self.from_picker = QtGui.QPushButton(self.groupBox)
        self.from_picker.setObjectName("from_picker")
        self.gridLayout.addWidget(self.from_picker, 1, 1, 1, 1)
        self.label = QtGui.QLabel(self.groupBox)
        font = QtGui.QFont()
        font.setUnderline(False)
        self.label.setFont(font)
        self.label.setOpenExternalLinks(False)
        self.label.setObjectName("label")
        self.gridLayout.addWidget(self.label, 2, 0, 1, 2)
        self.to_location = QtGui.QLineEdit(self.groupBox)
        self.to_location.setObjectName("to_location")
        self.gridLayout.addWidget(self.to_location, 3, 0, 1, 1)
        self.to_picker = QtGui.QPushButton(self.groupBox)
        self.to_picker.setObjectName("to_picker")
        self.gridLayout.addWidget(self.to_picker, 3, 1, 1, 1)
        self.verticalLayout.addWidget(self.groupBox)
        self.groupBox_3 = QtGui.QGroupBox(NewWorkingTreeForm)
        self.groupBox_3.setObjectName("groupBox_3")
        self.gridLayout_2 = QtGui.QGridLayout(self.groupBox_3)
        self.gridLayout_2.setObjectName("gridLayout_2")
        self.but_checkout = QtGui.QRadioButton(self.groupBox_3)
        self.but_checkout.setChecked(True)
        self.but_checkout.setObjectName("but_checkout")
        self.gridLayout_2.addWidget(self.but_checkout, 0, 0, 1, 2)
        spacerItem = QtGui.QSpacerItem(18, 20, QtGui.QSizePolicy.Fixed, QtGui.QSizePolicy.Minimum)
        self.gridLayout_2.addItem(spacerItem, 1, 0, 1, 1)
        self.but_lightweight = QtGui.QCheckBox(self.groupBox_3)
        sizePolicy = QtGui.QSizePolicy(QtGui.QSizePolicy.Minimum, QtGui.QSizePolicy.Fixed)
        sizePolicy.setHorizontalStretch(1)
        sizePolicy.setVerticalStretch(0)
        sizePolicy.setHeightForWidth(self.but_lightweight.sizePolicy().hasHeightForWidth())
        self.but_lightweight.setSizePolicy(sizePolicy)
        self.but_lightweight.setObjectName("but_lightweight")
        self.gridLayout_2.addWidget(self.but_lightweight, 1, 1, 1, 1)
        self.but_branch = QtGui.QRadioButton(self.groupBox_3)
        self.but_branch.setObjectName("but_branch")
        self.gridLayout_2.addWidget(self.but_branch, 2, 0, 1, 2)
        spacerItem1 = QtGui.QSpacerItem(18, 20, QtGui.QSizePolicy.Fixed, QtGui.QSizePolicy.Minimum)
        self.gridLayout_2.addItem(spacerItem1, 3, 0, 1, 1)
        self.but_stacked = QtGui.QCheckBox(self.groupBox_3)
        self.but_stacked.setEnabled(False)
        self.but_stacked.setObjectName("but_stacked")
        self.gridLayout_2.addWidget(self.but_stacked, 3, 1, 1, 1)
        self.link_help = QtGui.QLabel(self.groupBox_3)
        font = QtGui.QFont()
        font.setUnderline(True)
        self.link_help.setFont(font)
        self.link_help.setCursor(QtCore.Qt.PointingHandCursor)
        self.link_help.setTextFormat(QtCore.Qt.RichText)
        self.link_help.setOpenExternalLinks(False)
        self.link_help.setTextInteractionFlags(QtCore.Qt.TextBrowserInteraction)
        self.link_help.setObjectName("link_help")
        self.gridLayout_2.addWidget(self.link_help, 4, 0, 1, 2)
        self.verticalLayout.addWidget(self.groupBox_3)
        self.groupBox_2 = QtGui.QGroupBox(NewWorkingTreeForm)
        self.groupBox_2.setObjectName("groupBox_2")
        self.gridLayout_3 = QtGui.QGridLayout(self.groupBox_2)
        self.gridLayout_3.setObjectName("gridLayout_3")
        self.but_rev_tip = QtGui.QRadioButton(self.groupBox_2)
        self.but_rev_tip.setChecked(True)
        self.but_rev_tip.setObjectName("but_rev_tip")
        self.gridLayout_3.addWidget(self.but_rev_tip, 0, 0, 1, 2)
        self.but_rev_specific = QtGui.QRadioButton(self.groupBox_2)
        self.but_rev_specific.setObjectName("but_rev_specific")
        self.gridLayout_3.addWidget(self.but_rev_specific, 1, 0, 1, 1)
        self.revision = QtGui.QLineEdit(self.groupBox_2)
        self.revision.setObjectName("revision")
        self.gridLayout_3.addWidget(self.revision, 1, 1, 1, 1)
        spacerItem2 = QtGui.QSpacerItem(208, 20, QtGui.QSizePolicy.Expanding, QtGui.QSizePolicy.Minimum)
        self.gridLayout_3.addItem(spacerItem2, 1, 2, 1, 1)
        self.but_show_log = QtGui.QPushButton(self.groupBox_2)
        self.but_show_log.setEnabled(False)
        self.but_show_log.setObjectName("but_show_log")
        self.gridLayout_3.addWidget(self.but_show_log, 1, 3, 1, 1)
        self.verticalLayout.addWidget(self.groupBox_2)

        self.retranslateUi(NewWorkingTreeForm)
        QtCore.QMetaObject.connectSlotsByName(NewWorkingTreeForm)

    def retranslateUi(self, NewWorkingTreeForm):
        NewWorkingTreeForm.setWindowTitle(gettext("Create a new Bazaar Working Tree"))
        self.groupBox.setTitle(gettext("Branch"))
        self.label_4.setText(gettext("Branch source (enter a URL or select a local directory with an exiting branch)"))
        self.from_picker.setText(gettext("Browse..."))
        self.label.setText(gettext("Local directory where the working tree will be created"))
        self.to_picker.setText(gettext("Browse..."))
        self.groupBox_3.setTitle(gettext("Working Tree Options"))
        self.but_checkout.setText(gettext("Create a checkout"))
        self.but_lightweight.setToolTip(QtGui.QApplication.translate("NewWorkingTreeForm", "<!DOCTYPE HTML PUBLIC \"-//W3C//DTD HTML 4.0//EN\" \"http://www.w3.org/TR/REC-html40/strict.dtd\">\n"
"<html><head><meta name=\"qrichtext\" content=\"1\" /><style type=\"text/css\">\n"
"p, li { white-space: pre-wrap; }\n"
"</style></head><body style=\" font-family:\'MS Shell Dlg 2\'; font-size:8.25pt; font-weight:400; font-style:normal;\">\n"
"<p style=\" margin-top:0px; margin-bottom:0px; margin-left:0px; margin-right:0px; -qt-block-indent:0; text-indent:0px;\"><span style=\" font-style:italic;\">Lightweight checkouts </span>depend on access to the branch for every operation.</p>\n"
"<p style=\" margin-top:0px; margin-bottom:0px; margin-left:0px; margin-right:0px; -qt-block-indent:0; text-indent:0px;\">Normal checkouts can perform common operations like diff and status without such access, and also support local commits.</p>\n"
"<p style=\"-qt-paragraph-type:empty; margin-top:0px; margin-bottom:0px; margin-left:0px; margin-right:0px; -qt-block-indent:0; text-indent:0px;\"></p></body></html>", None, QtGui.QApplication.UnicodeUTF8))
        self.but_lightweight.setText(gettext("Light-weight checkout"))
        self.but_branch.setText(gettext("Make a local copy of the branch"))
        self.but_stacked.setToolTip(QtGui.QApplication.translate("NewWorkingTreeForm", "<!DOCTYPE HTML PUBLIC \"-//W3C//DTD HTML 4.0//EN\" \"http://www.w3.org/TR/REC-html40/strict.dtd\">\n"
"<html><head><meta name=\"qrichtext\" content=\"1\" /><style type=\"text/css\">\n"
"p, li { white-space: pre-wrap; }\n"
"</style></head><body style=\" font-family:\'MS Shell Dlg 2\'; font-size:8.25pt; font-weight:400; font-style:normal;\">\n"
"<p style=\" margin-top:0px; margin-bottom:0px; margin-left:0px; margin-right:0px; -qt-block-indent:0; text-indent:0px;\">A <span style=\" font-style:italic;\">stacked branch</span> only stores information not in the source branch, and as such, depends on the availability of the source branch</p></body></html>", None, QtGui.QApplication.UnicodeUTF8))
        self.but_stacked.setText(gettext("Create a stacked branch referring to the source branch"))
        self.link_help.setToolTip(QtGui.QApplication.translate("NewWorkingTreeForm", "<!DOCTYPE HTML PUBLIC \"-//W3C//DTD HTML 4.0//EN\" \"http://www.w3.org/TR/REC-html40/strict.dtd\">\n"
"<html><head><meta name=\"qrichtext\" content=\"1\" /><style type=\"text/css\">\n"
"p, li { white-space: pre-wrap; }\n"
"</style></head><body style=\" font-family:\'MS Shell Dlg 2\'; font-size:8.25pt; font-weight:400; font-style:normal;\">\n"
"<p style=\" margin-top:0px; margin-bottom:0px; margin-left:0px; margin-right:0px; -qt-block-indent:0; text-indent:0px;\"><span style=\" font-weight:600; text-decoration: underline;\">Checkouts</span></p>\n"
"<p style=\"-qt-paragraph-type:empty; margin-top:0px; margin-bottom:0px; margin-left:0px; margin-right:0px; -qt-block-indent:0; text-indent:0px;\"></p>\n"
"<p style=\" margin-top:0px; margin-bottom:0px; margin-left:0px; margin-right:0px; -qt-block-indent:0; text-indent:0px;\">Checkouts are source trees that are connected to a branch, so that when</p>\n"
"<p style=\" margin-top:0px; margin-bottom:0px; margin-left:0px; margin-right:0px; -qt-block-indent:0; text-indent:0px;\">you commit in the source tree, the commit goes into that branch.  They</p>\n"
"<p style=\" margin-top:0px; margin-bottom:0px; margin-left:0px; margin-right:0px; -qt-block-indent:0; text-indent:0px;\">allow you to use a simpler, more centralized workflow, ignoring some of</p>\n"
"<p style=\" margin-top:0px; margin-bottom:0px; margin-left:0px; margin-right:0px; -qt-block-indent:0; text-indent:0px;\">Bazaar\'s decentralized features until you want them. Using checkouts</p>\n"
"<p style=\" margin-top:0px; margin-bottom:0px; margin-left:0px; margin-right:0px; -qt-block-indent:0; text-indent:0px;\">with shared repositories is very similar to working with SVN or CVS, but</p>\n"
"<p style=\" margin-top:0px; margin-bottom:0px; margin-left:0px; margin-right:0px; -qt-block-indent:0; text-indent:0px;\">doesn\'t have the same restrictions.  And using checkouts still allows</p>\n"
"<p style=\" margin-top:0px; margin-bottom:0px; margin-left:0px; margin-right:0px; -qt-block-indent:0; text-indent:0px;\">others working on the project to use whatever workflow they like.</p>\n"
"<p style=\"-qt-paragraph-type:empty; margin-top:0px; margin-bottom:0px; margin-left:0px; margin-right:0px; -qt-block-indent:0; text-indent:0px; font-weight:600;\"></p>\n"
"<p style=\" margin-top:0px; margin-bottom:0px; margin-left:0px; margin-right:0px; -qt-block-indent:0; text-indent:0px; font-weight:600;\"><span style=\" text-decoration: underline;\">Branches</span></p>\n"
"<p style=\"-qt-paragraph-type:empty; margin-top:0px; margin-bottom:0px; margin-left:0px; margin-right:0px; -qt-block-indent:0; text-indent:0px;\"></p>\n"
"<p style=\" margin-top:0px; margin-bottom:0px; margin-left:0px; margin-right:0px; -qt-block-indent:0; text-indent:0px;\">A branch consists of the state of a project, including all of its</p>\n"
"<p style=\" margin-top:0px; margin-bottom:0px; margin-left:0px; margin-right:0px; -qt-block-indent:0; text-indent:0px;\">history. All branches have a repository associated (which is where the</p>\n"
"<p style=\" margin-top:0px; margin-bottom:0px; margin-left:0px; margin-right:0px; -qt-block-indent:0; text-indent:0px;\">branch history is stored), but multiple branches may share the same</p>\n"
"<p style=\" margin-top:0px; margin-bottom:0px; margin-left:0px; margin-right:0px; -qt-block-indent:0; text-indent:0px;\">repository (a shared repository). Branches can be copied and merged.</p>\n"
"<p style=\"-qt-paragraph-type:empty; margin-top:0px; margin-bottom:0px; margin-left:0px; margin-right:0px; -qt-block-indent:0; text-indent:0px;\"></p></body></html>", None, QtGui.QApplication.UnicodeUTF8))
        self.link_help.setText(QtGui.QApplication.translate("NewWorkingTreeForm", "<!DOCTYPE HTML PUBLIC \"-//W3C//DTD HTML 4.0//EN\" \"http://www.w3.org/TR/REC-html40/strict.dtd\">\n"
"<html><head><meta name=\"qrichtext\" content=\"1\" /><style type=\"text/css\">\n"
"p, li { white-space: pre-wrap; }\n"
"</style></head><body style=\" font-family:\'MS Shell Dlg 2\'; font-size:8.25pt; font-weight:400; font-style:normal;\">\n"
"<p style=\" margin-top:0px; margin-bottom:0px; margin-left:0px; margin-right:0px; -qt-block-indent:0; text-indent:0px;\"><a href=\"qbzrglossary:checkouts_and_branches\"><span style=\" text-decoration: underline; color:#0000ff;\">Tell me more about checkouts and branches.</span></a></p></body></html>", None, QtGui.QApplication.UnicodeUTF8))
        self.groupBox_2.setTitle(gettext("Revision"))
        self.but_rev_tip.setText(gettext("Most recent (tip) revision"))
        self.but_rev_specific.setText(gettext("Revision:"))
        self.but_show_log.setText(gettext("Show Log..."))

