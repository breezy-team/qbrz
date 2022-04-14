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
import re
import time
import contextlib

from PyQt5 import QtCore, QtGui, QtWidgets

from breezy.errors import NoSuchRevision, PathsNotVersionedError
from breezy.mutabletree import MutableTree
# from patiencediff import PatienceSequenceMatcher as SequenceMatcher
from patiencediff import PatienceSequenceMatcher as SequenceMatcher
from breezy.revisiontree import RevisionTree
from breezy.workingtree import WorkingTree
from breezy.bzr.workingtree_4 import DirStateRevisionTree
from breezy import trace
# from breezy import cleanup
from breezy.plugins.qbrz.lib import cleanup

from breezy.plugins.qbrz.lib.diffview import (
    SidebySideDiffView,
    SimpleDiffView,
    )
from breezy.plugins.qbrz.lib.diff import (
    show_diff,
    has_ext_diff,
    ExtDiffMenu,
    DiffItem,
    ExtDiffContext,
    )

from breezy.plugins.qbrz.lib.i18n import gettext, ngettext, N_
from breezy.plugins.qbrz.lib.util import (
    FilterOptions,
    QBzrWindow,
    ToolBarThrobberWidget,
    get_icon,
    get_set_encoding,
    get_set_tab_width_chars,
    get_tab_width_pixels,
    content_seems_to_be_binary,
    run_in_loading_queue,
    runs_in_loading_queue,
    show_shortcut_hint,
    )
from breezy.plugins.qbrz.lib.widgets.toolbars import FindToolbar
from breezy.plugins.qbrz.lib.uifactory import ui_current_widget
from breezy.plugins.qbrz.lib.trace import reports_exception
from breezy.plugins.qbrz.lib.encoding_selector import EncodingMenuSelector
from breezy.plugins.qbrz.lib.widgets.tab_width_selector import TabWidthMenuSelector
from breezy.plugins.qbrz.lib.widgets.texteditaccessory import setup_guidebar_for_find



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

    # XXX I don't know what other cases we need to handle
    return 'Unknown tree'


class DiffWindow(QBzrWindow):
    documentChangeFinished = QtCore.pyqtSignal()

    def __init__(self, arg_provider, parent=None,
                 complete=False, encoding=None,
                 filter_options=None, ui_mode=True, allow_refresh=True):

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
        self.ignore_whitespace = False
        self.delayed_signal_connections = []

        self.diffview = SidebySideDiffView(self)
        self.sdiffview = SimpleDiffView(self)
        self.views = (self.diffview, self.sdiffview)
        for view in self.views:
            view.set_complete(complete)

        self.stack = QtWidgets.QStackedWidget(self.centralwidget)
        self.stack.addWidget(self.diffview)
        self.stack.addWidget(self.sdiffview)
        vbox = QtWidgets.QVBoxLayout(self.centralwidget)
        vbox.addWidget(self.stack)

        # Don't use a custom tab width by default
        # Indices are left side, right side and unidiff
        # respectively
        self.custom_tab_widths = [-1,-1,-1]

        for browser in self.diffview.browsers:
            browser.installEventFilter(self)

        self.create_main_toolbar(allow_refresh)
        self.addToolBarBreak()
        self.find_toolbar = FindToolbar(self, self.diffview.browsers, self.show_find)
        self.find_toolbar.hide()
        self.addToolBar(self.find_toolbar)
        setup_guidebar_for_find(self.sdiffview, self.find_toolbar, 1)
        for gb in self.diffview.guidebar_panels:
            setup_guidebar_for_find(gb, self.find_toolbar, 1)
        self.diff_context = ExtDiffContext(self)

    # # RJLRJL: As far as I can tell, this is only called ONCE...
    # def connect_later(self, *args, **kwargs):
    #     """Schedules a signal to be connected after loading CLI arguments.

    #     Accepts the same arguments as QObject.connect method.
    #     """
    #     self.delayed_signal_connections.append((args, kwargs))

    # # ...and this is only called by _initial_load. Once.
    # def process_delayed_connections(self):
    #     for (args, kwargs) in self.delayed_signal_connections:
    #         self.connect(*args, **kwargs)

    def create_main_toolbar(self, allow_refresh=True):
        toolbar = self.addToolBar(gettext("Diff"))
        toolbar.setMovable (False)
        toolbar.setToolButtonStyle(QtCore.Qt.ToolButtonTextBesideIcon)

        self.show_find = self.create_find_action()
        toolbar.addAction(self.show_find)
        toolbar.addAction(self.create_toggle_view_mode())
        self.view_refresh = self.create_refresh_action(allow_refresh)
        if allow_refresh:
            toolbar.addAction(self.view_refresh)

        if has_ext_diff():
            show_ext_diff_menu = self.create_ext_diff_action()
            toolbar.addAction(show_ext_diff_menu)
            widget = toolbar.widgetForAction(show_ext_diff_menu)
            widget.setPopupMode(QtWidgets.QToolButton.InstantPopup)
            widget.setShortcut("Alt+E")
            show_shortcut_hint(widget)

        show_view_menu = self.create_view_menu()
        toolbar.addAction(show_view_menu)
        widget = toolbar.widgetForAction(show_view_menu)
        widget.setPopupMode(QtWidgets.QToolButton.InstantPopup)
        widget.setShortcut("Alt+V")
        show_shortcut_hint(widget)

        spacer = QtWidgets.QWidget()
        spacer.setSizePolicy(QtWidgets.QSizePolicy.Expanding, QtWidgets.QSizePolicy.Expanding)
        toolbar.addWidget(spacer)

        self.throbber = ToolBarThrobberWidget(self)
        toolbar.addWidget(self.throbber)
        return toolbar

    def create_find_action(self):
        action = QtWidgets.QAction(get_icon("edit-find"), gettext("&Find"), self)
        action.setShortcut(QtGui.QKeySequence.Find)
        action.setToolTip(gettext("Find on active panel"))
        show_shortcut_hint(action)
        action.setCheckable(True)
        return action

    def create_toggle_view_mode(self):
        action = QtWidgets.QAction(get_icon("view-split-left-right"), gettext("Unidiff"), self)
        action.setToolTip(gettext("Toggle between Side by side and Unidiff view modes"))
        action.setShortcut("Ctrl+U")
        show_shortcut_hint(action)
        action.setCheckable(True)
        action.setChecked(False);
        action.toggled[bool].connect(self.click_toggle_view_mode)
        return action

    def create_refresh_action(self, allow_refresh=True):
        action = QtWidgets.QAction(get_icon("view-refresh"), gettext("&Refresh"), self)
        action.setShortcut("Ctrl+R")
        show_shortcut_hint(action)
        action.triggered[bool].connect(self.click_refresh)
        action.setEnabled(allow_refresh)
        return action

    def create_ext_diff_action(self):
        action = QtWidgets.QAction(get_icon("system-run"), gettext("&External Diff"), self)
        action.setToolTip(gettext("Launch an external diff application"))
        ext_diff_menu = ExtDiffMenu(parent=self, include_builtin = False)
        action.setMenu(ext_diff_menu)
        ext_diff_menu._triggered.connect(self.ext_diff_triggered)
        return action

    def create_view_menu(self):
        show_view_menu = QtWidgets.QAction(get_icon("document-properties"), gettext("&View Options"), self)
        view_menu = QtWidgets.QMenu(gettext('View Options'), self)
        show_view_menu.setMenu(view_menu)
        view_complete = QtWidgets.QAction(gettext("&Complete"), self)
        view_complete.setCheckable(True)
        view_complete.toggled [bool].connect(self.click_complete)
        view_menu.addAction(view_complete)
        self.ignore_whitespace_action = self.create_ignore_ws_action()
        view_menu.addAction(self.ignore_whitespace_action)

        # Indent is correct: nested function
        def on_unidiff_tab_width_changed(tabwidth):
            if self.branches:
                get_set_tab_width_chars(branch=self.branches[0],tab_width_chars=tabwidth)
            self.custom_tab_widths[2] = tabwidth
            self.setup_tab_width()

        self.tab_width_selector_unidiff = TabWidthMenuSelector(label_text=gettext("Tab width"), onChanged=on_unidiff_tab_width_changed)
        view_menu.addMenu(self.tab_width_selector_unidiff)

        # Indent is correct: nested function
        def on_left_tab_width_changed(tabwidth):
            if self.branches:
                get_set_tab_width_chars(branch=self.branches[0],tab_width_chars=tabwidth)
            self.custom_tab_widths[0] = tabwidth
            self.setup_tab_width()

        self.tab_width_selector_left = TabWidthMenuSelector(label_text=gettext("Left side tab width"), onChanged=on_left_tab_width_changed)
        view_menu.addMenu(self.tab_width_selector_left)

        # Indent is correct: nested function
        def on_right_tab_width_changed(tabwidth):
            if self.branches:
                get_set_tab_width_chars(branch=self.branches[1],tab_width_chars=tabwidth)
            self.custom_tab_widths[1] = tabwidth
            self.setup_tab_width()

        self.tab_width_selector_right = TabWidthMenuSelector(label_text=gettext("Right side tab width"), onChanged=on_right_tab_width_changed)
        view_menu.addMenu(self.tab_width_selector_right)

        if self.stack.currentWidget() == self.diffview:
            self.tab_width_selector_unidiff.menuAction().setVisible(False)
        else:
            self.tab_width_selector_left.menuAction().setVisible(False)
            self.tab_width_selector_right.menuAction().setVisible(False)

        # Indent is correct: nested function
        def on_left_encoding_changed(encoding):
            if self.branches:
                get_set_encoding(encoding, self.branches[0])
            self.click_refresh()

        self.encoding_selector_left = EncodingMenuSelector(self.encoding, gettext("Left side encoding"), on_left_encoding_changed)
        view_menu.addMenu(self.encoding_selector_left)

        # Indent is correct: nested function
        def on_right_encoding_changed(encoding):
            if self.branches:
                get_set_encoding(encoding, self.branches[1])
            self.click_refresh()

        self.encoding_selector_right = EncodingMenuSelector(self.encoding, gettext("Right side encoding"), on_right_encoding_changed)
        view_menu.addMenu(self.encoding_selector_right)
        return show_view_menu

    def create_ignore_ws_action(self):
        action = QtWidgets.QAction(gettext("&Ignore whitespace changes"), self)
        action.setCheckable(True)
        # RJLRJL removed spurious semi-colon (hmm...)
        action.setChecked(self.ignore_whitespace)
        # RJLRJL this is the only occurance of connect_later.
        # self.connect_later(action, QtCore.SIGNAL("toggled (bool)"), self.click_ignore_whitespace)
        # ...which ends up with eventually needing to call process_delayed_connections, etc.
        # Get rid of it and do it normally
        action.toggled[bool].connect(self.click_ignore_whitespace)
        return action

    def eventFilter(self, object, event):
        if event.type() == QtCore.QEvent.FocusIn:
            if object in self.diffview.browsers:
                self.find_toolbar.set_text_edit(object)
        return QBzrWindow.eventFilter(self, object, event)
        # Why doesn't this work?
        #return super(DiffWindow, self).eventFilter(object, event)

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
        # RJL Breezy expects a context handler of some type
        exit_stack = contextlib.ExitStack()
        args = self.arg_provider.get_diff_window_args(self.processEvents, exit_stack)
        # args = self.arg_provider.get_diff_window_args(self.processEvents, op.add_cleanup)

        self.trees = (args["old_tree"], args["new_tree"])
        self.branches = (args.get("old_branch", None), args.get("new_branch",None))
        self.specific_files = args.get("specific_files", None)
        self.ignore_whitespace = args.get("ignore_whitespace", False)
        # RJLRJL setChecked is also done in create_ignore_ws_action
        self.ignore_whitespace_action.setChecked(self.ignore_whitespace)
        # RJLRJL got rid of this
        # self.process_delayed_connections()
        self.load_branch_info()
        self.setup_tab_width()
        self.load_diff()

    def load_branch_info(self):
        self.set_diff_title()
        self.encoding_selector_left.encoding = get_set_encoding(self.encoding, self.branches[0])
        self.encoding_selector_right.encoding = get_set_encoding(self.encoding, self.branches[1])
        self.processEvents()

    def set_diff_title(self):
        rev1_title = get_title_for_tree(self.trees[0], self.branches[0], self.branches[1])
        rev2_title = get_title_for_tree(self.trees[1], self.branches[1], self.branches[0])
        title = [gettext("Diff"), "%s..%s" % (rev1_title, rev2_title)]
        if self.specific_files:
            nfiles = len(self.specific_files)
            if nfiles > 2:
                title.append(ngettext("%d file", "%d files", nfiles) % nfiles)
            else:
                title.append(", ".join(self.specific_files))
        else:
            if self.filter_options and not self.filter_options.is_all_enable():
                title.append(self.filter_options.to_str())
        self.set_title_and_icon(title)
        self.processEvents()

    def setup_tab_width(self):
        tabWidths = self.custom_tab_widths
        if tabWidths[0] < 0:
            tabWidths[0] = get_set_tab_width_chars(branch=self.branches[0])
            self.tab_width_selector_left.setTabWidth(tabWidths[0])
        if tabWidths[1] < 0:
            tabWidths[1] = get_set_tab_width_chars(branch=self.branches[1])
            self.tab_width_selector_right.setTabWidth(tabWidths[1])
        if tabWidths[2] < 0:
            tabWidths[2] = get_set_tab_width_chars(branch=self.branches[0])
            self.tab_width_selector_unidiff.setTabWidth(tabWidths[2])
        tabWidthsPixels = [get_tab_width_pixels(tab_width_chars=i) for i in tabWidths]
        self.diffview.setTabStopWidths(tabWidthsPixels)
        self.sdiffview.setTabStopWidth(tabWidthsPixels[2])

    def load_diff(self):
        self.view_refresh.setEnabled(False)
        self.processEvents()
        try:
            no_changes = True   # if there is no changes found we need to inform the user
            for di in DiffItem.iter_items(self.trees,
                                          specific_files=self.specific_files,
                                          filter=self.filter_options.check,
                                          lock_trees=True):
                lines = di.lines
                self.processEvents()
                groups = di.groups(self.complete, self.ignore_whitespace)
                self.processEvents()
                ulines = di.get_unicode_lines(
                    (self.encoding_selector_left.encoding,
                     self.encoding_selector_right.encoding))
                # If we've got binary, it'll be bytes (probably)...
                if di.binary:
                    data = [b''.join(l) for l in ulines]
                else:
                    data = [''.join(l) for l in ulines]
                for view in self.views:
                    view.append_diff(list(di.paths), di.file_id, di.kind, di.status,
                                     di.dates, di.versioned, di.binary, ulines, groups,
                                     data, di.properties_changed)
                    self.processEvents()
                no_changes = False
        except PathsNotVersionedError as e:
                QtWidgets.QMessageBox.critical(self, gettext('Diff'),
                    gettext('File %s is not versioned.\n'
                        'Operation aborted.') % e.paths_as_string,
                    gettext('&Close'))
                self.close()

        if no_changes:
            QtWidgets.QMessageBox.information(self, gettext('Diff'),
                gettext('No changes found.'),
                gettext('&OK'))
        for t in self.views[0].browsers + (self.views[1],):
            t.documentChangeFinished.emit()
        self.view_refresh.setEnabled(self.can_refresh())

    def click_toggle_view_mode(self, checked):
        if checked:
            view = self.sdiffview
            self.find_toolbar.set_text_edits([view.view])
            self.tab_width_selector_left.menuAction().setVisible(False)
            self.tab_width_selector_right.menuAction().setVisible(False)
            self.tab_width_selector_unidiff.menuAction().setVisible(True)
        else:
            view = self.diffview
            self.find_toolbar.set_text_edits(view.browsers)
            self.tab_width_selector_left.menuAction().setVisible(True)
            self.tab_width_selector_right.menuAction().setVisible(True)
            self.tab_width_selector_unidiff.menuAction().setVisible(False)
        view.rewind()
        index = self.stack.indexOf(view)
        self.stack.setCurrentIndex(index)

    def click_complete(self, checked ):
        self.complete = checked
        #Has the side effect of refreshing...
        self.diffview.set_complete(checked)
        self.sdiffview.set_complete(checked)
        self.diffview.clear()
        self.sdiffview.clear()
        run_in_loading_queue(self.load_diff)

    def click_refresh(self):
        self.diffview.clear()
        self.sdiffview.clear()
        run_in_loading_queue(self.load_diff)

    def can_refresh(self):
        """Does any of tree is Mutanble/Working tree."""
        if self.trees is None:  # we might still be loading...
            return False
        tree1, tree2 = self.trees
        if isinstance(tree1, MutableTree) or isinstance(tree2, MutableTree):
            return True
        return False

    def ext_diff_triggered(self, ext_diff):
        """@param ext_diff: path to external diff executable."""
        show_diff(self.arg_provider, ext_diff=ext_diff, parent_window=self, context=self.diff_context)

    def click_ignore_whitespace(self, checked ):
        self.ignore_whitespace = checked
        # Has the side effect of refreshing...
        self.diffview.clear()
        self.sdiffview.clear()
        run_in_loading_queue(self.load_diff)

