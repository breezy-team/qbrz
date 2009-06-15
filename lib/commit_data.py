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

    Hold the data as dictionary; almost all values are lists
    of strings (to use universal interface).
    All strings saved internally as unicode.

    Known items for data dict:
        message: list of strings (texts) - main commit message(s)
        bugs: list of 'id:number' strings for fixed bugs
        authors: list of strings with name(s) of patch author(s)
        file_message: dict for per-file commit messages (MySQL),
            keys in this dict are filenames/fileids,
            values are again lists of messages.

    Bencode used to serialize/deserialize data.

    Serialized data saved in tree.conf (as .bzr/checkout/tree.conf
    where .bzr/checkout/ is base of tree object)
    """

    def __init__(self, tree):
        """Initialize data object attached to some tree.
        @param tree: tree object where commit data saved.
        """
        self._tree = tree
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

    def __getattr__(self, key):
        """Provides access to data dictionary via attributes lookup interface,
        e.g. a.key
        @param key: key in data dictionary.
        @return: value or None if there is no such key.
        """
        return self._data.get(key)

    def insert_data(self, data=None, **kw):
        """Insert new data to dictionary.
        @param data: dictionary with new data.
        @param kw: pairs name=value to insert.
        """
        raise NotImplementedError

    def insert_from_revision(self, rev):
        """Insert data from revision.
        @param rev: revision object.
        """
        raise NotImplementedError

    def serialize_utf8(self):
        """Serialize data dict as utf-8 string."""
        raise NotImplementedError

    def deserialize_utf8(self, src):
        """Deserialize data dict from utf-8 string."""
        raise NotImplementedError

    def load(self):
        """Load saved data from tree."""
        raise NotImplementedError

    def save(self):
        """Save data to the tree."""
        raise NotImplementedError
