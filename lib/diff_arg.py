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

"""Diff Arg Provider classes."""

# These classes were extracted from diff.py to avoid dependency on PyQt4
# in commands.py where base provider class is used, but PyQt4 is not required
# for overriden merge command.


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
        
        :return: (dir, List of command line arguments).
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
    
    def need_to_load_paths(self):
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
        from bzrlib import urlutils

        args = []
        revspec = self.get_revspec()
        if revspec:
            args.append(revspec)
        
        if not self.old_branch.base == self.new_branch.base: 
            args.append("--old=%s" % self.old_branch.base)
        
        if self.need_to_load_paths():
            self.load_new_tree_and_paths()
            processEvents()
        if self.specific_files:
            args.extend(self.specific_files)
        dir = urlutils.local_path_from_url(self.new_branch.base)
        
        return dir, args


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

    def load_old_tree(self):
        if self.old_revid is None and self.old_tree is None:
            self.old_tree = self.new_tree.basis_tree()
            self.old_revid = self.old_tree.get_revision_id()
        else:
            InternalDiffArgProvider.load_old_tree(self)

    def get_diff_window_args(self, processEvents):
        self.load_old_tree()
        processEvents()
        
        return (self.old_tree, self.new_tree,
                self.old_branch, self.new_branch,
                self.specific_files)

    def get_revspec(self):
        if self.old_revid is not None:
            return "-r revid:%s" % (self.old_revid,)
        else:
            return None
    
    def need_to_load_paths(self):
        return False
