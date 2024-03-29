# -*- coding: utf-8 -*-
#
# QBzr - Qt frontend to Bazaar commands
# Copyright (C) 2007 Lukáš Lalinský <lalinsky@gmail.com>
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

import sys

from breezy import (
    errors,
    osutils,
    workingtree,
    )
from PyQt5 import QtCore


class CacheEntry(object):

    __slots__ = ['status', 'children']

    def __init__(self):
        self.status = 'unknown'
        self.children = {}

    def __repr__(self):
        return '(%s, %r)' % (self.status, self.children)


class StatusCache(QtCore.QObject):

    def __init__(self, window):
        QtCore.QObject.__init__(self)
        self.fileSystemWatcher = QtCore.QFileSystemWatcher(self)
        self.fileSystemWatcher.directoryChanged['QString'].connect(self.invalidateDirectory)
        self.autoRefreshPath = None
        self.autoRefreshTimer = QtCore.QTimer(self)
        self.autoRefreshTimer.setSingleShot(True)
        self.autoRefreshTimer.timeout.connect(self.autoRefresh)
        self.window = window
        self.cache = CacheEntry()

    def _cacheStatus(self, path, status, root=None):
        if root is None:
            root = self.cache
        entry = root
        for part in path:
            if part not in entry.children:
                entry.children[part] = CacheEntry()
            entry = entry.children[part]
        entry.status = status
        return entry

    def _getCacheEntry(self, parts):
        entry = self.cache
        for part in parts:
            entry = entry.children[part]
        return entry

    def _cacheDirectoryStatus(self, path):
        p = '/'.join(path)
        if sys.platform != 'win32':
            p = '/' + p
        # print "caching", p
        try:
            # to stop bzr-svn from trying to give status on svn checkouts
            # if not QtCore.QDir(p).exists('.bzr'):
            #    raise errors.NotBranchError(p)
            working_tree, relpath = workingtree.WorkingTree.open_containing(p)
        except errors.BzrError:
            self.fileSystemWatcher.addPath(p)
            return self._cacheStatus(path, 'non-versioned')
        self.fileSystemWatcher.addPath(working_tree.basedir)
        basis_tree = working_tree.basis_tree()
        root = self._cacheStatus(osutils.splitpath(working_tree.basedir), 'branch')
        # delta will be a TreeDelta: commit 7389 makes TreeDelta HOLD TreeChange objects in
        # list member variables called added, removed, renamed, copied, kind_changes, modified
        # unchanged, unversioned and missing
        delta = working_tree.changes_from(basis_tree, want_unchanged=True, want_unversioned=True)
        # ... and thus entry will be a TreeChange object, with the path in,
        # perhaps unsurprisingly, 'path' rather than entry[0]. Path is a tuple of
        # old and new path, so get whatever works
        for entry in delta.added:
            self._cacheStatus(osutils.splitpath(entry.path[0] or entry.path[1]), 'added', root=root)
        for entry in delta.removed:
            # BUGBUG - RJLRJL this FIXME might be why the test_tree_widget rename and
            # move_and_rename and its cousins are failing
            # FIXME
            self._cacheStatus(osutils.splitpath(entry.path[0] or entry.path[1]), 'modified', root=root)
#            self._cacheStatus(osutils.splitpath(entry[0]), 'removed', root=root)
        for entry in delta.modified:
            self._cacheStatus(osutils.splitpath(entry.path[0] or entry.path[1]), 'modified', root=root)
        for entry in delta.unchanged:
            self._cacheStatus(osutils.splitpath(entry.path[0] or entry.path[1]), 'unchanged', root=root)
            # self._cacheStatus(osutils.splitpath(entry[0]), 'unchanged', root=root)
        for entry in delta.unversioned:
            self._cacheStatus(osutils.splitpath(entry.path[0] or entry.path[1]), 'non-versioned', root=root)
        try:
            return self._getCacheEntry(path)
        except KeyError:
            self.fileSystemWatcher.addPath(p)
            return self._cacheStatus(path, 'non-versioned')

    def getFileStatus(self, path, name):
        try:
            parent_entry = self._getCacheEntry(path)
        except KeyError:
            parent_entry = None
        if parent_entry is None or parent_entry.status == 'unknown':
            parent_entry = self._cacheDirectoryStatus(path)
        try:
            entry = parent_entry.children[name]
        except KeyError:
            if parent_entry.status == 'non-versioned':
                return 'non-versioned'
            else:
                if sys.platform == 'win32':
                    return 'non-versioned'
                print("NOW WHAT??")
        return entry.status

    def getDirectoryStatus(self, path, name):
        path = path + [name]
        try:
            entry = self._getCacheEntry(path)
        except KeyError:
            entry = self._cacheDirectoryStatus(path)
        else:
            if entry.status == 'unknown':
                entry = self._cacheDirectoryStatus(path)
        # print path, entry.status
        return entry.status

    def invalidateDirectory(self, path):
        path = str(path)
        try:
            parts = osutils.splitpath(path)
            entry = self.cache
            for part in parts[:-1]:
                entry = entry.children[part]
            print("Removing", path, "from the cache")
            del entry.children[parts[-1]]
        except KeyError:
            pass
        else:
            self.autoRefreshPath = path
            self.autoRefreshTimer.start(1000)

    def autoRefresh(self):
        self.window.autoRefresh(self.autoRefreshPath)
