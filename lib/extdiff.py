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
    )
from bzrlib.plugins.qbzr.lib.diff import DiffWindow
from bzrlib.plugins.qbzr.lib.subprocess import SubProcessWindow
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

def showDiff(old_revid, new_revid, old_branch, new_branch, new_wt = None,
             specific_files=None, ext_diff=None, parent_window=None):
    
    if ext_diff is None:
        ext_diff = default_diff
    
    if ext_diff == "":
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
        
        args=["diff", "--using=%s" % ext_diff,
              revspec,
              "--old=%s" % old_branch.base, 
              "--new=%s" % new_branch.base]
        
        if specific_files:
            args.extend(specific_files)
        
        window = SubProcessWindow("External Diff",
                                  desc=ext_diff,
                                  args=args,
                                  auto_start_show_on_failed=True,
                                  parent=parent_window)
        window.process_widget.hide_progress()
        if parent_window:
            parent_window.windows.append(window)

def hasExtDiff():
    return len(ext_diffs) > 1

class ExtDiffMenu(QtGui.QMenu):
    
    def __init__ (self, parent = None):
        QtGui.QMenu.__init__(self, gettext("Show &differences"), parent)
        
        for name, command in ext_diffs.items():
            action = QtGui.QAction(name, self)
            action.setData(QtCore.QVariant (command))
            if command == default_diff:
                self.setDefaultAction(action)
            self.addAction(action)
    


