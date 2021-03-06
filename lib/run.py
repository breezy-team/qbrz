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
from PyQt5 import QtCore, QtGui, QtWidgets

from breezy import osutils

from breezy.plugins.qbrz.lib import MS_WINDOWS
from breezy.plugins.qbrz.lib.help import get_help_topic_as_html
from breezy.plugins.qbrz.lib.i18n import gettext
from breezy.plugins.qbrz.lib.subprocess import SubProcessDialog
from breezy.plugins.qbrz.lib.ui_run import Ui_RunDialog
from breezy.plugins.qbrz.lib.util import hookup_directory_picker, shlex_split_unicode


class QBzrRunDialog(SubProcessDialog):

    def __init__(self, command=None, parameters=None, workdir=None, category=None, ui_mode=False, parent=None, execute=False):
        """Build dialog.

        @param command: initial command selection.
        @param parameters: initial options and arguments (string) for command.
        @param workdir: working directory to run command.
        @param category: initial category selection.
        @param ui_mode: wait after the operation is complete.
        @param parent:  parent window.
        @param execute: True => run command immediately
        """
        super(QBzrRunDialog, self).__init__(name="run", ui_mode=ui_mode, dialog=True, parent=parent)
        self.ui = Ui_RunDialog()
        self.ui.setupUi(self)
        if workdir is None:
            workdir = osutils.getcwd()
        self.ui.wd_edit.setText(workdir)
        # set help_browser with some default text
        self.set_default_help()
        # cmd_combobox should fill all available space
        self.ui.cmd_layout.setColumnStretch(1, 1)
        self.ui.cmd_layout.setColumnStretch(2, 1)
        # fill cmd_combobox with available commands
        self.collect_command_names()
        # RJL in python 2 we could do this quite happily, even if a key were None
        #
        #   categories = sorted(self.all_cmds.keys())
        #
        # Python3 spits a TypeError at you, though, so convert None to ''
        categories = sorted(self.all_cmds, key=lambda k: '' if k is None else k)
        self.ui.cat_combobox.insertItems(0, categories)
        self.set_cmd_combobox(cmd_name=command)
        # add the parameters, if any
        if parameters:
            self.ui.opt_arg_edit.setText(parameters)

        # and add the subprocess widgets
        for w in self.make_default_layout_widgets():
            self.ui.subprocess_container_layout.addWidget(w)
        self.process_widget.hide_progress()

        # restore the sizes
        self.restoreSize("run", None)
        self.splitter = self.ui.splitter
        self.restoreSplitterSizes()
        # setup signals
        self.ui.hidden_checkbox.stateChanged[int].connect(self.set_show_hidden)
        self.ui.cmd_combobox.currentIndexChanged['QString'].connect(self.set_cmd_help)
        self.ui.cmd_combobox.editTextChanged['QString'].connect(self.set_cmd_help)
        self.ui.cat_combobox.currentIndexChanged['QString'].connect(self.set_category)
        hookup_directory_picker(self, self.ui.browse_button, self.ui.wd_edit, gettext("Select working directory"))
        self.ui.directory_button.clicked.connect(self.insert_directory)
        self.ui.filenames_button.clicked.connect(self.insert_filenames)
        # Init the category if set.
        # (This needs to be done after the signals are hooked up)
        if category:
            cb = self.ui.cat_combobox
            index = cb.findText(category)
            if index >= 0:
                cb.setCurrentIndex(index)
        # ready to go
        if execute:
            # hide user edit fields
            self.ui.run_container.hide()
            self.ui.help_browser.hide()

            # create edit button
            self.editButton = QtWidgets.QPushButton(gettext('&Edit'))
            self.editButton.clicked.connect(self.enable_command_edit)

            # cause edit button to be shown if command fails
            self.subprocessFailed[bool].connect(self.editButton.setHidden)

            # add edit button to dialog buttons
            self.buttonbox.addButton(self.editButton, QtWidgets.QDialogButtonBox.ResetRole)

            # setup initial dialog button status
            self.closeButton.setHidden(True)
            self.okButton.setHidden(True)
            self.editButton.setHidden(True)

            # cancel button gets hidden when finished.
            self.subprocessFinished[bool].connect(self.cancelButton.setHidden)

            # run command
            self.do_start()
        else:
            if command:
                self.ui.opt_arg_edit.setFocus()
            else:
                self.ui.cmd_combobox.setFocus()

    def enable_command_edit(self):
        """Hide Edit button and make user edit fields visible"""
        self.editButton.setHidden(True)
        self.subprocessFailed[bool].disconnect(self.editButton.setHidden)
        self.ui.run_container.show()
        self.ui.help_browser.show()
        self.okButton.setVisible(True)

    def set_default_help(self):
        """Set default text in help widget."""
        self.ui.help_browser.setHtml("<i><small>%s</small></i>" % gettext("Help for command"))

    def collect_command_names(self):
        """Collect names of available bzr commands."""
        from breezy import commands as _mod_commands
        names = list(_mod_commands.all_command_names())
        self.cmds_dict = dict((n, _mod_commands.get_cmd_object(n)) for n in names)
        # Find the commands for each category, public or otherwise
        builtins = _mod_commands.builtin_command_names()
        self.all_cmds = {'All': []}
        self.public_cmds = {'All': []}
        for name, cmd in self.cmds_dict.items():
            # If a command is builtin, we always put it into the Core
            # category, even if overridden in a plugin
            if name in builtins:
                category = 'Core'
            else:
                category = cmd.plugin_name()
            # RJLRJL Removed
            # if category is None:
            #     continue
            self.all_cmds['All'].append(name)
            self.all_cmds.setdefault(category, []).append(name)
            if not cmd.hidden:
                self.public_cmds['All'].append(name)
                self.public_cmds.setdefault(category, []).append(name)
        # Sort them
        for category in self.all_cmds:
            self.all_cmds[category].sort()
            try:
                self.public_cmds[category].sort()
            except KeyError:
                # no public commands - that's ok
                pass

    def set_category(self, category):
        cmd_name = self._get_cmd_name()
        all = self.ui.hidden_checkbox.isChecked()
        category = str(category)
        self.set_cmd_combobox(cmd_name=cmd_name, all=all, category=category)

    def set_show_hidden(self, show):
        cmd_name = self._get_cmd_name()
        all = bool(show)
        category = str(self.ui.cat_combobox.currentText())
        self.set_cmd_combobox(cmd_name=cmd_name, all=all, category=category)

    def set_cmd_combobox(self, cmd_name=None, all=False, category=None):
        """Fill command combobox with bzr commands names.

        @param cmd_name: if not None, the command to initially select
            if it exists in the list.
        @param all: show all commands including hidden ones.
        @param category: show commands just for this category.
            If None, commands in all categories are shown.
        """
        cb = self.ui.cmd_combobox
        cb.clear()
        if all:
            lookup = self.all_cmds
        else:
            lookup = self.public_cmds
        if category is None:
            category = 'All'
        cb.addItems(lookup.get(category, []))
        if cmd_name is None:
            index = -1
        else:
            index = cb.findText(cmd_name)
            if index >= 0:
                self.set_cmd_help(cmd_name)
        cb.setCurrentIndex(index)

    def _get_cmd_name(self):
        """Return the command name."""
        return str(self.ui.cmd_combobox.currentText()).strip()

    def set_cmd_help(self, cmd_name):
        """Show help for selected command in help widget.

        @param cmd_name: name of command to show help.
        """
        cmd_name = str(cmd_name)
        # XXX handle command aliases???
        cmd_object = self.cmds_dict.get(cmd_name)
        if cmd_object:
            # [Bug #963542] get_help_topic_as_html returns valid utf-8 encoded
            # HTML document, but QTextBrowser expects unicode.
            # (actually QString which is unicode in PyQt4).
            html_utf8 = get_help_topic_as_html("commands/" + cmd_name)
            if isinstance(html_utf8, str):
                html_unicode = html_utf8
            else:
                html_unicode = html_utf8.decode('utf-8')
            self.ui.help_browser.setHtml(html_unicode)
        else:
            self.set_default_help()

    def _get_cwd(self, default=None):
        """Return selected working dir for command.

        @param default: if working dir is not exists then return this default
            value.
        """
        cwd = str(self.ui.wd_edit.text())
        if not os.path.isdir(cwd):
            cwd = default
        return cwd

    def _prepare_filepath(self, path):
        """Ensure path is safe to insert to options/arguments command line.

        On Windows convert backslashes to slashes;
        if path contains spaces we need to quote it.
        @return: path string suitable to insert to command line.
        """
        if MS_WINDOWS:
            path = path.replace('\\', '/')
        if " " in path:
            path = '"%s"' % path
        return path

    def insert_directory(self):
        """Select existing directory and insert it to command line."""
        cwd = self._get_cwd("")
        path = QtWidgets.QFileDialog.getExistingDirectory(self,
            gettext("Select path to insert"),
            cwd)
        if path:
            self.ui.opt_arg_edit.insert(self._prepare_filepath(str(path)) + " ")

    def insert_filenames(self):
        """Select one or more existing files and insert them to command line."""
        cwd = self._get_cwd("")
        filenames = QtWidgets.QFileDialog.getOpenFileNames(self, gettext("Select files to insert"), cwd)[0]
        for i in filenames:
            self.ui.opt_arg_edit.insert(
                self._prepare_filepath(str(i)) + " ")

    def validate(self):
        """Validate before launch command: start command only if there is one."""
        if self._get_cmd_name():
            return True
        return False

    def do_start(self):
        """Launch command."""
        cwd = self._get_cwd()
        args = [self._get_cmd_name()]
        opt_arg = self.ui.opt_arg_edit.text()
        args.extend(shlex_split_unicode(opt_arg))
        self.process_widget.do_start(cwd, *args)

    def _saveSize(self, config):
        SubProcessDialog._saveSize(self, config)
        self._saveSplitterSizes(config, self.splitter)
