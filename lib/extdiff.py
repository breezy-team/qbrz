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

from bzrlib.plugins.qbzr.lib.util import ( 
    QBzrGlobalConfig,
    runs_in_loading_queue,
    )
from bzrlib.plugins.qbzr.lib.subprocess import SimpleSubProcessDialog
from bzrlib.plugins.qbzr.lib.i18n import gettext
from PyQt4 import QtCore, QtGui


qconfig = QBzrGlobalConfig()
qparser = qconfig._get_parser()
default_diff = qconfig.get_user_option("default_diff")
if default_diff is None:
    default_diff = ""
ext_diffs = {gettext("Builtin Diff"):""}
for name, command in qparser.get('EXTDIFF', {}).items():
    ext_diffs[name] = command

@runs_in_loading_queue
def show_diff(old_revid, new_revid, old_branch, new_branch, new_wt = None,
             specific_files=None, ext_diff=None, parent_window=None):
    
    if ext_diff is None:
        ext_diff = default_diff
    
    if ext_diff == "":
        
        # We can't import this globaly becuse it ties to import us,
        # which causes and Import Error.
        from bzrlib.plugins.qbzr.lib.diff import DiffWindow
        old_tree = old_branch.repository.revision_tree(old_revid)
        if new_wt:
            new_tree = new_wt
        else:
            new_tree = new_branch.repository.revision_tree(new_revid)
        
        window = DiffWindow(old_tree, new_tree,
                            old_branch, new_branch,
                            specific_files = specific_files,
                            parent=parent_window)
        window.show()
        if parent_window:
            parent_window.windows.append(window)
    else:
        if new_wt:
            revspec = "-r revid:%s" % (old_revid,)
        else:
            revspec = "-r revid:%s..revid:%s" % (old_revid, new_revid)
        
        args=["diff",
              "--using=%s" % ext_diff,
              revspec]
        
        if not old_branch.base == new_branch.base:
            args.append("--old=%s" % old_branch.base)
        
        if specific_files:
            args.extend(specific_files)
        
        window = SimpleSubProcessDialog("External Diff",
                                        desc=ext_diff,
                                        args=args,
                                        dir=new_branch.base,
                                        auto_start_show_on_failed=True,
                                        parent=parent_window)
        window.process_widget.hide_progress()
        if parent_window:
            parent_window.windows.append(window)

def has_ext_diff():
    return len(ext_diffs) > 1

class ExtDiffMenu(QtGui.QMenu):
    
    def __init__ (self, parent = None, include_builtin = True):
        QtGui.QMenu.__init__(self, gettext("Show &differences"), parent)
        
        for name, command in ext_diffs.items():
            if command == "" and include_builtin or not command == "":
                action = QtGui.QAction(name, self)
                action.setData(QtCore.QVariant (command))
                if command == default_diff:
                    self.setDefaultAction(action)
                self.addAction(action)
        
        self.connect(self, QtCore.SIGNAL("triggered(QAction *)"),
                     self.triggered)
    
    def triggered(self, action):
        ext_diff = unicode(action.data().toString())
        self.emit(QtCore.SIGNAL("triggered(QString)"), QtCore.QString(ext_diff))
    
class DiffButtons(QtGui.QWidget):
    
    def __init__(self, parent = None):
        QtGui.QWidget.__init__(self, parent)
        layout = QtGui.QHBoxLayout(self)
        
        self.default_button = QtGui.QPushButton(gettext('Diff'),
                                                 self)
        layout.addWidget(self.default_button)
        layout.setSpacing(0)
        self.connect(self.default_button,
                     QtCore.SIGNAL("clicked()"),
                     self.triggered)
        
        if has_ext_diff():
            self.menu = ExtDiffMenu(self)
            self.menu_button = QtGui.QPushButton("",
                                                 self)
            layout.addWidget(self.menu_button)
            self.menu_button.setMenu(self.menu)
            self.connect(self.menu, QtCore.SIGNAL("triggered(QString)"),
                         self.triggered)

    def triggered(self, ext_diff=None):
        if ext_diff is None:
            ext_diff = QtCore.QString(default_diff)
        self.emit(QtCore.SIGNAL("triggered(QString)"), ext_diff)

