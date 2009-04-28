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

import operator, sys, time
from PyQt4 import QtCore, QtGui
from bzrlib.plugins.qbzr.lib.diff import show_diff, InternalDiffArgProvider
from bzrlib.plugins.qbzr.lib.i18n import gettext
from bzrlib.plugins.qbzr.lib.util import (
    BTN_CLOSE,
    QBzrWindow,
    ThrobberWidget,
    format_revision_html,
    format_timestamp,
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
from bzrlib.plugins.qbzr.lib.logmodel import COL_DATE, COL_AUTHOR, RevIdRole

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
        self.fileId = fileId
        self.path = path
        self.encoding = encoding
        self.loader_func = loader
        self.loader_args = loader_args

        self.throbber = ThrobberWidget(self)
        
        self.browser = QtGui.QTreeWidget()
        self.browser.setRootIsDecorated(False)
        self.browser.setUniformRowHeights(True)
        self.browser.setHeaderLabels([gettext("Line"), gettext("Author"), gettext("Rev"), ""])
        self.browser.header().setStretchLastSection(False)
        self.browser.header().setResizeMode(QtGui.QHeaderView.ResizeToContents)
        # We don't connect the browser's signals up yet, to avoid errors if
        # the user clicks while loading - we hook them after initial load.

        self.message_doc = QtGui.QTextDocument()
        message = RevisionMessageBrowser()
        message.setDocument(self.message_doc)
        self.connect(message,
                     QtCore.SIGNAL("anchorClicked(QUrl)"),
                     self.linkClicked)

        self.log_list = LogList(self.processEvents, self.throbber, no_graph, self)
        self.log_list.header().hideSection(COL_DATE)
        #self.log_list.header().hideSection(COL_AUTHOR)
        
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
                self.branch, self.tree, self.path, self.fileId = \
                                        self.loader_func(*self.loader_args)
                self.loader_func = self.loader_args = None # kill extra refs...
                QtCore.QCoreApplication.processEvents()
            self.branch.lock_read()
            try:
                self.log_list.load_branch(self.branch, self.fileId)
                self.annotate(self.tree, self.fileId, self.path)
            finally:
                self.branch.unlock()
        finally:
            self.throbber.hide()

        # and once we are loaded we can hookup the signal handlers.
        # (our code currently can't handle items being clicked on until
        # the load is complete)
        self.connect(self.browser,
            QtCore.SIGNAL("itemSelectionChanged()"),
            self.setRevisionByLine)
        # and update the title to show we are done.
        self.set_title_and_icon([gettext("Annotate"), self.path])

    def annotate(self, tree, fileId, path):
        revnos = self.branch.get_revision_id_to_revno_map()
        revnos = dict((k, '.'.join(map(str, v))) for k, v in revnos.iteritems())
        font = QtGui.QFont("Courier New,courier", self.browser.font().pointSize())
        items = []
        self.rev_items = {}
        self.rev_top_items = {}
        last_revid = None
        encoding = get_set_encoding(self.encoding, self.branch)
        lines = []
        for i, (revid, text) in enumerate(tree.annotate_iter(fileId)):
            text = text.decode(encoding, 'replace')
            lines.append(text)
            item = QtGui.QTreeWidgetItem()
            item.setData(0, QtCore.Qt.UserRole, QtCore.QVariant(revid))
            item.setText(0, QtCore.QString.number(i + 1))
            
            if revid not in self.rev_items:
                self.rev_items[revid]=[]
            self.rev_items[revid].append(item)

            if last_revid != revid:
                if revid not in self.rev_top_items:
                    self.rev_top_items[revid]=[]
                self.rev_top_items[revid].append(item)
                item.setText(2, revnos[revid])
                item.setTextAlignment(2, QtCore.Qt.AlignRight)
            
            item.setText(3, text.rstrip())
            item.setFont(3, font)
            items.append(item)
            last_revid = revid
            self.processEvents()

        self.now = time.time()
        self.log_list.graph_provider.load_revisions(
            self.rev_items.keys(),
            revisions_loaded = self.revisions_loaded,
            pass_prev_loaded_rev = True
            )
        
        
        # take care to insert the items after we are done fiddling with
        # them, else performance suffers drastically.
        self.browser.insertTopLevelItems(0, items)
        self.processEvents()
        
        self.lines = None
        if have_pygments:
            try:
                # A more correct way to do this would be to add the tokens as
                # a data role to each respective tree item. But it is to much
                # effort to wrap them as QVariants. We will just pass the line
                # tokens to the delegate.
                lines_tokens = list(split_tokens_at_lines(\
                                  lex("".join(lines),
                                  get_lexer_for_filename(path))))
                self.browser.setItemDelegateForColumn(3,FormatedCodeItemDelegate(lines_tokens, self))
                
            except ClassNotFound:
                pass
    
    def revisions_loaded(self, revisions, last_call):
        self.log_list.model.on_revisions_loaded(revisions, last_call)
        for revid in revisions:
            rev = self.log_list.graph_provider.revision(revid)
            author_name = get_apparent_author_name(rev)
            for item in self.rev_top_items[revid]:
                item.setText(1, author_name)
            
            if self.now < rev.timestamp:
                days = 0
            else:
                days = (self.now - rev.timestamp) / (24 * 60 * 60)
            
            saturation = 0.5/((days/50) + 1)
            hue =  1-float(abs(hash(author_name))) / sys.maxint 
            color = QtGui.QColor.fromHsvF(hue, saturation, 1 )
            
            for item in self.rev_items[revid]:
                item.setBackground(3, color)
    
    def setRevisionByLine(self):
        items = self.browser.selectedItems()
        if not items:
            return
        rev_id = str(items[0].data(0, QtCore.Qt.UserRole).toString())
        if self.log_list.graph_provider.has_rev_id(rev_id):
            self.log_list.model.ensure_rev_visible(rev_id)
            index = self.log_list.model.indexFromRevId(rev_id)
            index = self.log_list.filter_proxy_model.mapFromSource(index)
            self.log_list.setCurrentIndex(index)

    def update_selection(self, selected, deselected):
        indexes = [index for index in self.log_list.selectedIndexes()
                   if index.column()==0]
        if not indexes:
            self.message_doc.setHtml("")
        else:
            index = indexes[0]
            revid = str(index.data(RevIdRole).toString())
            rev = self.log_list.graph_provider.revision(revid, force_load=True)
            self.message_doc.setHtml(format_revision_html(rev,
                                                          show_timestamp=True))

    def linkClicked(self, url):
        open_browser(str(url.toEncoded()))
