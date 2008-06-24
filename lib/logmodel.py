# -*- coding: utf-8 -*-
#
# QBzr - Qt frontend to Bazaar commands
# Copyright (C) 2006-2007 Gary van der Merwe <garyvdm@gmail.com> 
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

#TODO: This list just coppied and pasted. Work out what we really need.
import sys
import re
from PyQt4 import QtCore, QtGui
from time import (strftime, localtime)
from bzrlib import bugtracker, lazy_regex
from bzrlib.log import LogFormatter, show_log
from bzrlib.revision import NULL_REVISION
from bzrlib.plugins.qbzr.lib.linegraph import linegraph
from bzrlib.plugins.qbzr.lib.diff import DiffWindow
from bzrlib.plugins.qbzr.lib.i18n import gettext
from bzrlib.plugins.qbzr.lib.util import (
    BTN_CLOSE,
    QBzrWindow,
    extract_name,
    format_revision_html,
    format_timestamp,
    htmlize,
    open_browser,
    RevisionMessageBrowser,
    )

TagsRole = QtCore.Qt.UserRole + 1
BugIdsRole = QtCore.Qt.UserRole + 2
GraphNodeRole = QtCore.Qt.UserRole + 3
GraphLinesInRole = QtCore.Qt.UserRole + 4
GraphLinesOutRole = QtCore.Qt.UserRole + 5

FilterIdRole = QtCore.Qt.UserRole + 100
FilterMessageRole = QtCore.Qt.UserRole + 101
FilterAuthorRole = QtCore.Qt.UserRole + 102
FilterRevnoRole = QtCore.Qt.UserRole + 103

COL_REV = 0
COL_GRAPH = 1
COL_DATE = 2
COL_AUTHOR = 3
COL_MESSAGE = 4

_bug_id_re = lazy_regex.lazy_compile(r'(?:bugs/|ticket/|show_bug\.cgi\?id=)(\d+)(?:\b|$)')

def get_bug_id(branch, bug_url):
    match = _bug_id_re.search(bug_url)
    if match:
        return match.group(1)
    return None

class TreeModel(QtCore.QAbstractTableModel):
    def __init__(self, parent=None):
        QtCore.QAbstractTableModel.__init__(self, parent)
        
        self.horizontalHeaderLabels = [gettext("Rev"),
                                       gettext("Graph"),
                                       gettext("Date"),
                                       gettext("Author"),
                                       gettext("Message"),
                                       ]
        
        self.linegraphdata = []
        self.index = {}
        self.columns_len = 0
        self.revisions = {}
        self.tags = {}

    def loadBranch(self, branch, start_revs = None, maxnum = None,
                   broken_line_length = 32, graph_data = True,
                   mainline_only = False):
        self.branch = branch
        branch.lock_read()
        self.emit(QtCore.SIGNAL("layoutAboutToBeChanged()"))
        self.revisions = {}
        try:
            if start_revs is None:
                start_revs = [branch.last_revision()]
            (self.linegraphdata, self.index, self.columns_len) = linegraph(branch.repository,
                                                            start_revs,
                                                            maxnum, 
                                                            broken_line_length,
                                                            graph_data,
                                                            mainline_only)
            self.tags = branch.tags.get_reverse_tag_dict()
        except:
            self.linegraphdata = []
            self.index = {}
            self.columns_len = 0
            self.tags = {}
        finally:
            self.emit(QtCore.SIGNAL("layoutChanged()"))
            branch.unlock

    def columnCount(self, parent):
        if parent.isValid():
            return 0
        return len(self.horizontalHeaderLabels)

    def rowCount(self, parent):
        if parent.isValid():
            return 0
        return len(self.linegraphdata)
    
    def linesToQVariant(self,lines):
        qlines = []
        for start, end, colour in lines:
            if start is None: start = -1
            if end is None: end = -1
            qlines.append(QtCore.QVariant([QtCore.QVariant(start),
                                           QtCore.QVariant(end),
                                           QtCore.QVariant(colour)]))
        return QtCore.QVariant(qlines)

    def data(self, index, role):
        if not index.isValid():
            return QtCore.QVariant()
        
        (revid, node, lines, parents, children, revno_sequence) = \
            self.linegraphdata[index.row()]
        
        if role == QtCore.Qt.DisplayRole and index.column() == COL_REV:
            revnos = ".".join(["%d" % (revno)
                                      for revno in revno_sequence])
            return QtCore.QVariant(revnos)
        if role == TagsRole:
            tags = []
            if revid in self.tags:
                tags = self.tags[revid]
            return QtCore.QVariant(tags)
        if role == GraphNodeRole:
            return QtCore.QVariant([QtCore.QVariant(nodei) for nodei in node])
        if role == GraphLinesOutRole:
            return self.linesToQVariant(lines)
        if role == GraphLinesInRole:
            if index.row()>0:
                return self.linesToQVariant(self.linegraphdata[index.row()-1][2])
            return QtCore.QVariant([])
        
        #Everything from here foward need to have the revision loaded.
        if not revid or revid == NULL_REVISION:
            return QtCore.QVariant()
        if revid not in self.revisions:
            revision = self.branch.repository.get_revisions([revid])[0]
            self.revisions[revid] = revision
        else:
            revision = self.revisions[revid]
        
        if role == QtCore.Qt.DisplayRole and index.column() == COL_DATE:
            return QtCore.QVariant(strftime("%Y-%m-%d %H:%M",
                                            localtime(revision.timestamp)))
        if role == QtCore.Qt.DisplayRole and index.column() == COL_AUTHOR:
            return QtCore.QVariant(extract_name(revision.committer))
        if role == QtCore.Qt.DisplayRole and index.column() == COL_MESSAGE:
            return QtCore.QVariant(revision.get_summary())
        if role == BugIdsRole:
            bugtext = gettext("bug #%s")
            bugs = []
            for bug in revision.properties.get('bugs', '').split('\n'):
                if bug:
                    url, status = bug.split(' ')
                    bug_id = get_bug_id(self.branch, url)
                    if bug_id:
                        bugs.append(bugtext % bug_id)
            return QtCore.QVariant(bugs)

        
        #return QtCore.QVariant(item.data(index.column()))
        return QtCore.QVariant()

    def flags(self, index):
        if not index.isValid():
            return QtCore.Qt.ItemIsEnabled

        return QtCore.Qt.ItemIsEnabled | QtCore.Qt.ItemIsSelectable

    def headerData(self, section, orientation, role):
        if orientation == QtCore.Qt.Horizontal and role == QtCore.Qt.DisplayRole:
            return QtCore.QVariant(self.horizontalHeaderLabels[section])

        return QtCore.QVariant()