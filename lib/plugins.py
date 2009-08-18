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

from inspect import getdoc

from PyQt4 import QtCore, QtGui

from bzrlib import (
    _format_version_tuple,
    plugin as mod_plugin,
    )

from bzrlib.plugins.qbzr.lib.conditional_dataview import (
    QBzrConditionalDataView,
    )
from bzrlib.plugins.qbzr.lib.i18n import gettext
from bzrlib.plugins.qbzr.lib.util import (
    BTN_CLOSE,
    QBzrWindow,
    )


class QBzrPluginsWindow(QBzrWindow):

    def __init__(self, parent=None):
        QBzrWindow.__init__(self, [], parent)
        self.set_title(gettext("Plugins"))
        self.restoreSize("plugins", (400,256))
        self._view = self.build_view()
        btns = self.create_button_box(BTN_CLOSE)
        layout = QtGui.QVBoxLayout(self.centralWidget())
        layout.addWidget(self._view)
        layout.addWidget(btns)
        self.refresh_view()

    def build_view(self):
        """Build and return the widget displaying the data."""
        headers = [
            gettext("Name"),
            gettext("Version"),
            gettext("Description"),
            ]
        footer = gettext("Plugins installed: %(rows)d")
        # TODO: add a details pane showing the installed path
        # Should this only be on in verbose mode ala the CLI? Or always?
        details = None
        data_viewer = QBzrConditionalDataView("tree", headers, footer, details)
        return data_viewer

    def refresh_view(self):
        """Update the data in the view."""
        plugins = mod_plugin.plugins()
        data = []
        for name in sorted(plugins):
            plugin = plugins[name]
            version = format_plugin_version(plugin)
            description = format_plugin_description(plugin)
            data.append((name, version, description))
        self._view.setData(data)


def format_plugin_version(plugin):
    """Return the version of a plugin as a formatted string."""
    version_info = plugin.version_info()
    if version_info is None:
        result = ''
    else:
        try:
            result = _format_version_tuple(version_info)
        except ValueError:
            # Version info fails the expected rules
            result = "%s" % (version_info,)
    return result


def format_plugin_description(plugin):
    d = getdoc(plugin.module)
    if d:
        doc = d.split('\n')[0]
    else:
        doc = gettext('(no description)')
    return doc
