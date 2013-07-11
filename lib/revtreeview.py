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
from bzrlib.plugins.qbzr.lib import MS_WINDOWS

from bzrlib.lazy_import import lazy_import
lazy_import(globals(), '''
from bzrlib.plugins.qbzr.lib.util import run_in_loading_queue
from bzrlib.plugins.qbzr.lib.lazycachedrevloader import load_revisions
from bzrlib.plugins.qbzr.lib.diff import ExtDiffContext
from bzrlib.transport.local import LocalTransport
''')

RevIdRole = QtCore.Qt.UserRole + 1


class RevisionTreeView(QtGui.QTreeView):
    """TreeView widget to shows revisions.
    
    Only revisions that are visible on screen are loaded.
    
    The model for this tree view must have the following methods:
    def on_revisions_loaded(self, revisions, last_call)
    def get_revid(self, index)
    def get_repo(self)
    """

    def __init__(self, parent=None):
        QtGui.QTreeView.__init__(self, parent)
        self.connect(self.verticalScrollBar(),
                     QtCore.SIGNAL("valueChanged (int)"),
                     self.scroll_changed)
            
        self.connect(self,
                     QtCore.SIGNAL("collapsed (QModelIndex)"),
                     self.collapsed_expanded)
        
        self.connect(self,
                     QtCore.SIGNAL("expanded (QModelIndex)"),
                     self.collapsed_expanded)
        
        self.load_revisions_call_count = 0
        self.load_revisions_throbber_shown = False
        self.revision_loading_disabled = False
        self.diff_context = ExtDiffContext(self)

    def setModel(self, model):
        QtGui.QTreeView.setModel(self, model)
        
        if isinstance(model, QtGui.QAbstractProxyModel):
            # Connecting the below signal has funny results when we connect to
            # to a ProxyModel, so connect to the source model.
            model = model.sourceModel()
            
        model.connect(model,
                      QtCore.SIGNAL("dataChanged(QModelIndex, QModelIndex)"),
                      self.data_changed)
        model.connect(model,
                      QtCore.SIGNAL("layoutChanged()"),
                      self.layout_changed)
    
    def scroll_changed(self, value):
        self.load_visible_revisions()
    
    def data_changed(self, start_index, end_index):
        self.load_visible_revisions()
    
    def layout_changed(self):
        self.load_visible_revisions()
    
    def collapsed_expanded(self, index):
        self.load_visible_revisions()
    
    def resizeEvent(self, e):
        self.load_visible_revisions()
        QtGui.QTreeView.resizeEvent(self, e)
    
    def load_visible_revisions(self):
        if not self.revision_loading_disabled:
            run_in_loading_queue(self._load_visible_revisions)
    
    def _load_visible_revisions(self):
        model = self.model()
        
        index = self.indexAt(self.viewport().rect().topLeft())
        if not index.isValid():
            return
        
        #if self.throbber is not None:
        #    throbber_height = self.throbber.   etc...        
        bottom_index = self.indexAt(self.viewport().rect().bottomLeft()) # + throbber_height
        
        revids = []
        while True:
            revid = index.data(RevIdRole)
            if not revid.isNull():
                revid = str(revid.toByteArray())
                if revid not in revids:
                    revids.append(revid)
            if index == bottom_index:
                break
            index = self.indexBelow(index)
            if not index.isValid():
                break
        
        revids = list(revids)
        if len(revids) == 0:
            return
        
        self.load_revisions_call_count += 1
        current_call_count = self.load_revisions_call_count

        def before_batch_load(repo, revids):
            if current_call_count < self.load_revisions_call_count:
                return True
            
            repo_is_local = isinstance(repo.bzrdir.transport, LocalTransport)
            if not repo_is_local:
                # Disable this until we have thobber that does not irratate
                # users when we show and hide quickly.
                #if not self.load_revisions_throbber_shown \
                #            and hasattr(self, "throbber"):
                #    self.throbber.show()
                #    self.load_revisions_throbber_shown = True
                # Allow for more scrolling to happen.
                self.delay(0.5)
            
            return False

        try:
            load_revisions(revids, model.get_repo(),
                           revisions_loaded = model.on_revisions_loaded,
                           before_batch_load = before_batch_load)
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
        QtCore.QCoreApplication.processEvents(
                            QtCore.QEventLoop.WaitForMoreEvents)


has_vista_style = hasattr(QtGui, "QWindowsVistaStyle")
AERO_ENABLED = False
if MS_WINDOWS:
    from bzrlib.plugins.qbzr.lib import win32util
    # it seems that latest available bzr distributives for Windows
    # contain a bit outdated version of PyQt which does not support Win8 styles well.
    # But it does support Vista/Win7 good enough.
    # So we enable our hack with selected text color only on Vista/Win7
    if win32util.is_vista_or_win7():
        AERO_ENABLED = win32util.is_aero_enabled()


def get_text_color(option, style):
    # cg == ColorGroup
    if option.state & QtGui.QStyle.State_Enabled:
        if option.state & QtGui.QStyle.State_Active:
            cg = QtGui.QPalette.Active
        else:
            cg = QtGui.QPalette.Inactive
    else:
        cg = QtGui.QPalette.Disabled
    
    if option.state & QtGui.QStyle.State_Selected:
        if has_vista_style and isinstance(style, QtGui.QWindowsVistaStyle):
            # QWindowsVistaStyle normally modifies it palette,
            # but as we can't reuse that code, we have to reproduce
            # what it does here.
            # https://bugs.edge.launchpad.net/qbzr/+bug/457895
            return option.palette.color(cg, QtGui.QPalette.Text)
        elif AERO_ENABLED:
            # hack-hack-hack for Vista/Win7: we need to use the black text
            # when aero selection of light blue with gradient is used
            return option.palette.color(cg, QtGui.QPalette.Text)

        return option.palette.color(cg, QtGui.QPalette.HighlightedText)
    else:
        return option.palette.color(cg, QtGui.QPalette.Text)


class RevNoItemDelegate(QtGui.QStyledItemDelegate):

    def __init__ (self, max_mainline_digits=4, parent=None):
        QtGui.QItemDelegate.__init__(self, parent)
        self.max_mainline_digits = max_mainline_digits
    
    def paint(self, painter, option, index):
        option = QtGui.QStyleOptionViewItemV4(option)
        self.initStyleOption(option, index)
        widget = self.parent()
        style = widget.style()
        
        painter.save()
        painter.setClipRect(option.rect)
        style.drawPrimitive(QtGui.QStyle.PE_PanelItemViewItem,
                            option, painter, widget)
        
        text_margin = style.pixelMetric(QtGui.QStyle.PM_FocusFrameHMargin,
                                        None, widget) + 1
        text_rect = option.rect.adjusted(text_margin, 0, -text_margin, 0)
        
        painter.setPen(get_text_color(option, style))
        
        if not option.text.isEmpty():
            text = option.text
            paint_revno(painter, text_rect, text, self.max_mainline_digits)
        
        painter.restore()

    def set_max_revno(self, revno):
        """Update max_mainline_digits based on max revno.
        Return the new value of max_mainline_digits to caller.
        """
        mainline_digits = len("%d" % revno)
        self.max_mainline_digits = max(mainline_digits, 4)
        return self.max_mainline_digits


def paint_revno(painter, rect, revno, max_mainline_digits):
    splitpoint = revno.indexOf(".")
    if splitpoint == -1:
        splitpoint = len(revno)
    mainline, therest = revno[:splitpoint], revno[splitpoint:]
    
    if mainline.endsWith(" ?"):
        mainline = mainline[:-2]
        therest = " ?"
    
    fm = painter.fontMetrics()
    mainline_width = fm.width("8"*max_mainline_digits)
    therest_width = fm.width(therest)
    
    if mainline_width + therest_width > rect.width():
        text = revno
        if fm.width(text) > rect.width():
            text = fm.elidedText(text, QtCore.Qt.ElideRight, rect.width())
        painter.drawText(rect, QtCore.Qt.AlignRight, text);
    else:
        mainline_rect = QtCore.QRect(rect.x(),
                                     rect.y(),
                                     mainline_width,
                                     rect.height())
        therest_rect = QtCore.QRect(rect.x() + mainline_width,
                                    rect.y(),
                                    rect.width() - mainline_width,
                                    rect.height())
        painter.drawText(mainline_rect, QtCore.Qt.AlignRight, mainline)
        painter.drawText(therest_rect, QtCore.Qt.AlignLeft, therest)
