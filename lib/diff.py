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

class DiffArgProvider (object):
    """Contract class to pass arguments to either builtin diff window, or
    external diffs"""
    
    def get_diff_window_args(self, processEvents):
        """Returns the arguments for the builtin diff window.
        
        :return: (tree1, tree2, branch1, branch2, specific_files)
        """
        raise NotImplementedError()
    
    def get_ext_diff_args(self, processEvents):
        """Returns the command line arguments for running an ext diff window.
        
        :return: List of command line arguments.
        """        
        raise NotImplementedError()

class InternalDiffArgProvider(DiffArgProvider):
    """Use for passing arguments from internal source."""
    
    def __init__(self, old_revid, new_revid, old_branch, new_branch,
                 specific_files=None, specific_file_ids=None):
        self.old_revid = old_revid
        self.new_revid = new_revid
        self.old_branch = old_branch
        self.new_branch = new_branch
        self.specific_files = specific_files
        self.specific_file_ids = specific_file_ids
        
        self.old_tree = None
        self.new_tree = None
    
    def need_to_load_paths (self):
        return self.specific_file_ids is not None \
           and self.specific_files is None
    
    def load_old_tree(self):
        if not self.old_tree:
            self.old_tree = \
                    self.old_branch.repository.revision_tree(self.old_revid)
    
    def load_new_tree_and_paths(self):
        if not self.new_tree:
            self.new_tree = \
                    self.new_branch.repository.revision_tree(self.new_revid)
        
        if self.need_to_load_paths():
            self.specific_files = [self.new_tree.id2path(id) \
                                   for id in self.specific_file_ids]

    def need_to_load_paths(self):
        return False
    
    def get_diff_window_args(self, processEvents):
        self.load_old_tree()
        processEvents()
        self.load_new_tree_and_paths()
        processEvents()
        
        return (self.old_tree, self.new_tree,
                self.old_branch, self.new_branch,
                self.specific_files)
        
    def get_revspec(self):
        return "-r revid:%s..revid:%s" % (self.old_revid, self.new_revid)
    
    def get_ext_diff_args(self, processEvents):
        args = []
        args.append(self.get_revspec())
        
        args.append("--new=%s" % self.new_branch.base)
        args.append("--old=%s" % self.old_branch.base)
        
        if self.need_to_load_paths():
            self.load_new_tree_and_paths()
            processEvents()
        if self.specific_files:
            args.extend(self.specific_files)
        
        return args

class InternalWTDiffArgProvider(InternalDiffArgProvider):
    """Use for passing arguments from internal source where the new tree is
    the working tree."""
    
    def __init__(self, old_revid, new_tree, old_branch, new_branch,
                 specific_files=None):
        self.old_revid = old_revid
        self.new_tree = new_tree
        self.old_branch = old_branch
        self.new_branch = new_branch
        self.specific_files = specific_files
        
        self.old_tree = None

    def get_diff_window_args(self, processEvents):
        self.load_old_tree()
        processEvents()
        
        return (self.old_tree, self.new_tree,
                self.old_branch, self.new_branch,
                self.specific_files)

    def get_revspec(self):
        return "-r revid:%s" % (self.old_revid,)

    
def show_diff(arg_provider, ext_diff=None, parent_window=None):
    
    if ext_diff is None:
        ext_diff = default_diff
    
    if ext_diff == "":
        
        # We can't import this globaly becuse it ties to import us,
        # which causes and Import Error.
        from bzrlib.plugins.qbzr.lib.diffwindow import DiffWindow
        
        window = DiffWindow(arg_provider, parent=parent_window)
        window.show()
        if parent_window:
            parent_window.windows.append(window)
    else:
        args=["diff",
              "--using=%s" % ext_diff]
        # This should be move to after the window has been shown.
        args.extend(arg_provider.get_ext_diff_args(QtCore.QCoreApplication.processEvents))
        
        window = SimpleSubProcessDialog("External Diff",
                                        desc=ext_diff,
                                        args=args,
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

