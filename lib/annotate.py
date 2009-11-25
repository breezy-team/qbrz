# -*- coding: utf-8 -*-
#
# QBzr - Qt frontend to Bazaar commands
# Copyright (C) 2006 Lukáš Lalinský <lalinsky@gmail.com>
# Copyright (C) 2005 Dan Loda <danloda@gmail.com>
# Copyright (C) 2009 Gary van der Merwe <garyvdm@gmail.com>
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

# TODO:
#  - better annotate algorithm on packs

import sys, time
from PyQt4 import QtCore, QtGui
from bzrlib.workingtree import WorkingTree
from bzrlib.revisiontree import RevisionTree
from bzrlib.revision import CURRENT_REVISION

from bzrlib.plugins.qbzr.lib.i18n import gettext
from bzrlib.plugins.qbzr.lib.util import (
    BTN_CLOSE,
    QBzrWindow,
    ThrobberWidget,
    get_apparent_author_name,
    get_set_encoding,
    open_browser,
    split_tokens_at_lines,
    format_for_ttype,
    runs_in_loading_queue,
    )
from bzrlib.plugins.qbzr.lib.revisionmessagebrowser import LogListRevisionMessageBrowser
from bzrlib.plugins.qbzr.lib.uifactory import ui_current_widget
from bzrlib.plugins.qbzr.lib.trace import reports_exception
from bzrlib.plugins.qbzr.lib.logwidget import LogList
from bzrlib.plugins.qbzr.lib.logmodel import COL_DATE, RevIdRole
from bzrlib.plugins.qbzr.lib.lazycachedrevloader import (load_revisions,
                                                         cached_revisions)
from bzrlib.plugins.qbzr.lib.encoding_selector import EncodingSelector
from bzrlib.plugins.qbzr.lib.syntaxhighlighter import highlight_document
from bzrlib.plugins.qbzr.lib.texteditannotate import (AnnotateBarBase,
                                                      AnnotateEditerFrameBase)
from bzrlib.plugins.qbzr.lib.revtreeview import paint_revno

class AnnotateBar(AnnotateBarBase):
    
    def __init__(self, edit, parent, get_revno):
        super(AnnotateBar, self).__init__(edit, parent)
        
        self.get_revno = get_revno
        self.annotate = None
        self.rev_colors = {}
        
        self.splitter = None
        self.adjustWidth(1, 999)
        
        edit.selectionChanged.connect(self.edit_selectionChanged)
        self.show_current_line = False

    def edit_selectionChanged(self):
        self.show_current_line = True

    def adjustWidth(self, lines, max_revno):
        fm = self.fontMetrics()
        text_margin = self.style().pixelMetric(
            QtGui.QStyle.PM_FocusFrameHMargin, None, self) + 1
        
        self.line_number_width = fm.width(unicode(lines))
        self.line_number_width += (text_margin * 2)
        
        self.revno_width = fm.width(unicode(max_revno)+".8.88")
        self.max_mainline_digits = len(unicode(max_revno))
        self.revno_width += (text_margin * 2)
        
        if self.splitter:
            if 0: self.splitter = QtGui.QSplitter
            width = (self.line_number_width + self.revno_width +
                     fm.width("Joe I have a Long Name"))
            self.splitter.setSizes([width, 1000])
        
        self.setMinimumWidth(self.line_number_width + self.revno_width)
    
    def paint_line(self, painter, rect, line_number, is_current):
        if is_current and self.show_current_line:
            option = QtGui.QStyleOptionViewItemV4()
            option.initFrom(self)
            option.state = option.state | QtGui.QStyle.State_Selected
            option.rect = rect.toRect()
            self.style().drawPrimitive(QtGui.QStyle.PE_PanelItemViewItem,
                                       option, painter, self)
        elif self.annotate and line_number-1 < len(self.annotate):
            revid, is_top = self.annotate[line_number - 1]
            if revid in self.rev_colors:
                painter.fillRect(rect, self.rev_colors[revid])
        
        text_margin = self.style().pixelMetric(
            QtGui.QStyle.PM_FocusFrameHMargin, None, self) + 1
        
        if 0: rect = QtCore.QRect
        line_number_rect = QtCore.QRect(
            rect.left() + text_margin,
            rect.top(),
            rect.left() + self.line_number_width - text_margin,
            rect.bottom())
        
        painter.drawText(line_number_rect, QtCore.Qt.AlignRight,
                         unicode(line_number))
        
        if self.annotate and line_number-1 < len(self.annotate):
            revid, is_top = self.annotate[line_number - 1]
            if is_top:
                revno_rect = QtCore.QRect(
                    line_number_rect.right() + text_margin,
                    rect.top(),
                    line_number_rect.right()  + self.revno_width - text_margin,
                    rect.bottom())
                paint_revno(painter, revno_rect,
                            QtCore.QString(self.get_revno(revid)),
                            self.max_mainline_digits)
                
                if revid in cached_revisions:
                    rev = cached_revisions[revid]
                    author_rect = QtCore.QRect(
                        revno_rect.right() + text_margin,
                        rect.top(),
                        rect.right() - text_margin,
                        rect.bottom())
                    painter.drawText(author_rect, 0,
                                     get_apparent_author_name(rev))


class AnnotatedTextEdit(QtGui.QPlainTextEdit):
    annotate = None
    rev_colors = {}

    def paintEvent(self, event):
        if self.annotate:
            block = self.firstVisibleBlock()
            painter = QtGui.QPainter(self.viewport())
            painter.setClipRect(event.rect())
            
            line_count = block.blockNumber()
            # Iterate over all visible text blocks in the document.
            while block.isValid():
                line_count += 1
                # Check if the position of the block is out side of the visible
                # area.
                rect = self.blockBoundingGeometry(block)
                rect = rect.translated(self.contentOffset())
                
                if not block.isVisible() or rect.top() >= event.rect().bottom():
                    break
                
                if line_count - 1 >= len(self.annotate):
                    break
                
                revid, is_top = self.annotate[line_count - 1]
                if revid in self.rev_colors:
                    painter.fillRect(rect, self.rev_colors[revid])
                
                block = block.next()
            del painter
        super(AnnotatedTextEdit, self).paintEvent(event)


class AnnotateWindow(QBzrWindow):

    def __init__(self, branch, tree, path, fileId, encoding=None, parent=None,
                 ui_mode=True, loader=None, loader_args=None, no_graph=False):
        QBzrWindow.__init__(self,
                            [gettext("Annotate"), gettext("Loading...")],
                            parent, ui_mode=ui_mode)
        self.restoreSize("annotate", (780, 680))

        self.windows = []

        self.branch = branch
        self.tree = tree
        if isinstance(tree, WorkingTree):
            self.working_tree = tree
        else:
            self.working_tree = None
        
        self.fileId = fileId
        self.path = path
        self.encoding = encoding
        self.loader_func = loader
        self.loader_args = loader_args

        self.throbber = ThrobberWidget(self)
        
        self.text_edit_frame = AnnotateEditerFrameBase(self)
        self.text_edit = AnnotatedTextEdit(self)
        self.text_edit.setFrameStyle(QtGui.QFrame.NoFrame)
        self.text_edit.setReadOnly(True)
        self.text_edit.document().setDefaultFont(
            QtGui.QFont("Courier New,courier", 
                        self.text_edit.font().pointSize()))
        
        self.annotate_bar = AnnotateBar(self.text_edit, self, self.get_revno)
        annotate_spliter = QtGui.QSplitter(QtCore.Qt.Horizontal, self)
        annotate_spliter.addWidget(self.annotate_bar)
        annotate_spliter.addWidget(self.text_edit)
        self.annotate_bar.splitter = annotate_spliter
        self.text_edit_frame.hbox.addWidget(annotate_spliter)
        
        self.log_list = LogList(self.processEvents, self.throbber, no_graph, self)
        self.log_list.load = self.log_list_load
        self.log_list.header().hideSection(COL_DATE)
        #self.log_list.header().hideSection(COL_AUTHOR)
        self.log_branch_loaded = False
        
        self.message = LogListRevisionMessageBrowser(self.log_list, self)

        self.encoding_selector = EncodingSelector(self.encoding,
            gettext("Encoding:"),
            self._on_encoding_changed)

        hsplitter = QtGui.QSplitter(QtCore.Qt.Horizontal)
        hsplitter.addWidget(self.log_list)
        hsplitter.addWidget(self.message)

        hsplitter.setStretchFactor(0, 2)
        hsplitter.setStretchFactor(1, 2)

        splitter = QtGui.QSplitter(QtCore.Qt.Vertical)
        splitter.addWidget(self.text_edit_frame)
        splitter.addWidget(hsplitter)

        splitter.setStretchFactor(0, 5)
        splitter.setStretchFactor(1, 2)

        buttonbox = self.create_button_box(BTN_CLOSE)

        vbox = QtGui.QVBoxLayout(self.centralwidget)
        vbox.addWidget(self.throbber)
        vbox.addWidget(splitter)
        hbox = QtGui.QHBoxLayout()
        hbox.addWidget(self.encoding_selector)
        hbox.addWidget(buttonbox)
        vbox.addLayout(hbox)
        self.text_edit.setFocus()

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
        self.throbber.show()
        try:
            if self.loader_func is not None:
                (self.branch,
                 self.tree,
                 self.working_tree,
                 self.path, self.fileId) = self.loader_func(*self.loader_args)
                self.loader_func = self.loader_args = None # kill extra refs...
                QtCore.QCoreApplication.processEvents()
            self.encoding = get_set_encoding(self.encoding, self.branch)
            self.encoding_selector.encoding = self.encoding
            self.branch.lock_read()
            try:
                self.set_annotate_title()
                self.annotate(self.tree, self.fileId, self.path)
            finally:
                self.branch.unlock()
        finally:
            self.throbber.hide()
    
    def log_list_load(self):
        gp = self.log_list.graph_provider
        gp.lock_read_branches()
        try:
            gp.load_tags()
            self.log_list.log_model.load_graph(
                gp.load_graph_all_revisions_for_annotate)
        finally:
            gp.unlock_branches()
    
    def set_annotate_title(self):
        # and update the title to show we are done.
        if isinstance(self.tree, RevisionTree):
            revno = self.get_revno(self.tree.get_revision_id())
            if revno:
                self.set_title_and_icon([gettext("Annotate"), self.path,
                                         gettext("Revision %s") % revno])
                return
        
        self.set_title_and_icon([gettext("Annotate"), self.path])

    def get_revno(self, revid):
        if revid in self.log_list.graph_provider.revid_rev:
            return self.log_list.graph_provider.revid_rev[revid].revno_str
        return ""
    
    def annotate(self, tree, fileId, path):
        self.now = time.time()
        self.rev_indexes = {}
        last_revid = None
        lines = []
        annotate = []
        ordered_revids = []
        self.processEvents()
        for revid, text in tree.annotate_iter(fileId):
            text = text.decode(self.encoding, 'replace')
            
            lines.append(text)
            
            text = text.rstrip()
            if revid not in self.rev_indexes:
                self.rev_indexes[revid]=[]
                ordered_revids.append(revid)
            self.rev_indexes[revid].append(len(annotate))
            
            is_top = last_revid != revid
            last_revid = revid
            
            annotate.append((revid, is_top))
            if len(annotate) % 100 == 0:
                self.processEvents()
        
        self.text_edit.setPlainText("".join(lines))
        self.annotate_bar.adjustWidth(len(lines), 999)
        self.annotate_bar.annotate = annotate
        self.text_edit.annotate = annotate
        
        self.processEvents()

        if not self.log_branch_loaded:
            self.log_branch_loaded = True
            self.log_list.load_branch(self.branch, [self.fileId], tree)
            
            self.log_list.context_menu.addAction(
                                    gettext("&Annotate this revision"),
                                    self.set_annotate_revision)
        
        gp = self.log_list.graph_provider
        gp.filter_file_id = [False for i in xrange(len(gp.revisions))]
        
        changed_indexes = []
        for revid in self.rev_indexes.keys():
            index = gp.revid_rev[revid].index
            gp.filter_file_id[index] = True
            changed_indexes.append(index)
            
            if len(changed_indexes) >=500:
                gp.invaladate_filter_cache_revs(changed_indexes)
                changed_indexes = []
        
        gp.invaladate_filter_cache_revs(changed_indexes, last_call=True)
        
        self.annotate_bar.adjustWidth(len(lines),
                                      gp.revisions[0].revno_sequence[0])
        
        self.processEvents()
        highlight_document(self.text_edit, path)
        self.processEvents()
        load_revisions(ordered_revids, self.branch.repository,
                       revisions_loaded = self.revisions_loaded,
                       pass_prev_loaded_rev = True)
    
    def revisions_loaded(self, revisions, last_call):
        for rev in revisions.itervalues():
            author_name = get_apparent_author_name(rev)
            
            if rev.timestamp is None:
                days = sys.maxint
            elif self.now < rev.timestamp:
                days = 0
            else:
                days = (self.now - rev.timestamp) / (24 * 60 * 60)
            
            alpha = 0.5/((days/50) + 1)
            hue =  1-float(abs(hash(author_name))) / sys.maxint 
            color = QtGui.QColor.fromHsvF(hue, 1, 1, alpha)
            brush = QtGui.QBrush(color)
            
            self.annotate_bar.rev_colors[rev.revision_id] = brush
            self.text_edit.rev_colors[rev.revision_id] = brush
        
        self.annotate_bar.update()
        self.text_edit.update()

    def setRevisionByLine(self, selected, deselected):
        indexes = self.browser.selectedIndexes()
        if not indexes:
            return
        rev_id = str(indexes[0].data(self.model.REVID).toString())
        if self.log_list.graph_provider.has_rev_id(rev_id):
            self.log_list.log_model.ensure_rev_visible(rev_id)
            index = self.log_list.log_model.indexFromRevId(rev_id)
            index = self.log_list.filter_proxy_model.mapFromSource(index)
            self.log_list.setCurrentIndex(index)

    @runs_in_loading_queue
    def set_annotate_revision(self):
        self.throbber.show()
        try:
            self.branch.lock_read()
            try:
                revid = str(self.log_list.currentIndex().data(RevIdRole).toString())
                if revid == CURRENT_REVISION:
                    self.tree = self.working_tree
                else:
                    self.tree = self.branch.repository.revision_tree(revid)
                self.path = self.tree.id2path(self.fileId)
                self.set_annotate_title()
                self.processEvents()
                self.annotate(self.tree, self.fileId, self.path)
            finally:
                self.branch.unlock()
        finally:
            self.throbber.hide()

    @runs_in_loading_queue
    def _on_encoding_changed(self, encoding):
        self.encoding = encoding
        get_set_encoding(encoding, self.branch)
        self.throbber.show()
        try:
            self.branch.lock_read()
            try:
                self.annotate(self.tree, self.fileId, self.path)
            finally:
                self.branch.unlock()
        finally:
            self.throbber.hide()

    def browser_on_revisions_loaded(self, revisions, last_call):
        self.model.on_revisions_loaded(revisions, last_call)
