# -*- coding: utf-8 -*-

# Form implementation generated from reading ui file 'ui/sysinfo.ui'
#
# Created: Sat Jun 13 23:57:47 2009
#      by: PyQt4 UI code generator 4.3.1
#
# WARNING! All changes made in this file will be lost!

from PyQt4 import QtCore, QtGui
from bzrlib.plugins.qbzr.lib.i18n import gettext


class Ui_MainWindow(object):
    def setupUi(self, MainWindow):
        MainWindow.setObjectName("MainWindow")
        MainWindow.resize(QtCore.QSize(QtCore.QRect(0,0,387,254).size()).expandedTo(MainWindow.minimumSizeHint()))

        self.centralwidget = QtGui.QWidget(MainWindow)
        self.centralwidget.setObjectName("centralwidget")

        self.vboxlayout = QtGui.QVBoxLayout(self.centralwidget)
        self.vboxlayout.setObjectName("vboxlayout")

        self.bazaar_library = QtGui.QGroupBox(self.centralwidget)
        self.bazaar_library.setFlat(False)
        self.bazaar_library.setObjectName("bazaar_library")

        self.gridlayout = QtGui.QGridLayout(self.bazaar_library)
        self.gridlayout.setObjectName("gridlayout")

        self.label = QtGui.QLabel(self.bazaar_library)
        self.label.setObjectName("label")
        self.gridlayout.addWidget(self.label,0,0,1,1)

        self.bzr_version = QtGui.QLabel(self.bazaar_library)
        self.bzr_version.setObjectName("bzr_version")
        self.gridlayout.addWidget(self.bzr_version,0,1,1,1)

        self.label_3 = QtGui.QLabel(self.bazaar_library)
        self.label_3.setObjectName("label_3")
        self.gridlayout.addWidget(self.label_3,1,0,1,1)

        self.bzr_lib_path = QtGui.QLabel(self.bazaar_library)
        self.bzr_lib_path.setMinimumSize(QtCore.QSize(300,0))
        self.bzr_lib_path.setObjectName("bzr_lib_path")
        self.gridlayout.addWidget(self.bzr_lib_path,1,1,1,1)
        self.vboxlayout.addWidget(self.bazaar_library)

        self.bazaar_configuration = QtGui.QGroupBox(self.centralwidget)
        self.bazaar_configuration.setObjectName("bazaar_configuration")

        self.gridlayout1 = QtGui.QGridLayout(self.bazaar_configuration)
        self.gridlayout1.setObjectName("gridlayout1")

        self.label_2 = QtGui.QLabel(self.bazaar_configuration)
        self.label_2.setObjectName("label_2")
        self.gridlayout1.addWidget(self.label_2,0,0,1,1)

        self.bzr_config_dir = QtGui.QLabel(self.bazaar_configuration)
        self.bzr_config_dir.setObjectName("bzr_config_dir")
        self.gridlayout1.addWidget(self.bzr_config_dir,0,1,1,1)

        self.label_4 = QtGui.QLabel(self.bazaar_configuration)
        self.label_4.setObjectName("label_4")
        self.gridlayout1.addWidget(self.label_4,1,0,1,1)

        self.bzr_log_file = QtGui.QLabel(self.bazaar_configuration)
        self.bzr_log_file.setMinimumSize(QtCore.QSize(300,0))
        self.bzr_log_file.setObjectName("bzr_log_file")
        self.gridlayout1.addWidget(self.bzr_log_file,1,1,1,1)
        self.vboxlayout.addWidget(self.bazaar_configuration)

        self.python_interpreter = QtGui.QGroupBox(self.centralwidget)
        self.python_interpreter.setMinimumSize(QtCore.QSize(0,0))
        self.python_interpreter.setObjectName("python_interpreter")

        self.gridlayout2 = QtGui.QGridLayout(self.python_interpreter)
        self.gridlayout2.setObjectName("gridlayout2")

        self.label_5 = QtGui.QLabel(self.python_interpreter)
        self.label_5.setObjectName("label_5")
        self.gridlayout2.addWidget(self.label_5,0,0,1,1)

        self.python_version = QtGui.QLabel(self.python_interpreter)
        self.python_version.setObjectName("python_version")
        self.gridlayout2.addWidget(self.python_version,0,1,1,1)

        self.label_9 = QtGui.QLabel(self.python_interpreter)
        self.label_9.setObjectName("label_9")
        self.gridlayout2.addWidget(self.label_9,1,0,1,1)

        self.python_file = QtGui.QLabel(self.python_interpreter)
        self.python_file.setObjectName("python_file")
        self.gridlayout2.addWidget(self.python_file,1,1,1,1)

        self.label_7 = QtGui.QLabel(self.python_interpreter)
        self.label_7.setObjectName("label_7")
        self.gridlayout2.addWidget(self.label_7,2,0,1,1)

        self.python_lib_dir = QtGui.QLabel(self.python_interpreter)
        self.python_lib_dir.setMinimumSize(QtCore.QSize(300,0))
        self.python_lib_dir.setObjectName("python_lib_dir")
        self.gridlayout2.addWidget(self.python_lib_dir,2,1,1,1)
        self.vboxlayout.addWidget(self.python_interpreter)
        MainWindow.setCentralWidget(self.centralwidget)

        self.retranslateUi(MainWindow)
        QtCore.QMetaObject.connectSlotsByName(MainWindow)

    def retranslateUi(self, MainWindow):
        MainWindow.setWindowTitle(gettext("System Information"))
        self.bazaar_library.setTitle(gettext("Bazaar Library"))
        self.label.setText(gettext("Version:"))
        self.bzr_version.setText(gettext("(bzr-version)"))
        self.label_3.setText(gettext("Path:"))
        self.bzr_lib_path.setText(gettext("(bzr-lib-path)"))
        self.bazaar_configuration.setTitle(gettext("Bazaar Configuration"))
        self.label_2.setText(gettext("Settings:"))
        self.bzr_config_dir.setText(gettext("(bzr-config-dir)"))
        self.label_4.setText(gettext("Log File:"))
        self.bzr_log_file.setText(gettext("(bzr-log-file)"))
        self.python_interpreter.setTitle(gettext("Python Interpreter"))
        self.label_5.setText(gettext("Version:"))
        self.python_version.setText(gettext("(python-version)"))
        self.label_9.setText(gettext("Path:"))
        self.python_file.setText(gettext("(python-file)"))
        self.label_7.setText(gettext("Library:"))
        self.python_lib_dir.setText(gettext("(python-lib-dir)"))

