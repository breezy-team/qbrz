# -*- coding: utf-8 -*-

# Form implementation generated from reading ui file 'ui/tag.ui'
#
# Created: Tue Sep 30 06:20:10 2008
#      by: PyQt4 UI code generator 4.3.1
#
# WARNING! All changes made in this file will be lost!

from PyQt4 import QtCore, QtGui
from bzrlib.plugins.qbzr.lib.i18n import gettext


class Ui_TagForm(object):
    def setupUi(self, TagForm):
        TagForm.setObjectName("TagForm")
        TagForm.setWindowModality(QtCore.Qt.NonModal)
        TagForm.resize(QtCore.QSize(QtCore.QRect(0,0,400,164).size()).expandedTo(TagForm.minimumSizeHint()))

        sizePolicy = QtGui.QSizePolicy(QtGui.QSizePolicy.Preferred,QtGui.QSizePolicy.Preferred)
        sizePolicy.setHorizontalStretch(0)
        sizePolicy.setVerticalStretch(0)
        sizePolicy.setHeightForWidth(TagForm.sizePolicy().hasHeightForWidth())
        TagForm.setSizePolicy(sizePolicy)
        TagForm.setMinimumSize(QtCore.QSize(0,0))
        TagForm.setContextMenuPolicy(QtCore.Qt.DefaultContextMenu)

        self.vboxlayout = QtGui.QVBoxLayout(TagForm)
        self.vboxlayout.setObjectName("vboxlayout")

        self.tag_group = QtGui.QGroupBox(TagForm)
        self.tag_group.setMinimumSize(QtCore.QSize(373,146))
        self.tag_group.setObjectName("tag_group")

        self.gridLayout = QtGui.QWidget(self.tag_group)
        self.gridLayout.setGeometry(QtCore.QRect(10,10,361,131))
        self.gridLayout.setObjectName("gridLayout")

        self.gridlayout = QtGui.QGridLayout(self.gridLayout)
        self.gridlayout.setObjectName("gridlayout")

        self.label_branch = QtGui.QLabel(self.gridLayout)
        self.label_branch.setObjectName("label_branch")
        self.gridlayout.addWidget(self.label_branch,0,0,1,1)

        self.branch_location = QtGui.QLineEdit(self.gridLayout)
        self.branch_location.setObjectName("branch_location")
        self.gridlayout.addWidget(self.branch_location,0,1,1,1)

        self.branch_browse = QtGui.QPushButton(self.gridLayout)
        self.branch_browse.setObjectName("branch_browse")
        self.gridlayout.addWidget(self.branch_browse,0,2,1,1)

        self.label_action = QtGui.QLabel(self.gridLayout)
        self.label_action.setObjectName("label_action")
        self.gridlayout.addWidget(self.label_action,1,0,1,1)

        self.cb_action = QtGui.QComboBox(self.gridLayout)
        self.cb_action.setObjectName("cb_action")
        self.gridlayout.addWidget(self.cb_action,1,1,1,1)

        self.label_tag_name = QtGui.QLabel(self.gridLayout)
        self.label_tag_name.setObjectName("label_tag_name")
        self.gridlayout.addWidget(self.label_tag_name,2,0,1,1)

        self.cb_tag = QtGui.QComboBox(self.gridLayout)
        self.cb_tag.setEditable(True)
        self.cb_tag.setObjectName("cb_tag")
        self.gridlayout.addWidget(self.cb_tag,2,1,1,1)

        self.label_revision = QtGui.QLabel(self.gridLayout)
        self.label_revision.setObjectName("label_revision")
        self.gridlayout.addWidget(self.label_revision,3,0,1,1)

        self.rev_edit = QtGui.QLineEdit(self.gridLayout)
        self.rev_edit.setObjectName("rev_edit")
        self.gridlayout.addWidget(self.rev_edit,3,1,1,1)

        self.pick_rev = QtGui.QPushButton(self.gridLayout)
        self.pick_rev.setEnabled(False)
        self.pick_rev.setObjectName("pick_rev")
        self.gridlayout.addWidget(self.pick_rev,3,2,1,1)
        self.vboxlayout.addWidget(self.tag_group)
        self.label_branch.setBuddy(self.branch_location)
        self.label_action.setBuddy(self.cb_action)
        self.label_tag_name.setBuddy(self.cb_tag)
        self.label_revision.setBuddy(self.rev_edit)

        self.retranslateUi(TagForm)
        QtCore.QMetaObject.connectSlotsByName(TagForm)
        TagForm.setTabOrder(self.branch_location,self.branch_browse)
        TagForm.setTabOrder(self.branch_browse,self.cb_action)
        TagForm.setTabOrder(self.cb_action,self.cb_tag)
        TagForm.setTabOrder(self.cb_tag,self.rev_edit)
        TagForm.setTabOrder(self.rev_edit,self.pick_rev)

    def retranslateUi(self, TagForm):
        TagForm.setWindowTitle(gettext("Tag"))
        self.tag_group.setTitle(gettext("Edit tag"))
        self.label_branch.setText(gettext("&Branch:"))
        self.branch_browse.setText(gettext("Browse..."))
        self.label_action.setText(gettext("&Action:"))
        self.cb_action.addItem(gettext("Create new tag"))
        self.cb_action.addItem(gettext("Move existing tag"))
        self.cb_action.addItem(gettext("Delete existing tag"))
        self.label_tag_name.setText(gettext("&Tag name:"))
        self.label_revision.setText(gettext("&Revision:"))
        self.pick_rev.setText(gettext("Select..."))

