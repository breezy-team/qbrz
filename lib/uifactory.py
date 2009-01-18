# -*- coding: utf-8 -*-
#
# QBzr - Qt frontend to Bazaar commands
# Copyright (C) 2008 Gary van der Merwe <garyvdm@gmail.com>
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

from bzrlib.ui import text
from bzrlib.plugins.qbzr.lib.i18n import gettext, N_
from bzrlib.plugins.qbzr.lib.util import StopException

class QUIFactory(text.TextUIFactory):

    def __init__(self):
        super(QUIFactory, self).__init__()
        
    #    self._progress_view._repaint = self.progress_view_repaint
    #
    #def progress_view_repaint(self):
    #    pv = self._progress_view
    #    if pv._last_task:
    #        task_msg = pv._format_task(pv._last_task)
    #        progress_frac = pv._last_task._overall_completion_fraction()
    #        if progress_frac is not None:
    #            progress = int(progress_frac * 1000000)
    #        else:
    #            progress = 1
    #    else:
    #        task_msg = ''
    #        progress = 0
    #    
    #    trans = pv._last_transport_msg
    #    
    #    sys.stdout.write('qbzr:PROGRESS:' + bencode.bencode((progress,
    #                     trans, task_msg)) + '\n')
    #    sys.stdout.flush()

    def get_password(self, prompt='', **kwargs):
        password, ok = QtGui.QInputDialog.getText(None,
                                                  gettext("Enter Password"),
                                                  (prompt % kwargs),
                                                  QtGui.QLineEdit.Password)
        
        if ok:
            return str(password)
        else:
            raise KeyboardInterrupt()
