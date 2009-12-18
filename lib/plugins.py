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

from PyQt4 import QtGui

from bzrlib import (
    _format_version_tuple,
    osutils,
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
        view = self.build_view()
        btns = self.create_button_box(BTN_CLOSE)
        layout = QtGui.QVBoxLayout(self.centralWidget())
        layout.addWidget(view)
        layout.addWidget(btns)
        self.refresh_view()

    def build_view(self):
        """Build and return the widget displaying the data."""
        summary_headers = [
            gettext("Name"),
            gettext("Version"),
            gettext("Description"),
            ]
        locations_headers = [
            gettext("Name"),
            gettext("Directory"),
            ]
        footer = gettext("Plugins installed: %(rows)d")
        details = None
        self._summary_viewer = QBzrConditionalDataView("tree",
            summary_headers, footer, details)
        self._locations_viewer = QBzrConditionalDataView("tree",
            locations_headers, footer, details)
        tabs = QtGui.QTabWidget()
        tabs.addTab(self._summary_viewer, gettext("Summary"))
        tabs.addTab(self._locations_viewer, gettext("Locations"))
        return tabs

    def refresh_view(self):
        """Update the data in the view."""
        plugins = mod_plugin.plugins()
        summary_data = []
        locations_data = []
        for name in sorted(plugins):
            plugin = plugins[name]
            version = format_plugin_version(plugin)
            description = format_plugin_description(plugin)
            directory = osutils.dirname(plugin.path())
            summary_data.append((name, version, description))
            locations_data.append((name, directory))
        self._summary_viewer.setData(summary_data)
        self._locations_viewer.setData(locations_data)


def format_plugin_version(plugin):
    """Return the version of a plugin as a formatted string."""
    version_info = plugin.version_info()
    if version_info is None:
        result = ''
    else:
        try:
            result = _format_version_tuple(version_info)
        except (ValueError, IndexError):
            # Version info fails the expected rules.
            # Format it nicely anyhow.
            result = ".".join([str(part) for part in version_info])
    return result


def format_plugin_description(plugin):
    d = getdoc(plugin.module)
    if d:
        doc = d.split('\n')[0]
    else:
        doc = gettext('(no description)')
    return doc
