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
from PyQt5 import QtCore, QtGui, QtWidgets

from breezy.plugins.qbrz.lib.subprocess import SubProcessDialog
from breezy.plugins.qbrz.lib.util import (
    BTN_REFRESH,
    file_extension,
    get_global_config,
    get_qbrz_config,
    url_for_display,
    ThrobberWidget,
    runs_in_loading_queue,
    StandardButton,
    InfoWidget,
    )

from breezy.plugins.qbrz.lib.logwidget import LogList
from breezy.plugins.qbrz.lib.uifactory import ui_current_widget
from breezy.plugins.qbrz.lib.trace import reports_exception

from breezy import errors
from breezy.plugins.qbrz.lib.spellcheck import SpellCheckHighlighter, SpellChecker
from breezy.plugins.qbrz.lib.autocomplete import get_wordlist_builder
from breezy.plugins.qbrz.lib.commit_data import QBzrCommitData
from breezy.plugins.qbrz.lib.diff import (DiffButtons, show_diff, InternalWTDiffArgProvider)
from breezy.plugins.qbrz.lib.i18n import gettext
from breezy.plugins.qbrz.lib import logmodel
from breezy.plugins.qbrz.lib.loggraphviz import BranchInfo
from breezy.plugins.qbrz.lib.treewidget import (TreeWidget, SelectAllCheckBox, ChangeDescription, FilterModelKeys)
from breezy.plugins.qbrz.lib.revisionview import RevisionView
from breezy.plugins.qbrz.lib.update import QBzrUpdateWindow


MAX_AUTOCOMPLETE_FILES = 20


class TextEdit(QtWidgets.QTextEdit):
    messageEntered = QtCore.pyqtSignal()

    def __init__(self, spell_checker, parent=None, main_window=None):
        QtWidgets.QTextEdit.__init__(self, parent)
        # RJL The completer, I think, is to provide suggestions for anything typed
        self.context_tc = None
        self.completer = None
        self.spell_checker = spell_checker
        # RJL eow = 'end of word'?
        self.eow = "~!@#$%^&*()_+{}|:\"<>?,./;'[]\\-="
        self.main_window = main_window

    def inputMethodEvent(self, e):
        self.completer.popup().hide()
        QtWidgets.QTextEdit.inputMethodEvent(self, e)

    def keyPressEvent(self, e):
        c = self.completer
        e_key = e.key()
        if (e_key in (QtCore.Qt.Key_Tab, QtCore.Qt.Key_Backtab)
                or (c.popup().isVisible() and e_key in (QtCore.Qt.Key_Enter,
                                                        QtCore.Qt.Key_Return,
                                                        QtCore.Qt.Key_Escape))):
            e.ignore()
            return
        if (self.main_window and e_key in (QtCore.Qt.Key_Enter, QtCore.Qt.Key_Return)
                and (int(e.modifiers()) & QtCore.Qt.ControlModifier)):
            e.ignore()
            self.messageEntered.emit()
            return

        isShortcut = e.modifiers() & QtCore.Qt.ControlModifier and e.key() == QtCore.Qt.Key_E
        if not isShortcut:
            QtWidgets.QTextEdit.keyPressEvent(self, e)

        ctrlOrShift = e.modifiers() & (QtCore.Qt.ControlModifier | QtCore.Qt.ShiftModifier)
        if ctrlOrShift and not e.text():
            return

        hasModifier = (e.modifiers() != QtCore.Qt.NoModifier) and not ctrlOrShift
        completionPrefix = self.textUnderCursor()

        # RJL I *think* this is trying to find out whether to hide or display a list
        # of possible completions. right() is a QString method that:
        #
        #  Returns a substring that contains the n rightmost characters of the string.
        #  The entire string is returned if n is greater than size() or less than zero.
        #  QString x = "Pineapple";
        #  QString y = x.right(5);      // y == "apple"
        #
        # or simply x[-5:] in the land of Python, .right(1) is the last letter
        # which is e.text()[-1:]

        if not isShortcut and (hasModifier or not e.text() or len(completionPrefix) < 2 or e.text()[-1:] in self.eow):
            c.popup().hide()
            return

        if completionPrefix != c.completionPrefix():
            c.setCompletionPrefix(completionPrefix)
            c.popup().setCurrentIndex(c.completionModel().index(0, 0))

        cr = self.cursorRect()
        cr.setWidth(c.popup().sizeHintForColumn(0) + c.popup().verticalScrollBar().sizeHint().width())
        c.complete(cr)

    def textUnderCursor(self):
        tc = self.textCursor()
        tc.select(QtGui.QTextCursor.WordUnderCursor)
        return tc.selectedText()

    def insertCompletion(self, completion):
        tc = self.textCursor()
        extra = len(completion) - len(self.completer.completionPrefix())
        tc.movePosition(QtGui.QTextCursor.Left)
        tc.movePosition(QtGui.QTextCursor.EndOfWord)
        # We want the right-most 'extra' letters
        # tc.insertText(completion.right(extra))
        tc.insertText(completion[-extra:])
        self.setTextCursor(tc)

    def setCompleter(self, completer):
        self.completer = completer
        completer.setWidget(self)
        completer.setCaseSensitivity(QtCore.Qt.CaseSensitive)
        completer.activated['QString'].connect(self.insertCompletion)

    def contextMenuEvent(self, event):
        menu = self.createStandardContextMenu(event.globalPos())

        self.context_tc = self.cursorForPosition(event.pos())
        self.context_tc.movePosition(QtGui.QTextCursor.StartOfWord)
        self.context_tc.movePosition(QtGui.QTextCursor.EndOfWord, QtGui.QTextCursor.KeepAnchor)
        text = str(self.context_tc.selectedText())
        if list(self.spell_checker.check(text)):
            suggestions = self.spell_checker.suggest(text)
            first_action = menu.actions()[0]
            for suggestion in suggestions:
                action = QtWidgets.QAction(suggestion, self)
                action.triggered[bool].connect(self.suggestion_selected(suggestion))
                menu.insertAction(first_action, action)
            if suggestions:
                menu.insertSeparator(first_action)

        menu.exec_(event.globalPos())
        event.accept()

    def suggestion_selected(self, text):
        def _suggestion_selected(b):
            self.context_tc.insertText(text)
        return _suggestion_selected


class PendingMergesList(LogList):
    def __init__(self, *args, **kargs):
        super().__init__(*args, **kargs)
        # The rev numbers are currently bogus. Hide that column.
        # We could work out the revision numbers by loading whole graph, but
        # that is going to make this much slower.
        self.header().hideSection(0)
        self.log_model.last_rev_is_placeholder = True

    def load_tree(self, tree):
        bi = BranchInfo('', tree, tree.branch)
        self.log_model.load((bi,), bi, None, False, logmodel.PendingMergesGraphVizLoader)

    def create_context_menu(self, file_ids):
        super().create_context_menu(file_ids)
        showinfo = QtWidgets.QAction("Show &information...", self)
        self.context_menu.insertAction(self.context_menu.actions()[0], showinfo)
        self.context_menu.setDefaultAction(showinfo)
        showinfo.triggered[bool].connect(self.show_info_menu)

    def show_info_menu(self, b=False):
        self.default_action()

    def default_action(self, index=None):
        """Show information of a single revision from a index."""

        if index is None:
            index = self.currentIndex()

        # XXX We should make this show all selected revisions...

        revid = index.data(logmodel.RevIdRole)
        branch = self.log_model.graph_viz.get_revid_branch(revid)
        parent_window = self.window()
        window = RevisionView(revid, branch, parent=parent_window)
        window.show()
        parent_window.windows.append(window)


def ignore_pattern_handler(change_description: ChangeDescription):
    return not change_description.ignored_pattern()


class CommitWindow(SubProcessDialog):

    RevisionIdRole = QtCore.Qt.UserRole + 1
    ParentIdRole = QtCore.Qt.UserRole + 2

    def __init__(self, tree, selected_list, dialog=True, parent=None, local=None, message=None, ui_mode=True):
        super().__init__(gettext("Commit"), name="commit", default_size=(540, 540),
                         ui_mode=ui_mode, dialog=dialog, parent=parent)
        self.is_loading = False
        self.tree = tree
        self.ci_data = QBzrCommitData(tree=tree)
        self.ci_data.load()

        self.is_bound = bool(tree.branch.get_bound_location())
        self.has_pending_merges = len(tree.get_parent_ids()) > 1

        if self.has_pending_merges and selected_list:
            raise errors.CannotCommitSelectedFileMerge(selected_list)

        self.windows = []
        self.initial_selected_list = selected_list

        self.process_widget.failed['QString'].connect(self.on_failed)

        self.throbber = ThrobberWidget(self)

        # commit to branch location
        branch_groupbox = QtWidgets.QGroupBox(gettext("Branch"), self)
        branch_layout = QtWidgets.QGridLayout(branch_groupbox)
        self.branch_location = QtWidgets.QLineEdit()
        self.branch_location.setReadOnly(True)
        #
        branch_base = url_for_display(tree.branch.base)
        master_branch = url_for_display(tree.branch.get_bound_location())
        if not master_branch:
            self.branch_location.setText(branch_base)
            branch_layout.addWidget(self.branch_location, 0, 0, 1, 2)
        else:
            self.local_checkbox = QtWidgets.QCheckBox(gettext("&Local commit"))
            self.local_checkbox.setToolTip(gettext("Local commits are not pushed to the master branch until a normal commit is performed"))
            branch_layout.addWidget(self.local_checkbox, 0, 0, 1, 2)
            branch_layout.addWidget(self.branch_location, 1, 0, 1, 2)
            branch_layout.addWidget(QtWidgets.QLabel(gettext('Description:')), 2, 0, QtCore.Qt.AlignLeft | QtCore.Qt.AlignTop)
            self.commit_type_description = QtWidgets.QLabel()
            self.commit_type_description.setWordWrap(True)
            branch_layout.addWidget(self.commit_type_description, 2, 1)
            branch_layout.setColumnStretch(1,10)
            self.local_checkbox.stateChanged[int].connect(self.update_branch_groupbox)
            if local:
                self.local_checkbox.setChecked(True)
            self.update_branch_groupbox()

        self.not_uptodate_errors = {
            'BoundBranchOutOfDate': gettext(
                'Local branch is out of date with master branch.\n'
                'To commit to master branch, update the local branch.\n'
                'You can also pass select local to commit to continue working disconnected.'),
            'OutOfDateTree': gettext('Working tree is out of date. To commit, update the working tree.')
            }
        self.not_uptodate_info = InfoWidget(branch_groupbox)
        not_uptodate_layout = QtWidgets.QHBoxLayout(self.not_uptodate_info)

        # XXX this is to big. Resize
        not_uptodate_icon = QtWidgets.QLabel()
        not_uptodate_icon.setPixmap(self.style().standardPixmap(QtWidgets.QStyle.SP_MessageBoxWarning))
        not_uptodate_layout.addWidget(not_uptodate_icon)

        self.not_uptodate_label = QtWidgets.QLabel('error message goes here')
        not_uptodate_layout.addWidget(self.not_uptodate_label, 2)

        update_button = QtWidgets.QPushButton(gettext('Update'))
        update_button.clicked[bool].connect(self.open_update_win)

        not_uptodate_layout.addWidget(update_button)

        self.not_uptodate_info.hide()
        branch_layout.addWidget(self.not_uptodate_info, 3, 0, 1, 2)

        splitter = QtWidgets.QSplitter(QtCore.Qt.Vertical, self)

        message_groupbox = QtWidgets.QGroupBox(gettext("Message"), splitter)
        splitter.addWidget(message_groupbox)
        self.tabWidget = QtWidgets.QTabWidget()
        splitter.addWidget(self.tabWidget)
        splitter.setStretchFactor(0, 1)
        splitter.setStretchFactor(1, 8)

        grid = QtWidgets.QGridLayout(message_groupbox)

        self.show_nonversioned_checkbox = QtWidgets.QCheckBox(gettext("Show non-versioned files"))
        show_nonversioned = get_qbrz_config().get_option_as_bool(self._window_name + "_show_nonversioned")
        if show_nonversioned:
            self.show_nonversioned_checkbox.setChecked(True)
        else:
            self.show_nonversioned_checkbox.setChecked(False)

        self.filelist_widget = TreeWidget(self)
        self.filelist_widget.throbber = self.throbber
        if show_nonversioned:
            self.filelist_widget.tree_model.set_select_all_kind('all')
        else:
            self.filelist_widget.tree_model.set_select_all_kind('versioned')

        self.file_words = {}
        self.filelist_widget.tree_model.dataChanged[QtCore.QModelIndex, QtCore.QModelIndex].connect(self.on_filelist_data_changed)

        self.selectall_checkbox = SelectAllCheckBox(self.filelist_widget, self)
        self.selectall_checkbox.setCheckState(QtCore.Qt.Checked)

        language = get_global_config().get_user_option('spellcheck_language') or 'en'
        spell_checker = SpellChecker(language)

        # Equivalent for 'bzr commit --message'
        self.message = TextEdit(spell_checker, message_groupbox, main_window=self)
        self.message.setToolTip(gettext("Enter the commit message"))
        self.message.messageEntered.connect(self.do_accept)
        self.completer = QtWidgets.QCompleter()
        self.completer_model = QtCore.QStringListModel(self.completer)
        self.completer.setModel(self.completer_model)
        self.message.setCompleter(self.completer)
        self.message.setAcceptRichText(False)

        SpellCheckHighlighter(self.message.document(), spell_checker)

        grid.addWidget(self.message, 0, 0, 1, 2)

        # Equivalent for 'bzr commit --fixes'
        self.bugsCheckBox = QtWidgets.QCheckBox(gettext("&Fixed bugs:"))
        self.bugsCheckBox.setToolTip(gettext("Set the IDs of bugs fixed by this commit"))
        self.bugs = QtWidgets.QLineEdit()
        self.bugs.setToolTip(gettext("Enter the list of bug IDs in format "
                             "<i>tag:id</i> separated by a space, "
                             "e.g. <i>project:123 project:765</i>"))
        self.bugs.setEnabled(False)
        self.bugsCheckBox.stateChanged[int].connect(self.enableBugs)
        grid.addWidget(self.bugsCheckBox, 1, 0)
        grid.addWidget(self.bugs, 1, 1)

        # Equivalent for 'bzr commit --author'
        self.authorCheckBox = QtWidgets.QCheckBox(gettext("&Author:"))
        self.authorCheckBox.setToolTip(gettext("Set the author of this change,"
            " if it's different from the committer"))
        self.author = QtWidgets.QLineEdit()
        self.author.setToolTip(gettext("Enter the author's name, "
            "e.g. <i>John Doe &lt;jdoe@example.com&gt;</i>"))
        self.author.setEnabled(False)
        self.authorCheckBox.stateChanged[int].connect(self.enableAuthor)
        grid.addWidget(self.authorCheckBox, 2, 0)
        grid.addWidget(self.author, 2, 1)
        # default author from config
        config = self.tree.branch.get_config()
        self.default_author = config.username()
        self.custom_author = ''
        self.author.setText(self.default_author)

        # Display the list of changed files
        files_tab = QtWidgets.QWidget()
        self.tabWidget.addTab(files_tab, gettext("Changes"))

        vbox = QtWidgets.QVBoxLayout(files_tab)
        vbox.addWidget(self.filelist_widget)
        self.show_nonversioned_checkbox.toggled[bool].connect(self.show_nonversioned)
        vbox.addWidget(self.show_nonversioned_checkbox)
        vbox.addWidget(self.selectall_checkbox)

        # Display a list of pending merges
        if self.has_pending_merges:
            self.selectall_checkbox.setCheckState(QtCore.Qt.Checked)
            self.selectall_checkbox.setEnabled(False)
            self.pending_merges_list = PendingMergesList(self.processEvents, self.throbber, self)
            self.tabWidget.addTab(self.pending_merges_list,gettext("Pending Merges"))
            self.tabWidget.setCurrentWidget(self.pending_merges_list)
            # Pending-merge widget gets disabled as we are executing.
            self.disableUi[bool].connect(self.pending_merges_list.setDisabled)
        else:
            self.pending_merges_list = None

        self.process_panel = self.make_process_panel()
        self.tabWidget.addTab(self.process_panel, gettext("Status"))

        splitter.setStretchFactor(0, 3)

        vbox = QtWidgets.QVBoxLayout(self)
        vbox.addWidget(self.throbber)
        vbox.addWidget(branch_groupbox)
        vbox.addWidget(splitter)

        # Diff button to view changes in files selected to commit
        self.diffbuttons = DiffButtons(self)
        self.diffbuttons.setToolTip(gettext("View changes in files selected to commit"))
        self.diffbuttons._triggered['QString'].connect(self.show_diff_for_checked)

        self.refresh_button = StandardButton(BTN_REFRESH)
        self.refresh_button.clicked.connect(self.refresh)

        hbox = QtWidgets.QHBoxLayout()
        hbox.addWidget(self.diffbuttons)
        hbox.addWidget(self.refresh_button)
        hbox.addWidget(self.buttonbox)
        vbox.addLayout(hbox)

        # groupbox and tabbox signals handling.
        for w in (message_groupbox, files_tab):
            # when operation started we need to disable widgets
            self.disableUi[bool].connect(w.setDisabled)

        self.restore_commit_data()
        if message:
            self.message.setText(message)

        # Try to be smart: if there is no saved message
        # then set focus on Edit Area; otherwise on OK button.
        if str(self.message.toPlainText()).strip():
            self.buttonbox.setFocus()
        else:
            self.message.setFocus()

    def show(self):
        # we show the bare form as soon as possible.
        SubProcessDialog.show(self)
        # QtCore.QTimer.singleShot(1, self.load)
        self.load()

    def exec_(self):
        # QtCore.QTimer.singleShot(1, self.load)
        self.load()
        return SubProcessDialog.exec_(self)

    @runs_in_loading_queue
    @ui_current_widget
    @reports_exception()
    def load(self, refresh=False):
        if refresh:
            self.throbber.show()
        self.refresh_button.setDisabled(True)
        try:
            with self.tree.lock_read():
                if self.pending_merges_list:
                    self.pending_merges_list.load_tree(self.tree)
                    # Force the loading of the revisions, before we start
                    # loading the file list.
                    self.pending_merges_list._load_visible_revisions()
                    self.processEvents()

                # filelist_widget is actually a TreeWidget and its model will be a TreeModel
                self.filelist_widget.tree_model.checkable = not self.pending_merges_list
                self.is_loading = True
                # XXX Would be nice if we could only load the files when the
                # user clicks on the changes tab, but that would mean that
                # we can't load the words list.
                if not refresh:
                    want_unversioned = self.show_nonversioned_checkbox.isChecked()
                    self.filelist_widget.tree_filter_model.setFilter(FilterModelKeys.UNVERSIONED, want_unversioned)

                    if not want_unversioned and self.initial_selected_list:
                        # if there are any paths from the command line that are not versioned, we want_unversioned.
                        for path in self.initial_selected_list:
                            if not self.tree.is_versioned(path):
                                want_unversioned = True
                                break

                    # Now we call our old pal, TreeWidget::set_tree which goes away and calls TreeModel::set_tree
                    self.filelist_widget.set_tree(self.tree, branch=self.tree.branch, changes_mode=True,
                                                  want_unversioned=want_unversioned,
                                                  initial_checked_paths=self.initial_selected_list,
                                                  change_load_filter=ignore_pattern_handler)
                else:
                    self.filelist_widget.refresh()
                self.is_loading = False
                self.processEvents()
                self.update_compleater_words()
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
        for ref in self.filelist_widget.tree_model.iter_checked():
            path = ref.path
            if path not in self.file_words:
                file_words = set()
                if num_files_loaded < MAX_AUTOCOMPLETE_FILES:
                    file_words.add(path)
                    file_words.add(os.path.split(path)[-1])
                    change = self.filelist_widget.tree_model.inventory_data_by_path[ref.path].change
                    if change and change.is_renamed():
                        file_words.add(change.oldpath())
                        file_words.add(os.path.split(change.oldpath())[-1])
                    # if num_versioned_files < MAX_AUTOCOMPLETE_FILES:
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
        if self.tree.branch.get_physical_lock_status() or self.tree.branch.is_locked():
            # XXX maybe show this in a GUI MessageBox (information box)???
            from breezy.trace import warning
            warning("Cannot save commit data because the branch is locked.")
            return
        # collect data
        ci_data = QBzrCommitData(tree=self.tree)
        message = str(self.message.toPlainText()).strip()
        if message:
            ci_data['message'] = message
        bug_str = ''
        if self.bugsCheckBox.isChecked():
            bug_str = str(self.bugs.text()).strip()
        if bug_str:
            ci_data['bugs'] = bug_str
        # save only if data different
        if not ci_data.compare_data(self.ci_data, all_keys=False):
            ci_data.save()

    def wipe_commit_data(self):
        if self.tree.branch.get_physical_lock_status() or self.tree.branch.is_locked():
            # XXX maybe show this in a GUI MessageBox (information box)???
            from breezy.trace import warning
            warning("Cannot wipe commit data because the branch is locked.")
            return
        self.ci_data.wipe()

    def _get_message(self):
        return str(self.message.toPlainText()).strip()

    def _get_selected_files(self):
        """Return (has_files_to_commit[bool], files_to_commit[list], files_to_add[list])"""
        if self.has_pending_merges:
            return True, [], []

        files_to_commit = []
        files_to_add = []
        for ref in self.filelist_widget.tree_model.iter_checked():
            if ref.file_id is None:
                files_to_add.append(ref.path)
            files_to_commit.append(ref.path)

        if not files_to_commit:
            return False, [], []
        else:
            return True, files_to_commit, files_to_add

    def validate(self):
        if not self._get_message():
            self.operation_blocked(gettext("You should provide a commit message."))
            self.message.setFocus()
            return False
        if not self._get_selected_files()[0]:
            if not self.ask_confirmation(gettext("No changes selected to commit.\nDo you want to commit anyway?")):
                return False
        return True

    def do_start(self):
        args = ["commit"]
        message = self._get_message()
        # AND we need to quote it...
        args.extend(['-m', message])    # keep them separated to avoid bug #297606

        has_files_to_commit, files_to_commit, files_to_add = self._get_selected_files()
        if not has_files_to_commit:
            # Possible [rare] problems:
            # 1. unicode tree root in non-user encoding
            #    may provoke UnicodeEncodeError in subprocess (@win32)
            # 2. if branch has no commits yet then operation may fail
            #    because of bug #299879
            args.extend(['--exclude', self.tree.basedir])
            args.append('--unchanged')
        else:
            args.extend(files_to_commit)

        if self.bugsCheckBox.isChecked():
            for s in str(self.bugs.text()).split():
                args.append(("--fixes=%s" % s))

        if self.authorCheckBox.isChecked():
            args.append(("--author=%s" % str(self.author.text())))

        if self.is_bound and self.local_checkbox.isChecked():
            args.append("--local")

        base_directory = self.tree.basedir
        commands = []
        if files_to_add:
            commands.append((base_directory, ["add", "--no-recurse"] + files_to_add))
        commands.append((base_directory, args))

        self.tabWidget.setCurrentWidget(self.process_panel)
        self.process_widget.start_multi(commands)

    def show_nonversioned(self, state):
        """Show/hide non-versioned files."""
        if state and not self.filelist_widget.want_unversioned:
            state = self.filelist_widget.get_state()
            # RJLRJL: might need to set initial_checked_paths here
            self.filelist_widget.set_tree(self.tree, changes_mode=True, want_unversioned=True, change_load_filter=ignore_pattern_handler)
            self.filelist_widget.restore_state(state)
        if state:
            self.filelist_widget.tree_model.set_select_all_kind('all')
        else:
            self.filelist_widget.tree_model.set_select_all_kind('versioned')
        self.filelist_widget.tree_filter_model.setFilter(FilterModelKeys.UNVERSIONED, state)

    def _save_or_wipe_commit_data(self):
        if not self.process_widget.is_running():
            if self.process_widget.is_finished:
                self.wipe_commit_data()
            else:
                self.save_commit_data()

    def closeEvent(self, event):
        self._save_or_wipe_commit_data()
        qbrz_config = get_qbrz_config()
        qbrz_config.set_option(self._window_name + "_show_nonversioned", self.show_nonversioned_checkbox.isChecked())
        qbrz_config.save()  # do I need this or is .saveSize() enough?
        return SubProcessDialog.closeEvent(self, event)

    def reject(self):
        self._save_or_wipe_commit_data()
        return SubProcessDialog.reject(self)

    def update_branch_groupbox(self):
        if not self.local_checkbox.isChecked():
            # commit to master branch selected
            loc = url_for_display(self.tree.branch.get_bound_location())
            desc = gettext("A commit will be made directly to the master branch, keeping the local and master branches in sync.")
        else:
            # local commit selected
            loc = url_for_display(self.tree.branch.base)
            desc = gettext("A local commit to the branch will be performed. The master branch will not be updated until "
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
        if self.filelist_widget.tree_model.checkable:
            checked = []        # checked versioned
            unversioned = []    # checked unversioned (supposed to be added)
            for ref in self.filelist_widget.tree_model.iter_checked():
                if ref.file_id:
                    checked.append(ref.path)
                else:
                    unversioned.append(ref.path)

            if checked:
                arg_provider = InternalWTDiffArgProvider(
                    self.tree.basis_tree().get_revision_id(), self.tree,
                    self.tree.branch, self.tree.branch,
                    specific_files=checked)

                show_diff(arg_provider, ext_diff=ext_diff, parent_window=self, context=self.filelist_widget.diff_context)
            else:
                msg = "No changes selected to " + dialog_action
                QtWidgets.QMessageBox.warning(self, "QBrz - " + gettext("Diff"), gettext(msg), QtWidgets.QMessageBox.Ok)

            if unversioned:
                # XXX show infobox with message that not all files shown in diff
                pass
        else:
            arg_provider = InternalWTDiffArgProvider(self.tree.basis_tree().get_revision_id(), self.tree, self.tree.branch, self.tree.branch)
            show_diff(arg_provider, ext_diff=ext_diff, parent_window=self, context=self.filelist_widget.diff_context)

    def on_failed(self, error):
        SubProcessDialog.on_failed(self, error)
        error = str(error)
        if error in self.not_uptodate_errors:
            self.not_uptodate_label.setText(self.not_uptodate_errors[error])
            self.not_uptodate_info.show()

    def open_update_win(self, b):
        update_window = QBzrUpdateWindow(self.tree)
        self.windows.append(update_window)
        update_window.show()
        update_window.subprocessFinished[bool].connect(self.not_uptodate_info.setHidden)
