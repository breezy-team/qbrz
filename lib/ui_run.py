# -*- coding: utf-8 -*-

# Form implementation generated from reading ui file 'ui/run.ui'
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

class Ui_RunDialog(object):
    def setupUi(self, RunDialog):
        RunDialog.setObjectName(_fromUtf8("RunDialog"))
        RunDialog.resize(473, 367)
        self.main_v_layout = QtGui.QVBoxLayout(RunDialog)
        self.main_v_layout.setObjectName(_fromUtf8("main_v_layout"))
        self.splitter = QtGui.QSplitter(RunDialog)
        self.splitter.setOrientation(QtCore.Qt.Vertical)
        self.splitter.setOpaqueResize(False)
        self.splitter.setChildrenCollapsible(False)
        self.splitter.setObjectName(_fromUtf8("splitter"))
        self.run_container = QtGui.QGroupBox(self.splitter)
        self.run_container.setObjectName(_fromUtf8("run_container"))
        self.run_container_layout = QtGui.QVBoxLayout(self.run_container)
        self.run_container_layout.setObjectName(_fromUtf8("run_container_layout"))
        self.wd_layout = QtGui.QHBoxLayout()
        self.wd_layout.setObjectName(_fromUtf8("wd_layout"))
        self.wd_label = QtGui.QLabel(self.run_container)
        self.wd_label.setObjectName(_fromUtf8("wd_label"))
        self.wd_layout.addWidget(self.wd_label)
        self.wd_edit = QtGui.QLineEdit(self.run_container)
        self.wd_edit.setObjectName(_fromUtf8("wd_edit"))
        self.wd_layout.addWidget(self.wd_edit)
        self.browse_button = QtGui.QPushButton(self.run_container)
        self.browse_button.setObjectName(_fromUtf8("browse_button"))
        self.wd_layout.addWidget(self.browse_button)
        self.run_container_layout.addLayout(self.wd_layout)
        self.cmd_layout = QtGui.QGridLayout()
        self.cmd_layout.setObjectName(_fromUtf8("cmd_layout"))
        self.cat_label = QtGui.QLabel(self.run_container)
        self.cat_label.setObjectName(_fromUtf8("cat_label"))
        self.cmd_layout.addWidget(self.cat_label, 0, 0, 1, 1)
        self.cat_combobox = QtGui.QComboBox(self.run_container)
        self.cat_combobox.setMinimumSize(QtCore.QSize(170, 0))
        self.cat_combobox.setObjectName(_fromUtf8("cat_combobox"))
        self.cmd_layout.addWidget(self.cat_combobox, 0, 1, 1, 1)
        self.cmd_label = QtGui.QLabel(self.run_container)
        self.cmd_label.setObjectName(_fromUtf8("cmd_label"))
        self.cmd_layout.addWidget(self.cmd_label, 1, 0, 1, 1)
        self.cmd_combobox = QtGui.QComboBox(self.run_container)
        self.cmd_combobox.setMinimumSize(QtCore.QSize(170, 0))
        self.cmd_combobox.setEditable(True)
        self.cmd_combobox.setObjectName(_fromUtf8("cmd_combobox"))
        self.cmd_layout.addWidget(self.cmd_combobox, 1, 1, 1, 1)
        self.hidden_checkbox = QtGui.QCheckBox(self.run_container)
        self.hidden_checkbox.setObjectName(_fromUtf8("hidden_checkbox"))
        self.cmd_layout.addWidget(self.hidden_checkbox, 1, 2, 1, 1)
        self.run_container_layout.addLayout(self.cmd_layout)
        self.opt_arg_label = QtGui.QLabel(self.run_container)
        self.opt_arg_label.setLineWidth(0)
        self.opt_arg_label.setObjectName(_fromUtf8("opt_arg_label"))
        self.run_container_layout.addWidget(self.opt_arg_label)
        self.opt_arg_edit = QtGui.QLineEdit(self.run_container)
        self.opt_arg_edit.setObjectName(_fromUtf8("opt_arg_edit"))
        self.run_container_layout.addWidget(self.opt_arg_edit)
        self.opt_arg_btn_layout = QtGui.QHBoxLayout()
        self.opt_arg_btn_layout.setObjectName(_fromUtf8("opt_arg_btn_layout"))
        self.directory_button = QtGui.QPushButton(self.run_container)
        self.directory_button.setObjectName(_fromUtf8("directory_button"))
        self.opt_arg_btn_layout.addWidget(self.directory_button)
        self.filenames_button = QtGui.QPushButton(self.run_container)
        self.filenames_button.setObjectName(_fromUtf8("filenames_button"))
        self.opt_arg_btn_layout.addWidget(self.filenames_button)
        spacerItem = QtGui.QSpacerItem(40, 20, QtGui.QSizePolicy.Expanding, QtGui.QSizePolicy.Minimum)
        self.opt_arg_btn_layout.addItem(spacerItem)
        self.run_container_layout.addLayout(self.opt_arg_btn_layout)
        self.help_browser = QtGui.QTextBrowser(self.run_container)
        self.help_browser.setObjectName(_fromUtf8("help_browser"))
        self.run_container_layout.addWidget(self.help_browser)
        self.subprocess_container = QtGui.QWidget(self.splitter)
        self.subprocess_container.setObjectName(_fromUtf8("subprocess_container"))
        self.subprocess_container_layout = QtGui.QVBoxLayout(self.subprocess_container)
        self.subprocess_container_layout.setMargin(0)
        self.subprocess_container_layout.setObjectName(_fromUtf8("subprocess_container_layout"))
        self.main_v_layout.addWidget(self.splitter)
        self.wd_label.setBuddy(self.wd_edit)
        self.cat_label.setBuddy(self.cmd_combobox)
        self.cmd_label.setBuddy(self.cmd_combobox)
        self.opt_arg_label.setBuddy(self.opt_arg_edit)

        self.retranslateUi(RunDialog)
        QtCore.QObject.connect(RunDialog, QtCore.SIGNAL(_fromUtf8("disableUi(bool)")), self.run_container.setDisabled)
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

