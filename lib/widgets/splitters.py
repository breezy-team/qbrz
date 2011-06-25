# -*- coding: utf-8 -*-
#
# QBzr - Qt frontend to Bazaar commands
# Copyright (C) 2011 QBzr Developers
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

from PyQt4 import QtGui, QtCore
from bzrlib.plugins.qbzr.lib.util import (
    get_qbzr_config,
    )

class Splitters(object):
    """Save and restore splitter state."""
    
    def __init__(self, prefix):
        self.prefix = prefix
        self.splitters = []

    def add(self, name, splitter):
        self.splitters.append((name, splitter))

    def restore_state(self):
        config = get_qbzr_config()
        for name, splitter in self.splitters:
            data = config.get_option('%s_%s' % (self.prefix, name))
            if data:
                splitter.restoreState(QtCore.QByteArray.fromBase64(data))

    def save_state(self):
        config = get_qbzr_config()
        for name, splitter in self.splitters:
            value = splitter.saveState().toBase64().data()
            config.set_option('%s_%s' % (self.prefix, name), value)
        config.save()
