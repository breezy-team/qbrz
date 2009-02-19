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

from PyQt4 import QtCore, QtGui
from bzrlib.plugins.qbzr.lib import logmodel
from bzrlib.plugins.qbzr.lib.util import StopException


class LogList(QtGui.QTreeView):
    """TreeView widget to show log with metadata and graph of revisions."""

    def __init__(self, processEvents, report_exception,
                 throbber, parent=None):
        """Costructing new widget.
        @param  throbber:   throbber widget in parent window
        @param  parent:     parent window
        """
        QtGui.QTreeView.__init__(self, parent)
        self.setContextMenuPolicy(QtCore.Qt.CustomContextMenu)
        self.setSelectionMode(QtGui.QAbstractItemView.ContiguousSelection)
        self.setUniformRowHeights(True)        
        self.setAllColumnsShowFocus(True)
        self.setRootIsDecorated (False)
        self.setVerticalScrollBarPolicy(QtCore.Qt.ScrollBarAlwaysOn)
        self.connect(self.verticalScrollBar(), QtCore.SIGNAL("valueChanged (int)"),
                     self.scroll_changed)

        self.setItemDelegateForColumn(logmodel.COL_MESSAGE,
                                        GraphTagsBugsItemDelegate(self))

        self.processEvents = processEvents
        self.throbber = throbber
        self.report_exception = report_exception

        self.graph_provider = logmodel.QLogGraphProvider(self.processEvents,
                                                         self.report_exception,
                                                         self.throbber)

        self.model = logmodel.LogModel(self.graph_provider, self)

        self.filter_proxy_model = logmodel.LogFilterProxyModel(self.graph_provider, self)
        self.filter_proxy_model.setSourceModel(self.model)
        self.filter_proxy_model.setDynamicSortFilter(True)

        self.setModel(self.filter_proxy_model)
        self.connect(self.model,
                     QtCore.SIGNAL("dataChanged(QModelIndex, QModelIndex)"),
                     self.model_data_changed)

        header = self.header()
        header.setStretchLastSection(False)
        header.setResizeMode(logmodel.COL_REV, QtGui.QHeaderView.Interactive)
        header.setResizeMode(logmodel.COL_MESSAGE, QtGui.QHeaderView.Stretch)
        header.setResizeMode(logmodel.COL_DATE, QtGui.QHeaderView.Interactive)
        header.setResizeMode(logmodel.COL_AUTHOR, QtGui.QHeaderView.Interactive)
        header.resizeSection(logmodel.COL_REV, 70)
        header.resizeSection(logmodel.COL_DATE, 100) # TODO - Make this dynamic
        header.resizeSection(logmodel.COL_AUTHOR, 150)

        self.load_revisions_call_count = 0
        self.load_revisions_throbber_shown = False

    def load_branch(self, branch, specific_fileids):
        self.throbber.show()
        try:
            self.graph_provider.open_branch(branch, specific_fileids)
            self.processEvents()
            self.load()
        finally:
            self.throbber.hide()
    
    def load_locations(self, locations):
        self.throbber.show()
        try:
            self.graph_provider.open_locations(locations)
            self.processEvents()
            self.load()
        finally:
            self.throbber.hide()
    
    def refresh(self):
        self.throbber.show()
        try:
            self.graph_provider.unlock_repos()
            self.load()
        finally:
            self.throbber.hide()
    
    def load(self):
        self.graph_provider.lock_read_branches()
        try:
            self.graph_provider.load_branch_heads()
            self.graph_provider.load_tags()
        finally:
            self.graph_provider.unlock_branches()
        
        self.graph_provider.lock_read_repos()
        # And will remain locked until the window is closed or we refresh.
        self.model.loadBranch()
        
        self.graph_provider.load_filter_file_id()
        
        self.load_visible_revisions()
    
    def closeEvent (self, QCloseEvent):
        self.graph_provider.unlock_repos()

    def mouseReleaseEvent (self, e):
        try:
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
                            revision_id = str(index.data(logmodel.RevIdRole).toString())
                            self.model.colapse_expand_rev(revision_id, not twisty_state.toBool())
                            e.accept ()
            QtGui.QTreeView.mouseReleaseEvent(self, e)
        except:
            self.report_exception()

    def keyPressEvent (self, e):
        try:
            e_key = e.key()
            if e_key in (QtCore.Qt.Key_Left, QtCore.Qt.Key_Right):
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
                    self.model.colapse_expand_rev(revision_id, True)
                if e.key() == QtCore.Qt.Key_Left:
                    if twisty_state.isValid() and twisty_state.toBool():
                        self.model.colapse_expand_rev(revision_id, False)
                    else:
                        #find merge of child branch
                        revision_id = self.graph_provider.\
                                      find_child_branch_merge_revision(revision_id)
                        if revision_id is None:
                            return
                newindex = self.model.indexFromRevId(revision_id)
                newindex = self.filter_proxy_model.mapFromSource(newindex)
                self.setCurrentIndex(newindex)
                self.load_visible_revisions()
            else:
                QtGui.QTreeView.keyPressEvent(self, e)
        except:
            self.report_exception()
    
    def scroll_changed(self, value):
        try:
            self.load_visible_revisions()
        except:
            self.report_exception()
    
    def model_data_changed(self, start_index, end_index):
        try:
            self.load_visible_revisions()
        except:
            self.report_exception()
    
    def load_visible_revisions(self):
        top_index = self.indexAt(self.viewport().rect().topLeft()).row()
        bottom_index = self.indexAt(self.viewport().rect().bottomLeft()).row()
        if top_index == -1:
            #Nothing is visible
            return
        if bottom_index == -1:
            bottom_index = len(self.graph_provider.graph_line_data)-1
        # The + 2 is so that the rev that is off screen due to the throbber
        # is loaded.
        bottom_index = min((bottom_index + 2,
                            len(self.graph_provider.graph_line_data)-1))
        revids = []
        for i in xrange(top_index, bottom_index): 
            msri = self.graph_provider.graph_line_data[i][0]
            revid = self.graph_provider.merge_sorted_revisions[msri][1]
            revids.append(revid)
        
        self.load_revisions_call_count += 1
        current_call_count = self.load_revisions_call_count
        
        def before_batch_load(repo, revids):
            if current_call_count < self.load_revisions_call_count:
                return True
            
            if not repo.is_local:
                if not self.load_revisions_throbber_shown:
                    self.throbber.show()
                    self.load_revisions_throbber_shown = True
                # Allow for more scrolling to happen.
                self.delay(0.5)
            
            return False
        
        try:
            self.graph_provider.load_revisions(revids,
                            revisions_loaded = self.model.on_revisions_loaded,
                            before_batch_load = before_batch_load
                            )
        finally:
            self.load_revisions_call_count -=1
            if self.load_revisions_call_count == 0:
                # This is the last running method
                if self.load_revisions_throbber_shown:
                    self.load_revisions_throbber_shown = False
                    self.throbber.hide()
    
    def delay(self, timeout):
        
        def null():
            pass
        
        QtCore.QTimer.singleShot(timeout, null)
        self.processEvents(QtCore.QEventLoop.WaitForMoreEvents)
    
    def set_search(self, str, field):
        self.graph_provider.set_search(str, field)

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
