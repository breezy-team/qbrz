# -*- coding: utf-8 -*-
#
# QBzr - Qt frontend to Bazaar commands
# Copyright (C) 2009 Alexander Belchenko
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

"""Commit data save/restore support."""


class CommitData(object):
    """Class to manipulate with commit data.

    Hold the data as dictionary and provide dict-like interface.
    All strings saved internally as unicode.

    Known items for data dict:
        message: main commit message.
        bugs: list of 'id:number' strings for fixed bugs
        authors: list of strings with name(s) of patch author(s)
        file_message: dict for per-file commit messages (MySQL),
            keys in this dict are filenames/fileids,
            values are specific commit messages.
        old_revid: old tip revid (before uncommit)
        new_revid: new tip revid (after uncommit)

    [bialix 20090812] Data saved in branch.conf in [commit_data] section
    as plain dict.
    """

    def __init__(self, branch=None, tree=None):
        """Initialize data object attached to some tree.
        @param tree: working tree object for commit/uncommit.
        @param branch:  branch object for commit/uncommit.
        """
        self._tree = tree
        self._branch = branch
        self._data = {}

    def __nonzero__(self):
        """Check if there is some data actually.
        @return: True if data dictionary is not empty.
        """
        return bool(self._data)

    def __getitem__(self, key):
        """Read the value of specified key via dict-like interface, e.g. a[key].
        @param key: key in data dictionary.
        @return: value or None if there is no such key.
        """
        return self._data.get(key)

    def __setitem__(self, key, value):
        """Set new value for specified key."""
        self._data[key] = value

    def __delitem__(self, key):
        """Delete key from dictionary."""
        del self._data[key]

    def as_dict(self):
        return self._data.copy()

    def set_data(self, data=None, **kw):
        """Set new data to dictionary (e.g. to save data from commit dialog).
        @param data: dictionary with new data.
        @param kw: pairs name=value to insert.
        """
        if data:
            self._data.update(data)
        for key, value in kw.iteritems():
            self._data[key] = value

    def set_data_on_uncommit(self, old_revid, new_revid):
        """Set data from post_uncommit hook.
        @param old_revid: old tip revid (before uncommit)
        @param new_revid: new tip revid (after uncommit). Could be None.
        """
        branch = self._get_branch()
        revision = branch.repository.get_revision(old_revid)
        # remember revids
        self._data['old_revid'] = old_revid
        if new_revid is None:
            from bzrlib.revision import NULL_REVISION
            new_revid = NULL_REVISION
        self._data['new_revid'] = new_revid
        # set data from revision
        self._data['message'] = revision.message

    def load(self):
        """Load saved data from branch/tree."""
        branch = self._get_branch()
        config = branch.get_config()
        data = config.get_user_option('commit_data')
        self.set_data(data)

    def save(self):
        """Save data to the branch/tree."""
        branch = self._get_branch()
        config = branch.get_config()
        config.set_user_option('commit_data', self._data)

    def wipe(self):
        """Delete saved data from branch/tree config."""
        branch = self._get_branch()
        config = branch.get_config()
        config.set_user_option('commit_data', {})

    def _get_branch(self):
        """Return branch object if either branch or tree was specified on init.
        Raise BzrInternalError otherwise.
        """
        if self._branch:
            return self._branch
        if self._tree:
            return self._tree.branch
        # too bad
        from bzrlib import errors
        raise errors.BzrInternalError("CommitData has no saved branch or tree.")
