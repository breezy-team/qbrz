# -*- coding: utf-8 -*-
#
# QBzr - Qt frontend to Bazaar commands
# Copyright (C) 2007 Lukáš Lalinský <lalinsky@gmail.com>
#
# This program is free software; you can redistribute it and/or
# modify it under the terms of the GNU General Public License
# as published by the Free Software Foundation; either version 2
# of the License, or (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program; if not, write to the Free Software
# Foundation, Inc., 51 Franklin Street, Fifth Floor, Boston, MA 02110-1301, USA.

import re
import os.path
from PyQt4 import QtCore, QtGui
from bzrlib.config import (
    GlobalConfig,
    ensure_config_dir_exists,
    extract_email_address,
    )
from bzrlib import errors

from bzrlib.plugins.qbzr.lib.i18n import gettext, N_
from bzrlib.plugins.qbzr.lib.util import (
    BTN_OK,
    BTN_CANCEL,
    QBzrDialog,
    extract_name,
    )


_mail_clients = [
    ('default', N_('Default')),
    ('thunderbird', N_('Thunderbird')),
    ('evolution', N_('Evolution')),
    ('kmail', N_('KMail')),
    ('mutt', N_('Mutt')),
    ('xdg-email', N_('XDG e-mail client')),
    ('mapi', N_('MAPI e-mail client')),
    ('editor', N_('Editor')),
]

_bug_tracker_re = re.compile('bugtracker_(.+?)_url')


class QBzrConfigWindow(QBzrDialog):

    def __init__(self, parent=None):
        QBzrDialog.__init__(self, [gettext("Configuration")], parent)
        self.restoreSize("config", (400, 300))

        tabwidget = QtGui.QTabWidget()

        generalWidget = QtGui.QWidget()
        generalVBox = QtGui.QVBoxLayout(generalWidget)
        generalGrid = QtGui.QGridLayout()

        self.nameEdit = QtGui.QLineEdit()
        label = QtGui.QLabel(gettext("&Name:"))
        label.setBuddy(self.nameEdit)
        generalGrid.addWidget(label, 0, 0)
        generalGrid.addWidget(self.nameEdit, 0, 1)

        self.emailEdit = QtGui.QLineEdit()
        label = QtGui.QLabel(gettext("E-&mail:"))
        label.setBuddy(self.emailEdit)
        generalGrid.addWidget(label, 1, 0)
        generalGrid.addWidget(self.emailEdit, 1, 1)

        self.editorEdit = QtGui.QLineEdit()
        label = QtGui.QLabel(gettext("&Editor:"))
        label.setBuddy(self.editorEdit)
        generalGrid.addWidget(label, 2, 0)
        generalGrid.addWidget(self.editorEdit, 2, 1)

        self.emailClientCombo = QtGui.QComboBox()
        for name, label in _mail_clients:
            self.emailClientCombo.addItem(gettext(label), QtCore.QVariant(name))
        label = QtGui.QLabel(gettext("E-mail &client:"))
        label.setBuddy(self.emailClientCombo)
        generalGrid.addWidget(label, 3, 0)
        generalGrid.addWidget(self.emailClientCombo, 3, 1)

        generalVBox.addLayout(generalGrid)
        generalVBox.addStretch()

        self.aliasesList = QtGui.QTreeWidget()
        self.aliasesList.setRootIsDecorated(False)
        self.aliasesList.setHeaderLabels([gettext("Alias"), gettext("Command")])

        addAliasButton = QtGui.QPushButton(gettext("Add"))
        self.connect(addAliasButton, QtCore.SIGNAL("clicked()"),
                     self.addAlias)
        removeAliasButton = QtGui.QPushButton(gettext("Remove"))
        self.connect(removeAliasButton, QtCore.SIGNAL("clicked()"),
                     self.removeAlias)

        aliasesHBox = QtGui.QHBoxLayout()
        aliasesHBox.addWidget(addAliasButton)
        aliasesHBox.addWidget(removeAliasButton)
        aliasesHBox.addStretch()

        aliasesWidget = QtGui.QWidget()
        aliasesVBox = QtGui.QVBoxLayout(aliasesWidget)
        aliasesVBox.addWidget(self.aliasesList)
        aliasesVBox.addLayout(aliasesHBox)

        self.bugTrackersList = QtGui.QTreeWidget()
        self.bugTrackersList.setRootIsDecorated(False)
        self.bugTrackersList.setHeaderLabels([gettext("Abbreviation"), gettext("URL")])

        addBugTrackerButton = QtGui.QPushButton(gettext("Add"))
        self.connect(addBugTrackerButton, QtCore.SIGNAL("clicked()"),
                     self.addBugTracker)
        removeBugTrackerButton = QtGui.QPushButton(gettext("Remove"))
        self.connect(removeBugTrackerButton, QtCore.SIGNAL("clicked()"),
                     self.removeBugTracker)

        bugTrackersHBox = QtGui.QHBoxLayout()
        bugTrackersHBox.addWidget(addBugTrackerButton)
        bugTrackersHBox.addWidget(removeBugTrackerButton)
        bugTrackersHBox.addStretch()

        bugTrackersWidget = QtGui.QWidget()
        bugTrackersVBox = QtGui.QVBoxLayout(bugTrackersWidget)
        bugTrackersVBox.addWidget(self.bugTrackersList)
        bugTrackersVBox.addLayout(bugTrackersHBox)

        tabwidget.addTab(generalWidget, gettext("General"))
        tabwidget.addTab(aliasesWidget, gettext("Aliases"))
        tabwidget.addTab(bugTrackersWidget, gettext("Bug Trackers"))

        buttonbox = self.create_button_box(BTN_OK, BTN_CANCEL)

        vbox = QtGui.QVBoxLayout(self.centralwidget)
        vbox.addWidget(tabwidget)
        vbox.addWidget(buttonbox)
        self.load()

    def load(self):
        """Load the configuration."""
        config = GlobalConfig()
        parser = config._get_parser()

        # Name & e-mail
        username = config.username()
        if username:
            self.nameEdit.setText(extract_name(username, strict=True))
            try:
                self.emailEdit.setText(extract_email_address(username))
            except errors.NoEmailInUsername:
                pass

        # Editor
        editor = config.get_user_option('editor')
        if editor:
            self.editorEdit.setText(editor)

        # E-mail client
        mailClient = config.get_user_option('mail_client')
        if mailClient:
            index = self.emailClientCombo.findData(
                QtCore.QVariant(mailClient))
            if index >= 0:
                self.emailClientCombo.setCurrentIndex(index)

        # Aliases
        aliases = parser.get('ALIASES', {})
        for alias, command in aliases.items():
            item = QtGui.QTreeWidgetItem(self.aliasesList)
            item.setFlags(QtCore.Qt.ItemIsSelectable |
                          QtCore.Qt.ItemIsEditable |
                          QtCore.Qt.ItemIsEnabled)
            item.setText(0, alias)
            item.setText(1, command)

        # Bug trackers
        for name, value in parser.get('DEFAULT', {}).items():
            m = _bug_tracker_re.match(name)
            if not m:
                continue
            abbreviation = m.group(1)
            item = QtGui.QTreeWidgetItem(self.bugTrackersList)
            item.setFlags(QtCore.Qt.ItemIsSelectable |
                          QtCore.Qt.ItemIsEditable |
                          QtCore.Qt.ItemIsEnabled)
            item.setText(0, abbreviation)
            item.setText(1, value)

    def save(self):
        """Save the configuration."""
        config = GlobalConfig()
        parser = config._get_parser()

        if 'DEFAULT' not in parser:
            parser['DEFAULT'] = {}

        # Name & e-mail
        username = '%s <%s>' % (
            unicode(self.nameEdit.text()),
            unicode(self.emailEdit.text()))
        parser['DEFAULT']['email'] = username

        # Editor
        editor = unicode(self.editorEdit.text())
        if editor:
            parser['DEFAULT']['editor'] = editor
        else:
            try:
                del parser['DEFAULT']['editor']
            except KeyError, e:
                pass

        # E-mail client
        index = self.emailClientCombo.currentIndex()
        emailClient = unicode(self.emailClientCombo.itemData(index).toString())
        if emailClient:
            parser['DEFAULT']['mail_client'] = emailClient
        else:
            try:
                del parser['DEFAULT']['mail_client']
            except KeyError:
                pass

        # Aliases
        parser['ALIASES'] = {}
        for index in range(self.aliasesList.topLevelItemCount()):
            item = self.aliasesList.topLevelItem(index)
            alias = unicode(item.text(0))
            command = unicode(item.text(1))
            if alias and command:
                parser['ALIASES'][alias] = command

        # Bug trackers
        for name, value in parser.get('DEFAULT', {}).items():
            m = _bug_tracker_re.match(name)
            if m:
                abbrev = m.group(1)
                del parser['DEFAULT']['bugtracker_%s_url' % abbrev]
        for index in range(self.bugTrackersList.topLevelItemCount()):
            item = self.bugTrackersList.topLevelItem(index)
            abbrev = unicode(item.text(0))
            url = unicode(item.text(1))
            # FIXME add URL validation (must contain {id})
            if abbrev and url:
                parser['DEFAULT']['bugtracker_%s_url' % abbrev] = url

        ensure_config_dir_exists(os.path.dirname(config._get_filename()))
        f = open(config._get_filename(), 'wb')
        parser.write(f)
        f.close()

    def accept(self):
        """Save changes and close the window."""
        self.save()
        self.close()

    def reject(self):
        """Close the window."""
        self.close()

    def addAlias(self):
        item = QtGui.QTreeWidgetItem(self.aliasesList)
        item.setFlags(QtCore.Qt.ItemIsSelectable |
                      QtCore.Qt.ItemIsEditable |
                      QtCore.Qt.ItemIsEnabled)
        self.aliasesList.setCurrentItem(item)
        self.aliasesList.editItem(item, 0)

    def removeAlias(self):
        for item in self.aliasesList.selectedItems():
            index = self.aliasesList.indexOfTopLevelItem(item)
            if index >= 0:
                self.aliasesList.takeTopLevelItem(index)

    def addBugTracker(self):
        item = QtGui.QTreeWidgetItem(self.bugTrackersList)
        item.setFlags(QtCore.Qt.ItemIsSelectable |
                      QtCore.Qt.ItemIsEditable |
                      QtCore.Qt.ItemIsEnabled)
        self.bugTrackersList.setCurrentItem(item)
        self.bugTrackersList.editItem(item, 0)

    def removeBugTracker(self):
        for item in self.bugTrackersList.selectedItems():
            index = self.bugTrackersList.indexOfTopLevelItem(item)
            if index >= 0:
                self.bugTrackersList.takeTopLevelItem(index)