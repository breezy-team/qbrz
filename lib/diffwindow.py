# -*- coding: utf-8 -*-
#
# QBzr - Qt frontend to Bazaar commands
# Copyright (C) 2006 Lukáš Lalinský <lalinsky@gmail.com>
# Portions Copyright (C) 2006 Jelmer Vernooij <jelmer@samba.org>
# Portions Copyright (C) 2005 Canonical Ltd. (author: Scott James Remnant <scott@ubuntu.com>)
# Portions Copyright (C) 2004-2006 Christopher Lenz <cmlenz@gmx.de>
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

import errno
import time

from PyQt4 import QtCore, QtGui

from bzrlib.errors import NoSuchRevision, PathsNotVersionedError
from bzrlib.mutabletree import MutableTree
from bzrlib.patiencediff import PatienceSequenceMatcher as SequenceMatcher
from bzrlib.revisiontree import RevisionTree
from bzrlib.transform import _PreviewTree
from bzrlib.workingtree import WorkingTree
from bzrlib.workingtree_4 import DirStateRevisionTree
from bzrlib import trace
from bzrlib import cleanup

from bzrlib.plugins.qbzr.lib.diffview import (
    SidebySideDiffView,
    SimpleDiffView,
    )
from bzrlib.plugins.qbzr.lib.diff import (
    show_diff,
    has_ext_diff,
    ExtDiffMenu,
    )

from bzrlib.plugins.qbzr.lib.i18n import gettext, ngettext, N_
from bzrlib.plugins.qbzr.lib.util import (
    BTN_CLOSE, BTN_REFRESH,
    FilterOptions,
    QBzrWindow,
    ThrobberWidget,
    StandardButton,
    get_set_encoding,
    is_binary_content,
    run_in_loading_queue,
    runs_in_loading_queue
    )
from bzrlib.plugins.qbzr.lib.uifactory import ui_current_widget
from bzrlib.plugins.qbzr.lib.trace import reports_exception
from bzrlib.plugins.qbzr.lib.encoding_selector import EncodingSelector

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

def get_title_for_tree(tree, branch, other_branch):
    branch_title = ""
    if None not in (branch, other_branch) and branch.base != other_branch.base:
        branch_title = branch.nick
    
    if isinstance(tree, WorkingTree):
        if branch_title:
            return gettext("Working Tree for %s") % branch_title
        else:
            return gettext("Working Tree")
    
    elif isinstance(tree, (RevisionTree, DirStateRevisionTree)):
        # revision_id_to_revno is faster, but only works on mainline rev
        revid = tree.get_revision_id()
        try:
            revno = branch.revision_id_to_revno(revid)
        except NoSuchRevision:
            try:
                revno_map = branch.get_revision_id_to_revno_map()
                revno_tuple = revno_map[revid]      # this can raise KeyError is revision not in the branch
                revno = ".".join("%d" % i for i in revno_tuple)
            except KeyError:
                # this can happens when you try to diff against other branch
                # or pending merge
                revno = revid

        if revno is not None:
            if branch_title:
                return gettext("Rev %(rev)s for %(branch)s") % {"rev": revno, "branch": branch_title}
            else:
                return gettext("Rev %s") % revno
        else:
            if branch_title:
                return gettext("Revid: %(revid)s for %(branch)s") %  {"revid": revid, "branch": branch_title}
            else:
                return gettext("Revid: %s") % revid

    elif isinstance(tree, _PreviewTree):
        return gettext('Merge Preview')

    # XXX I don't know what other cases we need to handle    
    return 'Unknown tree'


class DiffWindow(QBzrWindow):

    def __init__(self, arg_provider, parent=None,
                 complete=False, encoding=None,
                 filter_options=None, ui_mode=True):

        title = [gettext("Diff"), gettext("Loading...")]
        QBzrWindow.__init__(self, title, parent, ui_mode=ui_mode)
        self.restoreSize("diff", (780, 580))

        self.trees = None
        self.encoding = encoding
        self.arg_provider = arg_provider
        self.filter_options = filter_options
        if filter_options is None:
            self.filter_options = FilterOptions(all_enable=True)
        self.complete = complete

        self.throbber = ThrobberWidget(self)
        
        self.diffview = SidebySideDiffView(self)
        self.sdiffview = SimpleDiffView(self)
        self.views = (self.diffview, self.sdiffview)

        self.stack = QtGui.QStackedWidget(self.centralwidget)
        self.stack.addWidget(self.diffview)
        self.stack.addWidget(self.sdiffview)

        vbox = QtGui.QVBoxLayout(self.centralwidget)
        vbox.addWidget(self.throbber)
        vbox.addWidget(self.stack)

        diffsidebyside = QtGui.QRadioButton(gettext("Side by side"),
                                            self.centralwidget)
        self.connect(diffsidebyside,
                     QtCore.SIGNAL("clicked(bool)"),
                     self.click_diffsidebyside)
        diffsidebyside.setChecked(True);

        unidiff = QtGui.QRadioButton(gettext("Unidiff"), self.centralwidget)
        self.connect(unidiff,
                     QtCore.SIGNAL("clicked(bool)"),
                     self.click_unidiff)

        def on_left_encoding_changed(encoding):
            if self.branches:
                get_set_encoding(encoding, self.branches[0])
            self.click_refresh()
        self.encoding_selector_left = EncodingSelector(encoding,
                                            gettext("Left side encoding:"),
                                            on_left_encoding_changed)

        def on_right_encoding_changed(encoding):
            if self.branches:
                get_set_encoding(encoding, self.branches[1])
            self.click_refresh()
        self.encoding_selector_right = EncodingSelector(encoding,
                                            gettext("Right side encoding:"),
                                            on_right_encoding_changed)


        complete = QtGui.QCheckBox (gettext("Complete"),
                                            self.centralwidget)
        self.connect(complete,
                     QtCore.SIGNAL("clicked(bool)"),
                     self.click_complete)
        complete.setChecked(self.complete);
        
        if has_ext_diff():
            self.menu = ExtDiffMenu(include_builtin = False)
            ext_diff_button = QtGui.QPushButton(gettext('Using'), self)
            ext_diff_button.setMenu(self.menu)
            self.connect(self.menu, QtCore.SIGNAL("triggered(QString)"),
                         self.ext_diff_triggered)

        buttonbox = self.create_button_box(BTN_CLOSE)

        refresh = StandardButton(BTN_REFRESH)
        refresh.setEnabled(self.can_refresh())
        buttonbox.addButton(refresh, QtGui.QDialogButtonBox.ActionRole)
        self.connect(refresh,
                     QtCore.SIGNAL("clicked()"),
                     self.click_refresh)
        self.refresh_button = refresh

        hbox = QtGui.QHBoxLayout()
        hbox.addWidget(diffsidebyside)
        hbox.addWidget(unidiff)
        hbox.addWidget(complete)
        if has_ext_diff():
            hbox.addWidget(ext_diff_button)
        hbox.addWidget(self.encoding_selector_left)
        hbox.addWidget(self.encoding_selector_right)
        hbox.addWidget(buttonbox)
        vbox.addLayout(hbox)

    def show(self):
        QBzrWindow.show(self)
        QtCore.QTimer.singleShot(1, self.initial_load)

    @runs_in_loading_queue
    @ui_current_widget
    @reports_exception()
    def initial_load(self):
        """Called to perform the initial load of the form.  Enables a
        throbber window, then loads the branches etc if they weren't specified
        in our constructor.
        """
        op = cleanup.OperationWithCleanups(self._initial_load)
        self.throbber.show()
        op.add_cleanup(self.throbber.hide)
        op.run()
    
    def _initial_load(self, op):
        (tree1, tree2,
         branch1, branch2,
         specific_files) = self.arg_provider.get_diff_window_args(
                                        self.processEvents, op.add_cleanup)
        
        self.trees = (tree1, tree2)
        self.branches = (branch1, branch2)
        self.specific_files = specific_files
        
        self.load_branch_info()
        self.load_diff()
    
    def load_branch_info(self):
        self.set_diff_title()
        
        self.encoding_selector_left.encoding = get_set_encoding(self.encoding, self.branches[0])
        self.encoding_selector_right.encoding = get_set_encoding(self.encoding, self.branches[1])
        self.processEvents()
    
    def set_diff_title(self):
        rev1_title = get_title_for_tree(self.trees[0], self.branches[0],
                                        self.branches[1])
        rev2_title = get_title_for_tree(self.trees[1], self.branches[1],
                                        self.branches[0])
        
        title = [gettext("Diff"), "%s..%s" % (rev1_title, rev2_title)]

        if self.specific_files:
            nfiles = len(self.specific_files)
            if nfiles > 2:
                title.append(
                    ngettext("%d file", "%d files", nfiles) % nfiles)
            else:
                title.append(", ".join(self.specific_files))
        else:
            if self.filter_options and not self.filter_options.is_all_enable():
                title.append(self.filter_options.to_str())

        self.set_title_and_icon(title)
        self.processEvents()

    def load_diff(self):
        self.refresh_button.setEnabled(False)
        for tree in self.trees: tree.lock_read()
        self.processEvents()
        try:
            changes = self.trees[1].iter_changes(self.trees[0],
                                                 specific_files=self.specific_files,
                                                 require_versioned=True)
            def changes_key(change):
                old_path, new_path = change[1]
                path = new_path
                if path is None:
                    path = old_path
                return path

            try:
                no_changes = True   # if there is no changes found we need to inform the user
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

                    self.processEvents()

                    if parent == (None, None):  # filter out TREE_ROOT (?)
                        continue

                    # check for manually deleted files (w/o using bzr rm commands)
                    if kind[1] is None:
                        if versioned == (False, True):
                            # added and missed
                            continue
                        if versioned == (True, True):
                            versioned = (True, False)
                            paths = (paths[0], None)

                    renamed = (parent[0], name[0]) != (parent[1], name[1])

                    dates = [None, None]
                    for ix in range(2):
                        if versioned[ix]:
                            try:
                                dates[ix] = self.trees[ix].get_file_mtime(file_id, paths[ix])
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
                    if not self.filter_options.check(status):
                        continue

                    if ((versioned[0] != versioned[1] or changed_content)
                        and (kind[0] == 'file' or kind[1] == 'file')):
                        lines = []
                        binary = False
                        for ix, tree in enumerate(self.trees):
                            content = ()
                            if versioned[ix] and kind[ix] == 'file':
                                content = get_file_lines_from_tree(tree, file_id)
                            lines.append(content)
                            binary = binary or is_binary_content(content)
                            self.processEvents()
                        if not binary:
                            if versioned == (True, False):
                                groups = [[('delete', 0, len(lines[0]), 0, 0)]]
                            elif versioned == (False, True):
                                groups = [[('insert', 0, 0, 0, len(lines[1]))]]
                            else:
                                matcher = SequenceMatcher(None, lines[0], lines[1])
                                self.processEvents()
                                if self.complete:
                                    groups = list([matcher.get_opcodes()])
                                else:
                                    groups = list(matcher.get_grouped_opcodes())
                            ulines = []
                            for l, encoding in zip(lines, [self.encoding_selector_left.encoding,
                                                           self.encoding_selector_right.encoding]):
                                try:
                                    ulines.append([i.decode(encoding) for i in l])
                                except UnicodeDecodeError, e:
                                    trace.note('Failed to decode using %s, falling back to latin1', e.encoding)
                                    ulines.append([i.decode('latin1') for i in l])
                            lines = ulines
                            data = ((),())
                        else:
                            groups = []
                        data = [''.join(l) for l in lines]
                    else:
                        binary = False
                        lines = ((),())
                        groups = ()
                        data = ("", "")
                    for view in self.views:
                        view.append_diff(list(paths), file_id, kind, status,
                                         dates, versioned, binary, lines, groups,
                                         data, properties_changed)
                        self.processEvents()
                    no_changes = False
            except PathsNotVersionedError, e:
                    QtGui.QMessageBox.critical(self, gettext('Diff'),
                        gettext(u'File %s is not versioned.\n'
                            'Operation aborted.') % e.paths_as_string,
                        gettext('&Close'))
                    self.close()
        finally:
            for tree in self.trees: tree.unlock()
        if no_changes:
            QtGui.QMessageBox.information(self, gettext('Diff'),
                gettext('No changes found.'),
                gettext('&OK'))
        self.refresh_button.setEnabled(self.can_refresh())

    def click_unidiff(self, checked):
        if checked:
            self.sdiffview.rewind()
            self.stack.setCurrentIndex(1)

    def click_diffsidebyside(self, checked):
        if checked:
            self.diffview.rewind()
            self.stack.setCurrentIndex(0)
    
    def click_complete(self, checked ):
        self.complete = checked
        #Has the side effect of refreshing...
        self.diffview.clear()
        self.sdiffview.clear()
        run_in_loading_queue(self.load_diff)

    def click_refresh(self):
        self.diffview.clear()
        self.sdiffview.clear()
        run_in_loading_queue(self.load_diff)

    def can_refresh(self):
        """Does any of tree is Mutanble/Working tree."""
        if self.trees is None: # we might still be loading...
            return False
        tree1, tree2 = self.trees
        if isinstance(tree1, MutableTree) or isinstance(tree2, MutableTree):
            return True
        return False
    
    def ext_diff_triggered(self, ext_diff):
        """@param ext_diff: path to external diff executable."""
        show_diff(self.arg_provider, ext_diff=ext_diff, parent_window = self)
