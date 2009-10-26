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

import os
import shlex
from PyQt4 import QtCore, QtGui

from bzrlib import osutils

from bzrlib.plugins.qbzr.lib import MS_WINDOWS
from bzrlib.plugins.qbzr.lib.help import get_help_topic_as_html
from bzrlib.plugins.qbzr.lib.i18n import gettext
from bzrlib.plugins.qbzr.lib.subprocess import SubProcessDialog
from bzrlib.plugins.qbzr.lib.ui_run import Ui_RunDialog
from bzrlib.plugins.qbzr.lib.util import hookup_directory_picker


class QBzrRunDialog(SubProcessDialog):

    def __init__(self, workdir=None, ui_mode=False, parent=None):
        """Build dialog.
        @param workdir: working directory to run command.
        @param ui_mode: wait after the operation is complete.
        @param parent:  parent window.
        """
        super(QBzrRunDialog, self).__init__(name="run", ui_mode=ui_mode,
            dialog=True, parent=parent)
        self.ui = Ui_RunDialog()
        self.ui.setupUi(self)
        if workdir is None:
            workdir = osutils.getcwd()
        self.ui.wd_edit.setText(workdir)
        # cmd_combobox should fill all available space
        self.ui.cmd_layout.setColumnStretch(1, 1)
        self.ui.cmd_layout.setColumnStretch(2, 1)
        # fill cmd_combobox with available commands
        self.collect_command_names()
        self.set_cmd_combobox()
        # set help_browser with some default text
        self.set_default_help()
        # and add the subprocess widgets
        self.splitter = self.ui.splitter
        for w in self.make_default_layout_widgets():
            self.splitter.addWidget(w)
        self.process_widget.hide_progress()
        # restore the sizes
        self.restoreSize("run", None)
        self.restoreSplitterSizes()
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
        QtCore.QObject.connect(self.ui.directory_button,
            QtCore.SIGNAL("clicked()"),
            self.insert_directory)
        QtCore.QObject.connect(self.ui.filenames_button,
            QtCore.SIGNAL("clicked()"),
            self.insert_filenames)
        # ready to go
        self.ui.cmd_combobox.setFocus()

    def set_default_help(self):
        """Set default text in help widget."""
        self.ui.help_browser.setHtml("<i><small>%s</small></i>" % 
            gettext("Help for command"))

    def collect_command_names(self):
        """Collect names of available bzr commands."""
        from bzrlib import commands as _mod_commands
        names = list(_mod_commands.all_command_names())
        self.cmds_dict = dict((n, _mod_commands.get_cmd_object(n)) 
                              for n in names)
        self.all_cmds = sorted(names)
        self.public_cmds = sorted([n 
                                   for n,o in self.cmds_dict.iteritems()
                                   if not o.hidden])

    def set_cmd_combobox(self, all=False):
        """Fill command combobox with bzr commands names.
        @param all: show all commands including hidden ones.
        """
        cb = self.ui.cmd_combobox
        cb.clear()
        if all:
            cb.addItems(self.all_cmds)
        else:
            cb.addItems(self.public_cmds)
        cb.setCurrentIndex(-1)    

    def set_cmd_help(self, cmd_name):
        """Show help for selected command in help widget.
        @param cmd_name: name of command to show help.
        """
        cmd_name = unicode(cmd_name)
        # XXX handle command aliases???
        cmd_object = self.cmds_dict.get(cmd_name)
        if cmd_object:
            self.ui.help_browser.setHtml(
                get_help_topic_as_html("commands/"+cmd_name))
        else:
            self.set_default_help()

    def _get_cwd(self, default=None):
        """Return selected working dir for command.
        @param default: if working dir is not exists then return this default 
            value.
        """
        cwd = unicode(self.ui.wd_edit.text())
        if not os.path.isdir(cwd):
            cwd = default
        return cwd

    def _prepare_filepath(self, path):
        """Ensure path is safe to insert to options/arguments command line.
        On Windows convert backslashes to slashes;
        if path contains spaces we need to quote it.
        @return: path string suitabe to insert to command line.
        """
        if MS_WINDOWS:
            path = path.replace('\\', '/')
        if " " in path:
            path = '"%s"' % path
        return path

    def insert_directory(self):
        """Select exisiting directory and insert it to command line."""
        cwd = self._get_cwd("")
        path = QtGui.QFileDialog.getExistingDirectory(self,
            gettext("Select path to insert"),
            cwd)
        if path:
            self.ui.opt_arg_edit.insert(
                self._prepare_filepath(unicode(path))+" ")

    def insert_filenames(self):
        """Select one or more existing files and insert them to command line."""
        cwd = self._get_cwd("")
        filenames = QtGui.QFileDialog.getOpenFileNames(self,
            gettext("Select files to insert"),
            cwd)
        for i in filenames:
            self.ui.opt_arg_edit.insert(
                self._prepare_filepath(unicode(i))+" ")

    def validate(self):
        """Validate before launch command: start command only if there is one."""
        if unicode(self.ui.cmd_combobox.currentText()).strip():
            return True
        return False

    def do_start(self):
        """Launch command."""
        cwd = self._get_cwd()
        args = [unicode(self.ui.cmd_combobox.currentText())]
        cmd_utf8 = unicode(self.ui.opt_arg_edit.text()).encode('utf-8')
        args.extend([unicode(p,'utf8') for p in shlex.split(cmd_utf8)])
        # show actual command line
        cmd_line = ["bzr"]
        for a in args:
            if " " in a:
                a = '"%s"' % a
            cmd_line.append(a)
        self.process_widget.logMessageEx("Run command: "+' '.join(cmd_line), 
            "cmdline")
        self.process_widget.do_start(cwd, *args)

    def saveSize(self):
        SubProcessDialog.saveSize(self)
        self.saveSplitterSizes()