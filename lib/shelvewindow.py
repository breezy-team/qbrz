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

import sys, time
from PyQt4 import QtCore, QtGui
from PyQt4.QtGui import QKeySequence

from bzrlib.revision import CURRENT_REVISION
from bzrlib.errors import (
        NoSuchRevision, 
        NoSuchRevisionInTree,
        PathsNotVersionedError)
from bzrlib.plugins.qbzr.lib.i18n import gettext, N_
from bzrlib.plugins.qbzr.lib.util import (
    QBzrWindow,
    ToolBarThrobberWidget,
    get_apparent_author_name,
    get_set_encoding,
    runs_in_loading_queue,
    get_icon,
    get_monospace_font,
    StandardButton,
    get_tab_width_pixels,
    )

from bzrlib.plugins.qbzr.lib.uifactory import ui_current_widget
from bzrlib.plugins.qbzr.lib.trace import reports_exception
from bzrlib.plugins.qbzr.lib.logwidget import LogList
from bzrlib.lazy_import import lazy_import
lazy_import(globals(), '''
from bzrlib import transform
from bzrlib.workingtree import WorkingTree
from bzrlib.revisiontree import RevisionTree
from bzrlib.plugins.qbzr.lib.encoding_selector import EncodingMenuSelector
from bzrlib.plugins.qbzr.lib.widgets.shelve import ShelveWidget
from bzrlib.plugins.qbzr.lib.widgets.shelvelist import ShelveListWidget
from bzrlib.plugins.qbzr.lib.widgets.splitters import Splitters
from bzrlib.patiencediff import PatienceSequenceMatcher as SequenceMatcher
from bzrlib.shelf import Unshelver
from bzrlib.shelf_ui import Unshelver as Unshelver_ui
''')

class ShelveWindow(QBzrWindow):

    def __init__(self, initial_tab=0, directory=None, file_list=None, complete=False,
                 ignore_whitespace=False, encoding=None, parent=None, ui_mode=True,
                 select_all=False, message=None):
        QBzrWindow.__init__(self,
                            [gettext("Shelve Manager")],
                            parent, ui_mode=ui_mode)
        self.restoreSize("shelve", (780, 680))
        
        vbox = QtGui.QVBoxLayout(self.centralwidget)
        vbox.setMargin(2)
        self.throbber = ToolBarThrobberWidget(self)
        vbox.addWidget(self.throbber)
        self.tab = QtGui.QTabWidget(self)
        vbox.addWidget(self.tab)

        self.splitters = Splitters("shelve")

        self.directory = directory or '.'

        shelve_view = ShelveWidget(file_list=file_list, directory=self.directory,
                                    complete=complete, encoding=encoding, 
                                    splitters=self.splitters, parent=self,
                                    select_all=select_all, init_msg=message)
        shelvelist_view = ShelveListWidget(directory=self.directory,
                                    complete=complete, ignore_whitespace=ignore_whitespace,
                                    encoding=encoding, splitters=self.splitters, parent=self)

        self.tab.addTab(shelve_view, gettext('Shelve'))
        self.tab.addTab(shelvelist_view, gettext('View shelved changes'))
        self.tab.setCurrentIndex(initial_tab)
        self.connect(self.tab, QtCore.SIGNAL("currentChanged(int)"),
                self.current_tab_changed)
        self.connect(shelve_view, QtCore.SIGNAL("shelfCreated(int)"),
                self.shelf_created)
        self.connect(shelvelist_view, QtCore.SIGNAL("unshelved(int, QString*)"),
                self.unshelved)

        self.splitters.restore_state()

    def show(self):
        QBzrWindow.show(self)
        QtCore.QTimer.singleShot(0, self.initial_load)

    @runs_in_loading_queue
    @ui_current_widget
    @reports_exception()
    def initial_load(self):
        try:
            self.throbber.show()
            self.processEvents()
            view = self.tab.currentWidget()
            view.refresh()
            if hasattr(view, "files_str") and view.files_str:
                self.setWindowTitle(gettext("Shelve Manager") + " - %s" % view.files_str)
        finally:
            self.throbber.hide()

    def current_tab_changed(self, index):
        view = self.tab.currentWidget()
        if not view.loaded:
            view.refresh()
        if hasattr(view, "files_str") and view.files_str:
            self.setWindowTitle(gettext("Shelve Manager") + " - %s" % view.files_str)
        else:
            self.setWindowTitle(gettext("Shelve Manager"))

    def shelf_created(self, id):
        # Refresh shelf list after new shelf created.
        self.tab.widget(1).refresh()
        self.tab.setCurrentIndex(1)

    def unshelved(self, id, action):
        if action in ('apply', 'keep'):
            self.tab.widget(0).loaded = False

    def hideEvent(self, event):
        self.splitters.save_state()
        QBzrWindow.hideEvent(self, event)

