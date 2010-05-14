# -*- coding: utf-8 -*-
#
# QBzr - Qt frontend to Bazaar commands
# Copyright (C) 2009 Alexander Belchenko
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

"""Simple GUI for `bzr update` command for updating out-of-date working tree
of a branch.
"""

from bzrlib.plugins.qbzr.lib.i18n import gettext
from bzrlib.plugins.qbzr.lib.subprocess import SimpleSubProcessDialog


class QBzrUpdateWindow(SimpleSubProcessDialog):

    def __init__(self, tree, ui_mode=True, immediate=False, parent=None):
        self.tree = tree
        super(QBzrUpdateWindow, self).__init__(
            title=gettext("Update working tree"),
            desc=gettext("Update tree %s") % tree.basedir,
            name="update",
            args=["update"],
            dir=self.tree.basedir,
            default_size=(256, 256),
            ui_mode=ui_mode,
            parent=parent,
            immediate=immediate,
            )
