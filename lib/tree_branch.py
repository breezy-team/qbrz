# -*- coding: utf-8 -*-
#
# QBzr - Qt frontend to Bazaar commands
#
# Contributor:
#   Alexander Belchenko, 2009
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

"""Universal tree and/or branch wrapper object for convenience."""

from PyQt4 import QtGui

from bzrlib import (
    bzrdir,
    errors,
    osutils,
    urlutils,
    )

from bzrlib.plugins.qbzr.lib.i18n import gettext


class TreeBranch(object):
    """Universal tree and/or branch wrapper object."""

    __slots__ = ['location', 'tree', 'branch', 'relpath']

    def __init__(self, location, tree, branch, relpath):
        """Use open_containg method to create the object."""
        self.location = location
        self.tree = tree
        self.branch = branch
        self.relpath = relpath

    @staticmethod
    def open_containing(location=None, require_tree=False, ui_mode=False,
        _critical_dialog=QtGui.QMessageBox.critical):
        """Open the branch and tree at location (or in current directory).

        @return: initialized TreeBranch if opened successfully,
            None if branch or tree not found.

        @param location: URL or local path, if None then current working
            directory will be used.
        @param require_tree: if True then NoWorkingTree error will be
            raised if there is no working tree found. Otherwise it's
            acceptable to open only branch object.
        @param ui_mode: if True show errors in the GUI error dialogs;
            otherwise propagate the error up the stack.
        @param _critical_dialog: hook for testing.
        """
        if location is None:
            location = osutils.getcwd()
        try:
            (tree,
             branch,
             relpath
            ) = bzrdir.BzrDir.open_containing_tree_or_branch(location)

            if require_tree and tree is None:
                raise errors.NoWorkingTree(location)
        except (errors.NotBranchError, errors.NoWorkingTree), e:
            if not ui_mode:
                raise
            TreeBranch._report_error(location, e, _critical_dialog)
            return None
        return TreeBranch(location, tree, branch, relpath)

    @staticmethod
    def _report_error(location, err,
        _critical_dialog=QtGui.QMessageBox.critical):
        """Report error in GUI dialog.
        @param location: valid location for which error is reported.
        @param err: error object (NotBranchError or NoWorkingTree).
        @param _critical_dialog: callable to show error dialog.
        """
        if isinstance(err, errors.NotBranchError):
            text = gettext('Not a branch "%s"') % location
        elif isinstance(err, errors.NoWorkingTree):
            text = gettext('No working tree exists for "%s"') % location
        _critical_dialog(None,
            gettext("Error"),
            text,
            gettext('&Close'))

    def is_light_co(self):
        """Return True if location is lightweight checkout."""
        if (self.tree and self.tree.bzrdir.root_transport.base !=
            self.branch.bzrdir.root_transport.base):
            return True
        return False

    def is_bound(self):
        """Return True if location is bound branch."""
        if self.branch.get_bound_location():
            return True
        return False

    def get_type(self):
        """Return type of the object as string.
        @return: type of object ('tree', 'branch', 'light-checkout', 'bound'
            or None)
        """
        if self.branch is None:
            return None
        if self.is_light_co():
            return 'light-checkout'
        elif self.is_bound():
            return 'bound'
        else:
            if self.tree:
                return 'tree'
            else:
                return 'branch'

    def get_root(self):
        """Return root working directory (or URL for treeless remote branch)."""
        if self.tree:
            return self.tree.basedir
        else:
            url = self.branch.base
            if url.startswith('file://'):
                return urlutils.local_path_from_url(url)
            return url
