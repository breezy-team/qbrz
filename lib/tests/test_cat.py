# -*- coding: utf-8 -*-
#
# Copyright (C) 2009 Gary van der Merwe <garyvdm@gmail.com>
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

from bzrlib.tests import TestCase, TestCaseWithTransport
from PyQt4 import QtCore, QtGui
from bzrlib.plugins.qbzr.lib import tests as qtests
from bzrlib.plugins.qbzr.lib.cat import QBzrCatWindow


class TestCat(qtests.QTestCase):

    def test_show_cat_change_encoding(self):
        tree = self.make_branch_and_tree('branch')
        self.build_tree_contents([('branch/a', 'foo\n')])
        tree.add('a')
        tree.commit(message='1')
        win = QBzrCatWindow('a', tree=tree, encoding='utf-8')
        self.addCleanup(win.close)
        win.show()
        QtCore.QCoreApplication.processEvents()

        # Change the encoding.
        encode_combo = win.encoding_selector.chooser
        encode_combo.setCurrentIndex(encode_combo.findText("ascii"))
        QtCore.QCoreApplication.processEvents()
