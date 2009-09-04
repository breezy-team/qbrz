# -*- coding: utf-8 -*-

# Form implementation generated from reading ui file 'ui/tag.ui'
#
# Created: Thu Jul 30 12:12:07 2009
#      by: PyQt4 UI code generator 4.4.3
#
# WARNING! All changes made in this file will be lost!

from PyQt4 import QtCore, QtGui
from bzrlib.plugins.qbzr.lib.i18n import gettext


class Ui_TagForm(object):
    def setupUi(self, TagForm):
        TagForm.setObjectName("TagForm")
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
        self.vboxlayout.setObjectName("vboxlayout")
        self.branch_group = QtGui.QGroupBox(TagForm)
        self.branch_group.setObjectName("branch_group")
        self.gridlayout = QtGui.QGridLayout(self.branch_group)
        self.gridlayout.setObjectName("gridlayout")
        self.branch_location = QtGui.QLineEdit(self.branch_group)
        self.branch_location.setObjectName("branch_location")
        self.gridlayout.addWidget(self.branch_location, 0, 0, 1, 2)
        spacerItem = QtGui.QSpacerItem(261, 25, QtGui.QSizePolicy.Expanding, QtGui.QSizePolicy.Minimum)
        self.gridlayout.addItem(spacerItem, 1, 0, 1, 1)
        self.branch_browse = QtGui.QPushButton(self.branch_group)
        self.branch_browse.setObjectName("branch_browse")
        self.gridlayout.addWidget(self.branch_browse, 1, 1, 1, 1)
        self.vboxlayout.addWidget(self.branch_group)
        self.tag_group = QtGui.QGroupBox(TagForm)
        self.tag_group.setMinimumSize(QtCore.QSize(0, 0))
        self.tag_group.setObjectName("tag_group")
        self.gridlayout1 = QtGui.QGridLayout(self.tag_group)
        self.gridlayout1.setObjectName("gridlayout1")
        self.label_action = QtGui.QLabel(self.tag_group)
        self.label_action.setObjectName("label_action")
        self.gridlayout1.addWidget(self.label_action, 0, 0, 1, 1)
        self.cb_action = QtGui.QComboBox(self.tag_group)
        self.cb_action.setObjectName("cb_action")
        self.cb_action.addItem(QtCore.QString())
        self.cb_action.addItem(QtCore.QString())
        self.cb_action.addItem(QtCore.QString())
        self.gridlayout1.addWidget(self.cb_action, 0, 1, 1, 1)
        self.label_tag_name = QtGui.QLabel(self.tag_group)
        self.label_tag_name.setObjectName("label_tag_name")
        self.gridlayout1.addWidget(self.label_tag_name, 1, 0, 1, 1)
        self.cb_tag = QtGui.QComboBox(self.tag_group)
        self.cb_tag.setEditable(True)
        self.cb_tag.setObjectName("cb_tag")
        self.gridlayout1.addWidget(self.cb_tag, 1, 1, 1, 1)
        self.label_revision = QtGui.QLabel(self.tag_group)
        self.label_revision.setObjectName("label_revision")
        self.gridlayout1.addWidget(self.label_revision, 2, 0, 1, 1)
        self.rev_edit = QtGui.QLineEdit(self.tag_group)
        self.rev_edit.setObjectName("rev_edit")
        self.gridlayout1.addWidget(self.rev_edit, 2, 1, 1, 1)
        self.pick_rev = QtGui.QPushButton(self.tag_group)
        self.pick_rev.setEnabled(False)
        self.pick_rev.setObjectName("pick_rev")
        self.gridlayout1.addWidget(self.pick_rev, 2, 2, 1, 1)
        self.vboxlayout.addWidget(self.tag_group)
        self.label_action.setBuddy(self.cb_action)
        self.label_tag_name.setBuddy(self.cb_tag)
        self.label_revision.setBuddy(self.rev_edit)

        self.retranslateUi(TagForm)
        QtCore.QObject.connect(TagForm, QtCore.SIGNAL("disableUi(bool)"), self.tag_group.setDisabled)
        QtCore.QObject.connect(TagForm, QtCore.SIGNAL("disableUi(bool)"), self.branch_group.setDisabled)
        QtCore.QMetaObject.connectSlotsByName(TagForm)
        TagForm.setTabOrder(self.branch_location, self.branch_browse)
        TagForm.setTabOrder(self.branch_browse, self.cb_action)
        TagForm.setTabOrder(self.cb_action, self.cb_tag)
        TagForm.setTabOrder(self.cb_tag, self.rev_edit)
        TagForm.setTabOrder(self.rev_edit, self.pick_rev)

    def retranslateUi(self, TagForm):
        TagForm.setWindowTitle(gettext("Edit tag"))
        self.branch_group.setTitle(gettext("Branch"))
        self.branch_browse.setText(gettext("&Browse..."))
        self.tag_group.setTitle(gettext("Tag"))
        self.label_action.setText(gettext("&Action:"))
        self.cb_action.setItemText(0, gettext("Create new tag"))
        self.cb_action.setItemText(1, gettext("Move existing tag"))
        self.cb_action.setItemText(2, gettext("Delete existing tag"))
        self.label_tag_name.setText(gettext("&Tag name:"))
        self.label_revision.setText(gettext("&Revision:"))
        self.pick_rev.setText(gettext("&Select..."))

