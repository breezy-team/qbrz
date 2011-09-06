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

from PyQt4 import QtCore, QtGui

from bzrlib.plugins.qbzr.lib.diff_arg import *   # import DiffArgProvider classes
from bzrlib.plugins.qbzr.lib.i18n import gettext
from bzrlib.plugins.qbzr.lib.subprocess import SimpleSubProcessDialog
from bzrlib.plugins.qbzr.lib.util import ( 
    get_qbzr_config,
    is_binary_content,
    )

from bzrlib.lazy_import import lazy_import
lazy_import(globals(), '''
import errno
import re
import time
from bzrlib.patiencediff import PatienceSequenceMatcher as SequenceMatcher
from bzrlib.plugins.qbzr.lib.i18n import gettext, ngettext, N_
from bzrlib import trace
''')

qconfig = get_qbzr_config()
default_diff = qconfig.get_option("default_diff")
if default_diff is None:
    default_diff = ""
ext_diffs = {gettext("Builtin Diff"):""}
for name, command in qconfig.get_section('EXTDIFF').items():
    ext_diffs[name] = command


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
        args=["diff", "--using", ext_diff]  # NEVER USE --using=xxx, ALWAYS --using xxx
        # This should be move to after the window has been shown.
        dir, extra_args = arg_provider.get_ext_diff_args(
                                        QtCore.QCoreApplication.processEvents)
        args.extend(extra_args)

        window = SimpleSubProcessDialog("External Diff",
                                        desc=ext_diff,
                                        args=args,
                                        dir=dir,
                                        auto_start_show_on_failed=True,
                                        parent=parent_window)
        window.process_widget.hide_progress()
        if parent_window:
            parent_window.windows.append(window)


def has_ext_diff():
    return len(ext_diffs) > 1


class ExtDiffMenu(QtGui.QMenu):
    
    def __init__ (self, parent=None, include_builtin=True, set_default=True):
        QtGui.QMenu.__init__(self, gettext("Show &differences"), parent)
        
        for name, command in ext_diffs.items():
            if command == "" and include_builtin or not command == "":
                action = QtGui.QAction(name, self)
                action.setData(QtCore.QVariant (command))
                if command == default_diff and set_default:
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
            #QStyle.PM_MenuButtonIndicator
            self.menu_button.setFixedWidth(
                self.menu_button.style().pixelMetric(
                    QtGui.QStyle.PM_MenuButtonIndicator) +
                self.menu_button.style().pixelMetric(
                    QtGui.QStyle.PM_ButtonMargin)
                )
            self.connect(self.menu, QtCore.SIGNAL("triggered(QString)"),
                         self.triggered)

    def triggered(self, ext_diff=None):
        if ext_diff is None:
            ext_diff = QtCore.QString(default_diff)
        self.emit(QtCore.SIGNAL("triggered(QString)"), ext_diff)

try:
    from bzrlib.errors import FileTimestampUnavailable
except ImportError:
    # FileTimestampUnavailable is available only in bzr 2.1.0rc1 and up
    from bzrlib.errors import BzrError
    class FileTimestampUnavailable(BzrError):
        """Fake FileTimestampUnavailable error for older bzr."""
        pass

def get_file_lines_from_tree(tree, file_id):
    try:
        return tree.get_file_lines(file_id)
    except AttributeError:
        return tree.get_file(file_id).readlines()

class DiffItem(object):

    @classmethod
    def create(klass, trees, file_id, paths, changed_content, versioned, 
            parent, name, kind, executable, filter = None):

        if parent == (None, None): # filter out TREE_ROOT (?)
            return None

        # check for manually deleted files (w/o using bzr rm commands)
        if kind[1] is None:
            if versioned == (False, True):
                # added and missed
                return None
            if versioned == (True, True):
                versioned = (True, False)
                paths = (paths[0], None)

        renamed = (parent[0], name[0]) != (parent[1], name[1])

        dates = [None, None]
        for ix in range(2):
            if versioned[ix]:
                try:
                    dates[ix] = trees[ix].get_file_mtime(file_id, paths[ix])
                except OSError, e:
                    if not renamed or e.errno != errno.ENOENT:
                        raise
                    # If we get ENOENT error then probably we trigger
                    # bug #251532 in bzrlib. Take current time instead
                    dates[ix] = time.time()
                except FileTimestampUnavailable:
                    # ghosts around us (see Bug #513096)
                    dates[ix] = 0  # using 1970/1/1 instead

        properties_changed = [] 
        if bool(executable[0]) != bool(executable[1]):
            descr = {True: "+x", False: "-x", None: None}
            properties_changed.append((descr[executable[0]],
                                       descr[executable[1]]))

        if versioned == (True, False):
            status = N_('removed')
        elif versioned == (False, True):
            status = N_('added')
        elif renamed and changed_content:
            status = N_('renamed and modified')
        elif renamed:
            status = N_('renamed')
        else:
            status = N_('modified')
        # check filter options
        if filter and not filter(status):
            return None

        return klass(trees, file_id, paths, changed_content, versioned, kind, 
                        properties_changed, dates, status)

    def __init__(self, trees, file_id, paths, changed_content, versioned, kind,
                        properties_changed, dates, status):
        self.trees = trees
        self.file_id = file_id
        self.paths = paths
        self.changed_content = changed_content
        self.versioned = versioned
        self.kind = kind
        self.properties_changed = properties_changed
        self.dates = dates
        self.status = status

        self._lines = None
        self._binary = None
        self._group_cache = {}
        self._encodings = [None, None]
        self._ulines = [None, None]

    def load(self):
        if self._lines is None:
            self._load_lines()

    def _load_lines(self):
        if ((self.versioned[0] != self.versioned[1] or self.changed_content)
            and (self.kind[0] == 'file' or self.kind[1] == 'file')):
            lines = []
            binary = False
            for ix, tree in enumerate(self.trees):
                content = ()
                if self.versioned[ix] and self.kind[ix] == 'file':
                    content = get_file_lines_from_tree(tree, self.file_id)
                lines.append(content)
                binary = binary or is_binary_content(content)
            self._lines = lines
            self._binary = binary
        else:
            self._lines = ((),())
            self._binary = False

    @property
    def lines(self):
        if self._lines is None:
            self._load_lines()
        return self._lines

    @property
    def binary(self):
        if self._binary is None:
            self._load_lines()
        return self._binary

    def groups(self, complete, ignore_whitespace):
        key = (complete, ignore_whitespace)
        groups = self._group_cache.get(key)
        if groups is not None:
            return groups

        lines = self.lines

        if not self.binary:
            if self.versioned == (True, False):
                groups = [[('delete', 0, len(lines[0]), 0, 0)]]
            elif self.versioned == (False, True):
                groups = [[('insert', 0, 0, 0, len(lines[1]))]]
            else:
                groups = self.difference_groups(lines, complete, ignore_whitespace)
        else:
            groups = []

        self._group_cache[key] = groups
        return groups

    def difference_groups(self, lines, complete, ignore_whitespace):
        left, right = lines
        if ignore_whitespace:
            re_whitespaces = re.compile("\s+")
            left  = (re_whitespaces.sub(" ", line) for line in left)
            right = (re_whitespaces.sub(" ", line) for line in right)
        matcher = SequenceMatcher(None, left, right)
        if complete:
            groups = list([matcher.get_opcodes()])
        else:
            groups = list(matcher.get_grouped_opcodes())

        return groups

    def get_unicode_lines(self, encodings):
        """Return pair of unicode lines for each side of diff.
        Parameter encodings is 2-list or 2-tuple with encoding names (str)
        for each side of diff.
        """
        lines = self.lines
        ulines = self._ulines
        for i in range(2):
            if encodings[i] != self._encodings[i]:
                self._encodings[i] = encodings[i]
                if self.binary:
                    ulines[i] = lines[i][:]
                else:
                    try:
                        ulines[i] = [l.decode(encodings[i]) for l in lines[i]]
                    except UnicodeDecodeError, e:
                        filename = self.paths[i]
                        trace.note("Some characters in file %s "
                                   "could not be properly decoded "
                                   "using '%s' encoding "
                                   "and therefore they replaced with special character.",
                                   filename,
                                   e.encoding)
                        ulines[i] = [l.decode(encodings[i], 'replace') for l in lines[i]]
        return ulines

