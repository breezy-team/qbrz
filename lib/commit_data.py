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
        bugs: string with space separated fixed bugs ids
            in the form 'id:number'
        authors: string with name(s) of patch author(s)
        file_message: dict for per-file commit messages (used e.g. in MySQL),
            keys in this dict are filenames/fileids,
            values are specific commit messages.
        old_revid: old tip revid (before uncommit)
        new_revid: new tip revid (after uncommit)

    Pair of revision ids (old_revid and new_revid) could be used
    to get all revision messages from uncommitted chain.
    XXX provide some helper API to get uncommitted chain of revisions
    and/or graph and/or revisions data.

    [bialix 20090812] Data saved in branch.conf in [commit_data] section
    as plain dict.
    """

    def __init__(self, branch=None, tree=None, data=None):
        """Initialize data object attached to some tree.
        @param tree: working tree object for commit/uncommit.
        @param branch: branch object for commit/uncommit.
        @param data: initial data values (dictionary).
        """
        self._tree = tree
        self._branch = branch
        self._data = {}
        if data:
            self._data.update(data)

    def _filtered_data(self):
        """Return copy of internal data dictionary without
        keys with "empty" values (i.e. those equal to empty
        string or None).
        """
        d = {}
        for k,v in self._data.iteritems():
            if v not in (None, ''):
                d[k] = v
        return d

    def __nonzero__(self):
        """Check if there is some data actually.
        @return: True if data dictionary is not empty.
        """
        return bool(self._filtered_data())

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

    def keys(self):
        """Return keys of internal dict."""
        return self._data.keys()

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
        from bzrlib.plugins.qbzr.lib.bugs import bug_urls_to_ids
        branch = self._get_branch()
        revision = branch.repository.get_revision(old_revid)
        # remember revids
        self._data['old_revid'] = old_revid
        if new_revid is None:
            from bzrlib.revision import NULL_REVISION
            new_revid = NULL_REVISION
        self._data['new_revid'] = new_revid
        # set data from revision
        self._data['message'] = revision.message or ''
        bug_urls = revision.properties.get('bugs', None)
        if bug_urls:
            self._data['bugs'] = ' '.join(bug_urls_to_ids(bug_urls.split('\n')))

    def compare_data(self, other, all_keys=True):
        """Compare this data with other data.
        @return:    True if data equals.
        @param other: other object (dict or instance of CommitData).
        @param all_keys: if True all keys in both objects
            are compared. If False then only keys in this
            instance compared with corresponding keys in other
            instance.
        """
        try:
            for k,v in self._data.iteritems():
                if v != other[k]:
                    return False
        except KeyError:
            return False
        if all_keys:
            if set(self._data.keys()) != set(other.keys()):
                return False
        return True

    def _load_old_data(self):
        """Load saved data in old format."""
        return

    def load(self):
        """Load saved data from branch/tree."""
        config = self._get_branch_config()
        data = config.get_user_option('commit_data', expand=False)
        if data:
            self.set_data(data)
        else:
            # for backward compatibility
            self._load_old_data()

    def save(self):
        """Save data to the branch/tree."""
        br = self._get_branch()
        br.lock_write()
        try:
            # XXX save should wipe if self._data is empty
            self._set_new_commit_data(self._filtered_data())
            # clear old data
            self._wipe_old_data()
        finally:
            br.unlock()

    def _wipe_old_data(self):
        """Wipe saved data in old format."""
        return

    def wipe(self):
        """Delete saved data from branch/tree config."""
        br = self._get_branch()
        br.lock_write()
        try:
            self._set_new_commit_data({})
            # clear old data
            self._wipe_old_data()
        finally:
            br.unlock()

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

    def _get_branch_config(self):
        return self._get_branch().get_config()

    def _set_new_commit_data(self, new_data):
        config = self._get_branch_config()
        old_data = config.get_user_option('commit_data', expand=False)
        if old_data == new_data:
            return
        try:
            config.set_user_option('commit_data', new_data)
        except AttributeError:
            pass


class QBzrCommitData(CommitData):
    """CommitData variant with backward compatibility support.
    This class knows about old data saved as qbzr_commit_message
    and can provide automatic migration of data.
    """

    def _load_old_data(self):
        config = self._get_branch_config()
        old_data = config.get_user_option('qbzr_commit_message', expand=False)
        if old_data:
            self.set_data(message=old_data)

    def _wipe_old_data(self):
        config = self._get_branch_config()
        if config.get_user_option('qbzr_commit_message', expand=False):
            config.set_user_option('qbzr_commit_message', '')


# in similar way to QBzrCommitData it's possible to implement
# class for bzr-gtk.
