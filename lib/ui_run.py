# -*- coding: utf-8 -*-

# Form implementation generated from reading ui file 'ui/run.ui'
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

class Ui_RunDialog(object):
    def setupUi(self, RunDialog):
        RunDialog.setObjectName("RunDialog")
        RunDialog.resize(473, 367)
        self.main_v_layout = QtWidgets.QVBoxLayout(RunDialog)
        self.main_v_layout.setObjectName("main_v_layout")
        self.splitter = QtWidgets.QSplitter(RunDialog)
        self.splitter.setOrientation(QtCore.Qt.Vertical)
        self.splitter.setOpaqueResize(False)
        self.splitter.setChildrenCollapsible(False)
        self.splitter.setObjectName("splitter")
        self.run_container = QtWidgets.QGroupBox(self.splitter)
        self.run_container.setObjectName("run_container")
        self.run_container_layout = QtWidgets.QVBoxLayout(self.run_container)
        self.run_container_layout.setObjectName("run_container_layout")
        self.wd_layout = QtWidgets.QHBoxLayout()
        self.wd_layout.setObjectName("wd_layout")
        self.wd_label = QtWidgets.QLabel(self.run_container)
        self.wd_label.setObjectName("wd_label")
        self.wd_layout.addWidget(self.wd_label)
        self.wd_edit = QtWidgets.QLineEdit(self.run_container)
        self.wd_edit.setObjectName("wd_edit")
        self.wd_layout.addWidget(self.wd_edit)
        self.browse_button = QtWidgets.QPushButton(self.run_container)
        self.browse_button.setObjectName("browse_button")
        self.wd_layout.addWidget(self.browse_button)
        self.run_container_layout.addLayout(self.wd_layout)
        self.cmd_layout = QtWidgets.QGridLayout()
        self.cmd_layout.setObjectName("cmd_layout")
        self.cat_label = QtWidgets.QLabel(self.run_container)
        self.cat_label.setObjectName("cat_label")
        self.cmd_layout.addWidget(self.cat_label, 0, 0, 1, 1)
        self.cat_combobox = QtWidgets.QComboBox(self.run_container)
        self.cat_combobox.setMinimumSize(QtCore.QSize(170, 0))
        self.cat_combobox.setObjectName("cat_combobox")
        self.cmd_layout.addWidget(self.cat_combobox, 0, 1, 1, 1)
        self.cmd_label = QtWidgets.QLabel(self.run_container)
        self.cmd_label.setObjectName("cmd_label")
        self.cmd_layout.addWidget(self.cmd_label, 1, 0, 1, 1)
        self.cmd_combobox = QtWidgets.QComboBox(self.run_container)
        self.cmd_combobox.setMinimumSize(QtCore.QSize(170, 0))
        self.cmd_combobox.setEditable(True)
        self.cmd_combobox.setObjectName("cmd_combobox")
        self.cmd_layout.addWidget(self.cmd_combobox, 1, 1, 1, 1)
        self.hidden_checkbox = QtWidgets.QCheckBox(self.run_container)
        self.hidden_checkbox.setObjectName("hidden_checkbox")
        self.cmd_layout.addWidget(self.hidden_checkbox, 1, 2, 1, 1)
        self.run_container_layout.addLayout(self.cmd_layout)
        self.opt_arg_label = QtWidgets.QLabel(self.run_container)
        self.opt_arg_label.setLineWidth(0)
        self.opt_arg_label.setObjectName("opt_arg_label")
        self.run_container_layout.addWidget(self.opt_arg_label)
        self.opt_arg_edit = QtWidgets.QLineEdit(self.run_container)
        self.opt_arg_edit.setObjectName("opt_arg_edit")
        self.run_container_layout.addWidget(self.opt_arg_edit)
        self.opt_arg_btn_layout = QtWidgets.QHBoxLayout()
        self.opt_arg_btn_layout.setObjectName("opt_arg_btn_layout")
        self.directory_button = QtWidgets.QPushButton(self.run_container)
        self.directory_button.setObjectName("directory_button")
        self.opt_arg_btn_layout.addWidget(self.directory_button)
        self.filenames_button = QtWidgets.QPushButton(self.run_container)
        self.filenames_button.setObjectName("filenames_button")
        self.opt_arg_btn_layout.addWidget(self.filenames_button)
        spacerItem = QtWidgets.QSpacerItem(40, 20, QtWidgets.QSizePolicy.Expanding, QtWidgets.QSizePolicy.Minimum)
        self.opt_arg_btn_layout.addItem(spacerItem)
        self.run_container_layout.addLayout(self.opt_arg_btn_layout)
        self.help_browser = QtWidgets.QTextBrowser(self.run_container)
        self.help_browser.setObjectName("help_browser")
        self.run_container_layout.addWidget(self.help_browser)
        self.subprocess_container = QtWidgets.QWidget(self.splitter)
        self.subprocess_container.setObjectName("subprocess_container")
        self.subprocess_container_layout = QtWidgets.QVBoxLayout(self.subprocess_container)
        self.subprocess_container_layout.setContentsMargins(0, 0, 0, 0)
        self.subprocess_container_layout.setObjectName("subprocess_container_layout")
        self.main_v_layout.addWidget(self.splitter)
        self.wd_label.setBuddy(self.wd_edit)
        self.cat_label.setBuddy(self.cmd_combobox)
        self.cmd_label.setBuddy(self.cmd_combobox)
        self.opt_arg_label.setBuddy(self.opt_arg_edit)

        self.retranslateUi(RunDialog)
        RunDialog.disableUi[bool].connect(self.run_container.setDisabled)
        QtCore.QMetaObject.connectSlotsByName(RunDialog)
        RunDialog.setTabOrder(self.wd_edit, self.browse_button)
        RunDialog.setTabOrder(self.browse_button, self.hidden_checkbox)
        RunDialog.setTabOrder(self.hidden_checkbox, self.cmd_combobox)
        RunDialog.setTabOrder(self.cmd_combobox, self.opt_arg_edit)
        RunDialog.setTabOrder(self.opt_arg_edit, self.directory_button)
        RunDialog.setTabOrder(self.directory_button, self.filenames_button)
        RunDialog.setTabOrder(self.filenames_button, self.help_browser)

    def retranslateUi(self, RunDialog):
        RunDialog.setWindowTitle(_translate("RunDialog", "Run bzr command", None))
        self.run_container.setTitle(_translate("RunDialog", "Options", None))
        self.wd_label.setText(_translate("RunDialog", "&Working directory:", None))
        self.browse_button.setText(_translate("RunDialog", "&Browse...", None))
        self.cat_label.setText(_translate("RunDialog", "C&ategory:", None))
        self.cmd_label.setText(_translate("RunDialog", "&Command:", None))
        self.hidden_checkbox.setText(_translate("RunDialog", "&Show hidden commands", None))
        self.opt_arg_label.setText(_translate("RunDialog", "&Options and arguments for command:", None))
        self.directory_button.setText(_translate("RunDialog", "Insert &directory...", None))
        self.filenames_button.setText(_translate("RunDialog", "Insert &filenames...", None))

