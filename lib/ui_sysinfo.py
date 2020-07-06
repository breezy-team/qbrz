# -*- coding: utf-8 -*-

# Form implementation generated from reading ui file 'ui/sysinfo.ui'
#
# Created by: PyQt4 UI code generator 4.11.4
#
# WARNING! All changes made in this file will be lost!

from PyQt4 import QtCore, QtGui
from breezy.plugins.qbrz.lib.i18n import gettext


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

class Ui_MainWindow(object):
    def setupUi(self, MainWindow):
        MainWindow.setObjectName(_fromUtf8("MainWindow"))
        MainWindow.resize(404, 288)
        self.centralwidget = QtGui.QWidget(MainWindow)
        self.centralwidget.setObjectName(_fromUtf8("centralwidget"))
        self.vboxlayout = QtGui.QVBoxLayout(self.centralwidget)
        self.vboxlayout.setObjectName(_fromUtf8("vboxlayout"))
        self.bazaar_library = QtGui.QGroupBox(self.centralwidget)
        self.bazaar_library.setFlat(False)
        self.bazaar_library.setObjectName(_fromUtf8("bazaar_library"))
        self.gridlayout = QtGui.QGridLayout(self.bazaar_library)
        self.gridlayout.setObjectName(_fromUtf8("gridlayout"))
        self.label = QtGui.QLabel(self.bazaar_library)
        self.label.setObjectName(_fromUtf8("label"))
        self.gridlayout.addWidget(self.label, 0, 0, 1, 1)
        self.bzr_version = QtGui.QLabel(self.bazaar_library)
        self.bzr_version.setObjectName(_fromUtf8("bzr_version"))
        self.gridlayout.addWidget(self.bzr_version, 0, 1, 1, 1)
        self.label_3 = QtGui.QLabel(self.bazaar_library)
        self.label_3.setObjectName(_fromUtf8("label_3"))
        self.gridlayout.addWidget(self.label_3, 1, 0, 1, 1)
        self.bzr_lib_path = QtGui.QLabel(self.bazaar_library)
        self.bzr_lib_path.setMinimumSize(QtCore.QSize(300, 0))
        self.bzr_lib_path.setObjectName(_fromUtf8("bzr_lib_path"))
        self.gridlayout.addWidget(self.bzr_lib_path, 1, 1, 1, 1)
        self.vboxlayout.addWidget(self.bazaar_library)
        self.bazaar_configuration = QtGui.QGroupBox(self.centralwidget)
        self.bazaar_configuration.setObjectName(_fromUtf8("bazaar_configuration"))
        self.gridlayout1 = QtGui.QGridLayout(self.bazaar_configuration)
        self.gridlayout1.setObjectName(_fromUtf8("gridlayout1"))
        self.label_2 = QtGui.QLabel(self.bazaar_configuration)
        self.label_2.setObjectName(_fromUtf8("label_2"))
        self.gridlayout1.addWidget(self.label_2, 0, 0, 1, 1)
        self.bzr_config_dir = QtGui.QLabel(self.bazaar_configuration)
        self.bzr_config_dir.setObjectName(_fromUtf8("bzr_config_dir"))
        self.gridlayout1.addWidget(self.bzr_config_dir, 0, 1, 1, 1)
        self.label_4 = QtGui.QLabel(self.bazaar_configuration)
        self.label_4.setObjectName(_fromUtf8("label_4"))
        self.gridlayout1.addWidget(self.label_4, 1, 0, 1, 1)
        self.bzr_log_file = QtGui.QLabel(self.bazaar_configuration)
        self.bzr_log_file.setMinimumSize(QtCore.QSize(300, 0))
        self.bzr_log_file.setObjectName(_fromUtf8("bzr_log_file"))
        self.gridlayout1.addWidget(self.bzr_log_file, 1, 1, 1, 1)
        self.vboxlayout.addWidget(self.bazaar_configuration)
        self.python_interpreter = QtGui.QGroupBox(self.centralwidget)
        self.python_interpreter.setMinimumSize(QtCore.QSize(0, 0))
        self.python_interpreter.setObjectName(_fromUtf8("python_interpreter"))
        self.gridlayout2 = QtGui.QGridLayout(self.python_interpreter)
        self.gridlayout2.setObjectName(_fromUtf8("gridlayout2"))
        self.label_5 = QtGui.QLabel(self.python_interpreter)
        self.label_5.setObjectName(_fromUtf8("label_5"))
        self.gridlayout2.addWidget(self.label_5, 0, 0, 1, 1)
        self.python_version = QtGui.QLabel(self.python_interpreter)
        self.python_version.setObjectName(_fromUtf8("python_version"))
        self.gridlayout2.addWidget(self.python_version, 0, 1, 1, 1)
        self.label_9 = QtGui.QLabel(self.python_interpreter)
        self.label_9.setObjectName(_fromUtf8("label_9"))
        self.gridlayout2.addWidget(self.label_9, 1, 0, 1, 1)
        self.python_file = QtGui.QLabel(self.python_interpreter)
        self.python_file.setObjectName(_fromUtf8("python_file"))
        self.gridlayout2.addWidget(self.python_file, 1, 1, 1, 1)
        self.label_7 = QtGui.QLabel(self.python_interpreter)
        self.label_7.setObjectName(_fromUtf8("label_7"))
        self.gridlayout2.addWidget(self.label_7, 2, 0, 1, 1)
        self.python_lib_dir = QtGui.QLabel(self.python_interpreter)
        self.python_lib_dir.setMinimumSize(QtCore.QSize(300, 0))
        self.python_lib_dir.setObjectName(_fromUtf8("python_lib_dir"))
        self.gridlayout2.addWidget(self.python_lib_dir, 2, 1, 1, 1)
        self.vboxlayout.addWidget(self.python_interpreter)
        MainWindow.setCentralWidget(self.centralwidget)

        self.retranslateUi(MainWindow)
        QtCore.QMetaObject.connectSlotsByName(MainWindow)

    def retranslateUi(self, MainWindow):
        MainWindow.setWindowTitle(_translate("MainWindow", "System Information", None))
        self.bazaar_library.setTitle(_translate("MainWindow", "Breezy Library", None))
        self.label.setText(_translate("MainWindow", "Version:", None))
        self.bzr_version.setText(_translate("MainWindow", "(bzr-version)", None))
        self.label_3.setText(_translate("MainWindow", "Path:", None))
        self.bzr_lib_path.setText(_translate("MainWindow", "(bzr-lib-path)", None))
        self.bazaar_configuration.setTitle(_translate("MainWindow", "Breezy Configuration", None))
        self.label_2.setText(_translate("MainWindow", "Settings:", None))
        self.bzr_config_dir.setText(_translate("MainWindow", "(bzr-config-dir)", None))
        self.label_4.setText(_translate("MainWindow", "Log File:", None))
        self.bzr_log_file.setText(_translate("MainWindow", "(bzr-log-file)", None))
        self.python_interpreter.setTitle(_translate("MainWindow", "Python Interpreter", None))
        self.label_5.setText(_translate("MainWindow", "Version:", None))
        self.python_version.setText(_translate("MainWindow", "(python-version)", None))
        self.label_9.setText(_translate("MainWindow", "Path:", None))
        self.python_file.setText(_translate("MainWindow", "(python-file)", None))
        self.label_7.setText(_translate("MainWindow", "Library:", None))
        self.python_lib_dir.setText(_translate("MainWindow", "(python-lib-dir)", None))

