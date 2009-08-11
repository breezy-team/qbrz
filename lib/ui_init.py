# -*- coding: utf-8 -*-

# Form implementation generated from reading ui file 'ui/init.ui'
#
# Created: Thu Jul 30 12:22:19 2009
#      by: PyQt4 UI code generator 4.4.3
#
# WARNING! All changes made in this file will be lost!

from PyQt4 import QtCore, QtGui
from bzrlib.plugins.qbzr.lib.i18n import gettext


class Ui_InitForm(object):
    def setupUi(self, InitForm):
        InitForm.setObjectName("InitForm")
        InitForm.resize(417, 351)
        self.verticalLayout = QtGui.QVBoxLayout(InitForm)
        self.verticalLayout.setMargin(9)
        self.verticalLayout.setObjectName("verticalLayout")
        self.groupBox_3 = QtGui.QGroupBox(InitForm)
        self.groupBox_3.setObjectName("groupBox_3")
        self.horizontalLayout = QtGui.QHBoxLayout(self.groupBox_3)
        self.horizontalLayout.setObjectName("horizontalLayout")
        self.location = QtGui.QLineEdit(self.groupBox_3)
        sizePolicy = QtGui.QSizePolicy(QtGui.QSizePolicy.Expanding, QtGui.QSizePolicy.Fixed)
        sizePolicy.setHorizontalStretch(1)
        sizePolicy.setVerticalStretch(0)
        sizePolicy.setHeightForWidth(self.location.sizePolicy().hasHeightForWidth())
        self.location.setSizePolicy(sizePolicy)
        self.location.setObjectName("location")
        self.horizontalLayout.addWidget(self.location)
        self.location_picker = QtGui.QPushButton(self.groupBox_3)
        self.location_picker.setObjectName("location_picker")
        self.horizontalLayout.addWidget(self.location_picker)
        self.verticalLayout.addWidget(self.groupBox_3)
        self.groupBox = QtGui.QGroupBox(InitForm)
        self.groupBox.setObjectName("groupBox")
        self.verticalLayout_3 = QtGui.QVBoxLayout(self.groupBox)
        self.verticalLayout_3.setObjectName("verticalLayout_3")
        self.but_init = QtGui.QRadioButton(self.groupBox)
        self.but_init.setChecked(True)
        self.but_init.setObjectName("but_init")
        self.verticalLayout_3.addWidget(self.but_init)
        self.horizontalLayout_3 = QtGui.QHBoxLayout()
        self.horizontalLayout_3.setObjectName("horizontalLayout_3")
        spacerItem = QtGui.QSpacerItem(20, 20, QtGui.QSizePolicy.Fixed, QtGui.QSizePolicy.Minimum)
        self.horizontalLayout_3.addItem(spacerItem)
        self.but_append_only = QtGui.QCheckBox(self.groupBox)
        self.but_append_only.setObjectName("but_append_only")
        self.horizontalLayout_3.addWidget(self.but_append_only)
        self.verticalLayout_3.addLayout(self.horizontalLayout_3)
        self.radioButton_2 = QtGui.QRadioButton(self.groupBox)
        self.radioButton_2.setObjectName("radioButton_2")
        self.verticalLayout_3.addWidget(self.radioButton_2)
        self.horizontalLayout_4 = QtGui.QHBoxLayout()
        self.horizontalLayout_4.setObjectName("horizontalLayout_4")
        spacerItem1 = QtGui.QSpacerItem(20, 20, QtGui.QSizePolicy.Fixed, QtGui.QSizePolicy.Minimum)
        self.horizontalLayout_4.addItem(spacerItem1)
        self.but_no_trees = QtGui.QCheckBox(self.groupBox)
        self.but_no_trees.setEnabled(False)
        self.but_no_trees.setObjectName("but_no_trees")
        self.horizontalLayout_4.addWidget(self.but_no_trees)
        self.verticalLayout_3.addLayout(self.horizontalLayout_4)
        self.link_help = QtGui.QLabel(self.groupBox)
        self.link_help.setObjectName("link_help")
        self.verticalLayout_3.addWidget(self.link_help)
        self.horizontalLayout_2 = QtGui.QHBoxLayout()
        self.horizontalLayout_2.setObjectName("horizontalLayout_2")
        self.label = QtGui.QLabel(self.groupBox)
        self.label.setObjectName("label")
        self.horizontalLayout_2.addWidget(self.label)
        self.combo_format = QtGui.QComboBox(self.groupBox)
        sizePolicy = QtGui.QSizePolicy(QtGui.QSizePolicy.Preferred, QtGui.QSizePolicy.Fixed)
        sizePolicy.setHorizontalStretch(1)
        sizePolicy.setVerticalStretch(0)
        sizePolicy.setHeightForWidth(self.combo_format.sizePolicy().hasHeightForWidth())
        self.combo_format.setSizePolicy(sizePolicy)
        self.combo_format.setObjectName("combo_format")
        self.horizontalLayout_2.addWidget(self.combo_format)
        self.verticalLayout_3.addLayout(self.horizontalLayout_2)
        self.scrollArea = QtGui.QScrollArea(self.groupBox)
        sizePolicy = QtGui.QSizePolicy(QtGui.QSizePolicy.Expanding, QtGui.QSizePolicy.Expanding)
        sizePolicy.setHorizontalStretch(0)
        sizePolicy.setVerticalStretch(0)
        sizePolicy.setHeightForWidth(self.scrollArea.sizePolicy().hasHeightForWidth())
        self.scrollArea.setSizePolicy(sizePolicy)
        self.scrollArea.setWidgetResizable(True)
        self.scrollArea.setObjectName("scrollArea")
        self.scrollAreaWidgetContents = QtGui.QWidget(self.scrollArea)
        self.scrollAreaWidgetContents.setGeometry(QtCore.QRect(0, 0, 377, 60))
        self.scrollAreaWidgetContents.setObjectName("scrollAreaWidgetContents")
        self.verticalLayout_2 = QtGui.QVBoxLayout(self.scrollAreaWidgetContents)
        self.verticalLayout_2.setMargin(4)
        self.verticalLayout_2.setObjectName("verticalLayout_2")
        self.format_desc = QtGui.QLabel(self.scrollAreaWidgetContents)
        self.format_desc.setAlignment(QtCore.Qt.AlignLeading|QtCore.Qt.AlignLeft|QtCore.Qt.AlignTop)
        self.format_desc.setWordWrap(True)
        self.format_desc.setObjectName("format_desc")
        self.verticalLayout_2.addWidget(self.format_desc)
        self.scrollArea.setWidget(self.scrollAreaWidgetContents)
        self.verticalLayout_3.addWidget(self.scrollArea)
        self.link_help_formats = QtGui.QLabel(self.groupBox)
        self.link_help_formats.setObjectName("link_help_formats")
        self.verticalLayout_3.addWidget(self.link_help_formats)
        self.verticalLayout.addWidget(self.groupBox)

        self.retranslateUi(InitForm)
        QtCore.QObject.connect(self.link_help, QtCore.SIGNAL("linkActivated(QString)"), InitForm.linkActivated)
        QtCore.QObject.connect(self.link_help_formats, QtCore.SIGNAL("linkActivated(QString)"), InitForm.linkActivated)
        QtCore.QObject.connect(InitForm, QtCore.SIGNAL("disableUi(bool)"), self.groupBox_3.setDisabled)
        QtCore.QObject.connect(InitForm, QtCore.SIGNAL("disableUi(bool)"), self.groupBox.setDisabled)
        QtCore.QObject.connect(self.but_init, QtCore.SIGNAL("toggled(bool)"), self.but_append_only.setEnabled)
        QtCore.QObject.connect(self.radioButton_2, QtCore.SIGNAL("toggled(bool)"), self.but_no_trees.setEnabled)
        QtCore.QMetaObject.connectSlotsByName(InitForm)

    def retranslateUi(self, InitForm):
        InitForm.setWindowTitle(gettext("Initialize"))
        self.groupBox_3.setTitle(gettext("Local Directory"))
        self.location_picker.setText(gettext("Browse..."))
        self.groupBox.setTitle(gettext("Repository"))
        self.but_init.setText(gettext("Create a new standalone tree"))
        self.but_append_only.setText(gettext("Ensure all revisions are appended to the log"))
        self.radioButton_2.setText(gettext("Create a new shared repository"))
        self.but_no_trees.setText(gettext("Skip the creation of working trees in this repository"))
        self.link_help.setText(QtGui.QApplication.translate("InitForm", "<!DOCTYPE HTML PUBLIC \"-//W3C//DTD HTML 4.0//EN\" \"http://www.w3.org/TR/REC-html40/strict.dtd\">\n"
"<html><head><meta name=\"qrichtext\" content=\"1\" /><style type=\"text/css\">\n"
"p, li { white-space: pre-wrap; }\n"
"</style></head><body style=\" font-family:\'MS Shell Dlg 2\'; font-size:8.25pt; font-weight:400; font-style:normal;\">\n"
"<p style=\" margin-top:0px; margin-bottom:0px; margin-left:0px; margin-right:0px; -qt-block-indent:0; text-indent:0px;\">Tell me more about <a href=\"bzrtopic:standalone-trees\"><span style=\" text-decoration: underline; color:#0000ff;\">standalone trees</span></a>, <a href=\"bzrtopic:repositories\"><span style=\" text-decoration: underline; color:#0000ff;\">repositories</span></a> and <a href=\"bzrtopic:branches\"><span style=\" text-decoration: underline; color:#0000ff;\">branches</span></a>.</p></body></html>", None, QtGui.QApplication.UnicodeUTF8))
        self.label.setText(gettext("Repository Format:"))
        self.format_desc.setText(gettext("Description of format"))
        self.link_help_formats.setText(QtGui.QApplication.translate("InitForm", "<!DOCTYPE HTML PUBLIC \"-//W3C//DTD HTML 4.0//EN\" \"http://www.w3.org/TR/REC-html40/strict.dtd\">\n"
"<html><head><meta name=\"qrichtext\" content=\"1\" /><style type=\"text/css\">\n"
"p, li { white-space: pre-wrap; }\n"
"</style></head><body style=\" font-family:\'MS Shell Dlg 2\'; font-size:8.25pt; font-weight:400; font-style:normal;\">\n"
"<p style=\" margin-top:0px; margin-bottom:0px; margin-left:0px; margin-right:0px; -qt-block-indent:0; text-indent:0px;\"><a href=\"bzrtopic:formats\"><span style=\" text-decoration: underline; color:#0000ff;\">More information about repository formats.</span></a></p></body></html>", None, QtGui.QApplication.UnicodeUTF8))

