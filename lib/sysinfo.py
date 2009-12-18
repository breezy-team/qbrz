# -*- coding: utf-8 -*-
#
# QBzr - Qt frontend to Bazaar commands
# Copyright (C) 2009 Canonical Ltd
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

from bzrlib.plugins.qbzr.lib.i18n import gettext
from bzrlib.plugins.qbzr.lib.sysinfo_data import get_sys_info
from bzrlib.plugins.qbzr.lib.ui_sysinfo import Ui_MainWindow
from bzrlib.plugins.qbzr.lib.util import (
    BTN_CLOSE,
    QBzrWindow,
    )


class QBzrSysInfoWindow(QBzrWindow):

    def __init__(self, parent=None):
        QBzrWindow.__init__(self, [], parent)
        self.ui = Ui_MainWindow()
        self.ui.setupUi(self)
        self.set_title(gettext("System Information"))
        self.restoreSize("sysinfo", (400,256))
        btns = self.create_button_box(BTN_CLOSE)
        self.ui.vboxlayout.addWidget(btns)
        self.display_sys_info(get_sys_info())

    def display_sys_info(self, props):
        """Update the view.

        :param props: a dictionary mapping field names to values.
        """
        # Bazaar Library section
        self.ui.bzr_version.setText(props.get("bzr-version", "?"))
        bzrlib_path = props.get("bzr-lib-path")
        try:
            bzrlib_head = bzrlib_path[0]
        except IndexError:
            bzrlib_head = ""
        self.ui.bzr_lib_path.setText(bzrlib_head)

        # Bazaar Configuration section
        self.ui.bzr_config_dir.setText(props.get("bzr-config-dir", "?"))
        self.ui.bzr_log_file.setText(props.get("bzr-log-file", "?"))

        # Python Interpreter section
        self.ui.python_version.setText(props.get("python-version", "?"))
        self.ui.python_file.setText(props.get("python-file", "?"))
        self.ui.python_lib_dir.setText(props.get("python-lib-dir", "?"))
