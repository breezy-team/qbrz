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

from PyQt4 import QtCore, QtGui
from bzrlib.branch import Branch
from bzrlib import osutils
from bzrlib.plugins.qbzr.lib import logmodel
from bzrlib.plugins.qbzr.lib.logwidget import LogList
from bzrlib.plugins.qbzr.lib.diff import (
    has_ext_diff,
    ExtDiffMenu,
    DiffButtons,
    )
from bzrlib.plugins.qbzr.lib.i18n import gettext
from bzrlib.plugins.qbzr.lib.util import (
    BTN_CLOSE,
    BTN_REFRESH,
    QBzrWindow,
    ThrobberWidget,
    StandardButton,
    open_browser,
    url_for_display,
    runs_in_loading_queue,
    get_set_encoding,
    )
from bzrlib.plugins.qbzr.lib.revisionmessagebrowser import LogListRevisionMessageBrowser
from bzrlib.plugins.qbzr.lib.trace import *
from bzrlib.plugins.qbzr.lib.uifactory import ui_current_widget
from bzrlib.plugins.qbzr.lib.cat import QBzrCatWindow
from bzrlib.plugins.qbzr.lib.annotate import AnnotateWindow

try:
    from bzrlib.plugins.svn.repository import SvnRepository
    has_svn = True
except ImportError:
    has_svn = False


PathRole = QtCore.Qt.UserRole + 1
FileIdRole = QtCore.Qt.UserRole + 2


class Compleater(QtGui.QCompleter):
    def splitPath (self, path):
        return QtCore.QStringList([path.split(" ")[-1]])


class LogWindow(QBzrWindow):

    FilterIdRole = QtCore.Qt.UserRole + 100
    FilterMessageRole = QtCore.Qt.UserRole + 101
    FilterAuthorRole = QtCore.Qt.UserRole + 102
    FilterRevnoRole = QtCore.Qt.UserRole + 103
    FilterSearchRole = QtCore.Qt.UserRole + 104
    FilterTagRole = QtCore.Qt.UserRole + 105
    FilterBugRole = QtCore.Qt.UserRole + 106

    def __init__(self, locations, branch, specific_fileids=None, parent=None,
                 ui_mode=True, no_graph=False):
        """Create qlog window.

        Note: you must use either locations or branch+specific_fileid
        arguments, but not both.

        @param  locations:  list of locations to show log
            (either list of URL/paths for several branches,
            or list of filenames from one branch).
            This list used when branch argument is None.

        @param  branch: branch object to show the log.
            Could be None, in this case locations list will be used
            to open branch(es).

        @param  specific_fileids:    file ids from the branch to filter
            the log.

        @param  parent: parent widget.

        @param  ui_mode:    for compatibility with TortoiseBzr.

        @param  no_graph:   don't show the graph of revisions (make sense
            for `bzr qlog FILE` to force plain log a-la `bzr log`).
        """
        self.title = [gettext("Log")]
        QBzrWindow.__init__(self, self.title, parent, ui_mode=ui_mode)
        self.restoreSize("log", (710, 580))
        
        if branch:
            self.branch = branch
            self.locations = (branch,)
            self.specific_fileids = specific_fileids
            assert locations is None, "can't specify both branch and locations"
        else:
            self.branch = None
            self.locations = locations
            if self.locations is None:
                self.locations = [u"."]
            assert specific_fileids is None, "specific_fileids is ignored if branch is None"
        
        self.branches = None
        self.replace = {}
        
        self.throbber = ThrobberWidget(self)
        
        logwidget = QtGui.QWidget()
        logbox = QtGui.QVBoxLayout(logwidget)
        logbox.setContentsMargins(0, 0, 0, 0)

        searchbox = QtGui.QHBoxLayout()

        self.search_label = QtGui.QLabel(gettext("&Search:"))
        self.search_edit = QtGui.QLineEdit()
        self.search_label.setBuddy(self.search_edit)
        self.connect(self.search_edit, QtCore.SIGNAL("textEdited(QString)"),
                     self.set_search_timer)

        self.search_timer = QtCore.QTimer(self)
        self.search_timer.setSingleShot(True)
        self.connect(self.search_timer, QtCore.SIGNAL("timeout()"),
                     self.update_search)

        searchbox.addWidget(self.search_label)
        searchbox.addWidget(self.search_edit)

        self.searchType = QtGui.QComboBox()
            
        self.searchType.addItem(gettext("Messages"),
                                QtCore.QVariant(self.FilterMessageRole))
        self.searchType.addItem(gettext("Authors"),
                                QtCore.QVariant(self.FilterAuthorRole))
        self.searchType.addItem(gettext("Revision IDs"),
                                QtCore.QVariant(self.FilterIdRole))
        self.searchType.addItem(gettext("Revision Numbers"),
                                QtCore.QVariant(self.FilterRevnoRole))
        self.searchType.addItem(gettext("Tags"),
                                QtCore.QVariant(self.FilterTagRole))
        self.searchType.addItem(gettext("Bugs"),
                                QtCore.QVariant(self.FilterBugRole))
        searchbox.addWidget(self.searchType)
        self.connect(self.searchType,
                     QtCore.SIGNAL("currentIndexChanged(int)"),
                     self.updateSearchType)

        logbox.addLayout(searchbox)

        self.log_list = LogList(self.processEvents,
                                self.throbber,
                                no_graph,
                                self)
        

        logbox.addWidget(self.throbber)
        logbox.addWidget(self.log_list)

        self.current_rev = None
        self.connect(self.log_list.selectionModel(),
                     QtCore.SIGNAL("selectionChanged(QItemSelection, QItemSelection)"),
                     self.update_selection)
        
        self.message = QtGui.QTextDocument()
        self.message_browser = LogListRevisionMessageBrowser(self.log_list, 
                                                             self)
        self.message_browser.setDocument(self.message)

        self.file_list_container = FileListContainer(self.log_list, self)
        self.connect(self.log_list.selectionModel(),
                     QtCore.SIGNAL("selectionChanged(QItemSelection, QItemSelection)"),
                     self.file_list_container.revision_selection_changed)
        
        hsplitter = QtGui.QSplitter(QtCore.Qt.Horizontal)
        hsplitter.addWidget(self.message_browser)
        hsplitter.addWidget(self.file_list_container)
        hsplitter.setStretchFactor(0, 3)
        hsplitter.setStretchFactor(1, 1)

        splitter = QtGui.QSplitter(QtCore.Qt.Vertical)
        splitter.addWidget(logwidget)
        splitter.addWidget(hsplitter)
        splitter.setStretchFactor(0, 5)
        splitter.setStretchFactor(1, 3)

        buttonbox = self.create_button_box(BTN_CLOSE)
        self.refresh_button = StandardButton(BTN_REFRESH)
        buttonbox.addButton(self.refresh_button, QtGui.QDialogButtonBox.ActionRole)
        self.connect(self.refresh_button,
                     QtCore.SIGNAL("clicked()"),
                     self.refresh)

        self.diffbuttons = DiffButtons(self.centralwidget)
        self.diffbuttons.setEnabled(False)
        self.connect(self.diffbuttons, QtCore.SIGNAL("triggered(QString)"),
                     self.log_list.show_diff_specified_files_ext)

        vbox = QtGui.QVBoxLayout(self.centralwidget)
        vbox.addWidget(splitter)
        hbox = QtGui.QHBoxLayout()
        hbox.addWidget(self.diffbuttons)
        hbox.addWidget(buttonbox)
        vbox.addLayout(hbox)
        self.windows = []
        # set focus on search edit widget
        self.log_list.setFocus()

    @runs_in_loading_queue
    @ui_current_widget
    @reports_exception()
    def load(self):
        self.refresh_button.setDisabled(True)            
        
        # Set window title. 
        lt = self._locations_for_title(self.locations)
        if lt:
            self.title.append(lt)
        self.set_title (self.title)
        
        self.processEvents()
        try:
            if self.branch:
                self.log_list.load_branch(self.branch, self.specific_fileids)
            else:
                self.log_list.load_locations(self.locations)
            
            for index in self.log_list.graph_provider.search_indexes():
                indexes_availble = True
                break
            else:
                indexes_availble = False
            
            if indexes_availble:
                self.searchType.insertItem(0,
                        gettext("Messages and File text (indexed)"),
                        QtCore.QVariant(self.FilterSearchRole))
                self.searchType.setCurrentIndex(0)
                
                self.completer = Compleater(self)
                self.completer_model = QtGui.QStringListModel(self)
                self.completer.setModel(self.completer_model)
                self.search_edit.setCompleter(self.completer)
                self.connect(self.search_edit, QtCore.SIGNAL("textChanged(QString)"),
                             self.update_search_completer)
                self.suggestion_letters_loaded = {"":QtCore.QStringList()}
                self.suggestion_last_first_letter = ""
                self.connect(self.completer, QtCore.SIGNAL("activated(QString)"),
                             self.set_search_timer)
            
            #if len(self.log_list.graph_provider.fileids)==1 and \
            #        not self.log_list.graph_provider.has_dir:
            #    self.file_list.hide()
        finally:
            self.refresh_button.setDisabled(False)
    
    @runs_in_loading_queue
    @ui_current_widget
    @reports_exception(type = SUB_LOAD_METHOD)
    def refresh(self):
        self.refresh_button.setDisabled(True)            
        self.processEvents()
        try:
            self.replace = {}
            self.log_list.refresh()
        finally:
            self.refresh_button.setDisabled(False)

    def replace_config(self, branch):
        if branch.base not in self.replace:
            config = branch.get_config()
            replace = config.get_user_option("qlog_replace")
            if replace:
                replace = replace.split("\n")
                replace = [tuple(replace[2*i:2*i+2])
                                for i in range(len(replace) // 2)]
            self.replace[branch.base] = replace
        
        return self.replace[branch.base]
    
    def show(self):
        # we show the bare form as soon as possible.
        QBzrWindow.show(self)
        QtCore.QTimer.singleShot(1, self.load)

    def update_selection(self, selected, deselected):
        indexes = self.log_list.get_selection_indexes()
        if not indexes:
            self.diffbuttons.setEnabled(False)
        else:
            self.diffbuttons.setEnabled(True)
    
    @ui_current_widget
    def update_search(self):
        # TODO in_paths = self.search_in_paths.isChecked()
        role = self.searchType.itemData(self.searchType.currentIndex()).toInt()[0]
        search_text = unicode(self.search_edit.text())
        if search_text == u"":
            self.log_list.set_search(None, None)
        elif role == self.FilterIdRole:
            self.log_list.set_search(None, None)
            if self.log_list.graph_provider.has_rev_id(search_text):
                self.log_list.log_model.ensure_rev_visible(search_text)
                index = self.log_list.log_model.indexFromRevId(search_text)
                index = self.log_list.filter_proxy_model.mapFromSource(index)
                self.log_list.setCurrentIndex(index)
        elif role == self.FilterRevnoRole:
            self.log_list.set_search(None, None)
            try:
                revno = tuple((int(number) for number in search_text.split('.')))
            except ValueError:
                revno = ()
                # Not sure what to do if there is an error. Nothing for now
            revid = self.log_list.graph_provider.revid_from_revno(revno)
            if revid:
                self.log_list.log_model.ensure_rev_visible(revid)
                index = self.log_list.log_model.indexFromRevId(revid)
                index = self.log_list.filter_proxy_model.mapFromSource(index)
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
        # We only load the suggestions a letter at a time when needed.
        term = unicode(text).split(" ")[-1]
        if term:
            first_letter = term[0]
        else:
            first_letter = ""
        
        if first_letter != self.suggestion_last_first_letter:
            self.suggestion_last_first_letter = first_letter
            if first_letter not in self.suggestion_letters_loaded:
                suggestions = set()
                for index in self.log_list.graph_provider.search_indexes():
                    for s in index.suggest(((first_letter,),)): 
                        #if suggestions.count() % 100 == 0: 
                        #    QtCore.QCoreApplication.processEvents() 
                        suggestions.add(s[0])
                suggestions = QtCore.QStringList(list(suggestions))
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
        if locations == ['.']:
            return osutils.getcwd()
        else:
            if len(locations) > 1:
                return (", ".join(url_for_display(i) for i in locations
                                 ).rstrip(", "))
            else:
                if isinstance(locations[0], Branch):
                    location = locations[0].base
                else:
                    location = locations[0]
                from bzrlib.directory_service import directories
                return (url_for_display(directories.dereference(location)))


class FileListContainer(QtGui.QWidget):
    
    def __init__(self, log_list, parent=None):
        QtGui.QWidget.__init__(self, parent)
        
        self.log_list = log_list
        
        self.throbber = ThrobberWidget(self)
        self.throbber.hide()
        
        self.file_list = QtGui.QListWidget()
        self.connect(self.file_list,
                     QtCore.SIGNAL("doubleClicked(QModelIndex)"),
                     self.show_diff_files)
        self.file_list.setContextMenuPolicy(QtCore.Qt.CustomContextMenu)        
        self.file_list_context_menu = QtGui.QMenu(self)
        if has_ext_diff():
            diff_menu = ExtDiffMenu(self)
            self.file_list_context_menu.addMenu(diff_menu)
            self.connect(diff_menu, QtCore.SIGNAL("triggered(QString)"),
                         self.show_diff_files_ext)
        else:
            show_diff_action = self.file_list_context_menu.addAction(
                                        gettext("Show &differences..."),
                                        self.show_diff_files)
            self.file_list_context_menu.setDefaultAction(show_diff_action)
        
        self.file_list_context_menu_annotate = \
            self.file_list_context_menu.addAction(gettext("Annotate"),
                                                  self.show_file_annotate)
        self.file_list_context_menu_cat = \
            self.file_list_context_menu.addAction(gettext("View file"),
                                                  self.show_file_content)

        self.file_list.connect(
            self.file_list,
            QtCore.SIGNAL("customContextMenuRequested(QPoint)"),
            self.show_file_list_context_menu)
        
        vbox = QtGui.QVBoxLayout(self)
        vbox.setContentsMargins(0, 0, 0, 0)
        vbox.addWidget(self.throbber)
        vbox.addWidget(self.file_list)
        
        self.delta_load_timer = QtCore.QTimer(self)
        self.delta_load_timer.setSingleShot(True)
        self.connect(self.delta_load_timer, QtCore.SIGNAL("timeout()"),
                     self.load_delta)
        
        self.tree_cache = {}
        self.delta_cache = {}
    
    def processEvents(self):
        self.window().processEvents()

    def revision_selection_changed(self, selected, deselected):
        self.file_list.clear()
        self.delta_load_timer.start(1)
    
    @runs_in_loading_queue
    @ui_current_widget
    def load_delta(self):
        revids, count = \
            self.log_list.get_selection_top_and_parent_revids_and_count()
        
        if not revids:
            return
        
        if revids not in self.delta_cache:
            self.throbber.show()
            gp = self.log_list.graph_provider
            repos = [gp.get_revid_branch(revid).repository for revid in revids]
            if has_svn and (isinstance(repos[0], SvnRepository) or
                            isinstance(repos[1], SvnRepository)):
                # Loading trees from a remote svn repo is unusably slow.
                # See https://bugs.launchpad.net/qbzr/+bug/450225
                # If only 1 revision is selected, use a optimized svn method
                # which actualy gets the server to do the delta,
                # else, don't do any delta.
                if count == 1:
                    delta = repos[0].get_revision_delta(revids[0])
                else:
                    delta = None
            else:
                if (len(repos)==2 and
                    repos[0].base == repos[1].base):
                    # Both revids are from the same repository. Load together.
                    repos_revids = [(repos[0], revids)]
                else:
                    repos_revids = [(repo, [revid])
                            for revid, repo in zip(revids, repos)]
                
                for repo, repo_revids in repos_revids:
                    repo_revids = [revid for revid in repo_revids 
                                   if revid not in self.tree_cache]
                    if repo_revids:
                        repo.lock_read()
                        self.processEvents()
                        try:
                            for revid in repo_revids:
                                tree = repo.revision_tree(revid)
                                self.tree_cache[revid] = tree
                            self.processEvents()
                        finally:
                            repo.unlock()
                    self.processEvents()
                
                delta = self.tree_cache[revids[0]].changes_from(
                                                self.tree_cache[revids[1]])
            self.delta_cache[revids] = delta
            self.throbber.hide()
            self.processEvents()
        else:
            delta = self.delta_cache[revids]
        
        if delta:
            items = []
            specific_fileids = self.log_list.graph_provider.fileids
            
            for path, id, kind in delta.added:
                items.append((id,
                              path,
                              id not in specific_fileids,
                              path,
                              "blue"))
    
            for path, id, kind, text_modified, meta_modified in delta.modified:
                items.append((id,
                              path,
                              id not in specific_fileids,
                              path,
                              None))
    
            for path, id, kind in delta.removed:
                items.append((id,
                              path,
                              id not in specific_fileids,
                              path,
                              "red"))
    
            for (oldpath, newpath, id, kind,
                text_modified, meta_modified) in delta.renamed:
                items.append((id,
                              newpath,
                              id not in specific_fileids,
                              "%s => %s" % (oldpath, newpath),
                              "purple"))
            
            for (id, path,
                 is_not_specific_fileid,
                 display, color) in sorted(items, key = lambda x: (x[2],x[1])):
                item = QtGui.QListWidgetItem(display, self.file_list)
                item.setData(PathRole, QtCore.QVariant(path))
                item.setData(FileIdRole, QtCore.QVariant(id))
                if color:
                    item.setTextColor(QtGui.QColor(color))
                if not is_not_specific_fileid:
                    f = item.font()
                    f.setBold(True)
                    item.setFont(f)

    def show_file_list_context_menu(self, pos):
        # XXX - We should also check that the selected file is a file, and 
        # not a dir
        paths, file_ids = self.get_file_selection_paths_and_ids()
        is_single_file = len(paths) == 1
        self.file_list_context_menu_annotate.setEnabled(is_single_file)
        self.file_list_context_menu_cat.setEnabled(is_single_file)
        
        self.file_list_context_menu.popup(
            self.file_list.viewport().mapToGlobal(pos))
    
    def get_file_selection_indexes(self, index=None):
        if index is None:
            return self.file_list.selectionModel().selectedRows(0)
        else:
            return [index]
    
    def get_file_selection_paths_and_ids(self, index=None):
        indexes = self.get_file_selection_indexes(index)
        
        paths = []
        ids = []
        
        for index in indexes:
            item = self.file_list.itemFromIndex(index)
            paths.append(unicode(item.data(PathRole).toString()))
            ids.append(str(item.data(FileIdRole).toString()))
        return paths, ids
    
    @ui_current_widget
    def show_diff_files(self, index=None, ext_diff=None):
        """Show differences of a specific file in a single revision"""
        paths, ids = self.get_file_selection_paths_and_ids(index)
        self.log_list.show_diff(specific_files=paths, specific_file_ids=ids,
                                ext_diff=ext_diff)
    
    @ui_current_widget
    def show_diff_files_ext(self, ext_diff=None):
        """Show differences of a specific file in a single revision"""
        self.show_diff_files(ext_diff=ext_diff)
    
    @runs_in_loading_queue
    @ui_current_widget
    def show_file_content(self):
        """Launch qcat for one selected file."""
        paths, file_ids = self.get_file_selection_paths_and_ids()
        (top_revid, old_revid), count = \
            self.log_list.get_selection_top_and_parent_revids_and_count()
        
        branch = self.log_list.graph_provider.get_revid_branch(top_revid)
        tree = branch.repository.revision_tree(top_revid)
        encoding = get_set_encoding(None, branch)
        window = QBzrCatWindow(filename = paths[0], tree = tree, parent=self,
            encoding=encoding)
        window.show()
        self.window().windows.append(window)

    @ui_current_widget
    def show_file_annotate(self):
        """Show qannotate for selected file."""
        paths, file_ids = self.get_file_selection_paths_and_ids()
        (top_revid, old_revid), count = \
            self.log_list.get_selection_top_and_parent_revids_and_count()
        
        branch = self.log_list.graph_provider.get_revid_branch(top_revid)
        tree = branch.repository.revision_tree(top_revid)
        window = AnnotateWindow(branch, tree, paths[0], file_ids[0])
        window.show()
        self.window().windows.append(window)
