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
from bzrlib.plugins.qbzr.lib.diff import DiffWindow
from bzrlib.plugins.qbzr.lib.extdiff import (
    show_diff,
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
    format_revision_html,
    format_timestamp,
    open_browser,
    RevisionMessageBrowser,
    url_for_display,
    runs_in_loading_queue,
    )
from bzrlib.plugins.qbzr.lib.trace import *
from bzrlib.plugins.qbzr.lib.uifactory import ui_current_widget

PathRole = QtCore.Qt.UserRole + 1


class Compleater(QtGui.QCompleter):
    def splitPath (self, path):
        return QtCore.QStringList([path.split(" ")[-1]])


class LogWindow(QBzrWindow):

    FilterIdRole = QtCore.Qt.UserRole + 100
    FilterMessageRole = QtCore.Qt.UserRole + 101
    FilterAuthorRole = QtCore.Qt.UserRole + 102
    FilterRevnoRole = QtCore.Qt.UserRole + 103
    FilterSearchRole = QtCore.Qt.UserRole + 104
    
    def __init__(self, locations, branch, specific_fileids, parent=None,
                 ui_mode=True):        
        self.title = [gettext("Log")]
        QBzrWindow.__init__(self, self.title, parent, ui_mode=ui_mode)
        self.restoreSize("log", (710, 580))
        
        if branch:
            self.branch = branch
            self.locations = (branch,)
            self.specific_fileids = specific_fileids
            assert locations is None, "can't specify both branch and loc"
        else:
            self.branch = None
            self.locations = locations
            if self.locations is None:
                self.locations = ["."]
            assert specific_fileids is None, "this is ignored if no branch"
        
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
        searchbox.addWidget(self.searchType)
        self.connect(self.searchType,
                     QtCore.SIGNAL("currentIndexChanged(int)"),
                     self.updateSearchType)

        logbox.addLayout(searchbox)

        self.log_list = LogList(self.processEvents,
                                self.report_exception,
                                self.throbber,
                                self)
        self.log_list.keyPressEvent  = self.log_list_keyPressEvent
        

        logbox.addWidget(self.throbber)
        logbox.addWidget(self.log_list)

        self.revision_delta_timer = QtCore.QTimer(self)
        self.revision_delta_timer.setSingleShot(True)
        self.connect(self.revision_delta_timer, QtCore.SIGNAL("timeout()"),
                     self.update_revision_delta)

        self.current_rev = None
        self.connect(self.log_list.selectionModel(),
                     QtCore.SIGNAL("selectionChanged(QItemSelection, QItemSelection)"),
                     self.update_selection)
        self.connect(self.log_list,
                     QtCore.SIGNAL("doubleClicked(QModelIndex)"),
                     self.show_differences)
        self.connect(self.log_list,
                     QtCore.SIGNAL("customContextMenuRequested(QPoint)"),
                     self.show_context_menu)
        #self.connect(self.log_list,
        #             QtCore.SIGNAL("clicked (QModelIndex)"),
        #             self.changesList_clicked)


        self.message = QtGui.QTextDocument()
        self.message_browser = RevisionMessageBrowser()
        self.message_browser.setDocument(self.message)
        self.connect(self.message_browser,
                     QtCore.SIGNAL("anchorClicked(QUrl)"),
                     self.link_clicked)

        self.fileList = QtGui.QListWidget()
        self.connect(self.fileList,
                     QtCore.SIGNAL("doubleClicked(QModelIndex)"),
                     self.show_file_differences)

        hsplitter = QtGui.QSplitter(QtCore.Qt.Horizontal)
        hsplitter.addWidget(self.message_browser)
        hsplitter.addWidget(self.fileList)
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
                     self.diff_pushed)

        self.contextMenu = QtGui.QMenu(self)
        if has_ext_diff():
            diffMenu = ExtDiffMenu(self)
            self.contextMenu.addMenu(diffMenu)
            self.connect(diffMenu, QtCore.SIGNAL("triggered(QString)"),
                         self.diff_pushed)
        else:
            show_diff_action = self.contextMenu.addAction(
                gettext("Show &differences..."), self.diff_pushed)
            self.contextMenu.setDefaultAction(show_diff_action)
        
        self.contextMenu.addAction(gettext("Show &tree..."), self.show_revision_tree)

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
                self.log_list.load_branch(self.branch,
                                                self.specific_fileids)
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

    def link_clicked(self, url):
        scheme = unicode(url.scheme())
        if scheme == 'qlog-revid':
            revision_id = unicode(url.path())
            self.log_list.model.ensure_rev_visible(revision_id)
            index = self.log_list.model.indexFromRevId(revision_id)
            index = self.log_list.filter_proxy_model.mapFromSource(index)
            self.log_list.setCurrentIndex(index)
        else:
            open_browser(str(url.toEncoded()))

    @runs_in_loading_queue
    @ui_current_widget
    def update_revision_delta(self):
        rev = self.current_rev
        if not hasattr(rev, 'delta'):
            # TODO move this to a thread
            rev.repository.lock_read()
            self.processEvents()
            try:
                rev.delta = rev.repository.get_deltas_for_revisions(
                    [rev]).next()
                self.processEvents()
            finally:
                rev.repository.unlock()
                self.processEvents()
        if self.current_rev is not rev:
            # new update was requested, don't bother populating the list
            return
        delta = rev.delta

        for path, id_, kind in delta.added:
            item = QtGui.QListWidgetItem(path, self.fileList)
            item.setTextColor(QtGui.QColor("blue"))

        for path, id_, kind, text_modified, meta_modified in delta.modified:
            item = QtGui.QListWidgetItem(path, self.fileList)

        for path, id_, kind in delta.removed:
            item = QtGui.QListWidgetItem(path, self.fileList)
            item.setTextColor(QtGui.QColor("red"))

        for (oldpath, newpath, id_, kind,
            text_modified, meta_modified) in delta.renamed:
            item = QtGui.QListWidgetItem("%s => %s" % (oldpath, newpath), self.fileList)
            item.setData(PathRole, QtCore.QVariant(newpath))
            item.setTextColor(QtGui.QColor("purple"))

    @runs_in_loading_queue
    @ui_current_widget
    def update_selection(self, selected, deselected):
        indexes = [index for index in self.log_list.selectedIndexes() if index.column()==0]
        self.fileList.clear()
        if not indexes:
            self.diffbuttons.setEnabled(False)
            self.message.setHtml("")
        else:
            self.diffbuttons.setEnabled(True)
            index = indexes[0]
            revid = str(index.data(logmodel.RevIdRole).toString())
            rev = self.log_list.graph_provider.revision(revid)
            parents_ids = self.log_list.graph_provider.graph_parents[revid]
            child_ids = self.log_list.graph_provider.graph_children[revid]
            self.log_list.graph_provider.load_revisions([revid] + \
                                    list(parents_ids) + list(child_ids))
            rev = self.log_list.graph_provider.revision(revid)
            
            if not hasattr(rev, "children"):
                rev.children = [self.log_list.graph_provider.revision(revid)
                                for revid in child_ids]
            if not hasattr(rev, "parents"):
                rev.parents = [self.log_list.graph_provider.revision(revid)
                                for revid in parents_ids]
            self.current_rev = rev
            
            replace = self.replace_config(rev.branch)
            self.message.setHtml(format_revision_html(rev, replace))
            self.revision_delta_timer.start(1)

    def log_list_keyPressEvent (self, e):
        try:
            e_key = e.key()
            if e_key in (QtCore.Qt.Key_Enter, QtCore.Qt.Key_Return):
                e.accept()
                self.diff_pushed()
            else:
                LogList.keyPressEvent(self.log_list, e)
        except:
            self.report_exception        
    
    @ui_current_widget
    def show_diff_window(self, new_rev, old_rev, specific_files=None, ext_diff = None):
        new_revid = new_rev.revision_id
        new_branch = new_rev.branch
        
        if not old_rev.parent_ids:
            old_revid = None
            old_branch = new_branch
        else:
            old_revid = old_rev.parent_ids[0]
            old_branch =  old_rev.branch

        show_diff(old_revid, new_revid,
                 old_branch, new_branch,
                 ext_diff = ext_diff,
                 specific_files=specific_files,
                 parent_window = self)

    def show_differences(self, index):
        """Show differences of a single revision"""
        revid = str(index.data(logmodel.RevIdRole).toString())
        rev = self.log_list.graph_provider.revision(revid, force_load=True)
        self.show_diff_window(rev, rev)

    def show_file_differences(self, index):
        """Show differences of a specific file in a single revision"""
        item = self.fileList.itemFromIndex(index)
        if item and self.current_rev:
            path = item.data(PathRole).toString()
            if path.isNull():
                path = item.text()
            rev = self.current_rev
            self.show_diff_window(rev, rev, [unicode(path)])

    def diff_menu_item_pushed(self, action):
        self.diff_pushed()

    def diff_pushed(self, ext_diff = None):
        """Show differences of the selected range or of a single revision"""
        indexes = [index for index in self.log_list.selectedIndexes() if index.column()==0]
        if not indexes:
            # the list is empty
            return
        revid1 = str(indexes[0].data(logmodel.RevIdRole).toString())
        rev1 = self.log_list.graph_provider.revision(revid1)
        revid2 = str(indexes[-1].data(logmodel.RevIdRole).toString())
        rev2 = self.log_list.graph_provider.revision(revid2)
        self.show_diff_window(rev1, rev2, ext_diff = ext_diff)

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
                self.log_list.model.ensure_rev_visible(search_text)
                index = self.log_list.model.indexFromRevId(search_text)
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
                self.log_list.model.ensure_rev_visible(revid)
                index = self.log_list.model.indexFromRevId(revid)
                index = self.log_list.filter_proxy_model.mapFromSource(index)
                self.log_list.setCurrentIndex(index)
        else:
            if role == self.FilterMessageRole:
                field = "message"
            elif role == self.FilterAuthorRole:
                field = "author"
            elif role == self.FilterSearchRole:
                field = "index"
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

    def show_revision_tree(self):
        from bzrlib.plugins.qbzr.lib.browse import BrowseWindow
        rev = self.current_rev
        window = BrowseWindow(rev.branch, revision_id=rev.revision_id,
                              revision_spec=rev.revno, parent=self)
        window.show()
        self.windows.append(window)

    def show_context_menu(self, pos):
        self.contextMenu.popup(self.log_list.viewport().mapToGlobal(pos))

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
