# -*- coding: utf-8 -*-
#
# QBzr - Qt frontend to Bazaar commands
# Copyright (C) 2008 Lukáš Lalinský <lalinsky@gmail.com>
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

from bzrlib import bzrdir, osutils

from bzrlib.info import show_bzrdir_info

from bzrlib.plugins.qbzr.lib.i18n import gettext
from bzrlib.plugins.qbzr.lib.ui_info import Ui_InfoForm
from bzrlib.plugins.qbzr.lib.util import (
    BTN_CLOSE,
    QBzrWindow,
    url_for_display,
    )

import StringIO


class QBzrInfoWindow(QBzrWindow):

    def __init__(self, location, parent=None):
        QBzrWindow.__init__(self, [gettext("Info")], parent)
        self.restoreSize("info", (580, 250))
        self.buttonbox = self.create_button_box(BTN_CLOSE)
        self.ui = Ui_InfoForm()
        self.ui.setupUi(self.centralwidget)
        self.ui.verticalLayout.addWidget(self.buttonbox)
        self.refresh_view(location)
        self.ui.tabWidget.setCurrentIndex(0)

    def refresh_view(self, location):
        self._set_location(location)
        self.populate_unparsed_info(location)

    def _set_location(self, location):
        if not location:
            self.ui.local_location.setText('-')
            return
        if location != '.':
            self.ui.local_location.setText(url_for_display(location))
            return
        self.ui.local_location.setText(osutils.abspath(location))

    def populate_unparsed_info(self, location):
        basic = StringIO.StringIO()
        detailed = StringIO.StringIO()
        a_bzrdir = bzrdir.BzrDir.open_containing(location)[0]
        show_bzrdir_info(a_bzrdir, 0, basic)
        show_bzrdir_info(a_bzrdir, 2, detailed)
        self.ui.basic_info.setText(basic.getvalue())
        self.ui.detailed_info.setText(detailed.getvalue())
        basic.close()
        detailed.close()
