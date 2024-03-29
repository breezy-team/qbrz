# -*- coding: utf-8 -*-
#
# QBzr - Qt frontend to Bazaar commands
# Copyright (C) 2006-2007 Lukáš Lalinský <lalinsky@gmail.com>
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

from PyQt5 import QtCore, QtGui, QtWidgets

from breezy.revision import CURRENT_REVISION

from breezy.plugins.qbrz.lib.util import (
    BTN_CLOSE,
    BTN_REFRESH,
    QBzrWindow,
    ThrobberWidget,
    StandardButton,
    url_for_display,
    runs_in_loading_queue,
    get_set_encoding,
    )
from breezy.plugins.qbrz.lib.trace import reports_exception
from breezy.plugins.qbrz.lib.uifactory import ui_current_widget
from breezy.plugins.qbrz.lib.loggraphviz import GhostRevisionError

import re

from breezy import errors
from breezy import osutils
from breezy.controldir import ControlDir
from breezy.urlutils import determine_relative_path, join, split

from breezy.plugins.qbrz.lib.logwidget import LogList
from breezy.plugins.qbrz.lib import logmodel
from breezy.plugins.qbrz.lib.loggraphviz import BranchInfo

from breezy.plugins.qbrz.lib.diff import has_ext_diff, ExtDiffMenu, DiffButtons
from breezy.plugins.qbrz.lib.i18n import gettext
from breezy.plugins.qbrz.lib.revisionmessagebrowser import LogListRevisionMessageBrowser
from breezy.plugins.qbrz.lib.cat import QBzrCatWindow
from breezy.plugins.qbrz.lib.annotate import AnnotateWindow


QStringList = list

PathRole    = QtCore.Qt.UserRole + 1
file_idRole = QtCore.Qt.UserRole + 2
AliveRole   = QtCore.Qt.UserRole + 3

have_search = None


class Compleater(QtWidgets.QCompleter):
    def splitPath(self, path):
        return QStringList([path.split(" ")[-1]])


class LogWindow(QBzrWindow):

    FilterIdRole = QtCore.Qt.UserRole + 100
    FilterMessageRole = QtCore.Qt.UserRole + 101
    FilterAuthorRole = QtCore.Qt.UserRole + 102
    FilterRevnoRole = QtCore.Qt.UserRole + 103
    FilterSearchRole = QtCore.Qt.UserRole + 104
    FilterTagRole = QtCore.Qt.UserRole + 105
    FilterBugRole = QtCore.Qt.UserRole + 106

    def __init__(self, locations=None,
                 branch=None, tree=None, specific_file_ids=None,
                 parent=None, ui_mode=True, no_graph=False,
                 show_trees=False):
        """Create qlog window.

        Note: you must use either locations or branch+tree+specific_file_id
        arguments, but not both.

        @param  locations:  list of locations to show log
            (either list of URL/paths for several branches,
            or list of filenames from one branch).
            This list used when branch argument is None.

        @param  branch: branch object to show the log.
            Could be None, in this case locations list will be used
            to open branch(es).

        @param  specific_file_ids:    file ids from the branch to filter
            the log.

        @param  parent: parent widget.

        @param  ui_mode:    for compatibility with TortoiseBzr.

        @param  no_graph:   don't show the graph of revisions (make sense
            for `bzr qlog FILE` to force plain log a-la `bzr log`).
        """
        self.title = gettext("Log")
        QBzrWindow.__init__(self, [self.title], parent, ui_mode=ui_mode)
        self.restoreSize("log", (710, 580))

        self.no_graph = no_graph
        self.show_trees = show_trees
        if branch:
            self.branch = branch
            self.tree = tree
            self.locations = (branch,)
            self.specific_file_ids = specific_file_ids
            assert locations is None, "can't specify both branch and locations"
        else:
            self.branch = None
            self.locations = locations
            # if self.locations is None:
            #    self.locations = [u"."]
            assert specific_file_ids is None, "specific_file_ids is ignored if branch is None"

        self.branches = None
        self.replace = {}

        self.throbber = ThrobberWidget(self)

        logwidget = QtWidgets.QWidget()
        logbox = QtWidgets.QVBoxLayout(logwidget)
        logbox.setContentsMargins(0, 0, 0, 0)

        searchbox = QtWidgets.QHBoxLayout()

        self.search_label = QtWidgets.QLabel(gettext("&Search:"))
        self.search_edit = QtWidgets.QLineEdit()
        self.search_label.setBuddy(self.search_edit)
        self.search_edit.textEdited['QString'].connect(self.set_search_timer)

        self.search_timer = QtCore.QTimer(self)
        self.search_timer.setSingleShot(True)
        self.search_timer.timeout.connect(self.update_search)

        searchbox.addWidget(self.search_label)
        searchbox.addWidget(self.search_edit)

        self.searchType = QtWidgets.QComboBox()

        self.searchType.addItem(gettext("Messages"), self.FilterMessageRole)
        self.searchType.addItem(gettext("Authors"), self.FilterAuthorRole)
        self.searchType.addItem(gettext("Revision IDs"), self.FilterIdRole)
        self.searchType.addItem(gettext("Revision Numbers"), self.FilterRevnoRole)
        self.searchType.addItem(gettext("Tags"), self.FilterTagRole)
        self.searchType.addItem(gettext("Bugs"), self.FilterBugRole)
        searchbox.addWidget(self.searchType)
        self.searchType.currentIndexChanged[int].connect(self.updateSearchType)

        logbox.addLayout(searchbox)

        self.log_list = LogList(self.processEvents, self.throbber, self, action_commands=True)

        logbox.addWidget(self.throbber)
        logbox.addWidget(self.log_list)

        self.current_rev = None

        self.message = QtGui.QTextDocument()
        self.message_browser = LogListRevisionMessageBrowser(self.log_list, self)
        self.message_browser.setDocument(self.message)

        self.file_list_container = FileListContainer(self.log_list, self)
        self.log_list.selectionModel().selectionChanged[QtCore.QItemSelection,
            QtCore.QItemSelection].connect(self.file_list_container.revision_selection_changed)

        hsplitter = QtWidgets.QSplitter(QtCore.Qt.Horizontal)
        hsplitter.addWidget(self.message_browser)
        hsplitter.addWidget(self.file_list_container)
        hsplitter.setStretchFactor(0, 3)
        hsplitter.setStretchFactor(1, 1)

        splitter = QtWidgets.QSplitter(QtCore.Qt.Vertical)
        splitter.addWidget(logwidget)
        splitter.addWidget(hsplitter)
        splitter.setStretchFactor(0, 5)
        splitter.setStretchFactor(1, 3)

        buttonbox = self.create_button_box(BTN_CLOSE)
        self.refresh_button = StandardButton(BTN_REFRESH)
        buttonbox.addButton(self.refresh_button, QtWidgets.QDialogButtonBox.ActionRole)
        self.refresh_button.clicked.connect(self.refresh)

        self.diffbuttons = DiffButtons(self.centralwidget)
        self.diffbuttons.setEnabled(False)
        self.diffbuttons._triggered['QString'].connect(self.log_list.show_diff_specified_files_ext)

        vbox = QtWidgets.QVBoxLayout(self.centralwidget)
        vbox.addWidget(splitter)
        hbox = QtWidgets.QHBoxLayout()
        hbox.addWidget(self.diffbuttons)
        hbox.addWidget(buttonbox)
        vbox.addLayout(hbox)
        self.windows = []
        # set focus on search edit widget
        self.log_list.setFocus()

    @ui_current_widget
    @reports_exception()
    def load(self):
        self.refresh_button.setDisabled(True)
        self.throbber.show()
        self.processEvents()
        try:
            # Set window title.
            lt = self._locations_for_title(self.locations)
            if lt:
                self.set_title((self.title, lt))

            branches, primary_bi, file_ids = self.get_branches_and_file_ids()
            if self.show_trees:
                gz_cls = logmodel.WithWorkingTreeGraphVizLoader
            else:
                gz_cls = logmodel.GraphVizLoader

            self.log_list.load(branches, primary_bi, file_ids, self.no_graph, gz_cls)
            self.log_list.selectionModel().selectionChanged[QtCore.QItemSelection, QtCore.QItemSelection].connect(self.update_selection)
            self.load_search_indexes(branches)
        finally:
            self.refresh_button.setDisabled(False)
            self.throbber.hide()
            self.processEvents()

    def get_branches_and_file_ids(self):
        if self.branch:
            if self.tree is None:
                try:
                    self.tree = self.branch.controldir.open_workingtree()
                except (errors.NoWorkingTree, errors.NotLocalUrl):
                    pass
            label = self.branch_label(None, self.branch)
            bi = BranchInfo(label, self.tree, self.branch)
            return [bi], bi, self.specific_file_ids
        else:
            primary_bi = None
            branches = set()
            file_ids = []
            if self.locations is not None:
                locations = self.locations
            else:
                locations = ['.']

            # Branch names that indicated primary branch.
            # TODO: Make config option.
            primary_branch_names = ('trunk', 'bzr.dev')

            for location in locations:
                tree, br, repo, fp = ControlDir.open_containing_tree_branch_or_repository(location)
                self.processEvents()

                if br is None:
                    if fp:
                        raise errors.NotBranchError(fp)

                    #  RJLRJL: bzr-3.1
                    # * ``Repository.find_branches`` now returns an iterator rather than a
                    # list. (Jelmer Vernooĳ, #413970)
                    repo_branches = list(repo.find_branches(using=True))
                    if not repo_branches:
                        raise errors.NotBranchError(fp)

                    for br in repo_branches:
                        self.processEvents()
                        try:
                            tree = br.controldir.open_workingtree()
                            self.processEvents()
                        except errors.NoWorkingTree:
                            tree = None
                        label = self.branch_label(None, br, location, repo)
                        bi = BranchInfo(label, tree, br)
                        branches.add(bi)
                        if not primary_bi and br.nick in primary_branch_names:
                            primary_bi = bi
                else:
                    if len(locations) > 1:
                        label = self.branch_label(location, br)
                    else:
                        label = None
                    bi = BranchInfo(label, tree, br)
                    if len(branches) == 0:
                        # The first sepecified branch becomes the primary
                        # branch.
                        primary_bi = bi
                    branches.add(bi)

                # If no locations were sepecified, don't do fileids
                # Otherwise it gives you the history for the dir if you are
                # in a sub dir.
                if fp != '' and self.locations is None:
                    fp = ''

                if fp != '':
                    # TODO: Have a way to specify a revision to find to file
                    # path in, so that one can show deleted files.
                    if tree is None:
                        tree = br.basis_tree()

                    file_id = tree.path2id(fp)
                    if file_id is None:
                        raise errors.BzrCommandError("Path does not have any revision history: %s" % location)
                    file_ids.append(file_id)
            if file_ids and len(branches) > 1:
                raise errors.BzrCommandError(gettext(
                    'It is not possible to specify different file paths and different branches at the same time.'))
            return tuple(branches), primary_bi, file_ids

    def load_search_indexes(self, branches):
        global have_search, search_errors, search_index
        if have_search is None:
            have_search = True
            try:
                from breezy.plugins.search import errors as search_errors
                from breezy.plugins.search import index as search_index
            except ImportError:
                have_search = False

        if have_search:
            indexes_availble = False
            for bi in branches:
                try:
                    bi.index = search_index.open_index_branch(bi.branch)
                    indexes_availble = True
                except (search_errors.NoSearchIndex, errors.IncompatibleAPI):
                    pass
            if indexes_availble:
                self.searchType.insertItem(0, gettext("Messages and File text (indexed)"), self.FilterSearchRole)
                self.searchType.setCurrentIndex(0)
                self.completer = Compleater(self)
                self.completer_model = QStringListModel(self)
                self.completer.setModel(self.completer_model)
                self.search_edit.setCompleter(self.completer)
                self.search_edit.textChanged['QString'].connect(self.update_search_completer)
                self.suggestion_letters_loaded = {"":QStringList()}
                self.suggestion_last_first_letter = ""
                self.completer.activated['QString'].connect(self.set_search_timer)

    no_usefull_info_in_location_re = re.compile(r'^[.:/\\]*$')

    def branch_label(self, location, branch, shared_repo_location=None, shared_repo=None):
        # We should rather use QFontMetrics.elidedText. How do we decide on the width.
        def elided_text(text, length=20):
            if len(text) > length + 3:
                return text[:length] + '...'
            return text

        def elided_path(path):
            if len(path) > 23:
                directory, name = split(path)
                directory = elided_text(directory, 10)
                name = elided_text(name)
                return join(directory, name)
            return path

        if shared_repo_location and shared_repo and not location:
            # Once we depend on breezy 2.2, this can become .user_url
            branch_rel = determine_relative_path(shared_repo.controldir.root_transport.base, branch.controldir.root_transport.base)
            if shared_repo_location == 'colo:':
                location = shared_repo_location + branch_rel
            else:
                location = join(shared_repo_location, branch_rel)
        if location is None:
            return elided_text(branch.nick)
        has_explicit_nickname = getattr(branch.get_config(), 'has_explicit_nickname', lambda: False)()
        append_nick = (location.startswith(':') or bool(self.no_usefull_info_in_location_re.match(location)) or has_explicit_nickname)
        if append_nick:
            return '%s (%s)' % (elided_path(location), branch.nick)

        return elided_text(location)

    def refresh(self):
        self.file_list_container.drop_delta_cache_with_wt()
        self.replace = {}
        self.load()

    def replace_config(self, branch):
        if branch.base not in self.replace:
            config = branch.get_config()
            replace = config.get_user_option("qlog_replace")
            if replace:
                replace = replace.split("\n")
                replace = [tuple(replace[2 * i:2 * i + 2]) for i in range(len(replace) // 2)]
            self.replace[branch.base] = replace
        return self.replace[branch.base]

    def show(self):
        # we show the bare form as soon as possible.
        super().show()
        # QBzrWindow.show(self)
        QtCore.QTimer.singleShot(0, self.load)

    def update_selection(self, selected, deselected):
        indexes = self.log_list.get_selection_indexes()
        if not indexes:
            self.diffbuttons.setEnabled(False)
        else:
            self.diffbuttons.setEnabled(True)

    @ui_current_widget
    def update_search(self):
        # TODO in_paths = self.search_in_paths.isChecked()
        gv = self.log_list.log_model.graph_viz
        role = self.searchType.itemData(self.searchType.currentIndex())
        search_text = str(self.search_edit.text())
        if search_text == "":
            self.log_list.set_search(None, None)
        elif role == self.FilterIdRole:
            self.log_list.set_search(None, None)
            self.log_list.select_revid(search_text)
        elif role == self.FilterRevnoRole:
            self.log_list.set_search(None, None)
            try:
                revno = tuple((int(number) for number in search_text.split('.')))
            except ValueError:
                revno = ()
                # Not sure what to do if there is an error. Nothing for now
            if revno in gv.revno_rev:
                rev = gv.revno_rev[revno]
                index = self.log_list.log_model.index_from_rev(rev)
                self.log_list.setCurrentIndex(index)
        else:
            if role == self.FilterMessageRole:
                field = "message"
            elif role == self.FilterAuthorRole:
                field = "author"
            elif role == self.FilterSearchRole:
                field = "index"
            elif role == self.FilterTagRole:
                field = 'tag'
            elif role == self.FilterBugRole:
                field = 'bug'
            else:
                raise Exception("Not done")

            self.log_list.set_search(search_text, field)

        self.log_list.scrollTo(self.log_list.currentIndex())
        # Scroll to ensure the selection is on screen.

    @ui_current_widget
    def update_search_completer(self, text):
        gv = self.log_list.log_model.graph_viz
        # We only load the suggestions a letter at a time when needed.
        term = str(text).split(" ")[-1]
        if term:
            first_letter = term[0]
        else:
            first_letter = ""

        if first_letter != self.suggestion_last_first_letter:
            self.suggestion_last_first_letter = first_letter
            if first_letter not in self.suggestion_letters_loaded:
                suggestions = set()
                indexes = [bi.index for bi in gv.branches if bi.index is not None]
                for index in indexes:
                    for s in index.suggest(((first_letter,),)):
                        # if suggestions.count() % 100 == 0:
                        #    QtCore.QCoreApplication.processEvents()
                        suggestions.add(s[0])
                suggestions = QStringList(list(suggestions))
                suggestions.sort()
                self.suggestion_letters_loaded[first_letter] = suggestions
            else:
                suggestions = self.suggestion_letters_loaded[first_letter]
            self.completer_model.setStringList(suggestions)

    def updateSearchType(self, index=None):
        self.update_search()

    def set_search_timer(self):
        self.search_timer.start(200)

    def _locations_for_title(self, locations):
        if locations is None:
            return osutils.getcwd()
        else:
            from breezy.branch import Branch

            def title_for_location(location):
                if isinstance(location, str):
                    return url_for_display(location)
                if isinstance(location, Branch):
                    return url_for_display(location.base)
                return str(location)

            return ", ".join(title_for_location(location) for location in locations)


class FileListContainer(QtWidgets.QWidget):

    def __init__(self, log_list, parent=None):
        QtWidgets.QWidget.__init__(self, parent)

        self.log_list = log_list

        self.throbber = ThrobberWidget(self)
        self.throbber.hide()

        self.file_list = QtWidgets.QListWidget()
        self.file_list.doubleClicked[QtCore.QModelIndex].connect(self.show_diff_files)
        self.file_list.setContextMenuPolicy(QtCore.Qt.CustomContextMenu)
        self.file_list_context_menu = QtWidgets.QMenu(self)
        if has_ext_diff():
            diff_menu = ExtDiffMenu(self)
            self.file_list_context_menu.addMenu(diff_menu)
            diff_menu._triggered.connect(self.show_diff_files_ext)
        else:
            show_diff_action = self.file_list_context_menu.addAction(gettext("Show &differences..."), self.show_diff_files)
            self.file_list_context_menu.setDefaultAction(show_diff_action)

        self.file_list_context_menu_annotate = self.file_list_context_menu.addAction(gettext("Annotate"), self.show_file_annotate)
        self.file_list_context_menu_cat = self.file_list_context_menu.addAction(gettext("View file"), self.show_file_content)
        self.file_list_context_menu_save_old_file = self.file_list_context_menu.addAction(
            gettext("Save file on this revision as..."), self.save_old_revision_of_file)
        self.file_list_context_menu_revert_file = self.file_list_context_menu.addAction(gettext("Revert to this revision"), self.revert_file)

        self.file_list.customContextMenuRequested[QtCore.QPoint].connect(self.show_file_list_context_menu)

        vbox = QtWidgets.QVBoxLayout(self)
        vbox.setContentsMargins(0, 0, 0, 0)
        vbox.addWidget(self.throbber)
        vbox.addWidget(self.file_list)

        self.delta_load_timer = QtCore.QTimer(self)
        self.delta_load_timer.setSingleShot(True)
        self.delta_load_timer.timeout.connect(self.load_delta)
        self.current_revids = None

        self.tree_cache = {}
        self.delta_cache = {}

    def processEvents(self):
        self.window().processEvents()

    def revision_selection_changed(self, selected, deselected):
        revids, count = self.log_list.get_selection_top_and_parent_revids_and_count()
        if revids != self.current_revids:
            self.file_list.clear()
            self.current_revids = None
            self.delta_load_timer.start(200)

    @runs_in_loading_queue
    @ui_current_widget
    def load_delta(self):
        revids, count = self.log_list.get_selection_top_and_parent_revids_and_count()
        if revids == self.current_revids:
            return

        graph_viz = self.log_list.log_model.graph_viz
        is_working_tree_graph_viz = isinstance(graph_viz, logmodel.WithWorkingTreeGraphVizLoader)
        if self.log_list.log_model.file_id_filter:
            specific_file_ids = self.log_list.log_model.file_id_filter.file_ids
        else:
            specific_file_ids = []

        if not revids or revids == (None, None):
            return

        if revids not in self.delta_cache:
            self.throbber.show()
            try:
                repos = [graph_viz.get_revid_branch(revid).repository for revid in revids]
            except GhostRevisionError:
                delta = None
            else:
                if repos[0].__class__.__name__ == 'SvnRepository' or repos[1].__class__.__name__ == 'SvnRepository':
                    # Loading trees from a remote svn repo is unusably slow.
                    # See https://bugs.launchpad.net/qbrz/+bug/450225
                    # If only 1 revision is selected, use a optimized svn method
                    # which actualy gets the server to do the delta,
                    # else, don't do any delta.
                    if count == 1:
                        delta = repos[0].get_revision_delta(revids[0])
                    else:
                        delta = None
                else:
                    if len(repos) == 2 and repos[0].base == repos[1].base:
                        # Both revids are from the same repository. Load together.
                        repos_revids = [(repos[0], revids)]
                    else:
                        repos_revids = [(repo, [revid]) for revid, repo in zip(revids, repos)]

                    for repo, repo_revids in repos_revids:
                        repo_revids = [revid for revid in repo_revids if revid not in self.tree_cache]
                        if repo_revids:
                            with repo.lock_read():
                                self.processEvents()
                                for revid in repo_revids:
                                    if revid.startswith(CURRENT_REVISION) and is_working_tree_graph_viz:
                                        tree = graph_viz.working_trees[revid]
                                    else:
                                        tree = repo.revision_tree(revid)
                                    self.tree_cache[revid] = tree
                                self.processEvents()
                        self.processEvents()

                    delta = self.tree_cache[revids[0]].changes_from(self.tree_cache[revids[1]])
                self.delta_cache[revids] = delta
            finally:
                self.throbber.hide()
                self.processEvents()
        else:
            delta = self.delta_cache[revids]

        new_revids, count = self.log_list.get_selection_top_and_parent_revids_and_count()

        if new_revids != revids:
            return

        # Jelmer's commit 7389 states: TreeDelta holds TreeChange objects rather than tuples of various sizes
        #
        # It used to be seven lists:--
        #
        # added
        #     (path, id, kind)
        # removed
        #     (path, id, kind)
        # renamed
        #     (oldpath, newpath, id, kind, text_modified, meta_modified)
        # kind_changed
        #     (path, id, old_kind, new_kind)
        # modified
        #     (path, id, kind, text_modified, meta_modified)
        # unchanged
        #     (path, id, kind)
        # unversioned
        #     (path, None, kind)
        #
        # Now they are TreeChange objects in the lists added[], removed[] renamed[], copied[] and modified[]
        #
        # self.file_id = file_id
        # self.path = path
        # self.changed_content = changed_content
        # self.versioned = versioned
        # self.parent_id = parent_id
        # self.name = name
        # self.kind = kind
        # self.executable = executable
        #
        if delta:
            items = []  # each item is 6-tuple: (id, path, is_not_specific_file_id, display, color, is_alive)
            if delta.added:
                for tree_change in delta.added:
                    items.append(
                        (tree_change.file_id, tree_change.path[1],
                        tree_change.file_id not in specific_file_ids,
                        tree_change.path[1], 'blue', True))

            if delta.modified:
                for tree_change in delta.modified:
                    items.append(
                        (tree_change.file_id, tree_change.path[0],
                        tree_change.file_id not in specific_file_ids,
                        tree_change.path[0], None, True))

            if delta.removed:
                for tree_change in delta.removed:
                    items.append(
                        (tree_change.file_id, tree_change.path[0],
                        tree_change.file_id not in specific_file_ids,
                        tree_change.path[0], 'red', False))

            if delta.renamed:
                for tree_change in delta.renamed:
                    items.append(
                        (tree_change.file_id, tree_change.path[0],
                        tree_change.file_id not in specific_file_ids,
                        tree_change.path[1], None, True))

                # for (oldpath, newpath, id, kind, text_modified, meta_modified) in delta.renamed:
                # for tree_change in delta.renamed:
                #     items.append(
                #         (tree_change.file_id, tree_change.path,
                #         tree_change.file_id not in specific_file_ids,
                #         tree_change.path, 'purple', True))

                    # items.append((id,
                    #             newpath,
                    #             id not in specific_file_ids,
                    #             "%s => %s" % (oldpath, newpath),
                    #             "purple",
                    #             True))

            for (id, path, is_not_specific_file_id, display, color, is_alive) in sorted(items, key=lambda x: (x[2],x[1])):
                item = QtWidgets.QListWidgetItem(display, self.file_list)
                item.setData(PathRole, path)
                item.setData(file_idRole, id)
                item.setData(AliveRole, is_alive)
                if color:
                    item.setForeground(QtGui.QColor(color))
                if not is_not_specific_file_id:
                    f = item.font()
                    f.setBold(True)
                    item.setFont(f)
            self.current_revids = revids

    def drop_delta_cache_with_wt(self):
        gv = self.log_list.log_model.graph_viz
        if not isinstance(gv, logmodel.WithWorkingTreeGraphVizLoader):
            return
        cache = self.delta_cache
        keys = [k for k in cache.keys() if k[0].startswith(CURRENT_REVISION)]
        for key in keys:
            del(cache[key])

    def show_file_list_context_menu(self, pos):
        (top_revid, old_revid), count = self.log_list.get_selection_top_and_parent_revids_and_count()
        if count == 0:
            return
        # XXX - We should also check that the selected file is a file, and
        # not a dir
        paths, file_ids, alives = self._get_file_selection_paths_ids_and_alives()
        is_single_file = len(paths) == 1
        wt_selected = top_revid.startswith(CURRENT_REVISION)
        menu_enabled = is_single_file and alives[0]
        self.file_list_context_menu_annotate.setEnabled(menu_enabled)
        self.file_list_context_menu_cat.setEnabled(menu_enabled)
        menu_enabled = is_single_file and alives[0] and not wt_selected
        self.file_list_context_menu_save_old_file.setEnabled(menu_enabled)
        self.file_list_context_menu_save_old_file.setVisible(menu_enabled)

        gv = self.log_list.log_model.graph_viz
        # It would be nice if there were more than one branch, that we
        # show a menu so the user can chose which branch actions should take
        # place in.
        menu_enabled = (len(gv.branches) == 1 and gv.branches[0].tree is not None and not wt_selected)

        self.file_list_context_menu_revert_file.setEnabled(menu_enabled)
        self.file_list_context_menu_revert_file.setVisible(menu_enabled)
        self.file_list_context_menu.popup(self.file_list.viewport().mapToGlobal(pos))

    def get_file_selection_indexes(self, index=None):
        if index is None:
            return self.file_list.selectionModel().selectedRows(0)
        else:
            return [index]

    def get_file_selection_paths_and_ids(self, index=None):
        paths, ids, alives = self._get_file_selection_paths_ids_and_alives(index)
        return paths, ids

    def _get_file_selection_paths_ids_and_alives(self, index=None):
        indexes = self.get_file_selection_indexes(index)
        #
        paths = []
        ids = []
        alives = []
        #
        for index in indexes:
            item = self.file_list.itemFromIndex(index)
            paths.append(str(item.data(PathRole)))
            ids.append(item.data(file_idRole))
            alives.append(bool(item.data(AliveRole)))
        return paths, ids, alives

    @ui_current_widget
    def show_diff_files(self, index=None, ext_diff=None):
        """Show differences of a specific file in a single revision"""
        paths, ids = self.get_file_selection_paths_and_ids(index)
        self.log_list.show_diff(specific_files=paths, specific_file_ids=ids, ext_diff=ext_diff)

    @ui_current_widget
    def show_diff_files_ext(self, ext_diff=None):
        """Show differences of a specific file in a single revision"""
        self.show_diff_files(ext_diff=ext_diff)

    @runs_in_loading_queue
    @ui_current_widget
    def show_file_content(self):
        """Launch qcat for one selected file."""
        paths, file_ids = self.get_file_selection_paths_and_ids()
        (top_revid, old_revid), count = self.log_list.get_selection_top_and_parent_revids_and_count()

        gv = self.log_list.log_model.graph_viz
        branch = gv.get_revid_branch(top_revid)
        if top_revid.startswith(CURRENT_REVISION):
            tree = gv.working_trees[top_revid]
        else:
            tree = branch.repository.revision_tree(top_revid)
        encoding = get_set_encoding(None, branch)
        window = QBzrCatWindow(filename = paths[0], tree = tree, parent=self, encoding=encoding)
        window.show()
        self.window().windows.append(window)

    @ui_current_widget
    def save_old_revision_of_file(self):
        """Saves the selected file in its revision to a directory."""
        paths, file_ids = self.get_file_selection_paths_and_ids()
        (top_revid, old_revid), count = self.log_list.get_selection_top_and_parent_revids_and_count()
        branch = self.log_list.log_model.graph_viz.get_revid_branch(top_revid)
        tree = branch.repository.revision_tree(top_revid)
        path = paths[0]
        with tree.lock_read():
            kind = tree.kind(path)
            if kind == 'file':
                file_content_bytes = tree.get_file_text(path)
        if kind != 'file':
            QtWidgets.QMessageBox.information(self, gettext("Not a file"),
                gettext("Operation is supported for a single file only,\nnot for a %s." % kind))
            return
        filename = QtWidgets.QFileDialog.getSaveFileName(self, gettext("Save file in this revision as..."))[0]
        if filename:
            with open(str(filename), 'wb') as f:
                f.write(file_content_bytes)

    @ui_current_widget
    def revert_file(self):
        """Reverts the file to what it was at the selected revision."""
        res = QtWidgets.QMessageBox.question(self, gettext("Revert File"),
                    gettext("Are you sure you want to revert this file to the state it was at the selected revision?"),
                    QtWidgets.QMessageBox.Yes | QtWidgets.QMessageBox.No)
        if res == QtWidgets.QMessageBox.Yes:
            paths, file_ids = self.get_file_selection_paths_and_ids()

            (top_revid, old_revid), count = self.log_list.get_selection_top_and_parent_revids_and_count()
            gv = self.log_list.log_model.graph_viz
            assert(len(gv.branches) == 1)
            branch_info = gv.branches[0]
            rev_tree = gv.get_revid_repo(top_revid).revision_tree(top_revid)
            branch_info.tree.revert(paths, old_tree=rev_tree, report_changes=True)

    @ui_current_widget
    def show_file_annotate(self):
        """Show qannotate for selected file."""
        paths, file_ids = self.get_file_selection_paths_and_ids()
        (top_revid, old_revid), count = self.log_list.get_selection_top_and_parent_revids_and_count()

        branch_info = self.log_list.log_model.graph_viz.get_revid_branch_info(top_revid)
        if top_revid.startswith(CURRENT_REVISION):
            tree = branch_info.tree
        else:
            tree = branch_info.branch.repository.revision_tree(top_revid)
        window = AnnotateWindow(branch_info.branch, branch_info.tree, tree, paths[0], file_ids[0])
        window.show()
        self.window().windows.append(window)
