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
from PyQt4 import QtCore, QtGui

from bzrlib.plugins.qbzr.lib.spellcheck import SpellCheckHighlighter, SpellChecker
from bzrlib.plugins.qbzr.lib.autocomplete import get_wordlist_builder
from bzrlib.plugins.qbzr.lib.commit_data import QBzrCommitData
from bzrlib.plugins.qbzr.lib.diff import (
    DiffButtons,
    show_diff,
    InternalWTDiffArgProvider,
    )
from bzrlib.plugins.qbzr.lib.i18n import gettext
from bzrlib.plugins.qbzr.lib.subprocess import SubProcessDialog
from bzrlib.plugins.qbzr.lib.util import (
    BTN_REFRESH,
    file_extension,
    get_global_config,
    url_for_display,
    ThrobberWidget,
    runs_in_loading_queue,
    StandardButton,
    )

from bzrlib.plugins.qbzr.lib.logwidget import LogList
from bzrlib.plugins.qbzr.lib import logmodel
from bzrlib.plugins.qbzr.lib.trace import *
from bzrlib.plugins.qbzr.lib.uifactory import ui_current_widget
from bzrlib.plugins.qbzr.lib.treewidget import (
    TreeWidget,
    SelectAllCheckBox,
    )
from bzrlib.plugins.qbzr.lib.trace import reports_exception
from bzrlib.plugins.qbzr.lib.revisionview import RevisionView


MAX_AUTOCOMPLETE_FILES = 20


class TextEdit(QtGui.QTextEdit):

    def __init__(self, spell_checker, parent=None, main_window=None):
        QtGui.QTextEdit.__init__(self, parent)
        self.completer = None
        self.spell_checker = spell_checker
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
                self.main_window.do_accept()
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

    def contextMenuEvent(self, event):
        menu = self.createStandardContextMenu(event.globalPos())
        
        self.context_tc = self.cursorForPosition(event.pos())
        self.context_tc.movePosition(QtGui.QTextCursor.StartOfWord)
        self.context_tc.movePosition(QtGui.QTextCursor.EndOfWord,
                                     QtGui.QTextCursor.KeepAnchor)
        text = unicode(self.context_tc.selectedText())
        if list(self.spell_checker.check(text)):
            suggestions = self.spell_checker.suggest(text)
            first_action = menu.actions()[0]
            for suggestion in suggestions:
                action = QtGui.QAction(suggestion, self)
                self.connect(action, QtCore.SIGNAL("triggered(bool)"),
                             self.suggestion_selected(suggestion))
                menu.insertAction(first_action, action)
            if suggestions:
                menu.insertSeparator(first_action)
        
        menu.exec_(event.globalPos())
        event.accept()
    
    def suggestion_selected(self, text):
        def _suggestion_selected(b):
            self.context_tc.insertText(text);
        return _suggestion_selected


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
            self.log_model.load_graph_pending_merges()
        finally:
            self.graph_provider.unlock_branches()

    def create_context_menu(self):
        super(PendingMergesList, self).create_context_menu()
        showinfo = QtGui.QAction("Show &infomation...", self)
        self.context_menu.insertAction(self.context_menu.actions()[0],
                                       showinfo)
        self.context_menu.setDefaultAction(showinfo)
        self.connect(showinfo,
                     QtCore.SIGNAL("triggered(bool)"),
                     self.show_info_menu)

    def show_info_menu(self, b=False):
        self.default_action()

    def default_action(self, index=None):
        """Show information of a single revision from a index."""
        
        if index is None:
            index = self.currentIndex()
        
        # XXX We should make this show all selected revsions...
        
        revid = str(index.data(logmodel.RevIdRole).toString())
        branch = self.graph_provider.get_revid_branch(revid)
        rev = self.graph_provider.load_revisions([revid])[revid]
        parent_window = self.window()
        window = RevisionView(rev, branch, parent=parent_window)
        window.show()
        parent_window.windows.append(window)
    

class CommitWindow(SubProcessDialog):

    RevisionIdRole = QtCore.Qt.UserRole + 1
    ParentIdRole = QtCore.Qt.UserRole + 2

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
        self.ci_data = QBzrCommitData(tree=tree)
        self.ci_data.load()

        self.is_bound = bool(tree.branch.get_bound_location())
        self.has_pending_merges = len(tree.get_parent_ids())>1
        
        if self.has_pending_merges and selected_list:
            raise errors.CannotCommitSelectedFileMerge(selected_list)
        
        self.windows = []
        self.initial_selected_list = selected_list

        self.connect(self.process_widget,
            QtCore.SIGNAL("failed()"),
            self.on_failed)

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

        self.filelist = TreeWidget(self)
        self.filelist.throbber = self.throbber
        self.filelist.tree_model.is_item_in_select_all = lambda item: (
            item.change is None or
            item.change.is_versioned())
        
        self.file_words = {}
        self.connect(self.filelist.tree_model,
                     QtCore.SIGNAL("dataChanged(QModelIndex, QModelIndex)"),
                     self.on_filelist_data_changed)
        
        selectall_checkbox = SelectAllCheckBox(self.filelist, self)
        selectall_checkbox.setCheckState(QtCore.Qt.Checked)

        language = get_global_config().get_user_option('spellcheck_language') or 'en'
        spell_checker = SpellChecker(language)
        
        # Equivalent for 'bzr commit --message'
        self.message = TextEdit(spell_checker, message_groupbox, main_window=self)
        self.message.setToolTip(gettext("Enter the commit message"))
        self.completer = QtGui.QCompleter()
        self.completer_model = QtGui.QStringListModel(self.completer)
        self.completer.setModel(self.completer_model)
        self.message.setCompleter(self.completer)
        self.message.setAcceptRichText(False)

        spell_highlighter = SpellCheckHighlighter(self.message.document(),
                                                  spell_checker)

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

        # Display a list of pending merges
        if self.has_pending_merges:
            selectall_checkbox.setCheckState(QtCore.Qt.Checked)
            selectall_checkbox.setEnabled(False)
            self.pending_merges_list = PendingMergesList(
                self.processEvents, self.throbber, False, self)
            
            self.tabWidget.addTab(self.pending_merges_list,
                                  gettext("Pending Merges"))
            self.tabWidget.setCurrentWidget(self.pending_merges_list)
            
            # Pending-merge widget gets disabled as we are executing.
            QtCore.QObject.connect(self,
                                   QtCore.SIGNAL("disableUi(bool)"),
                                   self.pending_merges_list,
                                   QtCore.SLOT("setDisabled(bool)"))
        else:
            self.pending_merges_list = False

        self.tabWidget.addTab(self.process_widget, gettext("Status"))

        splitter.setStretchFactor(0, 3)

        vbox = QtGui.QVBoxLayout(self)
        vbox.addWidget(self.throbber)
        vbox.addWidget(branch_groupbox)
        vbox.addWidget(splitter)

        # Diff button to view changes in files selected to commit
        self.diffbuttons = DiffButtons(self)
        self.diffbuttons.setToolTip(
            gettext("View changes in files selected to commit"))
        self.connect(self.diffbuttons, QtCore.SIGNAL("triggered(QString)"),
                     self.show_diff_for_checked)

        self.refresh_button = StandardButton(BTN_REFRESH)
        self.connect(self.refresh_button,
                     QtCore.SIGNAL("clicked()"),
                     self.refresh)

        hbox = QtGui.QHBoxLayout()
        hbox.addWidget(self.diffbuttons)
        hbox.addWidget(self.refresh_button)
        hbox.addWidget(self.buttonbox)
        vbox.addLayout(hbox)

        # groupbox and tabbox signals handling.
        for w in (message_groupbox, files_tab):
            # when operation started we need to disable widgets
            QtCore.QObject.connect(self,
                QtCore.SIGNAL("disableUi(bool)"),
                w,
                QtCore.SLOT("setDisabled(bool)"))

        self.restore_commit_data()
        if message:
            self.message.setText(message)

        # Try to be smart: if there is no saved message
        # then set focus on Edit Area; otherwise on OK button.
        if unicode(self.message.toPlainText()).strip():
            self.buttonbox.setFocus()
        else:
            self.message.setFocus()

    def show(self):
        # we show the bare form as soon as possible.
        SubProcessDialog.show(self)
        QtCore.QTimer.singleShot(1, self.load)

    @runs_in_loading_queue
    @ui_current_widget
    @reports_exception()
    def load(self, refresh=False):
        if refresh:
            self.throbber.show()
        self.refresh_button.setDisabled(True)
        try:
            self.tree.lock_read()
            try:
                if self.pending_merges_list:
                    self.pending_merges_list.load_branch(self.tree.branch,
                                                         None,
                                                         self.tree)
                    # Force the loading of the revisions, before we start
                    # loading the file list.
                    self.pending_merges_list._load_visible_revisions()
                    self.processEvents()
                
                self.filelist.tree_model.checkable = not self.pending_merges_list
                self.is_loading = True
                # XXX Would be nice if we could only load the files when the
                # user clicks on the changes tab, but that would mean that
                # we can't load the words list.
                if not refresh:
                    fmodel = self.filelist.tree_filter_model
                    #fmodel.setFilter(fmodel.UNVERSIONED, False)
                    self.filelist.set_tree(
                        self.tree,
                        branch=self.tree.branch,
                        changes_mode=True,
                        want_unversioned=self.show_nonversioned_checkbox.isChecked(),
                        initial_checked_paths=self.initial_selected_list,
                        change_load_filter=lambda c:not c.is_ignored())
                else:
                    self.filelist.refresh()
                self.is_loading = False
                self.processEvents()
                self.update_compleater_words()
            finally:
                self.tree.unlock()
        finally:
            self.throbber.hide()
            self.refresh_button.setDisabled(False)
    
    def refresh(self):
        self.load(True)

    def on_filelist_data_changed(self, start_index, end_index):
        self.update_compleater_words()
    
    def update_compleater_words(self):
        if self.is_loading:
            return
        
        num_files_loaded = 0
        
        words = set()
        for ref in self.filelist.tree_model.iter_checked():
            path = ref.path
            if path not in self.file_words:
                file_words = set()
                if num_files_loaded < MAX_AUTOCOMPLETE_FILES:
                    file_words.add(path)
                    file_words.add(os.path.split(path)[-1])
                    change = self.filelist.tree_model.inventory_data_by_path[
                                                               ref.path].change
                    if change and change.is_renamed():
                        file_words.add(change.oldpath())
                        file_words.add(os.path.split(change.oldpath())[-1])
                    #if num_versioned_files < MAX_AUTOCOMPLETE_FILES:
                    ext = file_extension(path)
                    builder = get_wordlist_builder(ext)
                    if builder is not None:
                        try:
                            abspath = os.path.join(self.tree.basedir, path)
                            file = open(abspath, 'rt')
                            file_words.update(builder.iter_words(file))
                            self.processEvents()
                        except EnvironmentError:
                            pass
                    self.file_words[path] = file_words
                    num_files_loaded += 1
            else:
                file_words = self.file_words[path]
            words.update(file_words)
        words = list(words)
        words.sort(key=lambda x: x.lower())
        self.completer_model.setStringList(words)
    
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

    def restore_commit_data(self):
        message = self.ci_data['message']
        if message:
            self.message.setText(message)
        bug = self.ci_data['bugs']
        if bug:
            self.bugs.setText(bug)
            self.bugs.setEnabled(True)
            self.bugsCheckBox.setChecked(True)

    def save_commit_data(self):
        if (self.tree.branch.control_files.get_physical_lock_status()
            or self.tree.branch.is_locked()):
            # XXX maybe show this in a GUI MessageBox (information box)???
            from bzrlib.trace import warning
            warning("Cannot save commit data because the branch is locked.")
            return
        # collect data
        ci_data = QBzrCommitData(tree=self.tree)
        message = unicode(self.message.toPlainText()).strip()
        if message:
            ci_data['message'] = message
        bug_str = ''
        if self.bugsCheckBox.isChecked():
            bug_str = unicode(self.bugs.text()).strip()
        if bug_str:
            ci_data['bugs'] = bug_str
        # save only if data different
        if not ci_data.compare_data(self.ci_data, all_keys=False):
            ci_data.save()

    def wipe_commit_data(self):
        if (self.tree.branch.control_files.get_physical_lock_status()
            or self.tree.branch.is_locked()):
            # XXX maybe show this in a GUI MessageBox (information box)???
            from bzrlib.trace import warning
            warning("Cannot wipe commit data because the branch is locked.")
            return
        self.ci_data.wipe()

    def do_start(self):
        args = ["commit"]
        files_to_add = ["add", "--no-recurse"]
        
        message = unicode(self.message.toPlainText()).strip() 
        if not message: 
            QtGui.QMessageBox.warning(self,
                "QBzr - " + gettext("Commit"),
                gettext("You should provide commit message."),
                gettext('&OK'))
            # don't commit, but don't close the window either
            self.on_failed()
            self.message.setFocus()
            return

        args.extend(['-m', message])    # keep them separated to avoid bug #297606
        
        # starts with one because if pending changes are available the warning box will appear each time.
        checkedFiles = 1 
        if not self.has_pending_merges:
            checkedFiles = 0
            for ref in self.filelist.tree_model.iter_checked():
                checkedFiles = checkedFiles+1
                if ref.file_id is None:
                    files_to_add.append(ref.path)
                args.append(ref.path)
        
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
                self.on_failed()
                return
            else:
                # bzr >= 1.6
                button = QtGui.QMessageBox.question(self,
                    "QBzr - " + gettext("Commit"), 
                    gettext("No changes selected to commit.\n"
                        "Do you want to commit anyway?"),
                    QtGui.QMessageBox.Yes | QtGui.QMessageBox.No)
                if button == QtGui.QMessageBox.No:
                    self.on_failed()
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

    def show_nonversioned(self, state):
        """Show/hide non-versioned files."""
        if state and not self.filelist.want_unversioned:
            state = self.filelist.get_state()
            self.filelist.set_tree(
                self.tree, changes_mode=True, want_unversioned=True,
                change_load_filter=lambda c:not c.is_ignored())
            self.filelist.restore_state(state)
        
        fmodel = self.filelist.tree_filter_model
        fmodel.setFilter(fmodel.UNVERSIONED, state)

    def _save_or_wipe_commit_data(self):
        if not self.process_widget.is_running():
            if self.process_widget.finished:
                self.wipe_commit_data()
            else:
                self.save_commit_data()

    def closeEvent(self, event):
        self._save_or_wipe_commit_data()
        return SubProcessDialog.closeEvent(self, event)

    def reject(self):
        self._save_or_wipe_commit_data()
        return SubProcessDialog.reject(self)

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
        for ref in self.filelist.tree_model.iter_checked():
            if ref.file_id:
                checked.append(ref.path)
            else:
                unversioned.append(ref.path)

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
