# -*- coding: utf-8 -*-
#
# QBzr - Qt frontend to Bazaar commands
# Copyright (C) 2006 Lukáš Lalinský <lalinsky@gmail.com>
# Copyright (C) 2005 Dan Loda <danloda@gmail.com>
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
    format_revision_html,
    get_apparent_author_name,
    get_set_encoding,
    open_browser,
    RevisionMessageBrowser,
    split_tokens_at_lines,
    format_for_ttype,
    runs_in_loading_queue,
    )
from bzrlib.plugins.qbzr.lib.uifactory import ui_current_widget
from bzrlib.plugins.qbzr.lib.trace import reports_exception
from bzrlib.plugins.qbzr.lib.logwidget import LogList
from bzrlib.plugins.qbzr.lib.logmodel import COL_DATE, RevIdRole
from bzrlib.plugins.qbzr.lib.lazycachedrevloader import (load_revisions,
                                                         cached_revisions)
from bzrlib.plugins.qbzr.lib.revtreeview import (RevisionTreeView,
                                                 RevNoItemDelegate)

have_pygments = True
try:
    from pygments import lex
    from pygments.util import ClassNotFound
    from pygments.lexers import get_lexer_for_filename
except ImportError:
    have_pygments = False


class FormatedCodeItemDelegate(QtGui.QItemDelegate):
    
    def __init__(self, lines, parent = None):
        QtGui.QItemDelegate.__init__(self, parent)
        self.lines = lines

    def paint(self, painter, option, index):
        self.line = self.lines[index.row()]
        QtGui.QItemDelegate.paint(self, painter, option, index)

    def drawDisplay(self, painter, option, rect, text):
        painter.setFont(option.font)
        if (option.state & QtGui.QStyle.State_Selected
            and option.state & QtGui.QStyle.State_Active):
            painter.setPen(option.palette.highlightedText().color())
        else:
            painter.setPen(option.palette.text().color())
        
        textPoint = QtCore.QPoint(rect.left() + 2, rect.bottom() - option.fontMetrics.descent())
        for ttype, text in self.line:
            painter.save()
            format_for_ttype(ttype, painter)
            painter.drawText(textPoint, text.rstrip())
            textPoint.setX(textPoint.x() + QtGui.QFontMetrics(painter.font()).width(text))
            painter.restore()

class AnnotateModel(QtCore.QAbstractTableModel):

    LINE_NO, AUTHOR, REVNO, TEXT = range(4)
    REVID = QtCore.Qt.UserRole + 1
    
    def __init__(self, get_revno, font, parent=None):
        QtCore.QAbstractTableModel.__init__(self, parent)
        
        self.horizontalHeaderLabels = [gettext("Line"),
                                       gettext("Author"),
                                       gettext("Rev"),
                                       "",
                                       ]
        
        self.get_revno = get_revno
        self.font = font
        self.annotate = []
        self.revid_indexes = {}
        self.branch = None
    
    def set_annotate(self, annotate, revid_indexes, branch):
        try:
            self.emit(QtCore.SIGNAL("layoutAboutToBeChanged()"))
            self.annotate = annotate
            self.revid_indexes = revid_indexes
            self.branch = branch
            self.now = time.time()
        finally:
            self.emit(QtCore.SIGNAL("layoutChanged()"))
    
    def columnCount(self, parent):
        return len(self.horizontalHeaderLabels)

    def rowCount(self, parent):
        if parent.isValid():
            return 0
        return len(self.annotate)
    
    def data(self, index, role):
        if not index.isValid():
            return QtCore.QVariant()
        
        revid, text, is_top = self.annotate[index.row()]
        
        if role == self.REVID:
            return QtCore.QVariant(revid)
        
        if revid in cached_revisions:
            rev = cached_revisions[revid]
        else:
            rev = None

        column = index.column()
        if column == self.LINE_NO:
            if role == QtCore.Qt.DisplayRole:
                return QtCore.QVariant(index.row() + 1)
            if role == QtCore.Qt.TextAlignmentRole:
                return QtCore.QVariant(QtCore.Qt.AlignRight)
        
        if column == self.AUTHOR:
            if role == QtCore.Qt.DisplayRole:
                if is_top and rev:
                    return QtCore.QVariant(get_apparent_author_name(rev))
        
        if column == self.REVNO:
            if role == QtCore.Qt.DisplayRole:
                if is_top:
                    revno = self.get_revno(revid)
                    if revno is None:
                        revno = ""
                    return QtCore.QVariant(revno)

        if column == self.TEXT:
            if role == QtCore.Qt.DisplayRole:
                return QtCore.QVariant(text)
            if role == QtCore.Qt.FontRole:
                return QtCore.QVariant(self.font)
        
        if column == self.TEXT and role == QtCore.Qt.BackgroundRole and rev:
            if rev.timestamp is None:
                days = sys.maxint
            elif self.now < rev.timestamp:
                days = 0
            else:
                days = (self.now - rev.timestamp) / (24 * 60 * 60)
            
            saturation = 0.5/((days/50) + 1)
            hue =  1-float(abs(hash(get_apparent_author_name(rev)))) / sys.maxint 
            return QtCore.QVariant(QtGui.QColor.fromHsvF(hue, saturation, 1 ))
        
        if role == QtCore.Qt.DisplayRole: 
            return QtCore.QVariant("")
        return QtCore.QVariant()
    
    def flags(self, index):
        if not index.isValid():
            return QtCore.Qt.ItemIsEnabled

        return QtCore.Qt.ItemIsEnabled | QtCore.Qt.ItemIsSelectable

    def headerData(self, section, orientation, role):
        if orientation == QtCore.Qt.Horizontal and role == QtCore.Qt.DisplayRole:
            return QtCore.QVariant(self.horizontalHeaderLabels[section])
        return QtCore.QVariant()
    
    def on_revisions_loaded(self, revisions, last_call):
        for revid in revisions.iterkeys():
            for row in self.revid_indexes[revid]:
                self.emit(QtCore.SIGNAL("dataChanged(QModelIndex, QModelIndex)"),
                          self.index (row, 0, QtCore.QModelIndex()),
                          self.index (row, 4, QtCore.QModelIndex()))

    def get_repo(self):
        return self.branch.repository


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
        
        
        self.browser = RevisionTreeView()

        font = QtGui.QFont("Courier New,courier",
                           self.browser.font().pointSize())
        self.model = AnnotateModel(self.get_revno, font)
        self.browser.setModel(self.model)
        self.browser.throbber = self.throbber

        self.browser.setRootIsDecorated(False)

        self.browser.setItemDelegateForColumn(self.model.REVNO,
                                              RevNoItemDelegate(parent=self))
        header = self.browser.header()
        fm = self.fontMetrics()
        # XXX Make this dynamic.
        col_margin = 6
        header.resizeSection(self.model.LINE_NO,
                             fm.width("8888") + col_margin)
        header.resizeSection(self.model.AUTHOR,
                             fm.width("Joe I have a Long Name") + col_margin)
        header.resizeSection(self.model.REVNO,
                             fm.width("8888.8.888") + col_margin)

        self.browser.setUniformRowHeights(True)
        self.connect(self.browser.selectionModel(),
                     QtCore.SIGNAL("selectionChanged(QItemSelection, QItemSelection)"),
                     self.setRevisionByLine)

        
        self.message_doc = QtGui.QTextDocument()
        message = RevisionMessageBrowser()
        message.setDocument(self.message_doc)
        self.connect(message,
                     QtCore.SIGNAL("anchorClicked(QUrl)"),
                     self.linkClicked)

        self.log_list = LogList(self.processEvents, self.throbber, no_graph, self)
        self.log_list.load = self.log_list_load
        self.log_list.header().hideSection(COL_DATE)
        #self.log_list.header().hideSection(COL_AUTHOR)
        self.log_branch_loaded = False
        
        self.connect(self.log_list.selectionModel(),
                     QtCore.SIGNAL("selectionChanged(QItemSelection, QItemSelection)"),
                     self.update_selection)

        hsplitter = QtGui.QSplitter(QtCore.Qt.Horizontal)
        hsplitter.addWidget(self.log_list)
        hsplitter.addWidget(message)

        hsplitter.setStretchFactor(0, 2)
        hsplitter.setStretchFactor(1, 2)

        splitter = QtGui.QSplitter(QtCore.Qt.Vertical)
        splitter.addWidget(self.browser)
        splitter.addWidget(hsplitter)

        splitter.setStretchFactor(0, 5)
        splitter.setStretchFactor(1, 2)

        buttonbox = self.create_button_box(BTN_CLOSE)

        vbox = QtGui.QVBoxLayout(self.centralwidget)
        vbox.addWidget(self.throbber)
        vbox.addWidget(splitter)
        vbox.addWidget(buttonbox)
        self.browser.setFocus()

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
        self.rev_indexes = {}
        last_revid = None
        lines = []
        annotate = []
        text_max_len = 80
        self.processEvents()
        for revid, text in tree.annotate_iter(fileId):
            text = text.decode(self.encoding, 'replace')
            
            lines.append(text)
            
            text = text.rstrip()
            text_max_len = max(len(text), text_max_len)
            if revid not in self.rev_indexes:
                self.rev_indexes[revid]=[]
            self.rev_indexes[revid].append(len(annotate))
            
            is_top = last_revid != revid
            last_revid = revid
            
            annotate.append((revid, text, is_top))
            if len(annotate) % 100 == 0:
                self.processEvents()
        
        header = self.browser.header()
        fm = self.fontMetrics()
        # XXX Make this dynamic.
        col_margin = 6
        line_no_max_digts = len("%d"%len(annotate))
        if line_no_max_digts>4:
            header.resizeSection(self.model.LINE_NO,
                            fm.width("8"*line_no_max_digts) + col_margin)
        header.setStretchLastSection(False)
        header.resizeSection(self.model.TEXT,
                        fm.width("8"*text_max_len) + col_margin)
        
        self.model.set_annotate(annotate, self.rev_indexes, self.branch)
        self.processEvents()

        if not self.log_branch_loaded:
            self.log_branch_loaded = True
            if isinstance(tree, WorkingTree):
                self.log_list.load_branch(self.branch, [self.fileId], tree)
            else:
                self.log_list.load_branch(self.branch, [self.fileId])
            
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
        
        self.processEvents()
        
        if have_pygments:
            try:
                # A more correct way to do this would be to add the tokens as
                # a data role to each respective tree item. But it is to much
                # effort to wrap them as QVariants. We will just pass the line
                # tokens to the delegate.
                lines_tokens = list(split_tokens_at_lines(\
                                  lex("".join(lines),
                                  get_lexer_for_filename(path, stripnl=False))))
                self.browser.setItemDelegateForColumn(3,FormatedCodeItemDelegate(lines_tokens, self))
                
            except ClassNotFound:
                pass
    
    def revisions_loaded(self, revisions, last_call):
        self.log_list.model.on_revisions_loaded(revisions, last_call)
        for rev in revisions.itervalues():
            author_name = get_apparent_author_name(rev)
            for item in self.rev_top_items[rev.revision_id]:
                item.setText(1, author_name)
            
            if self.now < rev.timestamp:
                days = 0
            else:
                days = (self.now - rev.timestamp) / (24 * 60 * 60)
            
            saturation = 0.5/((days/50) + 1)
            hue =  1-float(abs(hash(author_name))) / sys.maxint 
            color = QtGui.QColor.fromHsvF(hue, saturation, 1 )
            
            for item in self.rev_indexes[rev.revision_id]:
                item.setBackground(3, color)
    
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

    # XXX this method should be common with the same method in log.py
    def update_selection(self, selected, deselected):
        indexes = [index for index in self.log_list.selectedIndexes()
                   if index.column()==0]
        if not indexes:
            self.message_doc.setHtml("")
        else:
            index = indexes[0]
            revid = str(index.data(RevIdRole).toString())
            gp = self.log_list.graph_provider
            rev  = gp.load_revisions([revid])[revid]
            if not hasattr(rev, "revno"):
                if rev.revision_id in gp.revid_rev:
                    rev.revno = gp.revid_rev[rev.revision_id].revno_str
                else:
                    rev.revno = ""
            self.message_doc.setHtml(format_revision_html(rev,
                                                          show_timestamp=True))

    def linkClicked(self, url):
        open_browser(str(url.toEncoded()))
    
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

    def browser_on_revisions_loaded(self, revisions, last_call):
        self.model.on_revisions_loaded(revisions, last_call)
