# -*- coding: utf-8 -*-

# Form implementation generated from reading ui file 'ui/sysinfo.ui'
#
# Created by: PyQt5 UI code generator 5.12.3
#
# WARNING! All changes made in this file will be lost!


from PyQt5 import QtCore, QtGui, QtWidgets
from breezy.plugins.qbrz.lib.i18n import gettext



class Ui_MainWindow(object):
    def setupUi(self, MainWindow):
        MainWindow.setObjectName("MainWindow")
        MainWindow.resize(404, 288)
        self.centralwidget = QtWidgets.QWidget(MainWindow)
        self.centralwidget.setObjectName("centralwidget")
        self.vboxlayout = QtWidgets.QVBoxLayout(self.centralwidget)
        self.vboxlayout.setObjectName("vboxlayout")
        self.bazaar_library = QtWidgets.QGroupBox(self.centralwidget)
        self.bazaar_library.setFlat(False)
        self.bazaar_library.setObjectName("bazaar_library")
        self.gridlayout = QtWidgets.QGridLayout(self.bazaar_library)
        self.gridlayout.setObjectName("gridlayout")
        self.label = QtWidgets.QLabel(self.bazaar_library)
        self.label.setObjectName("label")
        self.gridlayout.addWidget(self.label, 0, 0, 1, 1)
        self.bzr_version = QtWidgets.QLabel(self.bazaar_library)
        self.bzr_version.setObjectName("bzr_version")
        self.gridlayout.addWidget(self.bzr_version, 0, 1, 1, 1)
        self.label_3 = QtWidgets.QLabel(self.bazaar_library)
        self.label_3.setObjectName("label_3")
        self.gridlayout.addWidget(self.label_3, 1, 0, 1, 1)
        self.bzr_lib_path = QtWidgets.QLabel(self.bazaar_library)
        self.bzr_lib_path.setMinimumSize(QtCore.QSize(300, 0))
        self.bzr_lib_path.setObjectName("bzr_lib_path")
        self.gridlayout.addWidget(self.bzr_lib_path, 1, 1, 1, 1)
        self.vboxlayout.addWidget(self.bazaar_library)
        self.bazaar_configuration = QtWidgets.QGroupBox(self.centralwidget)
        self.bazaar_configuration.setObjectName("bazaar_configuration")
        self.gridlayout1 = QtWidgets.QGridLayout(self.bazaar_configuration)
        self.gridlayout1.setObjectName("gridlayout1")
        self.label_2 = QtWidgets.QLabel(self.bazaar_configuration)
        self.label_2.setObjectName("label_2")
        self.gridlayout1.addWidget(self.label_2, 0, 0, 1, 1)
        self.bzr_config_dir = QtWidgets.QLabel(self.bazaar_configuration)
        self.bzr_config_dir.setObjectName("bzr_config_dir")
        self.gridlayout1.addWidget(self.bzr_config_dir, 0, 1, 1, 1)
        self.label_4 = QtWidgets.QLabel(self.bazaar_configuration)
        self.label_4.setObjectName("label_4")
        self.gridlayout1.addWidget(self.label_4, 1, 0, 1, 1)
        self.bzr_log_file = QtWidgets.QLabel(self.bazaar_configuration)
        self.bzr_log_file.setMinimumSize(QtCore.QSize(300, 0))
        self.bzr_log_file.setObjectName("bzr_log_file")
        self.gridlayout1.addWidget(self.bzr_log_file, 1, 1, 1, 1)
        self.vboxlayout.addWidget(self.bazaar_configuration)
        self.python_interpreter = QtWidgets.QGroupBox(self.centralwidget)
        self.python_interpreter.setMinimumSize(QtCore.QSize(0, 0))
        self.python_interpreter.setObjectName("python_interpreter")
        self.gridlayout2 = QtWidgets.QGridLayout(self.python_interpreter)
        self.gridlayout2.setObjectName("gridlayout2")
        self.label_5 = QtWidgets.QLabel(self.python_interpreter)
        self.label_5.setObjectName("label_5")
        self.gridlayout2.addWidget(self.label_5, 0, 0, 1, 1)
        self.python_version = QtWidgets.QLabel(self.python_interpreter)
        self.python_version.setObjectName("python_version")
        self.gridlayout2.addWidget(self.python_version, 0, 1, 1, 1)
        self.label_9 = QtWidgets.QLabel(self.python_interpreter)
        self.label_9.setObjectName("label_9")
        self.gridlayout2.addWidget(self.label_9, 1, 0, 1, 1)
        self.python_file = QtWidgets.QLabel(self.python_interpreter)
        self.python_file.setObjectName("python_file")
        self.gridlayout2.addWidget(self.python_file, 1, 1, 1, 1)
        self.label_7 = QtWidgets.QLabel(self.python_interpreter)
        self.label_7.setObjectName("label_7")
        self.gridlayout2.addWidget(self.label_7, 2, 0, 1, 1)
        self.python_lib_dir = QtWidgets.QLabel(self.python_interpreter)
        self.python_lib_dir.setMinimumSize(QtCore.QSize(300, 0))
        self.python_lib_dir.setObjectName("python_lib_dir")
        self.gridlayout2.addWidget(self.python_lib_dir, 2, 1, 1, 1)
        self.vboxlayout.addWidget(self.python_interpreter)
        MainWindow.setCentralWidget(self.centralwidget)

        self.retranslateUi(MainWindow)
        QtCore.QMetaObject.connectSlotsByName(MainWindow)

    def retranslateUi(self, MainWindow):
        _translate = QtCore.QCoreApplication.translate
        MainWindow.setWindowTitle(_translate("MainWindow", "System Information"))
        self.bazaar_library.setTitle(_translate("MainWindow", "Breezy Library"))
        self.label.setText(_translate("MainWindow", "Version:"))
        self.bzr_version.setText(_translate("MainWindow", "(bzr-version)"))
        self.label_3.setText(_translate("MainWindow", "Path:"))
        self.bzr_lib_path.setText(_translate("MainWindow", "(bzr-lib-path)"))
        self.bazaar_configuration.setTitle(_translate("MainWindow", "Breezy Configuration"))
        self.label_2.setText(_translate("MainWindow", "Settings:"))
        self.bzr_config_dir.setText(_translate("MainWindow", "(bzr-config-dir)"))
        self.label_4.setText(_translate("MainWindow", "Log File:"))
        self.bzr_log_file.setText(_translate("MainWindow", "(bzr-log-file)"))
        self.python_interpreter.setTitle(_translate("MainWindow", "Python Interpreter"))
        self.label_5.setText(_translate("MainWindow", "Version:"))
        self.python_version.setText(_translate("MainWindow", "(python-version)"))
        self.label_9.setText(_translate("MainWindow", "Path:"))
        self.python_file.setText(_translate("MainWindow", "(python-file)"))
        self.label_7.setText(_translate("MainWindow", "Library:"))
        self.python_lib_dir.setText(_translate("MainWindow", "(python-lib-dir)"))
