# -*- coding: utf-8 -*-

# Form implementation generated from reading ui file 'ui/tag.ui'
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

class Ui_TagForm(object):
    def setupUi(self, TagForm):
        TagForm.setObjectName(_fromUtf8("TagForm"))
        TagForm.setWindowModality(QtCore.Qt.NonModal)
        TagForm.resize(340, 220)
        sizePolicy = QtGui.QSizePolicy(QtGui.QSizePolicy.Preferred, QtGui.QSizePolicy.Preferred)
        sizePolicy.setHorizontalStretch(0)
        sizePolicy.setVerticalStretch(0)
        sizePolicy.setHeightForWidth(TagForm.sizePolicy().hasHeightForWidth())
        TagForm.setSizePolicy(sizePolicy)
        TagForm.setMinimumSize(QtCore.QSize(0, 0))
        TagForm.setContextMenuPolicy(QtCore.Qt.DefaultContextMenu)
        self.vboxlayout = QtGui.QVBoxLayout(TagForm)
        self.vboxlayout.setMargin(9)
        self.vboxlayout.setSpacing(6)
        self.vboxlayout.setObjectName(_fromUtf8("vboxlayout"))
        self.branch_group = QtGui.QGroupBox(TagForm)
        self.branch_group.setObjectName(_fromUtf8("branch_group"))
        self.gridlayout = QtGui.QGridLayout(self.branch_group)
        self.gridlayout.setMargin(9)
        self.gridlayout.setSpacing(6)
        self.gridlayout.setObjectName(_fromUtf8("gridlayout"))
        self.branch_location = QtGui.QLineEdit(self.branch_group)
        self.branch_location.setObjectName(_fromUtf8("branch_location"))
        self.gridlayout.addWidget(self.branch_location, 0, 0, 1, 2)
        spacerItem = QtGui.QSpacerItem(261, 25, QtGui.QSizePolicy.Expanding, QtGui.QSizePolicy.Minimum)
        self.gridlayout.addItem(spacerItem, 1, 0, 1, 1)
        self.branch_browse = QtGui.QPushButton(self.branch_group)
        self.branch_browse.setObjectName(_fromUtf8("branch_browse"))
        self.gridlayout.addWidget(self.branch_browse, 1, 1, 1, 1)
        self.vboxlayout.addWidget(self.branch_group)
        self.tag_group = QtGui.QGroupBox(TagForm)
        self.tag_group.setMinimumSize(QtCore.QSize(0, 0))
        self.tag_group.setObjectName(_fromUtf8("tag_group"))
        self.gridlayout1 = QtGui.QGridLayout(self.tag_group)
        self.gridlayout1.setMargin(9)
        self.gridlayout1.setSpacing(6)
        self.gridlayout1.setObjectName(_fromUtf8("gridlayout1"))
        self.label_action = QtGui.QLabel(self.tag_group)
        self.label_action.setObjectName(_fromUtf8("label_action"))
        self.gridlayout1.addWidget(self.label_action, 0, 0, 1, 1)
        self.cb_action = QtGui.QComboBox(self.tag_group)
        self.cb_action.setObjectName(_fromUtf8("cb_action"))
        self.cb_action.addItem(_fromUtf8(""))
        self.cb_action.addItem(_fromUtf8(""))
        self.cb_action.addItem(_fromUtf8(""))
        self.gridlayout1.addWidget(self.cb_action, 0, 1, 1, 1)
        self.label_tag_name = QtGui.QLabel(self.tag_group)
        self.label_tag_name.setObjectName(_fromUtf8("label_tag_name"))
        self.gridlayout1.addWidget(self.label_tag_name, 1, 0, 1, 1)
        self.cb_tag = QtGui.QComboBox(self.tag_group)
        self.cb_tag.setEditable(True)
        self.cb_tag.setObjectName(_fromUtf8("cb_tag"))
        self.gridlayout1.addWidget(self.cb_tag, 1, 1, 1, 1)
        self.label_revision = QtGui.QLabel(self.tag_group)
        self.label_revision.setObjectName(_fromUtf8("label_revision"))
        self.gridlayout1.addWidget(self.label_revision, 2, 0, 1, 1)
        self.rev_edit = QtGui.QLineEdit(self.tag_group)
        self.rev_edit.setObjectName(_fromUtf8("rev_edit"))
        self.gridlayout1.addWidget(self.rev_edit, 2, 1, 1, 1)
        self.pick_rev = QtGui.QPushButton(self.tag_group)
        self.pick_rev.setEnabled(False)
        self.pick_rev.setObjectName(_fromUtf8("pick_rev"))
        self.gridlayout1.addWidget(self.pick_rev, 2, 2, 1, 1)
        self.vboxlayout.addWidget(self.tag_group)
        self.label_action.setBuddy(self.cb_action)
        self.label_tag_name.setBuddy(self.cb_tag)
        self.label_revision.setBuddy(self.rev_edit)

        self.retranslateUi(TagForm)
        QtCore.QObject.connect(TagForm, QtCore.SIGNAL(_fromUtf8("disableUi(bool)")), self.tag_group.setDisabled)
        QtCore.QObject.connect(TagForm, QtCore.SIGNAL(_fromUtf8("disableUi(bool)")), self.branch_group.setDisabled)
        QtCore.QMetaObject.connectSlotsByName(TagForm)
        TagForm.setTabOrder(self.branch_location, self.branch_browse)
        TagForm.setTabOrder(self.branch_browse, self.cb_action)
        TagForm.setTabOrder(self.cb_action, self.cb_tag)
        TagForm.setTabOrder(self.cb_tag, self.rev_edit)
        TagForm.setTabOrder(self.rev_edit, self.pick_rev)

    def retranslateUi(self, TagForm):
        TagForm.setWindowTitle(_translate("TagForm", "Edit tag", None))
        self.branch_group.setTitle(_translate("TagForm", "Branch", None))
        self.branch_browse.setText(_translate("TagForm", "&Browse...", None))
        self.tag_group.setTitle(_translate("TagForm", "Tag", None))
        self.label_action.setText(_translate("TagForm", "&Action:", None))
        self.cb_action.setItemText(0, _translate("TagForm", "Create new tag", None))
        self.cb_action.setItemText(1, _translate("TagForm", "Replace existing tag", None))
        self.cb_action.setItemText(2, _translate("TagForm", "Delete existing tag", None))
        self.label_tag_name.setText(_translate("TagForm", "&Tag name:", None))
        self.label_revision.setText(_translate("TagForm", "&Revision:", None))
        self.pick_rev.setText(_translate("TagForm", "&Select...", None))

