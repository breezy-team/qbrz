# -*- coding: utf-8 -*-
#
# QBzr - Qt frontend to Bazaar commands
#
# Contributor:
#   Alexander Belchenko, 2009
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

"""Dialog to run arbitrary bzr command."""

from PyQt4 import QtCore, QtGui

from bzrlib import osutils

from bzrlib.plugins.qbzr.lib.help import get_help_topic_as_html
from bzrlib.plugins.qbzr.lib.i18n import gettext
from bzrlib.plugins.qbzr.lib.subprocess import SubProcessDialog
from bzrlib.plugins.qbzr.lib.ui_run import Ui_RunDialog
from bzrlib.plugins.qbzr.lib.util import hookup_directory_picker


class QBzrRunDialog(SubProcessDialog):

    def __init__(self, location=None, ui_mode=False, parent=None):
        super(QBzrRunDialog, self).__init__(name="run", ui_mode=ui_mode,
            dialog=True, parent=parent)
        self.ui = Ui_RunDialog()
        self.ui.setupUi(self)
        if location is None:
            location = osutils.getcwd()
        self.ui.wd_edit.setText(location)
        # cmd_combobox should fill all available space
        self.ui.cmd_layout.setColumnStretch(1, 2)  
        # fill cmd_combobox with available commands
        self.collect_command_names()
        self.set_cmd_combobox()
        # set help_browser with some default text
        self.set_default_help()
        # and add the subprocess widgets
        for w in self.make_default_layout_widgets():
            self.ui.splitter.addWidget(w)
        self.process_widget.hide_progress()
        # setup signals
        QtCore.QObject.connect(self.ui.hidden_checkbox,
            QtCore.SIGNAL("stateChanged(int)"),
            self.set_cmd_combobox)
        QtCore.QObject.connect(self.ui.cmd_combobox,
            QtCore.SIGNAL("currentIndexChanged(const QString&)"),
            self.set_cmd_help)
        QtCore.QObject.connect(self.ui.cmd_combobox,
            QtCore.SIGNAL("editTextChanged(const QString&)"),
            self.set_cmd_help)
        hookup_directory_picker(self, self.ui.browse_button, 
            self.ui.wd_edit, gettext("Select working directory"))
        # ready to go
        self.ui.cmd_combobox.setFocus()

    def set_default_help(self):
        self.ui.help_browser.setHtml("<i><small>%s</small></i>" % 
            gettext("Help for command"))

    def collect_command_names(self):
        from bzrlib import commands as _mod_commands
        names = list(_mod_commands.all_command_names())
        self.cmds_dict = dict((n, _mod_commands.get_cmd_object(n)) 
                              for n in names)
        self.all_cmds = sorted(names)
        self.public_cmds = sorted([n 
                                   for n,o in self.cmds_dict.iteritems()
                                   if not o.hidden])

    def set_cmd_combobox(self, all=False):
        cb = self.ui.cmd_combobox
        cb.clear()
        if all:
            cb.addItems(self.all_cmds)
        else:
            cb.addItems(self.public_cmds)
        cb.setCurrentIndex(-1)    

    def set_cmd_help(self, cmd_name):
        cmd_name = unicode(cmd_name)
        cmd_object = self.cmds_dict.get(cmd_name)
        if cmd_object:
            self.ui.help_browser.setHtml(
                get_help_topic_as_html("commands/"+cmd_name))
        else:
            self.set_default_help()

    def validate(self):
        return False