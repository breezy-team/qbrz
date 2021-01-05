# -*- coding: utf-8 -*-

# Form implementation generated from reading ui file 'ui/new_tree.ui'
#
# Created by: PyQt4 UI code generator 4.12.3
#
# WARNING! All changes made in this file will be lost!

from PyQt5 import QtCore, QtGui, QtWidgets

try:
    _encoding = QtWidgets.QApplication.UnicodeUTF8
    def _translate(context, text, disambig):
        return QtCore.QCoreApplication.translate(context, text, disambig, _encoding)
except AttributeError:
    def _translate(context, text, disambig):
        return QtCore.QCoreApplication.translate(context, text, disambig)

class Ui_NewWorkingTreeForm(object):
    def setupUi(self, NewWorkingTreeForm):
        NewWorkingTreeForm.setObjectName("NewWorkingTreeForm")
        NewWorkingTreeForm.resize(479, 385)
        self.verticalLayout = QtWidgets.QVBoxLayout(NewWorkingTreeForm)
        self.verticalLayout.setContentsMargins(9, 9, 9, 9)
        self.verticalLayout.setObjectName("verticalLayout")
        self.groupBox = QtWidgets.QGroupBox(NewWorkingTreeForm)
        self.groupBox.setObjectName("groupBox")
        self.gridLayout = QtWidgets.QGridLayout(self.groupBox)
        self.gridLayout.setObjectName("gridLayout")
        self.label_4 = QtWidgets.QLabel(self.groupBox)
        self.label_4.setObjectName("label_4")
        self.gridLayout.addWidget(self.label_4, 0, 0, 1, 2)
        self.from_location = QtWidgets.QComboBox(self.groupBox)
        self.from_location.setEditable(True)
        self.from_location.setSizeAdjustPolicy(QtWidgets.QComboBox.AdjustToMinimumContentsLength)
        self.from_location.setObjectName("from_location")
        self.gridLayout.addWidget(self.from_location, 1, 0, 1, 1)
        self.from_picker = QtWidgets.QPushButton(self.groupBox)
        self.from_picker.setObjectName("from_picker")
        self.gridLayout.addWidget(self.from_picker, 1, 1, 1, 1)
        self.label = QtWidgets.QLabel(self.groupBox)
        font = QtGui.QFont()
        font.setUnderline(False)
        self.label.setFont(font)
        self.label.setOpenExternalLinks(False)
        self.label.setObjectName("label")
        self.gridLayout.addWidget(self.label, 2, 0, 1, 2)
        self.to_location = QtWidgets.QLineEdit(self.groupBox)
        self.to_location.setObjectName("to_location")
        self.gridLayout.addWidget(self.to_location, 3, 0, 1, 1)
        self.to_picker = QtWidgets.QPushButton(self.groupBox)
        self.to_picker.setObjectName("to_picker")
        self.gridLayout.addWidget(self.to_picker, 3, 1, 1, 1)
        self.verticalLayout.addWidget(self.groupBox)
        self.groupBox_3 = QtWidgets.QGroupBox(NewWorkingTreeForm)
        self.groupBox_3.setObjectName("groupBox_3")
        self.gridLayout_2 = QtWidgets.QGridLayout(self.groupBox_3)
        self.gridLayout_2.setObjectName("gridLayout_2")
        self.but_checkout = QtWidgets.QRadioButton(self.groupBox_3)
        self.but_checkout.setChecked(True)
        self.but_checkout.setObjectName("but_checkout")
        self.gridLayout_2.addWidget(self.but_checkout, 0, 0, 1, 2)
        spacerItem = QtWidgets.QSpacerItem(18, 20, QtWidgets.QSizePolicy.Fixed, QtWidgets.QSizePolicy.Minimum)
        self.gridLayout_2.addItem(spacerItem, 1, 0, 1, 1)
        self.but_lightweight = QtWidgets.QCheckBox(self.groupBox_3)
        sizePolicy = QtWidgets.QSizePolicy(QtWidgets.QSizePolicy.Minimum, QtWidgets.QSizePolicy.Fixed)
        sizePolicy.setHorizontalStretch(1)
        sizePolicy.setVerticalStretch(0)
        sizePolicy.setHeightForWidth(self.but_lightweight.sizePolicy().hasHeightForWidth())
        self.but_lightweight.setSizePolicy(sizePolicy)
        self.but_lightweight.setObjectName("but_lightweight")
        self.gridLayout_2.addWidget(self.but_lightweight, 1, 1, 1, 1)
        self.but_branch = QtWidgets.QRadioButton(self.groupBox_3)
        self.but_branch.setObjectName("but_branch")
        self.gridLayout_2.addWidget(self.but_branch, 2, 0, 1, 2)
        spacerItem1 = QtWidgets.QSpacerItem(18, 20, QtWidgets.QSizePolicy.Fixed, QtWidgets.QSizePolicy.Minimum)
        self.gridLayout_2.addItem(spacerItem1, 3, 0, 1, 1)
        self.but_stacked = QtWidgets.QCheckBox(self.groupBox_3)
        self.but_stacked.setEnabled(False)
        self.but_stacked.setObjectName("but_stacked")
        self.gridLayout_2.addWidget(self.but_stacked, 3, 1, 1, 1)
        self.link_help = QtWidgets.QLabel(self.groupBox_3)
        font = QtGui.QFont()
        font.setUnderline(True)
        self.link_help.setFont(font)
        self.link_help.setCursor(QtGui.QCursor(QtCore.Qt.ArrowCursor))
        self.link_help.setTextFormat(QtCore.Qt.RichText)
        self.link_help.setOpenExternalLinks(False)
        self.link_help.setTextInteractionFlags(QtCore.Qt.TextBrowserInteraction)
        self.link_help.setObjectName("link_help")
        self.gridLayout_2.addWidget(self.link_help, 4, 0, 1, 2)
        self.verticalLayout.addWidget(self.groupBox_3)
        self.groupBox_2 = QtWidgets.QGroupBox(NewWorkingTreeForm)
        self.groupBox_2.setObjectName("groupBox_2")
        self.gridLayout_3 = QtWidgets.QGridLayout(self.groupBox_2)
        self.gridLayout_3.setObjectName("gridLayout_3")
        self.but_rev_tip = QtWidgets.QRadioButton(self.groupBox_2)
        self.but_rev_tip.setChecked(True)
        self.but_rev_tip.setObjectName("but_rev_tip")
        self.gridLayout_3.addWidget(self.but_rev_tip, 0, 0, 1, 2)
        self.but_rev_specific = QtWidgets.QRadioButton(self.groupBox_2)
        self.but_rev_specific.setObjectName("but_rev_specific")
        self.gridLayout_3.addWidget(self.but_rev_specific, 1, 0, 1, 1)
        self.revision = QtWidgets.QLineEdit(self.groupBox_2)
        self.revision.setEnabled(False)
        sizePolicy = QtWidgets.QSizePolicy(QtWidgets.QSizePolicy.Expanding, QtWidgets.QSizePolicy.Fixed)
        sizePolicy.setHorizontalStretch(1)
        sizePolicy.setVerticalStretch(0)
        sizePolicy.setHeightForWidth(self.revision.sizePolicy().hasHeightForWidth())
        self.revision.setSizePolicy(sizePolicy)
        self.revision.setObjectName("revision")
        self.gridLayout_3.addWidget(self.revision, 1, 1, 1, 1)
        self.but_show_log = QtWidgets.QPushButton(self.groupBox_2)
        self.but_show_log.setEnabled(False)
        self.but_show_log.setObjectName("but_show_log")
        self.gridLayout_3.addWidget(self.but_show_log, 1, 3, 1, 1)
        self.link_help_revisions = QtWidgets.QLabel(self.groupBox_2)
        self.link_help_revisions.setObjectName("link_help_revisions")
        self.gridLayout_3.addWidget(self.link_help_revisions, 1, 2, 1, 1)
        self.verticalLayout.addWidget(self.groupBox_2)

        self.retranslateUi(NewWorkingTreeForm)
        self.link_help.linkActivated['QString'].connect(NewWorkingTreeForm.linkActivated)
        self.link_help_revisions.linkActivated['QString'].connect(NewWorkingTreeForm.linkActivated)
        self.but_checkout.toggled[bool].connect(self.but_lightweight.setEnabled)
        self.but_branch.toggled[bool].connect(self.but_stacked.setEnabled)
        self.but_rev_specific.toggled[bool].connect(self.revision.setEnabled)
        NewWorkingTreeForm.disableUi[bool].connect(self.groupBox.setDisabled)
        NewWorkingTreeForm.disableUi[bool].connect(self.groupBox_3.setDisabled)
        NewWorkingTreeForm.disableUi[bool].connect(self.groupBox_2.setDisabled)
        QtCore.QMetaObject.connectSlotsByName(NewWorkingTreeForm)

    def retranslateUi(self, NewWorkingTreeForm):
        NewWorkingTreeForm.setWindowTitle(_translate("NewWorkingTreeForm", "Create a new Bazaar Working Tree", None))
        self.groupBox.setTitle(_translate("NewWorkingTreeForm", "Branch", None))
        self.label_4.setText(_translate("NewWorkingTreeForm", "Branch source (enter a URL or select a local directory with an existing branch)", None))
        self.from_picker.setText(_translate("NewWorkingTreeForm", "Browse...", None))
        self.label.setText(_translate("NewWorkingTreeForm", "Local directory where the working tree will be created", None))
        self.to_picker.setText(_translate("NewWorkingTreeForm", "Browse...", None))
        self.groupBox_3.setTitle(_translate("NewWorkingTreeForm", "Working Tree Options", None))
        self.but_checkout.setText(_translate("NewWorkingTreeForm", "Create a checkout", None))
        self.but_lightweight.setToolTip(_translate("NewWorkingTreeForm", "<!DOCTYPE HTML PUBLIC \"-//W3C//DTD HTML 4.0//EN\" \"http://www.w3.org/TR/REC-html40/strict.dtd\">\n"
"<html><head><meta name=\"qrichtext\" content=\"1\" /><style type=\"text/css\">\n"
"p, li { white-space: pre-wrap; }\n"
"</style></head><body style=\" font-family:\'MS Shell Dlg 2\'; font-size:8.25pt; font-weight:400; font-style:normal;\">\n"
"<p style=\" margin-top:0px; margin-bottom:0px; margin-left:0px; margin-right:0px; -qt-block-indent:0; text-indent:0px;\"><span style=\" font-style:italic;\">Lightweight checkouts </span>depend on access to the branch for every operation.</p>\n"
"<p style=\" margin-top:0px; margin-bottom:0px; margin-left:0px; margin-right:0px; -qt-block-indent:0; text-indent:0px;\">Normal checkouts can perform common operations like diff and status without such access, and also support local commits.</p>\n"
"<p style=\"-qt-paragraph-type:empty; margin-top:0px; margin-bottom:0px; margin-left:0px; margin-right:0px; -qt-block-indent:0; text-indent:0px;\"></p></body></html>", None))
        self.but_lightweight.setText(_translate("NewWorkingTreeForm", "Light-weight checkout", None))
        self.but_branch.setText(_translate("NewWorkingTreeForm", "Make a local copy of the branch", None))
        self.but_stacked.setToolTip(_translate("NewWorkingTreeForm", "<!DOCTYPE HTML PUBLIC \"-//W3C//DTD HTML 4.0//EN\" \"http://www.w3.org/TR/REC-html40/strict.dtd\">\n"
"<html><head><meta name=\"qrichtext\" content=\"1\" /><style type=\"text/css\">\n"
"p, li { white-space: pre-wrap; }\n"
"</style></head><body style=\" font-family:\'MS Shell Dlg 2\'; font-size:8.25pt; font-weight:400; font-style:normal;\">\n"
"<p style=\" margin-top:0px; margin-bottom:0px; margin-left:0px; margin-right:0px; -qt-block-indent:0; text-indent:0px;\">A <span style=\" font-style:italic;\">stacked branch</span> only stores information not in the source branch, and as such, depends on the availability of the source branch</p></body></html>", None))
        self.but_stacked.setText(_translate("NewWorkingTreeForm", "Create a stacked branch referring to the source branch", None))
        self.link_help.setToolTip(_translate("NewWorkingTreeForm", "Click a link for more information about checkouts and branches.", None))
        self.link_help.setText(_translate("NewWorkingTreeForm", "<!DOCTYPE HTML PUBLIC \"-//W3C//DTD HTML 4.0//EN\" \"http://www.w3.org/TR/REC-html40/strict.dtd\">\n"
"<html><head><meta name=\"qrichtext\" content=\"1\" /><style type=\"text/css\">\n"
"p, li { white-space: pre-wrap; }\n"
"</style></head><body style=\" font-family:\'MS Shell Dlg 2\'; font-size:8.25pt; font-weight:400; font-style:normal;\">\n"
"<p style=\" margin-top:0px; margin-bottom:0px; margin-left:0px; margin-right:0px; -qt-block-indent:0; text-indent:0px; font-size:8pt;\">Tell me more about <a href=\"bzrtopic:checkouts\"><span style=\" text-decoration: underline; color:#0000ff;\">checkouts</span></a> and <a href=\"bzrtopic:branches\"><span style=\" text-decoration: underline; color:#0000ff;\">branches</span></a></p></body></html>", None))
        self.groupBox_2.setTitle(_translate("NewWorkingTreeForm", "Revision", None))
        self.but_rev_tip.setText(_translate("NewWorkingTreeForm", "Most recent (tip) revision", None))
        self.but_rev_specific.setText(_translate("NewWorkingTreeForm", "Revision:", None))
        self.but_show_log.setText(_translate("NewWorkingTreeForm", "Show Log...", None))
        self.link_help_revisions.setText(_translate("NewWorkingTreeForm", "<!DOCTYPE HTML PUBLIC \"-//W3C//DTD HTML 4.0//EN\" \"http://www.w3.org/TR/REC-html40/strict.dtd\">\n"
"<html><head><meta name=\"qrichtext\" content=\"1\" /><style type=\"text/css\">\n"
"p, li { white-space: pre-wrap; }\n"
"</style></head><body style=\" font-family:\'MS Shell Dlg 2\'; font-size:8.25pt; font-weight:400; font-style:normal;\">\n"
"<p style=\" margin-top:0px; margin-bottom:0px; margin-left:0px; margin-right:0px; -qt-block-indent:0; text-indent:0px; font-size:8pt;\"><a href=\"bzrtopic:revisionspec\"><span style=\" text-decoration: underline; color:#0000ff;\">About revision identifiers</span></a></p></body></html>", None))

