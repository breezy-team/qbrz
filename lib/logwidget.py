# -*- coding: utf-8 -*-
#
# QBzr - Qt frontend to Bazaar commands
# Copyright (C) 2006-2007 Gary van der Merwe <garyvdm@gmail.com> 
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

from PyQt4 import QtCore, QtGui, Qt

from bzrlib.bzrdir import BzrDir
from bzrlib.plugins.qbzr.lib.revtreeview import (RevisionTreeView,
                                                 RevNoItemDelegate)
from bzrlib.plugins.qbzr.lib import logmodel
from bzrlib.plugins.qbzr.lib.trace import *
from bzrlib.plugins.qbzr.lib.util import (
    runs_in_loading_queue,
    )
from bzrlib.plugins.qbzr.lib import diff

class LogList(RevisionTreeView):
    """TreeView widget to show log with metadata and graph of revisions."""

    def __init__(self, processEvents, throbber, no_graph, parent=None,
                 view_commands=True, action_commands=False):
        """Costructing new widget.
        @param  throbber:   throbber widget in parent window
        @param  parent:     parent window
        """
        RevisionTreeView.__init__(self, parent)
        self.setContextMenuPolicy(QtCore.Qt.CustomContextMenu)
        self.setSelectionMode(QtGui.QAbstractItemView.ContiguousSelection)
        self.setUniformRowHeights(True)
        self.setAllColumnsShowFocus(True)
        self.setRootIsDecorated (False)
        self.setVerticalScrollBarPolicy(QtCore.Qt.ScrollBarAlwaysOn)

        self.setItemDelegateForColumn(logmodel.COL_MESSAGE,
                                      GraphTagsBugsItemDelegate(self))
        self.setItemDelegateForColumn(logmodel.COL_REV,
                                      RevNoItemDelegate(parent=self))
        self.processEvents = processEvents
        self.throbber = throbber

        self.graph_provider = logmodel.QLogGraphProvider(self.processEvents,
                                                         self.throbber,
                                                         no_graph)

        self.log_model = logmodel.LogModel(self.graph_provider, self)

        self.filter_proxy_model = logmodel.LogFilterProxyModel(self.graph_provider, self)
        self.filter_proxy_model.setSourceModel(self.log_model)
        self.filter_proxy_model.setDynamicSortFilter(True)

        self.setModel(self.filter_proxy_model)
        
        header = self.header()
        header.setStretchLastSection(False)
        header.setResizeMode(logmodel.COL_REV, QtGui.QHeaderView.Interactive)
        header.setResizeMode(logmodel.COL_MESSAGE, QtGui.QHeaderView.Stretch)
        header.setResizeMode(logmodel.COL_DATE, QtGui.QHeaderView.Interactive)
        header.setResizeMode(logmodel.COL_AUTHOR, QtGui.QHeaderView.Interactive)
        fm = self.fontMetrics()
        # XXX Make this dynamic.
        col_margin = 6
        header.resizeSection(logmodel.COL_REV,
                             fm.width("8888.8.888") + col_margin)
        header.resizeSection(logmodel.COL_DATE,
                             fm.width("88-88-8888 88:88") + col_margin)
        header.resizeSection(logmodel.COL_AUTHOR,
                             fm.width("Joe I have a Long Name") + col_margin)

        self.view_commands = view_commands
        self.action_commands = action_commands
        
        if self.view_commands:
            self.connect(self,
                         QtCore.SIGNAL("doubleClicked(QModelIndex)"),
                         self.show_diff_index)
        self.context_menu = QtGui.QMenu(self)

    def create_context_menu(self):
        self.context_menu = QtGui.QMenu(self)
        if self.view_commands or self.action_commands:
            if self.graph_provider.fileids:
                if diff.has_ext_diff():
                    diff_menu = diff.ExtDiffMenu(self)
                    diff_menu.setTitle(gettext("Show file &differences"))
                    self.context_menu.addMenu(diff_menu)
                    self.connect(diff_menu, QtCore.SIGNAL("triggered(QString)"),
                                 self.show_diff_current_indexes)
                    
                    all_diff_menu = diff.ExtDiffMenu(self, set_default=False)
                    all_diff_menu.setTitle(gettext("Show all &differences"))
                    self.context_menu.addMenu(all_diff_menu)
                    self.connect(all_diff_menu, QtCore.SIGNAL("triggered(QString)"),
                                 self.show_diff_current_indexes_all_files)
                else:
                    show_diff_action = self.context_menu.addAction(
                                        gettext("Show file &differences..."),
                                        self.show_diff_current_indexes)
                    self.context_menu.setDefaultAction(show_diff_action)
                    self.context_menu.addAction(
                                        gettext("Show all &differences..."),
                                        self.show_diff_current_indexes_all_files)
            else:
                if diff.has_ext_diff():
                    diff_menu = diff.ExtDiffMenu(self)
                    self.context_menu.addMenu(diff_menu)
                    self.connect(diff_menu, QtCore.SIGNAL("triggered(QString)"),
                                 self.show_diff_current_indexes)
                else:
                    show_diff_action = self.context_menu.addAction(
                                        gettext("Show &differences..."),
                                        self.show_diff_current_indexes)
                    self.context_menu.setDefaultAction(show_diff_action)

            self.connect(self,
                         QtCore.SIGNAL("customContextMenuRequested(QPoint)"),
                         self.show_context_menu)
            
            self.context_menu.addAction(gettext("Show &tree..."),
                                        self.show_revision_tree)        

    def load_branch(self, branch, fileids, tree=None):
        self.throbber.show()
        try:
            self.graph_provider.open_branch(branch, fileids, tree)
            self.create_context_menu()
            self.load_current_dir_repo_if_no_local_repos()
            self.processEvents()
            self.load()
        finally:
            self.throbber.hide()
    
    def load_locations(self, locations):
        self.throbber.show()
        try:
            self.graph_provider.open_locations(locations)
            self.create_context_menu()
            self.load_current_dir_repo_if_no_local_repos()
            self.processEvents()
            self.load()
        finally:
            self.throbber.hide()
    
    def load_current_dir_repo_if_no_local_repos(self):
        # There are no local repositories. Try open the repository
        # of the current directory, and try load revsions data from
        # this before trying from remote repositories. This makes
        # the common use case of viewing a remote branch that is
        # related to the current branch much faster, because most
        # of the revision can be loaded from the local repoistory.
        has_local_repo = False
        for repo in self.graph_provider.repos.values():
            if repo.is_local:
                has_local_repo = True
                break
        if not has_local_repo:
            try:
                bzrdir, relpath = BzrDir.open_containing(".")
                repo = bzrdir.find_repository()
                self.graph_provider.append_repo(repo, local_copy = True)
            except Exception:
                pass
    
    def refresh(self):
        self.throbber.show()
        try:
            self.load()
        finally:
            self.throbber.hide()
    
    def load(self):
        self.graph_provider.lock_read_branches()
        try:
            self.graph_provider.load_tags()
            self.log_model.load_graph_all_revisions()
        finally:
            self.graph_provider.unlock_branches()
        
        # Start later so that it does not run in the loading queue.
        QtCore.QTimer.singleShot(1, self.graph_provider.load_filter_file_id)

    def mousePressEvent (self, e):
        colapse_expand_click = False
        if e.button() & QtCore.Qt.LeftButton:
            pos = e.pos()
            index = self.indexAt(pos)
            rect = self.visualRect(index)
            boxsize = rect.height()
            node = index.data(logmodel.GraphNodeRole).toList()
            if len(node)>0:
                node_column = node[0].toInt()[0]
                twistyRect = QtCore.QRect (rect.x() + boxsize * node_column,
                                           rect.y() ,
                                           boxsize,
                                           boxsize)
                if twistyRect.contains(pos):
                    twisty_state = index.data(logmodel.GraphTwistyStateRole)
                    if twisty_state.isValid():
                        colapse_expand_click = True
                        revision_id = str(index.data(logmodel.RevIdRole).toString())
                        self.log_model.colapse_expand_rev(revision_id, not twisty_state.toBool())
                        e.accept ()
        if not colapse_expand_click:
            QtGui.QTreeView.mousePressEvent(self, e)
    
    def mouseMoveEvent (self, e):
        colapse_expand_click = False
        pos = e.pos()
        index = self.indexAt(pos)
        rect = self.visualRect(index)
        boxsize = rect.height()
        node = index.data(logmodel.GraphNodeRole).toList()
        if len(node)>0:
            node_column = node[0].toInt()[0]
            twistyRect = QtCore.QRect (rect.x() + boxsize * node_column,
                                       rect.y() ,
                                       boxsize,
                                       boxsize)
            if twistyRect.contains(pos):
                twisty_state = index.data(logmodel.GraphTwistyStateRole)
                if twisty_state.isValid():
                    colapse_expand_click = True
        if not colapse_expand_click:
            QtGui.QTreeView.mouseMoveEvent(self, e)


    def keyPressEvent (self, e):
        e_key = e.key()
        if e_key in (QtCore.Qt.Key_Enter, QtCore.Qt.Key_Return) and self.view_commands:
            e.accept()
            self.show_diff_current_indexes()
        elif e_key in (QtCore.Qt.Key_Left, QtCore.Qt.Key_Right):
            e.accept()
            indexes = [index for index in self.selectedIndexes() if index.column()==0]
            if not indexes:
                return
            index = indexes[0]
            revision_id = str(index.data(logmodel.RevIdRole).toString())
            twisty_state = index.data(logmodel.GraphTwistyStateRole)
            if e.key() == QtCore.Qt.Key_Right \
                    and twisty_state.isValid() \
                    and not twisty_state.toBool():
                self.log_model.colapse_expand_rev(revision_id, True)
            if e.key() == QtCore.Qt.Key_Left:
                if twisty_state.isValid() and twisty_state.toBool():
                    self.log_model.colapse_expand_rev(revision_id, False)
                else:
                    #find merge of child branch
                    revision_id = self.graph_provider.\
                                  find_child_branch_merge_revision(revision_id)
                    if revision_id is None:
                        return
            newindex = self.log_model.indexFromRevId(revision_id)
            newindex = self.filter_proxy_model.mapFromSource(newindex)
            self.setCurrentIndex(newindex)
            self.load_visible_revisions()
        else:
            QtGui.QTreeView.keyPressEvent(self, e)
    
    def set_search(self, str, field):
        self.graph_provider.set_search(str, field)
    
    def show_diff(self, new_rev, old_rev,
                  specific_files=None, specific_file_ids=None,
                  ext_diff=None):
        new_revid = new_rev.revision_id
        new_branch = self.graph_provider.get_revid_branch(new_revid)
        
        if not old_rev.parent_ids:
            old_revid = None
            old_branch = new_branch
        else:
            old_revid = old_rev.parent_ids[0]
            old_branch =  self.graph_provider.get_revid_branch(old_revid)
        
        arg_provider = diff.InternalDiffArgProvider(
                                        old_revid, new_revid,
                                        old_branch, new_branch,
                                        specific_files = specific_files,
                                        specific_file_ids = specific_file_ids)
        
        diff.show_diff(arg_provider, ext_diff = ext_diff,
                       parent_window = self.window())

    def show_diff_index(self, index):
        """Show differences of a single revision from a index."""
        revid = str(index.data(logmodel.RevIdRole).toString())
        rev = self.graph_provider.load_revisions([revid])[revid]
        if self.graph_provider.fileids:
            self.show_diff(rev, rev,
                           specific_file_ids=self.graph_provider.fileids)
        else:
            self.show_diff(rev, rev)
    
    def show_diff_current_indexes(self, ext_diff=None,
                                  only_specified_files=True):
        """Show differences of the selected range or of a single revision"""
        # Find 1 index for each row.
        rows = {}
        for index in self.selectedIndexes():
            if index.row() not in rows:
                rows[index.row()] = index
        indexes = rows.values()
        if not indexes:
            # the list is empty
            return
        revid1 = str(indexes[0].data(logmodel.RevIdRole).toString())
        revid2 = str(indexes[-1].data(logmodel.RevIdRole).toString())
        revs = self.graph_provider.load_revisions([revid1, revid2])
        rev1 = revs[revid1]
        rev2 = revs[revid2]
        if only_specified_files and self.graph_provider.fileids:
            self.show_diff(rev1, rev2, ext_diff=ext_diff,
                           specific_file_ids = self.graph_provider.fileids)
        else:
            self.show_diff(rev1, rev2, ext_diff=ext_diff)
    
    def show_diff_current_indexes_all_files(self, ext_diff=None):
        self.show_diff_current_indexes(ext_diff=ext_diff,
                                       only_specified_files=False)
    
    def show_revision_tree(self):
        from bzrlib.plugins.qbzr.lib.browse import BrowseWindow
        revid = str(self.currentIndex().data(logmodel.RevIdRole).toString())
        revno = self.graph_provider.revid_rev[revid].revno_str
        branch = self.graph_provider.get_revid_branch(revid)
        window = BrowseWindow(branch, revision_id=revid,
                              revision_spec=revno, parent=self)
        window.show()
        self.window().windows.append(window)

    def show_context_menu(self, pos):
        self.context_menu.popup(self.viewport().mapToGlobal(pos))

    
class GraphTagsBugsItemDelegate(QtGui.QItemDelegate):

    _tagColor = QtGui.QColor(80, 128, 32)
    _bugColor = QtGui.QColor(164, 0, 0)
    _branchTagColor = QtGui.QColor(24, 80, 200)
    _labelColor = QtCore.Qt.white

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
                (tag, self._branchTagColor))
        # collect tag names
        for tag in index.data(logmodel.TagsRole).toStringList():
            self.labels.append(
                (tag, self._tagColor))
        # collect bug ids
        for bug in index.data(logmodel.BugIdsRole).toStringList():
            self.labels.append(
                (bug, self._bugColor))
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

        if not hasattr(self, '_usingGtkStyle'):
            self._usingGtkStyle = Qt.qApp.style().objectName() == 'gtk+'
            self._usingQt45 = Qt.qVersion() >= '4.5' 

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
                if not self._usingQt45:
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
                i, is_int = self.twisty_state.toInt()
                is_clicked = (is_int and i == -1)
                
                color = self.node[1].toInt()[0]
                column = self.node[0].toInt()[0]
                graphCols = max((graphCols, column))
                pen.setColor(self.get_color(color,False))
                painter.setPen(pen)
                if not is_clicked:
                    painter.setBrush(QtGui.QBrush(self.get_color(color,True)))
                else:
                    painter.setBrush(QtGui.QBrush(QtCore.Qt.white))
                    
                centerx = rect.x() + boxsize * (column + 0.5)
                centery = rect.y() + boxsize * 0.5
                painter.drawEllipse(
                    QtCore.QRectF(centerx - (boxsize * dotsize * 0.5 ),
                                  centery - (boxsize * dotsize * 0.5 ),
                                 boxsize * dotsize, boxsize * dotsize))

                # Draw twisty
                if not is_clicked and self.twisty_state.isValid():
                    linesize = 0.35
                    pen.setColor(self._twistyColor)
                    painter.setPen(pen)
                    i, is_int = self.twisty_state.toInt()
                    if is_int and i == -1:
                        painter.drawEllipse(
                            QtCore.QRectF(centerx - (boxsize * dotsize * 0.25 ),
                                          centery - (boxsize * dotsize * 0.25 ),
                                          boxsize * dotsize * 0.5,
                                          boxsize * dotsize * 0.5))
                    else:
                        painter.drawLine(QtCore.QLineF
                                         (centerx - boxsize * linesize / 2,
                                          centery,
                                          centerx + boxsize * linesize / 2,
                                          centery))
                        if not self.twisty_state.toBool():
                            painter.drawLine(QtCore.QLineF
                                             (centerx,
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
            for label, color in self.labels:
                tagRect = rect.adjusted(1, 1, -1, -1)
                tagRect.setWidth(QtGui.QFontMetrics(tagFont).width(label) + 6)
                tagRect.moveLeft(tagRect.x() + x)
                painter.fillRect(tagRect.adjusted(1, 1, -1, -1), color)
                painter.setPen(color)
                tl = tagRect.topLeft()
                br = tagRect.bottomRight()
                painter.drawLine(tl.x(), tl.y() + 1, tl.x(), br.y() - 1)
                painter.drawLine(br.x(), tl.y() + 1, br.x(), br.y() - 1)
                painter.drawLine(tl.x() + 1, tl.y(), br.x() - 1, tl.y())
                painter.drawLine(tl.x() + 1, br.y(), br.x() - 1, br.y())
                painter.setFont(tagFont)
                painter.setPen(self._labelColor)
                if self._usingGtkStyle:
                    painter.drawText(tagRect.left() + 3, tagRect.bottom() - option.fontMetrics.descent(), label)
                else:
                    painter.drawText(tagRect.left() + 3, tagRect.bottom() - option.fontMetrics.descent() + 1, label)
                x += tagRect.width() + 3
        finally:
            painter.restore()
        
        rect.adjust( x, 0, 0, 0)
        
        return QtGui.QItemDelegate.drawDisplay(self, painter, option, rect, text)
