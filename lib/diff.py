# -*- coding: utf-8 -*-
#
# QBzr - Qt frontend to Bazaar commands
# Copyright (C) 2006 Lukáš Lalinský <lalinsky@gmail.com>
# Portions Copyright (C) 2006 Jelmer Vernooij <jelmer@samba.org>
# Portions Copyright (C) 2005 Canonical Ltd. (author: Scott James Remnant <scott@ubuntu.com>)
# Portions Copyright (C) 2004-2006 Christopher Lenz <cmlenz@gmx.de>
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

import locale
import sys
import time
from cStringIO import StringIO

from PyQt4 import QtCore, QtGui

from bzrlib.errors import BinaryFile, NoSuchId
from bzrlib.textfile import check_text_lines
from bzrlib.config import GlobalConfig
from bzrlib.diff import show_diff_trees
from bzrlib.workingtree import WorkingTree
from bzrlib.patiencediff import PatienceSequenceMatcher as SequenceMatcher

from bzrlib.plugins.qbzr.lib.diffview import (
    SidebySideDiffView,
    SimpleDiffView,
    )
from bzrlib.plugins.qbzr.lib.i18n import gettext, ngettext, N_
from bzrlib.plugins.qbzr.lib.util import (
    BTN_CLOSE,
    FilterOptions,
    QBzrWindow,
    get_branch_config,
    get_set_encoding,
    )


def get_file_lines_from_tree(tree, file_id):
    try:
        return tree.get_file_lines(file_id)
    except AttributeError:
        return tree.get_file(file_id).readlines()

class DiffWindow(QBzrWindow):

    def __init__(self, tree1=None, tree2=None, specific_files=None,
                 parent=None, custom_title=None,
                 complete=False, branch=None, encoding=None,
                 filter_options=None):
        title = [gettext("Diff")]
        if custom_title:
            title.append(custom_title)
        if specific_files:
            nfiles = len(specific_files)
            if nfiles > 2:
                title.append(
                    ngettext("%d file", "%d files", nfiles) % nfiles)
            else:
                title.append(", ".join(specific_files))
        else:
            if filter_options and not filter_options.is_all_enable():
                title.append(filter_options.to_str())

        config = get_branch_config(branch)
        self.encoding = get_set_encoding(encoding, config)
        
        self.filter_options = filter_options

        QBzrWindow.__init__(self, title, parent)
        self.restoreSize("diff", (780, 580))

        self.trees = (tree1, tree2)
        self.specific_files = specific_files
        self.complete = complete

        self.diffview = SidebySideDiffView(self)
        self.sdiffview = SimpleDiffView(self)
        self.views = (self.diffview, self.sdiffview)

        self.stack = QtGui.QStackedWidget(self.centralwidget)
        self.stack.addWidget(self.diffview)
        self.stack.addWidget(self.sdiffview)

        vbox = QtGui.QVBoxLayout(self.centralwidget)
        vbox.addWidget(self.stack)

        diffsidebyside = QtGui.QRadioButton(gettext("Side by side"),
                                            self.centralwidget)
        self.connect(diffsidebyside,
                     QtCore.SIGNAL("clicked(bool)"),
                     self.click_diffsidebyside)
        diffsidebyside.setChecked(True);

        unidiff = QtGui.QRadioButton(gettext("Unidiff"), self.centralwidget)
        self.connect(unidiff,
                     QtCore.SIGNAL("clicked(bool)"),
                     self.click_unidiff)

        buttonbox = self.create_button_box(BTN_CLOSE)

        hbox = QtGui.QHBoxLayout()
        hbox.addWidget(diffsidebyside)
        hbox.addWidget(unidiff)
        hbox.addWidget(buttonbox)
        vbox.addLayout(hbox)

    def show(self):
        QBzrWindow.show(self)
        QtCore.QTimer.singleShot(1, self.load_diff)
    
    def load_diff(self):
        for tree in self.trees: tree.lock_read()
        try:
            changes = self.trees[1].iter_changes(self.trees[0],
                                                 specific_files=self.specific_files,
                                                 require_versioned=True)
            def changes_key(change):
                old_path, new_path = change[1]
                path = new_path
                if path is None:
                    path = old_path
                return path
            
            for (file_id, paths, changed_content, versioned, parent, name, kind,
                 executable) in sorted(changes, key=changes_key):
                if parent == (None, None):
                    continue
                
                present = [k is not None and v for k,v in kind, versioned]
                dates = [tree.get_file_mtime(file_id, path) if p else None
                         for tree, path, p in zip(self.trees, paths, present)]            
                paths_encoded = [(path.encode(self.encoding, "replace") \
                                 if path is not None else None )
                                 for path in paths]
                renamed = (parent[0], name[0]) != (parent[1], name[1])
                properties_changed = [] 
                if not executable[0]==executable[1]:
                    descr = { True:"+x", False:"-x", None:"??" }
                    properties_changed.append((descr[executable[0]],
                                               descr[executable[1]]))
                
                if present == [True, False]:
                    status = N_('removed')
                elif  present == [False, True]:
                    status = N_('added')
                elif renamed and changed_content:
                    status = N_('renamed and modified')
                elif renamed:
                    status = N_('renamed')
                else:
                    status = N_('modified')
                
                if present == (True, False) or present == (False, True) or changed_content:
                    lines = [get_file_lines_from_tree(tree, file_id) if p else []
                             for tree, p in zip(self.trees, present)]
                    try:
                        for l in lines:
                            check_text_lines(l)
                        binary = False
                        if present == (True, False):
                            groups = [[('delete', 0, len(lines[0]), 0, 0)]]
                        elif present == (False, True):
                            groups = [[('insert', 0, 0, 0, len(lines[1]))]]
                        else:
                            matcher = SequenceMatcher(None, lines[0], lines[1])
                            if self.complete:
                                groups = list([matcher.get_opcodes()])
                            else:
                                groups = list(matcher.get_grouped_opcodes())
                        lines = [[i.decode(self.encoding,'replace') for i in l]
                                 for l in lines]
                        data = ((),())
                    except BinaryFile:
                        binary = True
                        data = [''.join(l) for l in lines]
                        groups = []
                else:
                    binary = False
                    lines = ((),())
                    groups = ()
                    data = lines
                for view in self.views:
                    view.append_diff(paths_encoded, file_id,kind, status, dates,
                                     present, binary, lines, groups, data, properties_changed)
                QtCore.QCoreApplication.processEvents()
                
        finally:
            for tree in self.trees: tree.unlock()

    def click_unidiff(self, checked):
        if checked:
            self.sdiffview.rewind()
            self.stack.setCurrentIndex(1)

    def click_diffsidebyside(self, checked):
        if checked:
            self.diffview.rewind()
            self.stack.setCurrentIndex(0)