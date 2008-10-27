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
from bzrlib.bzrdir import BzrDir
from bzrlib.branch import Branch
from bzrlib import (
    errors,
    osutils,
    )
from bzrlib.plugins.qbzr.lib import logmodel
from bzrlib.plugins.qbzr.lib.diff import DiffWindow
from bzrlib.plugins.qbzr.lib.i18n import gettext
from bzrlib.plugins.qbzr.lib.util import (
    BTN_CLOSE,
    BTN_REFRESH,
    QBzrWindow,
    StandardButton,
    format_revision_html,
    format_timestamp,
    open_browser,
    RevisionMessageBrowser,
    url_for_display,
    )

have_search = True
try:
    from bzrlib.plugins.search import errors as search_errors
    from bzrlib.plugins.search import index as search_index
except ImportError:
    have_search = False

PathRole = QtCore.Qt.UserRole + 1

class GraphTagsBugsItemDelegate(QtGui.QItemDelegate):

    _tagColor = QtGui.QColor(255, 255, 170)
    _tagColorBorder = QtGui.QColor(255, 238, 0)

    _bugColor = QtGui.QColor(255, 188, 188)
    _bugColorBorder = QtGui.QColor(255, 79, 79)

    _branchTagColor = QtGui.QColor(188, 188, 255)
    _branchTagColorBorder = QtGui.QColor(79, 79, 255)

    _twistyColor = QtCore.Qt.black

    def paint(self, painter, option, index):
        node = index.data(logmodel.GraphNodeRole)
        if node.isValid():
            self.drawGraph = True
            self.node = node.toList()
            self.lines = index.data(logmodel.GraphLinesRole).toList()
            self.twisty_state = index.data(logmodel.GraphTwistyStateRole)
            
            prevIndex = index.sibling (index.row()-1, index.column())
            if prevIndex.isValid ():
                self.prevLines = prevIndex.data(logmodel.GraphLinesRole).toList()
            else:
                self.prevLines = []
        else:
            self.drawGraph = False
        
        self.labels = []
        # collect branch tags
        for tag in index.data(logmodel.BranchTagsRole).toStringList():
            self.labels.append(
                (tag, self._branchTagColor, self._branchTagColorBorder))
        # collect tag names
        for tag in index.data(logmodel.TagsRole).toStringList():
            self.labels.append(
                (tag, self._tagColor, self._tagColorBorder))
        # collect bug ids
        for bug in index.data(logmodel.BugIdsRole).toStringList():
            self.labels.append(
                (bug, self._bugColor, self._bugColorBorder))
        QtGui.QItemDelegate.paint(self, painter, option, index)
    
    def get_color(self, color, back):
        qcolor = QtGui.QColor()
        if color == 0:
            if back:
                qcolor.setHsvF(0,0,0.8)
            else:
                qcolor.setHsvF(0,0,0)
        else:
            h = float(color % 6) / 6
            if back:
                qcolor.setHsvF(h,0.4,1)
            else:
                qcolor.setHsvF(h,1,0.7)
        
        return qcolor
    
    def drawLine(self, painter, pen, rect, boxsize, mid, height,
                 start, end, color, direct):
        pen.setColor(self.get_color(color,False))
        if direct:
            pen.setStyle(QtCore.Qt.SolidLine)
        else:
            pen.setStyle(QtCore.Qt.DotLine)            
        painter.setPen(pen)
        startx = rect.x() + boxsize * start + boxsize / 2 
        endx = rect.x() + boxsize * end + boxsize / 2 
        
        path = QtGui.QPainterPath()
        path.moveTo(QtCore.QPointF(startx, mid - height / 2))
        
        if start - end == 0 :
            path.lineTo(QtCore.QPointF(endx, mid + height / 2)) 
        else:
            path.cubicTo(QtCore.QPointF(startx, mid - height / 5),
                         QtCore.QPointF(startx, mid - height / 5),
                         QtCore.QPointF(startx + (endx - startx) / 2, mid))

            path.cubicTo(QtCore.QPointF(endx, mid + height / 5),
                         QtCore.QPointF(endx, mid + height / 5),
                         QtCore.QPointF(endx, mid + height / 2 + 1))
        painter.drawPath(path)
        pen.setStyle(QtCore.Qt.SolidLine)

    def drawDisplay(self, painter, option, rect, text):
        graphCols = 0
        if self.drawGraph:
            painter.save()
            try:
                painter.setRenderHint(QtGui.QPainter.Antialiasing)            
                boxsize = float(rect.height())
                dotsize = 0.7
                pen = QtGui.QPen()
                penwidth = 1
                pen.setWidth(penwidth)
                pen.setCapStyle(QtCore.Qt.FlatCap)
                #this is to try get lines 1 pixel wide to actualy be 1 pixel wide.
                painter.translate(0.5, 0.5)
                
                
                # Draw lines into the cell
                for line in self.prevLines:
                    start, end, color = [linei.toInt()[0] for linei in line.toList()[0:3]]
                    direct = line.toList()[3].toBool()
                    self.drawLine (painter, pen, rect, boxsize,
                                   rect.y(), boxsize,
                                   start, end, color, direct)
                    graphCols = max((graphCols, min(start, end)))
        
                # Draw lines out of the cell
                for line in self.lines:
                    start, end, color = [linei.toInt()[0] for linei in line.toList()[0:3]]
                    direct = line.toList()[3].toBool()
                    self.drawLine (painter, pen, rect,boxsize,
                                   rect.y() + boxsize, boxsize,
                                   start, end, color, direct)
                    graphCols = max((graphCols, min(start, end)))
                
                # Draw the revision node in the right column
                color = self.node[1].toInt()[0]
                column = self.node[0].toInt()[0]
                graphCols = max((graphCols, column))
                pen.setColor(self.get_color(color,False))
                painter.setPen(pen)
                painter.setBrush(QtGui.QBrush(self.get_color(color,True)))
                centerx = rect.x() + boxsize * (column + 0.5)
                centery = rect.y() + boxsize * 0.5
                painter.drawEllipse(
                    QtCore.QRectF(centerx - (boxsize * dotsize * 0.5 ),
                                  centery - (boxsize * dotsize * 0.5 ),
                                 boxsize * dotsize, boxsize * dotsize))

                # Draw twisty
                if self.twisty_state.isValid():
                    linesize = 0.35
                    pen.setColor(self._twistyColor)
                    painter.setPen(pen)
                    painter.drawLine(QtCore.QLineF (centerx - boxsize * linesize / 2,
                                                    centery,
                                                    centerx + boxsize * linesize / 2,
                                                    centery))
                    if not self.twisty_state.toBool():
                        painter.drawLine(QtCore.QLineF (centerx,
                                                        centery - boxsize * linesize / 2,
                                                        centerx,
                                                        centery + boxsize * linesize / 2))
                
            finally:
                painter.restore()
            rect.adjust( (graphCols + 1.7) * boxsize, 0, 0, 0)
        
        painter.save()
        try:
            tagFont = QtGui.QFont(option.font)
            tagFont.setPointSizeF(tagFont.pointSizeF() * 9 / 10)
    
            x = 0
            for label, color, borderColor in self.labels:
                tagRect = rect.adjusted(1, 1, -1, -1)
                tagRect.setWidth(QtGui.QFontMetrics(tagFont).width(label) + 6)
                tagRect.moveLeft(tagRect.x() + x)
                painter.fillRect(tagRect.adjusted(1, 1, -1, -1), color)
                painter.setPen(borderColor)
                painter.drawRect(tagRect.adjusted(0, 0, -1, -1))
                painter.setFont(tagFont)
                painter.setPen(option.palette.text().color())
                painter.drawText(tagRect.left() + 3, tagRect.bottom() - option.fontMetrics.descent() + 1, label)
                x += tagRect.width() + 3
        finally:
            painter.restore()
        
        rect.adjust( x, 0, 0, 0)
        
        return QtGui.QItemDelegate.drawDisplay(self, painter, option, rect, text)

class Compleater(QtGui.QCompleter):
    def splitPath (self, path):
        return QtCore.QStringList([path.split(" ")[-1]])

def load_locataions(locations):
    file_ids = []
    heads = {}
    branches = {}
    paths_and_branches_err = "It is not possible to specify different file paths and different branches at the same time."
    
    def append_head_info(revid, branch, tag, is_branch_last_revision):
        if not revid in heads:
            heads[revid] = (len(heads), [])
        if tag:
            heads[revid][1].append ((branch, tag, is_branch_last_revision))
    
    def append_location(tree, br, repo, fp, tag):
        if br.base not in branches:
            branches[br.base] = br
        
        branch_last_revision = br.last_revision()
        append_head_info(branch_last_revision, br, tag, True)
        
        if tree:
            parent_ids = tree.get_parent_ids()
            if parent_ids:
                # first parent is last revision of the tree
                revid = parent_ids[0]
                if revid != branch_last_revision:
                    # working tree is out of date
                    if tag:
                        append_head_info(revid, br, "%s - Working Tree" % tag, False)
                    else:
                        append_head_info(revid, br, "Working Tree", False)
                # other parents are pending merges
                for revid in parent_ids[1:]:
                    if tag:
                        append_head_info(revid, br, "%s - Pending Merge" % tag, False)
                    else:
                        append_head_info(revid, br, "Pending Merge", False)
        
        if fp != '' : 
            if tree is None:
                tree = br.basis_tree()
            file_id = tree.path2id(fp)
            if file_id is None:
                raise errors.BzrCommandError(
                    "Path does not have any revision history: %s" %
                    location)
            file_ids.append(file_id)
            if not main_branch.base == br.base:
                raise errors.BzrCommandError(paths_and_branches_err)
    
    # This is copied stright from bzrlib/bzrdir.py. We can't just use the orig,
    # because that would mean we require bzr 1.6
    def open_containing_tree_branch_or_repository(location):
        """Return the working tree, branch and repo contained by a location.

        Returns (tree, branch, repository, relpath).
        If there is no tree containing the location, tree will be None.
        If there is no branch containing the location, branch will be None.
        If there is no repository containing the location, repository will be
        None.
        relpath is the portion of the path that is contained by the innermost
        BzrDir.

        If no tree, branch or repository is found, a NotBranchError is raised.
        """
        bzrdir, relpath = BzrDir.open_containing(location)
        try:
            tree, branch = bzrdir._get_tree_branch()
        except errors.NotBranchError:
            try:
                repo = bzrdir.find_repository()
                return None, None, repo, relpath
            except (errors.NoRepositoryPresent):
                raise errors.NotBranchError(location)
        return tree, branch, branch.repository, relpath
    
    for location in locations:
        if isinstance(location, Branch):
            br = location
            repo = location.repository
            try:
                tree = location.bzrdir.open_workingtree()
            except errors.NoWorkingTree:
                tree = None
            fp = None
        else:
            tree, br, repo, fp = open_containing_tree_branch_or_repository(location)
        
        if br == None:
            for br in repo.find_branches(using=True):
                tag = br.nick
                try:
                    tree = br.bzrdir.open_workingtree()
                except errors.NoWorkingTree:
                    tree = None
                append_location(tree, br, repo, '', tag)
            continue
        
        # If no locations were sepecified, don't do file_ids
        # Otherwise it gives you the history for the dir if you are
        # in a sub dir.
        if fp != '' and not locations_list:
            fp = ''
        
        if len(locations) == 1:
            tag = None
        else:
            tag = br.nick
        
        append_location(tree, br, repo, fp, tag)

    
    if file_ids and len(branches)>1:
        raise errors.BzrCommandError(paths_and_branches_err)
    
    return (branches.values(), heads, file_ids)


class LogWindow(QBzrWindow):
    
    def __init__(self, locations, branch, specific_fileids, parent=None):
        if branch:
            self.locations = (branch)
        else:
            self.locations = locations
            if self.locations is None:
                self.locations = ["."]
        
        (self.branches,
         self.heads,
         self.specific_fileids) = load_locataions(self.locations)
        
        if specific_fileids:
            self.specific_fileids = specific_fileids
        
        lt = self._locations_for_title(self.locations)
        title = [gettext("Log")]
        if lt:
            title.append(lt)
        QBzrWindow.__init__(self, title, parent)
        self.restoreSize("log", (710, 580))
        
        self.replace = {}
        for branch in self.branches:
            config = branch.get_config()
            replace = config.get_user_option("qlog_replace")
            if replace:
                replace = replace.split("\n")
                replace = [tuple(replace[2*i:2*i+2])
                                for i in range(len(replace) // 2)]
            self.replace[branch.base] = replace

        self.changesModel = logmodel.GraphModel()

        self.changesProxyModel = logmodel.GraphFilterProxyModel()
        self.changesProxyModel.setSourceModel(self.changesModel)
        self.changesProxyModel.setFilterCaseSensitivity(QtCore.Qt.CaseInsensitive)
        self.changesProxyModel.setFilterRole(logmodel.FilterMessageRole)
        self.changesProxyModel.setDynamicSortFilter(True)
        self.changesModel.setGraphFilterProxyModel(self.changesProxyModel)
        
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
            
        self.index = None
        if have_search:
            try:
                self.index = search_index.open_index_branch(self.branches[0])
                self.changesProxyModel.setSearchIndex(self.index)
                self.searchType.insertItem(0,
                                           gettext("Messages and File text (indexed)"),
                                           QtCore.QVariant(logmodel.FilterSearchRole))
                
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
            except search_errors.NoSearchIndex:
                pass
        
        self.searchType.addItem(gettext("Messages"),
                                QtCore.QVariant(logmodel.FilterMessageRole))
        self.searchType.addItem(gettext("Authors"),
                                QtCore.QVariant(logmodel.FilterAuthorRole))
        self.searchType.addItem(gettext("Revision IDs"),
                                QtCore.QVariant(logmodel.FilterIdRole))
        self.searchType.addItem(gettext("Revision Numbers"),
                                QtCore.QVariant(logmodel.FilterRevnoRole))
        searchbox.addWidget(self.searchType)
        self.connect(self.searchType,
                     QtCore.SIGNAL("currentIndexChanged(int)"),
                     self.updateSearchType)

        logbox.addLayout(searchbox)

        self.changesList = QtGui.QTreeView()
        self.changesList.setContextMenuPolicy(QtCore.Qt.CustomContextMenu)
        self.changesList.setModel(self.changesProxyModel)
        self.changesList.setSelectionMode(QtGui.QAbstractItemView.ContiguousSelection)
        self.changesList.setUniformRowHeights(True)
        if self.style().objectName() != 'gtk':
            self.changesList.setAllColumnsShowFocus(True)
        self.changesList.setRootIsDecorated (False)
        self.changesList.setVerticalScrollBarPolicy(QtCore.Qt.ScrollBarAlwaysOn)
        header = self.changesList.header()
        header.setStretchLastSection(False)
        header.setResizeMode(logmodel.COL_REV, QtGui.QHeaderView.Interactive)
        header.setResizeMode(logmodel.COL_MESSAGE, QtGui.QHeaderView.Stretch)
        header.setResizeMode(logmodel.COL_DATE, QtGui.QHeaderView.Interactive)
        header.setResizeMode(logmodel.COL_AUTHOR, QtGui.QHeaderView.Interactive)
        header.resizeSection(logmodel.COL_REV, 70)
        header.resizeSection(logmodel.COL_DATE, 100)
        header.resizeSection(logmodel.COL_AUTHOR, 150)

        logbox.addWidget(self.changesList)

        self.revision_delta_timer = QtCore.QTimer(self)
        self.revision_delta_timer.setSingleShot(True)
        self.connect(self.revision_delta_timer, QtCore.SIGNAL("timeout()"),
                     self.update_revision_delta)

        self.current_rev = None
        self.connect(self.changesList.selectionModel(),
                     QtCore.SIGNAL("selectionChanged(QItemSelection, QItemSelection)"),
                     self.update_selection)
        self.connect(self.changesList,
                     QtCore.SIGNAL("doubleClicked(QModelIndex)"),
                     self.show_differences)
        self.connect(self.changesList,
                     QtCore.SIGNAL("customContextMenuRequested(QPoint)"),
                     self.show_context_menu)
        #self.connect(self.changesList,
        #             QtCore.SIGNAL("clicked (QModelIndex)"),
        #             self.changesList_clicked)
        self.changesList.mouseReleaseEvent  = self.changesList_mouseReleaseEvent
        self.changesList.keyPressEvent  = self.changesList_keyPressEvent
        
        self.changesList.setItemDelegateForColumn(logmodel.COL_MESSAGE,
                                                  GraphTagsBugsItemDelegate(self))

        self.last_item = None
        #self.merge_stack = [self.changesModel.invisibleRootItem()]

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

        self.diffbutton = QtGui.QPushButton(gettext('Diff'),
            self.centralwidget)
        self.diffbutton.setEnabled(False)
        self.connect(self.diffbutton, QtCore.SIGNAL("clicked(bool)"), self.diff_pushed)

        self.contextMenu = QtGui.QMenu(self)
        self.show_diff_action = self.contextMenu.addAction(
            gettext("Show &differences..."), self.diff_pushed)
        self.contextMenu.addAction(gettext("Show &tree..."), self.show_revision_tree)
        self.contextMenu.setDefaultAction(self.show_diff_action)

        vbox = QtGui.QVBoxLayout(self.centralwidget)
        vbox.addWidget(splitter)
        hbox = QtGui.QHBoxLayout()
        hbox.addWidget(self.diffbutton)
        hbox.addWidget(buttonbox)
        vbox.addLayout(hbox)
        self.windows = []
        # set focus on search edit widget
        self.changesList.setFocus()

    def show(self):
        QBzrWindow.show(self)
        QtCore.QTimer.singleShot(1, self.load_history)

    def link_clicked(self, url):
        scheme = unicode(url.scheme())
        if scheme == 'qlog-revid':
            revision_id = unicode(url.path())
            self.changesModel.ensure_rev_visible(revision_id)
            index = self.changesModel.indexFromRevId(revision_id)
            index = self.changesProxyModel.mapFromSource(index)
            self.changesList.setCurrentIndex(index)
        else:
            open_browser(str(url.toEncoded()))

    def update_revision_delta(self):
        rev = self.current_rev
        if not hasattr(rev, 'delta'):
            # TODO move this to a thread
            rev.repository.lock_read()
            try:
                rev.delta = rev.repository.get_deltas_for_revisions(
                    [rev]).next()
            finally:
                rev.repository.unlock()
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

    def update_selection(self, selected, deselected):
        indexes = [index for index in self.changesList.selectedIndexes() if index.column()==0]
        self.fileList.clear()
        if not indexes:
            self.diffbutton.setEnabled(False)
            self.message.setHtml("")
        else:
            self.diffbutton.setEnabled(True)
            index = indexes[0]
            revid = str(index.data(logmodel.RevIdRole).toString())
            rev = self.changesModel.revision(revid)
            self.current_rev = rev
            head_info = self.changesModel.revisionHeadInfo(revid)
            branch = head_info[0][0]
            replace = self.replace[branch.base]
            self.message.setHtml(format_revision_html(rev, replace))
            self.revision_delta_timer.start(1)

    def show_diff_window(self, rev1, rev2, specific_files=None):
        if not rev2.parent_ids:
            tree = rev1.repository.revision_tree(rev1.revision_id)
            old_tree = rev1.repository.revision_tree(None)
        elif rev1.repository.base == rev2.repository.base:
            revs = [rev1.revision_id, rev2.parent_ids[0]]
            tree, old_tree = rev1.repository.revision_trees(revs)
        else:
            tree = rev1.repository.revision_tree(rev1.revision_id)
            old_tree = rev2.repository.revision_tree(rev2.parent_ids[0])
        
        rev1_head_info = self.changesModel.revisionHeadInfo(rev1.revision_id)
        rev2_head_info = self.changesModel.revisionHeadInfo(rev2.revision_id)
        
        window = DiffWindow(old_tree, tree,
                            rev2_head_info[0][0], rev1_head_info[0][0],
                            specific_files=specific_files)
        window.show()
        self.windows.append(window)

    def show_differences(self, index):
        """Show differences of a single revision"""
        revid = str(index.data(logmodel.RevIdRole).toString())
        rev = self.changesModel.revision(revid)
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

    def diff_pushed(self):
        """Show differences of the selected range or of a single revision"""
        indexes = [index for index in self.changesList.selectedIndexes() if index.column()==0]
        if not indexes:
            # the list is empty
            return
        revid1 = str(indexes[0].data(logmodel.RevIdRole).toString())
        rev1 = self.changesModel.revision(revid1)
        revid2 = str(indexes[-1].data(logmodel.RevIdRole).toString())
        rev2 = self.changesModel.revision(revid2)
        self.show_diff_window(rev1, rev2)

    def refresh(self):
        self.refresh_button.setDisabled(True)
        QtCore.QCoreApplication.processEvents()
        try:
            self.changesModel.stop_revision_loading = True
            if "locations" in dir(self):
                
                # The new branches will be the same as the old self.branches, so
                # don't change it, because doing so causes a UserWarning:
                # LockableFiles was gc'd while locked
                (newbranches,
                 self.heads, 
                 self.specific_fileids) = load_locataions(self.locations)
            
            self.changesModel.loadBranch(self.branches,
                                         self.heads,
                                         specific_fileids = self.specific_fileids)
        finally:
            self.refresh_button.setDisabled(False)
    
    def load_history(self):
        """Load branch history."""
        self.refresh_button.setDisabled(True)
        try:
            self.changesModel.loadBranch(self.branches,
                                         self.heads,
                                         specific_fileids = self.specific_fileids)
        finally:
            self.refresh_button.setDisabled(False)

    def update_search(self):
        # TODO in_paths = self.search_in_paths.isChecked()
        role = self.searchType.itemData(self.searchType.currentIndex()).toInt()[0]
        search_text = self.search_edit.text()
        search_mode = not role == logmodel.FilterIdRole and \
                      not role == logmodel.FilterRevnoRole and \
                      not role == logmodel.FilterSearchRole and \
                      search_text.length() > 0
        self.changesModel.set_search_mode(search_mode)
        if role == logmodel.FilterIdRole:
            self.changesProxyModel.setFilter(u"", role)
            search_text = str(search_text)
            if self.changesModel.has_rev_id(search_text):
                self.changesModel.ensure_rev_visible(search_text)
                index = self.changesModel.indexFromRevId(search_text)
                index = self.changesProxyModel.mapFromSource(index)
                self.changesList.setCurrentIndex(index)
        elif role == logmodel.FilterRevnoRole:
            self.changesProxyModel.setFilter(u"", role)
            try:
                revno = tuple((int(number) for number in str(search_text).split('.')))
            except ValueError:
                revno = ()
                # Not sure what to do if there is an error. Nothing for now
            revid = self.changesModel.revid_from_revno(revno)
            if revid:
                self.changesModel.ensure_rev_visible(revid)
                index = self.changesModel.indexFromRevId(revid)
                index = self.changesProxyModel.mapFromSource(index)
                self.changesList.setCurrentIndex(index)
        else:
            self.changesProxyModel.setFilter(self.search_edit.text(), role)
    
    
    def update_search_completer(self, text):
        # We only load the suggestions a letter at a time when needed.
        term = str(text).split(" ")[-1]
        if term:
            first_letter = term[0]
        else:
            first_letter = ""
        
        if first_letter != self.suggestion_last_first_letter:
            self.suggestion_last_first_letter = first_letter
            if first_letter not in self.suggestion_letters_loaded:
                suggestions = QtCore.QStringList() 
                for s in self.index.suggest(((first_letter,),)): 
                    #if suggestions.count() % 100 == 0: 
                    #    QtCore.QCoreApplication.processEvents() 
                    suggestions.append(s[0])
                suggestions.sort()
                self.suggestion_letters_loaded[first_letter] = suggestions
            else:
                suggestions = self.suggestion_letters_loaded[first_letter]
            self.completer_model.setStringList(suggestions)
    
    def closeEvent (self, QCloseEvent):
        QBzrWindow.closeEvent(self, QCloseEvent)
        self.changesModel.closing = True
    
    def updateSearchType(self, index=None):
        self.update_search()

    def set_search_timer(self):
        self.search_timer.start(200)

    def show_revision_tree(self):
        from bzrlib.plugins.qbzr.lib.browse import BrowseWindow
        rev = self.current_rev
        window = BrowseWindow(rev.first_branch, revision_id=rev.revision_id,
                              revision_spec=rev.revno, parent=self)
        window.show()
        self.windows.append(window)

    def show_context_menu(self, pos):
        index = self.changesList.indexAt(pos)
        revid = str(index.data(logmodel.RevIdRole).toString())
        rev = self.changesModel.revision(revid)
        #print index, item, rev
        self.contextMenu.popup(self.changesList.viewport().mapToGlobal(pos))
    
    def changesList_mouseReleaseEvent (self, e):
        if e.button() & QtCore.Qt.LeftButton:
            pos = e.pos()
            index = self.changesList.indexAt(pos)
            rect = self.changesList.visualRect(index)
            boxsize = rect.height()
            node = index.data(logmodel.GraphNodeRole).toList()
            if len(node)>0:
                node_column = node[0].toInt()[0]
                twistyRect = QtCore.QRect (rect.x() + boxsize * node_column,
                                           rect.y() ,
                                           boxsize,
                                           boxsize)
                if twistyRect.contains(pos):
                    e.accept ()
                    twisty_state = index.data(logmodel.GraphTwistyStateRole)
                    if twisty_state.isValid():
                        revision_id = str(index.data(logmodel.RevIdRole).toString())
                        self.changesModel.colapse_expand_rev(revision_id, not twisty_state.toBool())
        QtGui.QTreeView.mouseReleaseEvent(self.changesList, e)
    
    def changesList_keyPressEvent (self, e):
        e_key = e.key()
        if e_key in (QtCore.Qt.Key_Left, QtCore.Qt.Key_Right):
            e.accept()
            indexes = [index for index in self.changesList.selectedIndexes() if index.column()==0]
            if not indexes:
                return
            index = indexes[0]
            revision_id = str(index.data(logmodel.RevIdRole).toString())
            twisty_state = index.data(logmodel.GraphTwistyStateRole)
            if e.key() == QtCore.Qt.Key_Right \
                    and twisty_state.isValid() \
                    and not twisty_state.toBool():
                self.changesModel.colapse_expand_rev(revision_id, True)
            if e.key() == QtCore.Qt.Key_Left:
                if twisty_state.isValid() and twisty_state.toBool():
                    self.changesModel.colapse_expand_rev(revision_id, False)
                else:
                    #find merge of child branch
                    revision_id = self.changesModel.findChildBranchMergeRevision(revision_id)
                    if revision_id is None:
                        return
            newindex = self.changesModel.indexFromRevId(revision_id)
            newindex = self.changesProxyModel.mapFromSource(newindex)
            self.changesList.setCurrentIndex(newindex)
        elif e_key in (QtCore.Qt.Key_Enter, QtCore.Qt.Key_Return):
            e.accept()
            self.diff_pushed()
        else:
            QtGui.QTreeView.keyPressEvent(self.changesList, e)

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
