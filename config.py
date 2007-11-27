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

from PyQt4 import QtCore, QtGui
from bzrlib.config import GlobalConfig, extract_email_address
from bzrlib.plugins.qbzr.i18n import gettext, N_
from bzrlib.plugins.qbzr.util import (
    BTN_OK,
    BTN_CANCEL,
    QBzrWindow,
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


class QBzrConfigWindow(QBzrWindow):

    def __init__(self, parent=None):
        QBzrWindow.__init__(self, [gettext("Configure")], (400, 300), parent)

        tabwidget = QtGui.QTabWidget()

        general = QtGui.QWidget()
        generalVBox = QtGui.QVBoxLayout(general)
        generalGrid = QtGui.QGridLayout()

        self.nameEdit = QtGui.QLineEdit()
        label = QtGui.QLabel(gettext("&Name:"))
        label.setBuddy(self.nameEdit)
        generalGrid.addWidget(label, 0, 0)
        generalGrid.addWidget(self.nameEdit, 0, 1)

        self.emailEdit = QtGui.QLineEdit()
        label = QtGui.QLabel(gettext("&E-mail:"))
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
        tabwidget.addTab(general, gettext("General"))

        buttonbox = self.create_button_box(BTN_OK, BTN_CANCEL)

        vbox = QtGui.QVBoxLayout(self.centralwidget)
        vbox.addWidget(tabwidget)
        vbox.addWidget(buttonbox)
        self.load()

    def load(self):
        """Load the configuration."""
        config = GlobalConfig()

        # Name & e-mail
        username = config.username()
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
        mail_client = config.get_user_option('mail_client')
        index = self.emailClientCombo.findData(QtCore.QVariant(mail_client))
        if index >= 0:
            self.emailClientCombo.setCurrentIndex(index)

    def save(self):
        """Save the configuration."""
        config = GlobalConfig()

        # Name & e-mail
        username = '%s <%s>' % (
            unicode(self.nameEdit.text()),
            unicode(self.emailEdit.text()))
        config.set_user_option('email', username)

        # Editor
        editor = unicode(self.editorEdit.text())
        config.set_user_option('editor', editor)

        # E-mail client
        index = self.emailClientCombo.currentIndex()
        mail_client = unicode(self.emailClientCombo.itemData(index).toString())
        config.set_user_option('mail_client', mail_client)

    def accept(self):
        """Save changes and close the window."""
        self.save()
        self.close()

    def reject(self):
        """Close the window."""
        self.close()
