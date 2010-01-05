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
    runs_in_loading_queue,
    get_icon,
    FindToolbar,
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
from bzrlib.plugins.qbzr.lib.revtreeview import paint_revno, get_text_color


class AnnotateBar(AnnotateBarBase):
    
    def __init__(self, edit, parent, get_revno):
        super(AnnotateBar, self).__init__(edit, parent)
        
        self.get_revno = get_revno
        self.annotate = None
        self.rev_colors = {}
        self.highlight_revids = set()
        
        self.splitter = None
        self.adjustWidth(1, 999)
        
        self.connect(edit,
            QtCore.SIGNAL("cursorPositionChanged()"),
            self.edit_cursorPositionChanged)
        self.show_current_line = False

    def edit_cursorPositionChanged(self):
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
        fm = self.fontMetrics()
        painter.save()
        if is_current and self.show_current_line:
            style = self.style()
            option = QtGui.QStyleOptionViewItemV4()
            option.initFrom(self)
            option.state = option.state | QtGui.QStyle.State_Selected
            option.rect = rect.toRect()
            painter.fillRect(rect, QtGui.QBrush(option.palette.highlight()))
            style.drawPrimitive(QtGui.QStyle.PE_PanelItemViewItem,
                                       option, painter, self)
            
            painter.setPen(get_text_color(option, style))
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
            self.line_number_width - (2 * text_margin),
            rect.height())
        
        painter.drawText(line_number_rect, QtCore.Qt.AlignRight,
                         unicode(line_number))
        
        if self.annotate and line_number-1 < len(self.annotate):
            revid, is_top = self.annotate[line_number - 1]
            if is_top:
                if revid in self.highlight_revids:
                    font = painter.font()
                    font.setBold(True)
                    painter.setFont(font)
                
                revno_rect = QtCore.QRect(
                    rect.left() + self.line_number_width + text_margin,
                    rect.top(),
                    self.revno_width - (2 * text_margin),
                    rect.height())
                paint_revno(painter, revno_rect,
                            QtCore.QString(self.get_revno(revid)),
                            self.max_mainline_digits)
                
                if revid in cached_revisions:
                    rev = cached_revisions[revid]
                    author_rect = QtCore.QRect(
                        rect.left() + self.line_number_width
                                    + self.revno_width + text_margin,
                        rect.top(),
                        rect.right() - revno_rect.right() - (2 * text_margin),
                        rect.height())
                    author = QtCore.QString(get_apparent_author_name(rev))
                    if fm.width(author) > author_rect.width():
                        author= fm.elidedText(author, QtCore.Qt.ElideRight,
                                              author_rect.width())                    
                    painter.drawText(author_rect, 0, author)
        painter.restore()


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
        QtGui.QPlainTextEdit.paintEvent(self, event)


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
        self.text_edit.setTextInteractionFlags(
            QtCore.Qt.TextSelectableByMouse|
            QtCore.Qt.TextSelectableByKeyboard)
        self.text_edit.setLineWrapMode(QtGui.QPlainTextEdit.NoWrap)
        
        self.text_edit.document().setDefaultFont(
            QtGui.QFont("Courier New,courier", 
                        self.text_edit.font().pointSize()))
        
        self.annotate_bar = AnnotateBar(self.text_edit, self, self.get_revno)
        annotate_spliter = QtGui.QSplitter(QtCore.Qt.Horizontal, self)
        annotate_spliter.addWidget(self.annotate_bar)
        annotate_spliter.addWidget(self.text_edit)
        self.annotate_bar.splitter = annotate_spliter
        self.text_edit_frame.hbox.addWidget(annotate_spliter)
        
        self.connect(self.text_edit,
                     QtCore.SIGNAL("cursorPositionChanged()"),
                     self.edit_cursorPositionChanged)        
        self.connect(self.annotate_bar,
                     QtCore.SIGNAL("cursorPositionChanged()"),
                     self.edit_cursorPositionChanged)        
        
        self.log_list = LogList(self.processEvents, self.throbber, no_graph, self)
        self.log_list.load = self.log_list_load
        self.log_list.header().hideSection(COL_DATE)
        #self.log_list.header().hideSection(COL_AUTHOR)
        self.log_branch_loaded = False
        
        self.connect(self.log_list.selectionModel(),
                     QtCore.SIGNAL("selectionChanged(QItemSelection, QItemSelection)"),
                     self.log_list_selectionChanged)
        
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

        vbox = QtGui.QVBoxLayout(self.centralwidget)
        #vbox.addWidget(self.toolbar)
        vbox.addWidget(splitter)
        self.text_edit.setFocus()

        self.show_find = QtGui.QAction(get_icon("edit-find"), gettext("Find"), self)
        self.show_find.setShortcuts(QtGui.QKeySequence.Find)
        self.show_find.setCheckable(True)
        
        self.show_goto_line = QtGui.QAction(get_icon("go-jump"), gettext("Goto Line"), self)
        self.show_goto_line.setShortcuts((QtCore.Qt.CTRL + QtCore.Qt.Key_G,))
        self.show_goto_line.setCheckable(True)
        
        show_view_menu = QtGui.QAction(get_icon("document-properties"), gettext("&View Options"), self)
        view_menu = QtGui.QMenu(gettext('View Options'), self)
        show_view_menu.setMenu(view_menu)
        
        encoding_action = QtGui.QWidgetAction(view_menu)
        encoding_action.setDefaultWidget(self.encoding_selector)
        
        word_wrap = QtGui.QAction(gettext("Word Wrap"), self)
        word_wrap.setCheckable(True)
        self.connect(word_wrap,
                     QtCore.SIGNAL("toggled (bool)"),
                     self.word_wrap_toggle)
        
        view_menu.addAction(encoding_action)
        view_menu.addAction(word_wrap)
        
        toolbar = self.addToolBar(gettext("Annotate"))
        toolbar.setMovable (False)
        toolbar.setToolButtonStyle(QtCore.Qt.ToolButtonTextBesideIcon)
        
        #self.toolbar.setToolButtonStyle(QtCore.Qt.ToolButtonTextBesideIcon)
        toolbar.addAction(self.show_find)
        toolbar.addAction(self.show_goto_line)
        toolbar.addAction(show_view_menu)
        toolbar.widgetForAction(show_view_menu).setPopupMode(QtGui.QToolButton.InstantPopup)
        
        spacer = QtGui.QWidget()
        spacer.setSizePolicy(QtGui.QSizePolicy.Expanding, QtGui.QSizePolicy.Expanding)
        toolbar.addWidget(spacer) 
        toolbar.addWidget(self.throbber)
        
        self.addToolBarBreak()
        
        self.find_toolbar = FindToolbar(self, self.text_edit, self.show_find)
        self.find_toolbar.hide()
        self.addToolBar(self.find_toolbar)
        self.connect(self.show_find,
                     QtCore.SIGNAL("toggled (bool)"),
                     self.show_find_toggle)
        
        self.goto_line_toolbar = GotoLineToolbar(self, self.show_goto_line)
        self.goto_line_toolbar.hide()
        self.addToolBar(self.goto_line_toolbar)
        
        self.connect(self.show_goto_line,
                     QtCore.SIGNAL("toggled (bool)"),
                     self.show_goto_line_toggle )

    def show(self):
        QBzrWindow.show(self)
        QtCore.QTimer.singleShot(0, self.initial_load)

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
        self.annotate_bar.show_current_line = False
        
        self.processEvents()
        
        just_loaded_log = False
        if not self.log_branch_loaded:
            self.log_branch_loaded = True
            self.log_list.load_branch(self.branch, [self.fileId], tree)
            
            self.log_list.context_menu.addAction(
                                    gettext("&Annotate this revision"),
                                    self.set_annotate_revision)
            
            just_loaded_log = True
            
            # Show the revisions the we know about now.
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
        self.processEvents()
        
        if just_loaded_log:
            # Check for any other revisions we don't know about
            revids = [rev.revid for rev in gp.revisions
                      if rev.revid not in self.rev_indexes]
            
            for repo, revids in gp.get_repo_revids(revids):
                chunk_size = 500
                
                for start in xrange(0, len(revids), chunk_size):
                    gp.load_filter_file_id_chunk(repo, 
                            revids[start:start + chunk_size])
            gp.load_filter_file_id_chunk_finished()
    
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

    def edit_cursorPositionChanged(self):
        current_line = self.text_edit.document().findBlock(
            self.text_edit.textCursor().position()).blockNumber()
        if self.text_edit.annotate:
            rev_id, is_top = self.text_edit.annotate[current_line]
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
    
    def log_list_selectionChanged(self, selected, deselected):
        revids = self.log_list.get_selection_and_merged_revids()
        self.annotate_bar.highlight_revids = revids
        self.annotate_bar.update()
    
    def show_find_toggle(self, state):
        if state:
            self.show_goto_line.setChecked(False)

    def show_goto_line_toggle(self, state):
        self.goto_line_toolbar.setVisible(state)
        if state:
            self.goto_line_toolbar.line_edit.setFocus()
            self.show_find.setChecked(False)
        else:
            self.goto_line_toolbar.line_edit.setText('')
    
    def word_wrap_toggle(self, state):
        if state:
            self.text_edit.setLineWrapMode(QtGui.QPlainTextEdit.WidgetWidth)
        else:
            self.text_edit.setLineWrapMode(QtGui.QPlainTextEdit.NoWrap)

class GotoLineToolbar(QtGui.QToolBar):
    
    def __init__(self, anotate_window, show_action):
        QtGui.QToolBar.__init__(self, gettext("Goto Line"), anotate_window)
        self.anotate_window = anotate_window
        if 0: self.anotate_window = AnnotateWindow()
        self.show_action = show_action
        
        self.setToolButtonStyle(QtCore.Qt.ToolButtonTextBesideIcon)
        self.setMovable (False)
        
        label = QtGui.QLabel(gettext("Goto Line: "), self)
        self.addWidget(label)
        
        self.line_edit = QtGui.QLineEdit(self)
        self.line_edit.setValidator(
            QtGui.QIntValidator(1, sys.maxint, self.line_edit))
        self.addWidget(self.line_edit)
        label.setBuddy(self.line_edit)
        
        go = self.addAction(get_icon("go-next"), gettext("Go"))
        go.setShortcut((QtCore.Qt.Key_Enter))
        go.setShortcutContext(QtCore.Qt.WidgetWithChildrenShortcut)
        
        spacer = QtGui.QWidget()
        spacer.setSizePolicy(QtGui.QSizePolicy.Expanding, QtGui.QSizePolicy.Expanding)
        self.addWidget(spacer)
        
        close = QtGui.QAction(self)
        close.setIcon(self.style().standardIcon(
                                        QtGui.QStyle.SP_DialogCloseButton))
        self.addAction(close)
        close.setShortcut((QtCore.Qt.Key_Escape))
        close.setShortcutContext(QtCore.Qt.WidgetWithChildrenShortcut)
        close.setStatusTip(gettext("Close Goto Line"))
        self.connect(close,
                     QtCore.SIGNAL("triggered(bool)"),
                     self.close_triggered)
        self.connect(go,
                     QtCore.SIGNAL("triggered(bool)"),
                     self.go_triggered)
    
    def close_triggered(self, state):
        self.show_action.setChecked(False)
    
    def go_triggered(self, state):
        line = int(str(self.line_edit.text()))-1
        doc = self.anotate_window.text_edit.document()
        cursor = QtGui.QTextCursor(doc)
        cursor.setPosition(doc.findBlockByNumber(line).position())
        self.anotate_window.text_edit.setTextCursor(cursor)
        
        self.show_action.setChecked(False)

