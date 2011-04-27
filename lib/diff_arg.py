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

from bzrlib.revision import NULL_REVISION, CURRENT_REVISION


# These classes were extracted from diff.py to avoid dependency on PyQt4
# in commands.py where base provider class is used, but PyQt4 is not required
# for overriden merge command.

class DiffArgProvider (object):
    """Contract class to pass arguments to either builtin diff window, or
    external diffs"""

    def get_diff_window_args(self, processEvents, add_cleanup):
        """Returns the arguments for the builtin diff window.

        :return: {"old_tree": old_tree,
                  "new_tree": new_tree,
                  "old_branch": old_branch,           (optional)
                  "new_branch": new_branch,           (optional)
                  "specific_files": specific_files,   (optional)
                  "ignore_whitespace": True or False} (optional)
        """
        raise NotImplementedError()

    def get_ext_diff_args(self, processEvents):
        """Returns the command line arguments for running an ext diff window.

        :return: (dir, List of command line arguments).
        """
        raise NotImplementedError()


class InternalDiffArgProvider(DiffArgProvider):
    """Use for passing arguments from internal source."""
    
    def __init__(self,
                 old_revid, new_revid,
                 old_branch, new_branch,
                 old_tree=None, new_tree=None,
                 specific_files=None, specific_file_ids=None):
        self.old_revid = old_revid
        self.new_revid = new_revid
        self.old_branch = old_branch
        self.new_branch = new_branch
        self.specific_files = specific_files
        self.specific_file_ids = specific_file_ids

        self.old_tree = old_tree
        self.new_tree = new_tree
    
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
            self.new_tree.lock_read()
            try:
                self.specific_files = [self.new_tree.id2path(id) \
                                       for id in self.specific_file_ids]
            finally:
                self.new_tree.unlock()

    def get_diff_window_args(self, processEvents, add_cleanup):
        self.load_old_tree()
        processEvents()
        self.load_new_tree_and_paths()
        processEvents()

        return {"old_tree": self.old_tree,
                "new_tree": self.new_tree,
                "old_branch": self.old_branch,
                "new_branch": self.new_branch,
                "specific_files": self.specific_files}

    def get_revspec(self):
        def get_revspec_part(revid):
            if revid.startswith(CURRENT_REVISION):
                return ''
            return 'revid:%s' % revid
        
        return "-r%s..%s" % (
            get_revspec_part(self.old_revid),
            get_revspec_part(self.new_revid))
    
    def get_ext_diff_args(self, processEvents):
        from bzrlib import urlutils
        from bzrlib import errors

        args = []
        revspec = self.get_revspec()
        if revspec:
            args.append(revspec)

        from bzrlib.workingtree import WorkingTree
        def get_base(branch, tree):
            if tree and isinstance(tree, WorkingTree):
                return urlutils.local_path_to_url(tree.basedir)
            return branch.base

        old_base = get_base(self.old_branch, self.old_tree)
        new_base = get_base(self.new_branch, self.new_tree)

        # We need to avoid using --new and --old because diff tools
        # does not support it. There are however some cases where
        # this is not possilble.
        need_old = False
        if not self.old_branch.base == self.new_branch.base:
            need_old = True

        try:
            dir = urlutils.local_path_from_url(new_base)
        except errors.InvalidURL:
            dir = ""
            args.append("--new=%s" % new_base)
            need_old = True

        if need_old:
            args.append("--old=%s" % old_base)

        if self.need_to_load_paths():
            self.load_new_tree_and_paths()
            processEvents()
        if self.specific_files:
            args.extend(self.specific_files)

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

    def get_diff_window_args(self, processEvents, add_cleanup):
        self.load_old_tree()
        processEvents()

        return {"old_tree": self.old_tree,
                "new_tree": self.new_tree,
                "old_branch": self.old_branch,
                "new_branch": self.new_branch,
                "specific_files": self.specific_files}

    def get_revspec(self):
        if self.old_revid is not None:
            return "-rrevid:%s" % (self.old_revid,)
        else:
            return None

    def need_to_load_paths(self):
        return False
