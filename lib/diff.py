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

from bzrlib.errors import FileTimestampUnavailable, NoSuchId, ExecutableMissing
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
import sys
import os
import glob
from bzrlib.patiencediff import PatienceSequenceMatcher as SequenceMatcher
from bzrlib.plugins.qbzr.lib.i18n import gettext, ngettext, N_
from bzrlib import trace, osutils, cmdline
from bzrlib.workingtree import WorkingTree
from bzrlib.trace import mutter
''')
from bzrlib.diff import DiffFromTool, DiffPath
subprocess = __import__('subprocess', {}, {}, [])

qconfig = get_qbzr_config()
default_diff = qconfig.get_option("default_diff")
if default_diff is None:
    default_diff = ""
ext_diffs = {gettext("Builtin Diff"):""}
for name, command in qconfig.get_section('EXTDIFF').items():
    ext_diffs[name] = command


def show_diff(arg_provider, ext_diff=None, parent_window=None, context=None):
    
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
    elif context:
        ext_diff = str(ext_diff) # convert QString to str
        cleanup = []
        try:
            args = arg_provider.get_diff_window_args(
                QtGui.QApplication.processEvents, cleanup.append
            )
            old_tree = args["old_tree"]
            new_tree = args["new_tree"]
            specific_files = args.get("specific_files")
            context.setup(ext_diff, old_tree, new_tree)
            if specific_files:
                context.diff_paths(specific_files)
            else:
                context.diff_tree()
        finally:
            while cleanup:
                cleanup.pop()()

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

def get_file_lines_from_tree(tree, file_id):
    try:
        return tree.get_file_lines(file_id)
    except AttributeError:
        return tree.get_file(file_id).readlines()

class DiffItem(object):
    """
    Diff data for each file.

    This class has moved from lib/diffwindow.py.
    You can see annotation of older code by::

      bzr ann lib/diffwindow.py -r 1429
    """

    @classmethod
    def iter_items(cls, trees, specific_files=None, filter=None, lock_trees=False):
        try:
            cleanup = []
            if lock_trees:
                for t in trees:
                    cleanup.append(t.lock_read().unlock)

            changes = trees[1].iter_changes(trees[0],
                            specific_files=specific_files,
                            require_versioned=True)

            def changes_key(change):
                return change[1][1] or change[1][0]

            for (file_id, paths, changed_content, versioned, parent, name, kind,
                 executable) in sorted(changes, key=changes_key):
                # file_id         -> ascii string
                # paths           -> 2-tuple (old, new) fullpaths unicode/None
                # changed_content -> bool
                # versioned       -> 2-tuple (bool, bool)
                # parent          -> 2-tuple
                # name            -> 2-tuple (old_name, new_name) utf-8?/None
                # kind            -> 2-tuple (string/None, string/None)
                # executable      -> 2-tuple (bool/None, bool/None)
                # NOTE: None value used for non-existing entry in corresponding
                #       tree, e.g. for added/deleted file
                di = DiffItem.create(trees, file_id, paths, changed_content,
                        versioned, parent, name, kind, executable,
                        filter = filter)
                if not di:
                    continue
                yield di
        finally:
            while cleanup:
                cleanup.pop()()

    @classmethod
    def create(cls, trees, file_id, paths, changed_content, versioned, 
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

        return cls(trees, file_id, paths, changed_content, versioned, kind, 
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

CACHE_TIMEOUT = 3600

class _ExtDiffer(DiffFromTool):
    """
    Run extdiff async.
    XXX: This class is strongly depending on DiffFromTool internals now.
    """
    def __init__(self, command_string, old_tree, new_tree, to_file=None, path_encoding='utf-8'):
        DiffPath.__init__(self, old_tree, new_tree, to_file or sys.stdout, path_encoding)
        self.set_command_string(command_string)
        parent = osutils.joinpath([osutils.tempfile.gettempdir(), 'qbzr'])
        if not os.path.isdir(parent):
            os.mkdir(parent)
        self._root = osutils.mkdtemp(prefix='qbzr/bzr-diff-')
        self.prefixes = {}
        self._set_prefix()

    @property
    def trees(self):
        return self.old_tree, self.new_tree

    def set_trees(self, old_tree, new_tree):
        self.old_tree = old_tree
        self.new_tree = new_tree
        self._set_prefix()

    def _set_prefix(self):
        self.old_prefix = self.get_prefix(self.old_tree)
        self.new_prefix = self.get_prefix(self.new_tree)

    def get_prefix(self, tree):
        def get_key(tree):
            if hasattr(tree, "get_revision_id"):
                return tree.__class__.__name__ + ":" + tree.get_revision_id()
            elif hasattr(tree, "abspath"):
                return tree.__class__.__name__ + ":" + tree.abspath("")
            else:
                return tree.__class__.__name__ + ":" + str(hash(tree))

        if tree is None:
            return None
        key = get_key(tree)
        if self.prefixes.has_key(key):
            return self.prefixes[key]
        prefix = str(len(self.prefixes) + 1)
        self.prefixes[key] = prefix
        return prefix

    def set_command_string(self, command_string):
        command_template = cmdline.split(command_string)
        if '@' not in command_string:
            command_template.extend(['@old_path', '@new_path'])
        self.command_template = command_template

    def finish(self):
        parent = os.path.dirname(self._root)
        for path in glob.glob(os.path.join(parent, "*")):
            if self._is_deletable(path):
                self._delete_tmpdir(path)
        self._delete_tmpdir(self._root)

    def finish_lazy(self):
        parent = os.path.dirname(self._root)
        for path in glob.glob(os.path.join(parent, "*")):
            if self._is_deletable(path):
                self._delete_tmpdir(path)
        open(os.path.join(self._root, ".delete"), "w").close()

    def _is_deletable(self, root):
        if os.path.exists(os.path.join(root, ".delete")):
            return True
        elif time.time() > os.path.getctime(root) + CACHE_TIMEOUT:
            return True
        else:
            return False

    def _delete_tmpdir(self, path):
        try:
            osutils.rmtree(path)
        except:
            if os.path.isdir(path):
                open(os.path.join(path, ".delete"), "w").close()

    def _write_file(self, file_id, tree, prefix, relpath, force_temp=False,
                    allow_write=False):
        if force_temp or not isinstance(tree, WorkingTree):
            full_path = self._safe_filename(prefix, relpath)
            if os.path.isfile(full_path):
                return full_path
        return DiffFromTool._write_file(self, file_id, tree, prefix, 
                                        relpath, force_temp, allow_write)

    def _prepare_files(self, file_id, old_path, new_path, force_temp=False,
                       allow_write_new=False):
        old_disk_path = self._write_file(file_id, self.old_tree,
                                         self.old_prefix, old_path, force_temp)
        new_disk_path = self._write_file(file_id, self.new_tree,
                                         self.new_prefix, new_path, force_temp,
                                         allow_write=allow_write_new)
        return old_disk_path, new_disk_path

    def _execute(self, old_path, new_path):
        command = self._get_command(old_path, new_path)
        try:
            subprocess.Popen(command, cwd=self._root)
        except OSError, e:
            if e.errno == errno.ENOENT:
                raise ExecutableMissing(command[0])
            else:
                raise
        return 0

    def diff(self, file_id):
        try:
            new_path = self.new_tree.id2path(file_id)
            new_kind = self.new_tree.kind(file_id)
            old_path = self.old_tree.id2path(file_id)
            old_kind = self.old_tree.kind(file_id)
        except NoSuchId:
            return DiffPath.CANNOT_DIFF
        return DiffFromTool.diff(self, file_id, old_path, new_path, old_kind, new_kind)

class ExtDiffContext(QtCore.QObject):
    """
    Environment for external diff execution.
    This class manages cache of diffed files and when it will be deleted.
    """
    def __init__(self, parent, to_file=None, path_encoding='utf-8'):
        """
        :parent:  parent widget. If specified, cache is deleted automatically
                  when parent is closed.
        :to_file: stream to write output messages. If not specified, 
                  stdout is used.
        :path_encoding: encoding of path
        """
        QtCore.QObject.__init__(self, parent)
        self.to_file = to_file
        self.path_encoding = path_encoding
        self._differ = None
        if parent is not None:
            parent.window().installEventFilter(self)

    def finish(self):
        """
        Remove temporary directory which contains cached files.
        """
        try:
            if self._differ:
                self._differ.finish()
                self._differ = None
        except:
            pass

    def finish_lazy(self):
        """
        Mark temporary directory as deletable, without delete it actually.
        XXX: Directory marked as deletable will be deleted next time.
        """
        try:
            if self._differ:
                self._differ.finish_lazy()
                self._differ = None
        except:
            pass

    @property
    def rootdir(self):
        if self._differ:
            return self._differ._root
        else:
            return None

    def setup(self, command_string, old_tree, new_tree):
        """
        Set or change diff command and diffed trees.
        """
        if self._differ is None:
            self._differ = _ExtDiffer(command_string, old_tree, new_tree,
                                      self.to_file, self.path_encoding)
        else:
            self._differ.set_trees(old_tree, new_tree)
            self._differ.set_command_string(command_string)

    def eventFilter(self, obj, event):
        if event.type() == QtCore.QEvent.Close:
            self.finish()
        return QtCore.QObject.eventFilter(self, obj, event)

    def diff_ids(self, file_ids, interval=50, lock_trees=True):
        """
        Show diffs of specified file_ids.
        NOTE: Directories cannot be specified.
              Use diff_tree or diff_paths instead when specifing directory. 
        """
        cleanup = []
        try:
            if lock_trees:
                cleanup.append(self._differ.new_tree.lock_read().unlock)
                cleanup.append(self._differ.old_tree.lock_read().unlock)
            for file_id in file_ids:
                self._differ.diff(file_id)
                time.sleep(interval * 0.001)
        finally:
            while cleanup:
                cleanup.pop()()

    def diff_paths(self, paths, interval=50, lock_trees=True):
        """
        Show diffs of specified file paths.
        """
        new_tree = self._differ.new_tree
        old_tree = self._differ.old_tree

        valid_paths = []
        ids = []
        dir_included = False
        cleanup = []
        try:
            # Sometimes, we must lock tree before calling tree.kind()
            if lock_trees:
                cleanup.append(new_tree.lock_read().unlock)
                cleanup.append(old_tree.lock_read().unlock)
            for p in paths:
                id = new_tree.path2id(p)
                if id:
                    valid_paths.append(p)
                    ids.append(id)
                    dir_included = dir_included or (new_tree.kind(id) != 'file')
                else:
                    mutter('%s does not exist in the new tree' % p)
            if not ids:
                return
            if dir_included:
                self.diff_tree(valid_paths, interval, False)
            else:
                self.diff_ids(ids, interval, False)
        finally:
            while cleanup:
                cleanup.pop()()

    def diff_tree(self, specific_files=None, interval=50, lock_trees=True):
        """
        Show diffs between two trees. (trees must be set by setup method)
        NOTE: Directory path can be specified to specific_files.
        """
        for di in DiffItem.iter_items(self._differ.trees,
                                      specific_files=specific_files,
                                      lock_trees=lock_trees):
            if di.changed_content:
                self._differ.diff(di.file_id)
                time.sleep(interval * 0.001)


