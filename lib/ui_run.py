# -*- coding: utf-8 -*-

# Form implementation generated from reading ui file 'ui/run.ui'
#
# Created: Sat Aug 22 20:31:38 2009
#      by: PyQt4 UI code generator 4.4.3
#
# WARNING! All changes made in this file will be lost!

from PyQt4 import QtCore, QtGui
from bzrlib.plugins.qbzr.lib.i18n import gettext


class Ui_RunDialog(object):
    def setupUi(self, RunDialog):
        RunDialog.setObjectName("RunDialog")
        RunDialog.resize(473, 367)
        self.verticalLayout_3 = QtGui.QVBoxLayout(RunDialog)
        self.verticalLayout_3.setObjectName("verticalLayout_3")
        self.splitter = QtGui.QSplitter(RunDialog)
        self.splitter.setOrientation(QtCore.Qt.Vertical)
        self.splitter.setObjectName("splitter")
        self.frame = QtGui.QFrame(self.splitter)
        self.frame.setFrameShape(QtGui.QFrame.StyledPanel)
        self.frame.setFrameShadow(QtGui.QFrame.Raised)
        self.frame.setObjectName("frame")
        self.verticalLayout_2 = QtGui.QVBoxLayout(self.frame)
        self.verticalLayout_2.setObjectName("verticalLayout_2")
        self.horizontalLayout_4 = QtGui.QHBoxLayout()
        self.horizontalLayout_4.setObjectName("horizontalLayout_4")
        self.wd_label = QtGui.QLabel(self.frame)
        self.wd_label.setObjectName("wd_label")
        self.horizontalLayout_4.addWidget(self.wd_label)
        self.wd_edit = QtGui.QLineEdit(self.frame)
        self.wd_edit.setObjectName("wd_edit")
        self.horizontalLayout_4.addWidget(self.wd_edit)
        self.browse_button = QtGui.QPushButton(self.frame)
        self.browse_button.setObjectName("browse_button")
        self.horizontalLayout_4.addWidget(self.browse_button)
        self.verticalLayout_2.addLayout(self.horizontalLayout_4)
        self.gridLayout_4 = QtGui.QGridLayout()
        self.gridLayout_4.setObjectName("gridLayout_4")
        self.cmd_label = QtGui.QLabel(self.frame)
        self.cmd_label.setObjectName("cmd_label")
        self.gridLayout_4.addWidget(self.cmd_label, 0, 0, 1, 1)
        self.cmd_combobox = QtGui.QComboBox(self.frame)
        self.cmd_combobox.setMinimumSize(QtCore.QSize(170, 0))
        self.cmd_combobox.setEditable(True)
        self.cmd_combobox.setObjectName("cmd_combobox")
        self.gridLayout_4.addWidget(self.cmd_combobox, 0, 1, 1, 1)
        self.hidden_checkbox = QtGui.QCheckBox(self.frame)
        self.hidden_checkbox.setObjectName("hidden_checkbox")
        self.gridLayout_4.addWidget(self.hidden_checkbox, 0, 2, 1, 1)
        self.verticalLayout_2.addLayout(self.gridLayout_4)
        self.opt_arg_label = QtGui.QLabel(self.frame)
        self.opt_arg_label.setObjectName("opt_arg_label")
        self.verticalLayout_2.addWidget(self.opt_arg_label)
        self.opt_arg_edit = QtGui.QLineEdit(self.frame)
        self.opt_arg_edit.setObjectName("opt_arg_edit")
        self.verticalLayout_2.addWidget(self.opt_arg_edit)
        self.horizontalLayout_7 = QtGui.QHBoxLayout()
        self.horizontalLayout_7.setObjectName("horizontalLayout_7")
        self.path_button = QtGui.QPushButton(self.frame)
        self.path_button.setObjectName("path_button")
        self.horizontalLayout_7.addWidget(self.path_button)
        self.filename_button = QtGui.QPushButton(self.frame)
        self.filename_button.setObjectName("filename_button")
        self.horizontalLayout_7.addWidget(self.filename_button)
        spacerItem = QtGui.QSpacerItem(40, 20, QtGui.QSizePolicy.Expanding, QtGui.QSizePolicy.Minimum)
        self.horizontalLayout_7.addItem(spacerItem)
        self.verticalLayout_2.addLayout(self.horizontalLayout_7)
        self.help_browser = QtGui.QTextBrowser(self.splitter)
        self.help_browser.setObjectName("help_browser")
        self.verticalLayout_3.addWidget(self.splitter)
        self.wd_label.setBuddy(self.wd_edit)
        self.cmd_label.setBuddy(self.cmd_combobox)
        self.opt_arg_label.setBuddy(self.opt_arg_edit)

        self.retranslateUi(RunDialog)
        QtCore.QMetaObject.connectSlotsByName(RunDialog)

    def retranslateUi(self, RunDialog):
        RunDialog.setWindowTitle(gettext("Run bzr command"))
        self.wd_label.setText(gettext("&Working directory:"))
        self.browse_button.setText(gettext("&Browse..."))
        self.cmd_label.setText(gettext("&Command:"))
        self.hidden_checkbox.setText(gettext("&Show hidden commands"))
        self.opt_arg_label.setText(gettext("&Options and arguments for command:"))
        self.path_button.setText(gettext("Insert &path..."))
        self.filename_button.setText(gettext("Insert &filename..."))
        self.help_browser.setHtml(QtGui.QApplication.translate("RunDialog", "<!DOCTYPE HTML PUBLIC \"-//W3C//DTD HTML 4.0//EN\" \"http://www.w3.org/TR/REC-html40/strict.dtd\">\n"
"<html><head><meta name=\"qrichtext\" content=\"1\" /><style type=\"text/css\">\n"
"p, li { white-space: pre-wrap; }\n"
"</style></head><body style=\" font-family:\'MS Shell Dlg 2\'; font-size:8.25pt; font-weight:400; font-style:normal;\">\n"
"<p style=\"-qt-paragraph-type:empty; margin-top:0px; margin-bottom:0px; margin-left:0px; margin-right:0px; -qt-block-indent:0; text-indent:0px; font-size:8pt;\"></p></body></html>", None, QtGui.QApplication.UnicodeUTF8))

