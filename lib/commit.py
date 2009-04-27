# -*- coding: utf-8 -*-
#
# QBzr - Qt frontend to Bazaar commands
# Copyright (C) 2006-2007 Lukáš Lalinský <lalinsky@gmail.com>
# Copyright (C) 2006 Trolltech ASA
# Copyright (C) 2006 Jelmer Vernooij <jelmer@samba.org>
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

import os.path
import re
import sys
from PyQt4 import QtCore, QtGui

from bzrlib import (
    bugtracker,
    errors,
    osutils,
    )
from bzrlib.errors import BzrError, NoSuchRevision
from bzrlib.option import Option
from bzrlib.commands import Command, register_command
from bzrlib.commit import ReportCommitToLog
from bzrlib.workingtree import WorkingTree

from bzrlib.plugins.qbzr.lib.spellcheck import SpellCheckHighlighter, SpellChecker
from bzrlib.plugins.qbzr.lib.autocomplete import get_wordlist_builder
from bzrlib.plugins.qbzr.lib.diff import (
    DiffButtons,
    show_diff,
    InternalWTDiffArgProvider,
    InternalDiffArgProvider,
    )
from bzrlib.plugins.qbzr.lib.i18n import gettext
from bzrlib.plugins.qbzr.lib.subprocess import SubProcessWindow
from bzrlib.plugins.qbzr.lib.util import (
    BTN_CANCEL,
    BTN_OK,
    QBzrWindow,
    file_extension,
    format_timestamp,
    get_apparent_author,
    get_global_config,
    url_for_display,
    ThrobberWidget,
    runs_in_loading_queue,
    )
from bzrlib.plugins.qbzr.lib.wtlist import (
    ChangeDesc,
    WorkingTreeFileList,
    closure_in_selected_list,
    )
from bzrlib.plugins.qbzr.lib.logwidget import LogList
from bzrlib.plugins.qbzr.lib.trace import *
from bzrlib.plugins.qbzr.lib.uifactory import ui_current_widget


MAX_AUTOCOMPLETE_FILES = 20


class TextEdit(QtGui.QTextEdit):

    def __init__(self, parent=None, main_window=None):
        QtGui.QTextEdit.__init__(self, parent)
        self.completer = None
        self.eow = QtCore.QString("~!@#$%^&*()_+{}|:\"<>?,./;'[]\\-=")
        self.main_window = main_window

    def keyPressEvent(self, e):
        c = self.completer
        e_key = e.key()
        if (e_key in (QtCore.Qt.Key_Tab, QtCore.Qt.Key_Backtab)
            or (c.popup().isVisible() and e_key in (QtCore.Qt.Key_Enter,
                QtCore.Qt.Key_Return, QtCore.Qt.Key_Escape))):
            e.ignore()
            return
        if (self.main_window
            and e_key in (QtCore.Qt.Key_Enter, QtCore.Qt.Key_Return)
            and (int(e.modifiers()) & QtCore.Qt.ControlModifier)):
                e.ignore()
                # FIXME probably this is ugly hack and main qcommit window
                # should explicitly catch Ctrl+Enter by self
                self.main_window.accept()
                return

        isShortcut = e.modifiers() & QtCore.Qt.ControlModifier and e.key() == QtCore.Qt.Key_E
        if not isShortcut:
            QtGui.QTextEdit.keyPressEvent(self, e)

        ctrlOrShift = e.modifiers() & (QtCore.Qt.ControlModifier | QtCore.Qt.ShiftModifier)
        if ctrlOrShift and e.text().isEmpty():
            return

        hasModifier = (e.modifiers() != QtCore.Qt.NoModifier) and not ctrlOrShift
        completionPrefix = self.textUnderCursor()

        if not isShortcut and (hasModifier or e.text().isEmpty()
                               or completionPrefix.length() < 2
                               or self.eow.contains(e.text().right(1))):
            c.popup().hide()
            return

        if completionPrefix != c.completionPrefix():
            c.setCompletionPrefix(completionPrefix)
            c.popup().setCurrentIndex(c.completionModel().index(0, 0))

        cr = self.cursorRect()
        cr.setWidth(c.popup().sizeHintForColumn(0) +
                    c.popup().verticalScrollBar().sizeHint().width())
        c.complete(cr);

    def textUnderCursor(self):
        tc = self.textCursor()
        tc.select(QtGui.QTextCursor.WordUnderCursor)
        return tc.selectedText()

    def insertCompletion(self, completion):
        tc = self.textCursor()
        extra = completion.length() - self.completer.completionPrefix().length()
        tc.movePosition(QtGui.QTextCursor.Left)
        tc.movePosition(QtGui.QTextCursor.EndOfWord)
        tc.insertText(completion.right(extra))
        self.setTextCursor(tc)

    def setCompleter(self, completer):
        self.completer = completer
        completer.setWidget(self)
        completer.setCaseSensitivity(QtCore.Qt.CaseSensitive)
        self.connect(completer, QtCore.SIGNAL("activated(QString)"),
                     self.insertCompletion)

class PendingMergesList(LogList):
    def __init__(self, processEvents, throbber, no_graph, parent=None):
        super(PendingMergesList, self).__init__(processEvents,
                                        throbber, no_graph, parent)
        # The rev numbers are currently bogus. Hide that column.
        # We could work out the revision numbers by loading whole graph, but
        # that is going to make this much slower.
        self.header().hideSection(0)
    
    def load(self):
        self.graph_provider.lock_read_branches()
        try:
            self.graph_provider.load_tags()
            self.model.load_graph_pending_merges()
        finally:
            self.graph_provider.unlock_branches()

class CommitWindow(SubProcessWindow):

    RevisionIdRole = QtCore.Qt.UserRole + 1
    ParentIdRole = QtCore.Qt.UserRole + 2

    def iter_changes_and_state(self):
        """An iterator for the WorkingTreeFileList widget"""
        # a word list for message completer
        words = set()
        show_nonversioned = self.show_nonversioned_checkbox.isChecked()

        in_selected_list = closure_in_selected_list(self.initial_selected_list)

        num_versioned_files = 0
        for desc in self.tree.iter_changes(self.tree.basis_tree(),
                                           want_unversioned=True):
            desc = ChangeDesc(desc)

            if desc.is_tree_root() or desc.is_misadded():
                # skip uninteresting enties
                continue

            is_versioned = desc.is_versioned()
            path = desc.path()

            if not is_versioned and self.tree.is_ignored(path):
                continue

            visible = is_versioned or show_nonversioned
            check_state = None
            if not self.has_pending_merges:
                check_state = visible and is_versioned and in_selected_list(path)
            yield desc, visible, check_state

            if is_versioned:
                num_versioned_files += 1

                words.update(os.path.split(path))
                if desc.is_renamed():
                    words.update(os.path.split(desc.oldpath()))
                if num_versioned_files < MAX_AUTOCOMPLETE_FILES:
                    ext = file_extension(path)
                    builder = get_wordlist_builder(ext)
                    if builder is not None:
                        try:
                            abspath = os.path.join(self.tree.basedir, path)
                            file = open(abspath, 'rt')
                            words.update(builder.iter_words(file))
                        except EnvironmentError:
                            pass
        words = list(words)
        words.sort(lambda a, b: cmp(a.lower(), b.lower()))
        self.completion_words = words

    def __init__(self, tree, selected_list, dialog=True, parent=None,
                 local=None, message=None, ui_mode=True):
        super(CommitWindow, self).__init__(
                                  gettext("Commit"),
                                  name = "commit",
                                  default_size = (540, 540),
                                  ui_mode = ui_mode,
                                  dialog = dialog,
                                  parent = parent)
        self.tree = tree
        tree.lock_read()
        try:
            self.basis_tree = self.tree.basis_tree()
            self.is_bound = bool(tree.branch.get_bound_location())
            self.has_pending_merges = len(tree.get_parent_ids())>1
        finally:
            tree.unlock()
        
        self.windows = []
        self.initial_selected_list = selected_list

        self.connect(self.process_widget,
            QtCore.SIGNAL("failed()"),
            self.failed)

        self.throbber = ThrobberWidget(self)

        # commit to branch location
        branch_groupbox = QtGui.QGroupBox(gettext("Branch"), self)
        branch_layout = QtGui.QGridLayout(branch_groupbox)
        self.branch_location = QtGui.QLineEdit()
        self.branch_location.setReadOnly(True)
        #
        branch_base = url_for_display(tree.branch.base)
        master_branch = url_for_display(tree.branch.get_bound_location())
        if not master_branch:
            self.branch_location.setText(branch_base)
            branch_layout.addWidget(self.branch_location)
        else:
            self.local_checkbox = QtGui.QCheckBox(gettext(
                "&Local commit"))
            self.local_checkbox.setToolTip(gettext(
                "Local commits are not pushed to the master branch "
                "until a normal commit is performed"))
            branch_layout.addWidget(self.local_checkbox, 0, 0, 1, 2)
            branch_layout.addWidget(self.branch_location, 1, 0, 1, 2)
            branch_layout.addWidget(QtGui.QLabel(gettext('Description:')), 2, 0,
                QtCore.Qt.AlignLeft | QtCore.Qt.AlignTop)
            self.commit_type_description = QtGui.QLabel()
            self.commit_type_description.setWordWrap(True)
            branch_layout.addWidget(self.commit_type_description, 2, 1)
            branch_layout.setColumnStretch(1,10)
            self.connect(self.local_checkbox,
                QtCore.SIGNAL("stateChanged(int)"),
                self.update_branch_groupbox)
            if local:
                self.local_checkbox.setChecked(True)
            self.update_branch_groupbox()

        splitter = QtGui.QSplitter(QtCore.Qt.Vertical, self)

        message_groupbox = QtGui.QGroupBox(gettext("Message"), splitter)
        splitter.addWidget(message_groupbox)
        self.tabWidget = QtGui.QTabWidget()
        splitter.addWidget(self.tabWidget)
        
        grid = QtGui.QGridLayout(message_groupbox)

        self.show_nonversioned_checkbox = QtGui.QCheckBox(
            gettext("Show non-versioned files"))

        self.filelist = WorkingTreeFileList(message_groupbox, self.tree)
        selectall_checkbox = QtGui.QCheckBox(
                                gettext(self.filelist.SELECTALL_MESSAGE))
        selectall_checkbox.setCheckState(QtCore.Qt.Checked)
        self.filelist.set_selectall_checkbox(selectall_checkbox)

        # Equivalent for 'bzr commit --message'
        self.message = TextEdit(message_groupbox, main_window=self)
        self.message.setToolTip(gettext("Enter the commit message"))
        self.completer = QtGui.QCompleter()
        self.message.setCompleter(self.completer)
        self.message.setAcceptRichText(False)

        language = get_global_config().get_user_option('spellcheck_language') or 'en'
        spell_checker = SpellChecker(language)
        spell_highlighter = SpellCheckHighlighter(self.message.document(), spell_checker)

        self.restore_message()
        if message:
            self.message.setText(message)
        grid.addWidget(self.message, 0, 0, 1, 2)

        # Equivalent for 'bzr commit --fixes'
        self.bugsCheckBox = QtGui.QCheckBox(gettext("&Fixed bugs:"))
        self.bugsCheckBox.setToolTip(gettext("Set the IDs of bugs fixed by "
                                     "this commit"))
        self.bugs = QtGui.QLineEdit()
        self.bugs.setToolTip(gettext("Enter the list of bug IDs in format "
                             "<i>tag:id</i> separated by a space, "
                             "e.g. <i>project:123 project:765</i>"))
        self.bugs.setEnabled(False)
        self.connect(self.bugsCheckBox, QtCore.SIGNAL("stateChanged(int)"),
                     self.enableBugs)
        grid.addWidget(self.bugsCheckBox, 1, 0)
        grid.addWidget(self.bugs, 1, 1)

        # Equivalent for 'bzr commit --author'
        self.authorCheckBox = QtGui.QCheckBox(gettext("&Author:"))
        self.authorCheckBox.setToolTip(gettext("Set the author of this change,"
            " if it's different from the committer"))
        self.author = QtGui.QLineEdit()
        self.author.setToolTip(gettext("Enter the author's name, "
            "e.g. <i>John Doe &lt;jdoe@example.com&gt;</i>"))
        self.author.setEnabled(False)
        self.connect(self.authorCheckBox, QtCore.SIGNAL("stateChanged(int)"),
                     self.enableAuthor)
        grid.addWidget(self.authorCheckBox, 2, 0)
        grid.addWidget(self.author, 2, 1)
        # default author from config
        config = self.tree.branch.get_config()
        self.default_author = config.username()
        self.custom_author = ''
        self.author.setText(self.default_author)

        # Display the list of changed files
        files_tab = QtGui.QWidget()
        self.tabWidget.addTab(files_tab, gettext("Changes"))

        vbox = QtGui.QVBoxLayout(files_tab)
        vbox.addWidget(self.filelist)
        self.connect(self.show_nonversioned_checkbox, QtCore.SIGNAL("toggled(bool)"), self.show_nonversioned)
        vbox.addWidget(self.show_nonversioned_checkbox)
    
        vbox.addWidget(selectall_checkbox)

        self.filelist.sortItems(0, QtCore.Qt.AscendingOrder)

        # Display a list of pending merges
        if self.has_pending_merges:
            selectall_checkbox.setCheckState(QtCore.Qt.Checked)
            selectall_checkbox.setEnabled(False)
            self.pending_merges_list = PendingMergesList(
                self.processEvents, self.throbber, False, self)
            
            self.tabWidget.addTab(self.pending_merges_list,
                                  gettext("Pending Merges"))
            self.tabWidget.setCurrentWidget(self.pending_merges_list)
            
            self.connect(self.pending_merges_list,
                QtCore.SIGNAL("itemDoubleClicked(QTreeWidgetItem *, int)"),
                self.show_changeset)
            # Pending-merge widget gets disabled as we are executing.
            QtCore.QObject.connect(self,
                                   QtCore.SIGNAL("subprocessStarted(bool)"),
                                   self.pending_merges_list,
                                   QtCore.SLOT("setDisabled(bool)"))
        else:
            self.pending_merges_list = False

        self.tabWidget.addTab(self.process_widget, gettext("Status"))

        splitter.setStretchFactor(0, 3)


        vbox = QtGui.QVBoxLayout(self.centralwidget)
        vbox.addWidget(self.throbber)
        vbox.addWidget(branch_groupbox)
        vbox.addWidget(splitter)

        # Diff button to view changes in files selected to commit
        self.diffbuttons = DiffButtons(self.centralwidget)
        self.diffbuttons.setToolTip(
            gettext("View changes in files selected to commit"))
        self.connect(self.diffbuttons, QtCore.SIGNAL("triggered(QString)"),
                     self.show_diff_for_checked)
        hbox = QtGui.QHBoxLayout()
        hbox.addWidget(self.diffbuttons)
        hbox.addWidget(self.buttonbox)
        vbox.addLayout(hbox)

        # groupbox and tabbox get disabled as we are executing.
        QtCore.QObject.connect(self,
                               QtCore.SIGNAL("subprocessStarted(bool)"),
                               message_groupbox,
                               QtCore.SLOT("setDisabled(bool)"))
        QtCore.QObject.connect(self,
                               QtCore.SIGNAL("subprocessStarted(bool)"),
                               files_tab,
                               QtCore.SLOT("setDisabled(bool)"))
        
        # Try to be smart: if there is no saved message
        # then set focus on Edit Area; otherwise on OK button.
        if self.get_saved_message():
            self.buttonbox.setFocus()
        else:
            self.message.setFocus()

    def show(self):
        # we show the bare form as soon as possible.
        SubProcessWindow.show(self)
        QtCore.QTimer.singleShot(1, self.load)
    
    @ui_current_widget
    @reports_exception()
    def load(self):
        self.tree.lock_read()
        try:
            if self.pending_merges_list:
                self.pending_merges_list.load_branch(self.tree.branch,
                                                     None,
                                                     self.tree)
                self.pending_merges_list.load()
            self.filelist.fill(self.iter_changes_and_state())
        finally:
            self.tree.unlock()
 
        self.filelist.setup_actions()        
        self.completer.setModel(QtGui.QStringListModel(self.completion_words,
                                                       self.completer))
        self.throbber.hide()
    
    def enableBugs(self, state):
        if state == QtCore.Qt.Checked:
            self.bugs.setEnabled(True)
            self.bugs.setFocus(QtCore.Qt.OtherFocusReason)
        else:
            self.bugs.setEnabled(False)

    def enableAuthor(self, state):
        if state == QtCore.Qt.Checked:
            self.author.setEnabled(True)
            self.author.setText(self.custom_author)
            self.author.setFocus(QtCore.Qt.OtherFocusReason)
        else:
            self.author.setEnabled(False)
            self.custom_author = self.author.text()
            self.author.setText(self.default_author)

    def get_saved_message(self):
        config = self.tree.branch.get_config()._get_branch_data_config()
        return config.get_user_option('qbzr_commit_message')

    def restore_message(self):
        message = self.get_saved_message()
        if message:
            self.message.setText(message)

    def save_message(self):
        if self.tree.branch.control_files.get_physical_lock_status() or \
           self.tree.branch.repository.control_files.get_physical_lock_status() or\
           self.tree.branch.is_locked() or self.tree.branch.repository.is_locked():
            from bzrlib.trace import warning
            warning("Cannot save commit message because the branch is locked.")
        else:
            message = unicode(self.message.toPlainText())
            config = self.tree.branch.get_config()
            if message.strip():
                config.set_user_option('qbzr_commit_message', message)
            else:
                if config.get_user_option('qbzr_commit_message'):
                    # FIXME this should delete the config entry, not just set it to ''
                    config.set_user_option('qbzr_commit_message', '')

    def clear_saved_message(self):
        config = self.tree.branch.get_config()
        # FIXME this should delete the config entry, not just set it to ''
        config.set_user_option('qbzr_commit_message', '')

    def start(self):
        args = ["commit"]
        files_to_add = ["add"]
        
        message = unicode(self.message.toPlainText()).strip() 
        if not message: 
            QtGui.QMessageBox.warning(self,
                "QBzr - " + gettext("Commit"),
                gettext("You should provide commit message."),
                gettext('&OK'))
            # don't commit, but don't close the window either
            self.failed()
            self.message.setFocus()
            return

        args.extend(['-m', message])    # keep them separated to avoid bug #297606
        
        # starts with one because if pending changes are available the warning box will appear each time.
        checkedFiles = 1 
        if not self.has_pending_merges:
            checkedFiles = 0
            for desc in self.filelist.iter_checked():
                checkedFiles = checkedFiles+1
                path = desc.path()
                if not desc.is_versioned():
                    files_to_add.append(path)
                args.append(path)
        
        if checkedFiles == 0: # BUG: 295116
            # check for availability of --exclude option for commit
            # (this option was introduced in bzr 1.6)
            from bzrlib.commands import get_cmd_object
            kmd = get_cmd_object('commit', False)
            if kmd.options().get('exclude', None) is None:
                # bzr < 1.6 -- sorry but we can't allow empty commit
                QtGui.QMessageBox.warning(self,
                    "QBzr - " + gettext("Commit"), 
                    gettext("No changes to commit."),
                    QtGui.QMessageBox.Ok) 
                self.failed()
                return
            else:
                # bzr >= 1.6
                button = QtGui.QMessageBox.question(self,
                    "QBzr - " + gettext("Commit"), 
                    gettext("No changes selected to commit.\n"
                        "Do you want to commit anyway?"),
                    QtGui.QMessageBox.Yes | QtGui.QMessageBox.No)
                if button == QtGui.QMessageBox.No:
                    self.failed()
                    return
                else:
                    # Possible [rare] problems:
                    # 1. unicode tree root in non-user encoding
                    #    may provoke UnicodeEncodeError in subprocess (@win32)
                    # 2. if branch has no commits yet then operation may fail
                    #    because of bug #299879
                    args.extend(['--exclude', self.tree.basedir])
                    args.append('--unchanged')

        if self.bugsCheckBox.isChecked():
            for s in unicode(self.bugs.text()).split():
                args.append(("--fixes=%s" % s))
        
        if self.authorCheckBox.isChecked():
            args.append(("--author=%s" % unicode(self.author.text())))
        
        if self.is_bound and self.local_checkbox.isChecked():
            args.append("--local")
        
        dir = self.tree.basedir
        commands = []
        if len(files_to_add)>1:
            commands.append((dir, files_to_add))
        commands.append((dir, args))

        self.tabWidget.setCurrentWidget(self.process_widget)
        self.process_widget.start_multi(commands)
    
    def show_changeset(self, item=None, column=None):
        new_revid = str(item.data(0, self.RevisionIdRole).toString())
        old_revid = str(item.data(0, self.ParentIdRole).toString())
        arg_provider = InternalDiffArgProvider(old_revid, new_revid,
                                               self.tree.branch,
                                               self.tree.branch)

        show_diff(arg_provider, parent_window = self)

    def show_nonversioned(self, state):
        """Show/hide non-versioned files."""
        state = not state
        for (tree_item, change_desc) in self.filelist.iter_treeitem_and_desc(True):
            if change_desc[3] == (False, False):
                self.filelist.set_item_hidden(tree_item, state)
        self.filelist.update_selectall_state(None, None)

    def closeEvent(self, event):
        if not self.process_widget.is_running():
            if self.process_widget.finished:
                self.clear_saved_message()
            else:
                self.save_message()
        return SubProcessWindow.closeEvent(self, event)

    def update_branch_groupbox(self):
        if not self.local_checkbox.isChecked():
            # commit to master branch selected
            loc = url_for_display(self.tree.branch.get_bound_location())
            desc = gettext("A commit will be made directly to "
                           "the master branch, keeping the local "
                           "and master branches in sync.")
        else:
            # local commit selected
            loc = url_for_display(self.tree.branch.base)
            desc = gettext("A local commit to the branch will be performed. "
                           "The master branch will not be updated until "
                           "a non-local commit is made.")
        # update GUI
        self.branch_location.setText(loc)
        self.commit_type_description.setText(desc)

    def show_diff_for_checked(self, ext_diff=None, dialog_action='commit'):
        """Diff button clicked: show the diff for checked entries.

        @param  ext_diff:       selected external diff tool (if any)
        @param  dialog_action:  purpose of parent window (main action)
        """
        # XXX make this function universal for both qcommit and qrevert (?)
        checked = []        # checked versioned
        unversioned = []    # checked unversioned (supposed to be added)
        for desc in self.filelist.iter_checked():
            path = desc.path()
            if desc.is_versioned():
                checked.append(path)
            else:
                unversioned.append(path)

        if checked:
            arg_provider = InternalWTDiffArgProvider(
                self.tree.basis_tree().get_revision_id(), self.tree,
                self.tree.branch, self.tree.branch,
                specific_files=checked)
            
            show_diff(arg_provider, ext_diff=ext_diff, parent_window = self)
        else:
            msg = "No changes selected to " + dialog_action
            QtGui.QMessageBox.warning(self,
                "QBzr - " + gettext("Diff"),
                gettext(msg),
                QtGui.QMessageBox.Ok)

        if unversioned:
            # XXX show infobox with message that not all files shown in diff
            pass
