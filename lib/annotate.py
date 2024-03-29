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

import sys, time, hashlib
from itertools import groupby
from PyQt5 import QtCore, QtGui, QtWidgets

from breezy.revision import CURRENT_REVISION

from breezy.plugins.qbrz.lib.i18n import gettext
from breezy.plugins.qbrz.lib.util import (
    BTN_CLOSE,
    QBzrWindow,
    ToolBarThrobberWidget,
    get_apparent_author_name,
    get_icon,
    get_monospace_font,
    get_set_encoding,
    get_set_tab_width_chars,
    get_tab_width_pixels,
    runs_in_loading_queue,
    )
from breezy.plugins.qbrz.lib.widgets.toolbars import FindToolbar
from breezy.plugins.qbrz.lib.widgets.texteditaccessory import (
    GuideBarPanel, setup_guidebar_for_find
)
from breezy.plugins.qbrz.lib.uifactory import ui_current_widget
from breezy.plugins.qbrz.lib.trace import reports_exception
from breezy.plugins.qbrz.lib.logwidget import LogList
from breezy.plugins.qbrz.lib.lazycachedrevloader import (load_revisions,
                                                         cached_revisions)
from breezy.plugins.qbrz.lib.texteditannotate import (AnnotateBarBase,
                                                      AnnotateEditerFrameBase)
from breezy.lazy_import import lazy_import
lazy_import(globals(), '''
from breezy.config import parse_username
from breezy.workingtree import WorkingTree
from breezy.revisiontree import RevisionTree
from breezy.plugins.qbrz.lib.revisionmessagebrowser import LogListRevisionMessageBrowser
from breezy.plugins.qbrz.lib.encoding_selector import EncodingMenuSelector
from breezy.plugins.qbrz.lib.widgets.tab_width_selector import TabWidthMenuSelector
from breezy.plugins.qbrz.lib.syntaxhighlighter import highlight_document
from breezy.plugins.qbrz.lib.revtreeview import paint_revno, get_text_color
from breezy.plugins.qbrz.lib import logmodel
from breezy.plugins.qbrz.lib.loggraphviz import BranchInfo
from patiencediff import PatienceSequenceMatcher as SequenceMatcher
''')


class AnnotateBar(AnnotateBarBase):

    def __init__(self, edit, parent, get_revno):
        super(AnnotateBar, self).__init__(edit, parent)

        self.get_revno = get_revno
        self.annotate = None
        self.rev_colors = {}
        self._highlight_revids = set()
        self.highlight_lines = []

        self.splitter = None
        self.adjustWidth(1, 999)

        edit.cursorPositionChanged.connect(self.edit_cursorPositionChanged)
        self.show_current_line = False

    def get_highlight_revids(self):
        return self._highlight_revids

    def set_highlight_revids(self, value):
        if self._highlight_revids == value:
            return

        self._highlight_revids = value
        self.update_highlight_lines()

    def update_highlight_lines(self):
        self.highlight_lines = []
        if not self.annotate:
            return
        lines = [i for i, (revno, istop) in enumerate(self.annotate)
                 if revno in self._highlight_revids]

        # Convert [0,1,2,5,6,9,14,15,16,17] to [(0,3),(5,2),(9,1),(14,4)]
        def summarize(lines):
            for k, g in groupby(enumerate(lines), key=lambda x:x[1]-x[0]):
                yield [line for i, line in g]
        self.highlight_lines = [(x[0], len(x)) for x in summarize(lines)]

    highlight_revids = property(get_highlight_revids, set_highlight_revids)

    def edit_cursorPositionChanged(self):
        self.show_current_line = True

    def adjustWidth(self, lines, max_revno):
        fm = self.fontMetrics()
        text_margin = self.style().pixelMetric(QtWidgets.QStyle.PM_FocusFrameHMargin, None, self) + 1

        self.line_number_width = fm.width(str(lines))
        self.line_number_width += (text_margin * 2)

        self.revno_width = fm.width(str(max_revno)+".8.88")
        self.max_mainline_digits = len(str(max_revno))
        self.revno_width += (text_margin * 2)

        if self.splitter:
            if 0: self.splitter = QtWidgets.QSplitter
            width = (self.line_number_width + self.revno_width +
                     fm.width("Joe I have a Long Name"))
            self.splitter.setSizes([width, 1000])

        self.setMinimumWidth(self.line_number_width + self.revno_width)

    def paint_line(self, painter, rect, line_number, is_current):
        fm = self.fontMetrics()
        painter.save()
        if is_current and self.show_current_line:
            style = self.style()
            option = QtWidgets.QStyleOptionViewItem()
            option.initFrom(self)
            option.state = option.state | QtWidgets.QStyle.State_Selected
            option.rect = rect.toRect()
            painter.fillRect(rect, QtGui.QBrush(option.palette.highlight()))
            style.drawPrimitive(QtWidgets.QStyle.PE_PanelItemViewItem, option, painter, self)

            painter.setPen(get_text_color(option, style))
        elif self.annotate and line_number-1 < len(self.annotate):
            revid, is_top = self.annotate[line_number - 1]
            if revid in self.rev_colors:
                painter.fillRect(rect, self.rev_colors[revid])

        text_margin = self.style().pixelMetric(QtWidgets.QStyle.PM_FocusFrameHMargin, None, self) + 1

        if 0: rect = QtCore.QRect
        line_number_rect = QtCore.QRect(*map(int, [
            rect.left() + text_margin,
            rect.top(),
            self.line_number_width - (2 * text_margin),
            rect.height()]))

        painter.drawText(line_number_rect, QtCore.Qt.AlignRight, str(line_number))

        if self.annotate and line_number-1 < len(self.annotate):
            revid, is_top = self.annotate[line_number - 1]
            if is_top:
                if revid in self._highlight_revids:
                    font = painter.font()
                    font.setBold(True)
                    painter.setFont(font)

                revno_rect = QtCore.QRect(*map(int, [
                    rect.left() + self.line_number_width + text_margin,
                    rect.top(),
                    self.revno_width - (2 * text_margin),
                    rect.height()]))
                paint_revno(painter, revno_rect, str(self.get_revno(revid)), self.max_mainline_digits)

                if revid in cached_revisions:
                    rev = cached_revisions[revid]
                    author_rect = QtCore.QRect(*map(int, [
                        rect.left() + self.line_number_width
                                    + self.revno_width + text_margin,
                        rect.top(),
                        rect.right() - revno_rect.right() - (2 * text_margin),
                        rect.height()]))
                    author = get_apparent_author_name(rev)
                    if fm.width(author) > author_rect.width():
                        author= fm.elidedText(author, QtCore.Qt.ElideRight, author_rect.width())
                    painter.drawText(author_rect, 0, author)
        painter.restore()


class AnnotatedTextEdit(QtWidgets.QPlainTextEdit):
    annotate = None
    rev_colors = {}
    # RJLRJL: added for Qt5
    documentChangeFinished = QtCore.pyqtSignal()

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
        QtWidgets.QPlainTextEdit.paintEvent(self, event)

    def get_positions(self):
        """Returns the charator positons for the selection start,
        selection end, center of the viewport, an the number of lines from
        the top of the viewport to the center of the viewport."""
        old_cursor = self.textCursor()
        old_center = self.cursorForPosition(QtCore.QPoint(0, self.height() / 2))
        lines_to_center = (old_center.block().blockNumber() - self.verticalScrollBar().value())

        return (old_cursor.selectionStart(), old_cursor.selectionEnd(), old_center.position()) , lines_to_center

    def set_positions(self, new_positions, lines_to_center):
        new_start, new_end, new_center = new_positions
        if new_center:
            new_center_cursor = QtGui.QTextCursor(self.document())
            new_center_cursor.setPosition(new_center)
            new_scroll = new_center_cursor.block().blockNumber() - lines_to_center
            self.verticalScrollBar().setValue(new_scroll)

        new_selection_cursor = QtGui.QTextCursor(self.document())
        new_selection_cursor.movePosition(QtGui.QTextCursor.Right, QtGui.QTextCursor.MoveAnchor, new_start)
        new_selection_cursor.movePosition(QtGui.QTextCursor.Right, QtGui.QTextCursor.KeepAnchor, new_end - new_start)
        self.setTextCursor(new_selection_cursor)


class AnnotateWindow(QBzrWindow):
    documentChangeFinished = QtCore.pyqtSignal()

    def __init__(self, branch, working_tree, annotate_tree, path, fileId,
                 encoding=None, parent=None, ui_mode=True, no_graph=False,
                 loader=None, loader_args=None, activate_line=None):
        QBzrWindow.__init__(self, [gettext("Annotate"), gettext("Loading...")], parent, ui_mode=ui_mode)
        self.restoreSize("annotate", (780, 680))

        self.activate_line_after_load = activate_line

        self.windows = []

        self.branch = branch
        self.annotate_tree = annotate_tree
        self.working_tree = working_tree
        if (self.working_tree is None and isinstance(annotate_tree, WorkingTree)):
            self.working_tree = annotate_tree

        self.no_graph = no_graph
        self.old_lines = None

        self.fileId = fileId
        self.path = path
        self.encoding = encoding
        self.loader_func = loader
        self.loader_args = loader_args

        self.throbber = ToolBarThrobberWidget(self)

        self.text_edit_frame = AnnotateEditerFrameBase(self)
        self.text_edit = AnnotatedTextEdit(self)
        self.text_edit.setFrameStyle(QtWidgets.QFrame.NoFrame)
        self.text_edit.setTextInteractionFlags(QtCore.Qt.TextSelectableByMouse | QtCore.Qt.TextSelectableByKeyboard)
        self.text_edit.setLineWrapMode(QtWidgets.QPlainTextEdit.NoWrap)

        self.text_edit.document().setDefaultFont(get_monospace_font())

        self.guidebar_panel = GuideBarPanel(self.text_edit, parent=self)
        self.guidebar_panel.add_entry('annotate', QtGui.QColor(255, 160, 180))
        self.annotate_bar = AnnotateBar(self.text_edit, self, self.get_revno)
        annotate_spliter = QtWidgets.QSplitter(QtCore.Qt.Horizontal, self)
        annotate_spliter.addWidget(self.annotate_bar)
        annotate_spliter.addWidget(self.guidebar_panel)
        self.annotate_bar.splitter = annotate_spliter
        self.text_edit_frame.hbox.addWidget(annotate_spliter)

        self.text_edit.cursorPositionChanged.connect(self.edit_cursorPositionChanged)
        self.annotate_bar.cursorPositionChanged.connect(self.edit_cursorPositionChanged)
        self.text_edit.documentChangeFinished.connect(self.edit_documentChangeFinished)

        self.log_list = AnnotateLogList(self.processEvents, self.throbber, self)
        self.log_list.header().hideSection(logmodel.COL_DATE)
        self.log_list.parent_annotate_window = self
        self.log_branch_loaded = False

        self.log_list.selectionModel().selectionChanged[QtCore.QItemSelection, QtCore.QItemSelection].connect(self.log_list_selectionChanged)

        self.message = LogListRevisionMessageBrowser(self.log_list, self)

        self.encoding_selector = EncodingMenuSelector(self.encoding, gettext("Encoding"), self._on_encoding_changed)

        hsplitter = QtWidgets.QSplitter(QtCore.Qt.Horizontal)
        hsplitter.addWidget(self.log_list)
        hsplitter.addWidget(self.message)

        hsplitter.setStretchFactor(0, 2)
        hsplitter.setStretchFactor(1, 2)

        splitter = QtWidgets.QSplitter(QtCore.Qt.Vertical)
        splitter.addWidget(self.text_edit_frame)
        splitter.addWidget(hsplitter)

        splitter.setStretchFactor(0, 5)
        splitter.setStretchFactor(1, 2)

        vbox = QtWidgets.QVBoxLayout(self.centralwidget)
        #vbox.addWidget(self.toolbar)
        vbox.addWidget(splitter)
        self.text_edit.setFocus()

        self.show_find = QtWidgets.QAction(get_icon("edit-find"), gettext("Find"), self)
        self.show_find.setShortcuts(QtGui.QKeySequence.Find)
        self.show_find.setCheckable(True)

        self.show_goto_line = QtWidgets.QAction(get_icon("go-jump"), gettext("Goto Line"), self)
        self.show_goto_line.setShortcuts((QtCore.Qt.CTRL + QtCore.Qt.Key_L,))
        self.show_goto_line.setCheckable(True)

        show_view_menu = QtWidgets.QAction(get_icon("document-properties"), gettext("&View Options"), self)
        view_menu = QtWidgets.QMenu(gettext('View Options'), self)
        show_view_menu.setMenu(view_menu)

        word_wrap = QtWidgets.QAction(gettext("Word Wrap"), self)
        word_wrap.setCheckable(True)
        word_wrap.toggled [bool].connect(self.word_wrap_toggle)

        def setTabStopWidth(tw):
            self.text_edit.setTabStopWidth(get_tab_width_pixels(tab_width_chars=tw))
            get_set_tab_width_chars(branch=self.branch,tab_width_chars=tw)
        self.tab_width_selector = TabWidthMenuSelector(get_set_tab_width_chars(branch=branch), gettext("Tab Width"), setTabStopWidth)

        view_menu.addMenu(self.tab_width_selector)
        view_menu.addMenu(self.encoding_selector)
        view_menu.addAction(word_wrap)

        toolbar = self.addToolBar(gettext("Annotate"))
        toolbar.setMovable (False)
        toolbar.setToolButtonStyle(QtCore.Qt.ToolButtonTextBesideIcon)

        #self.toolbar.setToolButtonStyle(QtCore.Qt.ToolButtonTextBesideIcon)
        toolbar.addAction(self.show_find)
        toolbar.addAction(self.show_goto_line)
        toolbar.addAction(show_view_menu)
        toolbar.widgetForAction(show_view_menu).setPopupMode(QtWidgets.QToolButton.InstantPopup)

        spacer = QtWidgets.QWidget()
        spacer.setSizePolicy(QtWidgets.QSizePolicy.Expanding, QtWidgets.QSizePolicy.Expanding)
        toolbar.addWidget(spacer)
        toolbar.addWidget(self.throbber)

        self.addToolBarBreak()

        self.find_toolbar = FindToolbar(self, self.text_edit, self.show_find)
        self.find_toolbar.hide()
        self.addToolBar(self.find_toolbar)
        self.show_find.toggled [bool].connect(self.show_find_toggle)
        setup_guidebar_for_find(self.guidebar_panel, self.find_toolbar, index=1)

        self.goto_line_toolbar = GotoLineToolbar(self, self.show_goto_line)
        self.goto_line_toolbar.hide()
        self.addToolBar(self.goto_line_toolbar)

        self.show_goto_line.toggled [bool].connect(self.show_goto_line_toggle)

        self.__hashes = {}

    def show(self):
        QBzrWindow.show(self)
        # RJL 2023 - the singleShot causes problems, so just run the load
        # QtCore.QTimer.singleShot(0, self.initial_load)
        self.initial_load()

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
                 self.annotate_tree,
                 self.working_tree,
                 self.path, self.fileId) = self.loader_func(*self.loader_args)
                self.loader_func = self.loader_args = None # kill extra refs...
                QtCore.QCoreApplication.processEvents()
            self.encoding = get_set_encoding(self.encoding, self.branch)
            self.encoding_selector.encoding = self.encoding
            with self.branch.lock_read():
                self.set_annotate_title()
                self.annotate(self.annotate_tree, self.fileId, self.path)
        finally:
            self.throbber.hide()
        QtCore.QTimer.singleShot(1, self._activate_line)

    def _activate_line(self):
        # [bialix 2012/09/14] I have to use QtCore.QTimer.singleShot because
        # otherwise the line with uncommitted changes is not highlighted
        # properly: nothing appears in the revision message browser at all.
        # I didn't find the reason behind it, shame on me.
        n = self.activate_line_after_load
        self.activate_line_after_load = None    # clear the line number just in case
        if n:
            if n == 1:
                # [bialix 2012/09/13] actually after loading annotation
                # document implictly sets current position to the first line.
                # So we're unable to change position to 1st line.
                # Make a hack: select 2nd line, and then actually select 1st one.
                self.go_to_line(2)
            self.go_to_line(n)

    def set_annotate_title(self):
        # and update the title to show we are done.
        if isinstance(self.annotate_tree, RevisionTree):
            revno = self.get_revno(self.annotate_tree.get_revision_id())
            if revno:
                self.set_title_and_icon([gettext("Annotate"), self.path, gettext("Revision %s") % revno])
                return

        self.set_title_and_icon([gettext("Annotate"), self.path])

    def get_revno(self, revid):
        gv = self.log_list.log_model.graph_viz
        if (gv and
            revid in gv.revid_rev):
            return gv.revid_rev[revid].revno_str
        return ""

    def annotate(self, annotate_tree, fileId, path):
        self.now = time.time()
        self.rev_indexes = {}
        last_revid = None
        lines = []
        annotate = []
        ordered_revids = []

        self.processEvents()
        for revid, text in annotate_tree.annotate_iter(path):
            if revid == CURRENT_REVISION:
                revid = CURRENT_REVISION + annotate_tree.basedir.encode("utf-8")

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
        annotate.append((None, False))  # because the view has one more line

        new_positions = None
        if self.old_lines:
            # Try keep the scroll, and selection stable.
            old_positions, lines_to_center = self.text_edit.get_positions()
            new_positions = self.translate_positions(self.old_lines, lines, old_positions)

        self.text_edit.annotate = None
        self.text_edit.setPlainText("".join(lines))
        if new_positions:
            self.text_edit.set_positions(new_positions, lines_to_center)

        self.old_lines = lines
        self.annotate_bar.adjustWidth(len(lines), 999)
        self.annotate_bar.annotate = annotate
        self.text_edit.annotate = annotate
        self.annotate_bar.show_current_line = False

        self.text_edit.documentChangeFinished.emit()

        self.processEvents()

        just_loaded_log = False
        if not self.log_branch_loaded:
            self.log_branch_loaded = True
            bi = BranchInfo('', self.working_tree, self.branch)
            self.log_list.load((bi,), bi, [self.fileId], self.no_graph, logmodel.WithWorkingTreeGraphVizLoader)

            gv = self.log_list.log_model.graph_viz
            self.annotate_bar.adjustWidth(len(lines), gv.revisions[0].revno_sequence[0])

            just_loaded_log = True

            # Show the revisions the we know about from the annotate.
            filter = self.log_list.log_model.file_id_filter
            changed_revs = []
            for revid in list(self.rev_indexes.keys()):
                rev = gv.revid_rev[revid]
                filter.filter_file_id[rev.index] = True
                changed_revs.append(rev)
            filter.filter_changed_callback(changed_revs, last_call=True)

        self.processEvents()
        highlight_document(self.text_edit, path)
        self.processEvents()
        load_revisions(ordered_revids, self.branch.repository, revisions_loaded = self.revisions_loaded, pass_prev_loaded_rev = True)
        self.processEvents()

        if just_loaded_log:
            # Check for any other revisions we don't know about

            filter = self.log_list.log_model.file_id_filter
            revids = [rev.revid for rev in gv.revisions if rev.revid not in self.rev_indexes]
            filter.load(revids)

    def translate_positions(self, old_lines, new_lines, old_positions):
        sm = SequenceMatcher(None, old_lines, new_lines)
        opcodes = sm.get_opcodes()
        new_positions = [None for x in range(len(old_positions))]
        opcode_len = lambda start, end, lines: sum(
            [len(l) for l in lines[start:end]])
        for i, old_pos in enumerate(old_positions):
            old_char_start = 0
            new_char_start = 0
            for code, old_start, old_end, new_start, new_end in opcodes:
                old_len = opcode_len(old_start, old_end, old_lines)
                new_len = opcode_len(new_start, new_end, new_lines)
                if (old_pos >= old_char_start and
                    old_pos < old_char_start + old_len):
                    if code == 'delete':
                        new_pos = new_char_start
                    elif (code == 'replace' and len(opcodes)>1):
                        # XXX This should cache the opcodes if we do the same
                        # block more than once.
                        new_inner_pos = self.translate_positions(
                            ''.join(old_lines[old_start:old_end]),
                            ''.join(new_lines[new_start:new_end]),
                            [old_pos - old_char_start])[0]
                        new_pos = new_char_start + new_inner_pos
                    else:
                        new_pos = new_char_start + (old_pos - old_char_start)
                    new_positions[i] = new_pos
                    break
                old_char_start += old_len
                new_char_start += new_len
        return new_positions

    def revisions_loaded(self, revisions, last_call):
        for rev in revisions.values():
            authors = rev.get_apparent_authors()
            emails = list(map(self._maybe_extract_email, authors))
            author_id = ';'.join(emails)

            if rev.timestamp is None:
                days = sys.maxsize
            elif self.now < rev.timestamp:
                days = 0
            else:
                days = (self.now - rev.timestamp) / (24 * 60 * 60)

            alpha = 0.5/((days/50) + 1)
            h_sh = self._get_hash(author_id)
            hue = 1-float(h_sh) / sys.maxsize
            color = QtGui.QColor.fromHsvF(hue, 1, 1, alpha)
            brush = QtGui.QBrush(color)

            self.annotate_bar.rev_colors[rev.revision_id] = brush
            self.text_edit.rev_colors[rev.revision_id] = brush

        self.annotate_bar.update()
        self.text_edit.update()

    def _maybe_extract_email(self, author):
        name, email = parse_username(author)
        if email:
            return email
        return author

    def _get_hash(self, author_id):
        h = self.__hashes.get(author_id)
        if h is None:
            h = abs(hash(author_id))
            #h = abs(hash(hashlib.md5(author_id).hexdigest())) # maybe increase enthropy via md5?
            # XXX [bialix 2012/03/30]
            # I don't really like how we create colors for annotation.
            # Also, abs(hash) loses 1 bit of the hash result.
            # I think we can improve our algorithm to use more distinctive colors
            # maybe we should use md5 as more enthropy source for hash,
            # or maybe we can use some sort of predefined set of colors
            # and each next author will use color from that set,
            # but in this case we lose consistency of colors for the same author
            # between different annotations
            # I have no clever idea yet.
            self.__hashes[author_id] = h
        return h

    def edit_cursorPositionChanged(self):
        current_line = self.text_edit.document().findBlock(
            self.text_edit.textCursor().position()).blockNumber()
        if self.text_edit.annotate:
            rev_id, is_top = self.text_edit.annotate[current_line]
            self.log_list.select_revid(rev_id)

    def edit_documentChangeFinished(self):
        self.annotate_bar.update_highlight_lines()
        self.guidebar_panel.update_data(annotate=self.annotate_bar.highlight_lines)

    @runs_in_loading_queue
    def set_annotate_revision(self):
        self.throbber.show()
        try:
            with self.branch.lock_read():
                revid = self.log_list.currentIndex().data(logmodel.RevIdRole)
                if revid.startswith(CURRENT_REVISION):
                    rev = cached_revisions[revid]
                    self.annotate_tree = self.working_tree
                else:
                    self.annotate_tree = self.branch.repository.revision_tree(revid)
                self.path = self.annotate_tree.id2path(self.fileId)
                self.set_annotate_title()
                self.processEvents()
                self.annotate(self.annotate_tree, self.fileId, self.path)
        finally:
            self.throbber.hide()

    @runs_in_loading_queue
    def _on_encoding_changed(self, encoding):
        self.encoding = encoding
        get_set_encoding(encoding, self.branch)
        self.throbber.show()
        try:
            with self.branch.lock_read():
                self.annotate(self.annotate_tree, self.fileId, self.path)
        finally:
            self.throbber.hide()

    def log_list_selectionChanged(self, selected, deselected):
        revids = self.log_list.get_selection_and_merged_revids()
        self.annotate_bar.highlight_revids = revids
        self.guidebar_panel.update_data(annotate=self.annotate_bar.highlight_lines)
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
            self.text_edit.setLineWrapMode(QtWidgets.QPlainTextEdit.WidgetWidth)
        else:
            self.text_edit.setLineWrapMode(QtWidgets.QPlainTextEdit.NoWrap)

    def go_to_line(self, line):
        doc = self.text_edit.document()
        cursor = QtGui.QTextCursor(doc)
        cursor.setPosition(doc.findBlockByNumber(line-1).position())
        self.text_edit.setTextCursor(cursor)
        self.text_edit.centerCursor()


# QIntValidator did not work on vila's setup, so this is a workaround.
# RJLRJL QIntValidator seems to be working in 2020, whereas this isn't
# so ignored for now.
class IntValidator(QtGui.QValidator):
    def validate(self, input, pos):
        if input == '':
            return (QtGui.QValidator.Intermediate, pos)
        try:
            i = int(input)
        except ValueError:
            return (QtGui.QValidator.Invalid, pos)

        if i > 0:
            return (QtGui.QValidator.Acceptable, pos)
        else:
            return (QtGui.QValidator.Invalid, pos)


class GotoLineToolbar(QtWidgets.QToolBar):

    def __init__(self, anotate_window, show_action):
        QtWidgets.QToolBar.__init__(self, gettext("Goto Line"), anotate_window)
        self.anotate_window = anotate_window
        if 0:
            self.anotate_window = AnnotateWindow()
        self.show_action = show_action

        self.setToolButtonStyle(QtCore.Qt.ToolButtonTextBesideIcon)
        self.setMovable(False)

        label = QtWidgets.QLabel(gettext("Goto Line: "), self)
        self.addWidget(label)

        self.line_edit = QtWidgets.QLineEdit(self)
        # QIntValidator is working in python3, so we'll use that
        # self.line_edit.setValidator(IntValidator(self.line_edit))
        self.line_edit.setValidator(QtGui.QIntValidator())
        self.addWidget(self.line_edit)
        label.setBuddy(self.line_edit)

        go = self.addAction(get_icon("go-next"), gettext("Go"))

        spacer = QtWidgets.QWidget()
        spacer.setSizePolicy(QtWidgets.QSizePolicy.Expanding, QtWidgets.QSizePolicy.Expanding)
        self.addWidget(spacer)

        close = QtWidgets.QAction(self)
        close.setIcon(self.style().standardIcon(QtWidgets.QStyle.SP_DialogCloseButton))
        self.addAction(close)
        close.setShortcut((QtCore.Qt.Key_Escape))
        close.setShortcutContext(QtCore.Qt.WidgetWithChildrenShortcut)
        close.setStatusTip(gettext("Close Goto Line"))
        close.triggered[bool].connect(self.close_triggered)
        go.triggered[bool].connect(self.go_triggered)
        self.line_edit.returnPressed.connect(self.go_triggered)

    def close_triggered(self, state):
        self.show_action.setChecked(False)

    def go_triggered(self, state=True):
        try:
            line = int(str(self.line_edit.text()))
        except ValueError:
            pass
        else:
            self.anotate_window.go_to_line(line)
            self.show_action.setChecked(False)


class AnnotateLogList(LogList):

    parent_annotate_window = None

    def create_context_menu(self):
        LogList.create_context_menu(self, diff_is_default_action=False)
        set_rev_action = QtWidgets.QAction(gettext("&Annotate this revision"), self.context_menu)
        set_rev_action.triggered.connect(self.parent_annotate_window.set_annotate_revision)
        self.context_menu.insertAction(self.context_menu.actions()[0], set_rev_action)
        self.context_menu.setDefaultAction(set_rev_action)

    def default_action(self, index=None):
        self.parent_annotate_window.set_annotate_revision()
