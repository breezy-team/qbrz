# -*- coding: utf-8 -*-
#
# QBzr - Qt frontend to Bazaar commands
# Copyright (C) 2007 Lukáš Lalinský <lalinsky@gmail.com>
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

from PyQt4 import QtGui, QtCore

import re
from bzrlib import timestamp
from bzrlib.patiencediff import PatienceSequenceMatcher as SequenceMatcher
from bzrlib.plugins.qbzr.lib.i18n import gettext
from bzrlib.plugins.qbzr.lib.util import (
    file_extension,
    format_timestamp,
    get_qbzr_config,
    get_monospace_font,
    get_tab_width_pixels,
    )
from bzrlib.trace import mutter
from bzrlib.plugins.qbzr.lib.syntaxhighlighter import (
    CachedTTypeFormater,
    split_tokens_at_lines,
    )
from bzrlib.plugins.qbzr.lib.widgets.texteditaccessory import (
    GuideBarPanel,    GBAR_LEFT,  GBAR_RIGHT
)

have_pygments = True
try:
    from pygments import lex
    from pygments.util import ClassNotFound
    from pygments.lexers import get_lexer_for_filename
except ImportError:
    have_pygments = False

colors = {
    'delete': [QtGui.QColor(255, 160, 180), QtGui.QColor(200, 60, 90)],
    'insert': [QtGui.QColor(180, 255, 180), QtGui.QColor(80, 210, 80)],
    'replace': [QtGui.QColor(206, 226, 250), QtGui.QColor(90, 130, 180)],
    'blank': [QtGui.QColor(240, 240, 240), QtGui.QColor(171, 171, 171)],
    'dummy': [QtGui.QColor(0, 0, 0, 0), QtGui.QColor(0, 0, 0, 0)],
}
#The background color of the replacement text in a replacement group.
interline_changes_background = QtGui.QColor(180, 210, 250)

#load user-defined color mapping from configuration file.

#For each kind, there can be two entries in the configuration file,
#under the [QDIFF COLORS] section:
#  kind_bound -- the color of the boundary of the rectangle this kind refers to.
#  kind_fill  -- the color of the filling of that same rectangle.

config = get_qbzr_config()
component_dict = {0:'fill', 1:'bound'}
for key in colors.iterkeys():
    for comp in [0,1]:
        color = None
        try:
            color = config.get_color(key + '_' + component_dict[comp],
                                        'QDIFF COLORS')
        except ValueError, msg:
            #error handling.
            mutter(str(msg))
        if None != color:
            colors[key][comp] = color
            

#Get a user-defined replacement text background
try:
    new_interline_bg  = config.get_color('interline_changes_background',
                                         'QDIFF COLORS')
    if None != new_interline_bg:
      interline_changes_background = new_interline_bg
except ValueError, msg:
    mutter(str(msg))

brushes = {}
for kind, cols in colors.items():
    brushes[kind] = (QtGui.QBrush(cols[0]), QtGui.QBrush(cols[1]))


class DiffSourceView(QtGui.QTextBrowser):

    def __init__(self, parent=None):
        QtGui.QTextBrowser.__init__(self, parent)
        self.setLineWrapMode(QtGui.QTextEdit.NoWrap)
        self.clear()
        self.scrollbar = None

    def clear(self):
        self.changes = []
        self.infoBlocks = []

    def resizeEvent(self, event):
        QtGui.QTextBrowser.resizeEvent(self, event)
        self.emit(QtCore.SIGNAL("resized()"))

    def paintEvent(self, event):
        w = self.width()
        y = self.verticalScrollBar().value()
        painter = QtGui.QPainter(self.viewport())
        painter.setClipRect(event.rect())
        bot = event.rect().bottom()
        top = event.rect().top()
        pen = QtGui.QPen(QtCore.Qt.black)
        pen.setWidth(2)
        painter.setPen(pen)
        for block_y in self.infoBlocks:
            block_y = block_y - y
            if block_y < top:
                continue
            if block_y > bot:
                break
            painter.drawLine(0, block_y, w, block_y)
        
        pen.setWidth(1)
        for y_top, y_bot, kind in self.changes:
            y_top -= y
            y_bot -= y
            if y_top < top and y_bot < top:
                continue
            if y_top > bot and y_bot > bot:
                break
            painter.fillRect(0,  y_top, w, y_bot - y_top, brushes[kind][0])
            painter.setPen(colors[kind][1])
            painter.drawLine(0, y_top, w, y_top)
            painter.drawLine(0, y_bot - 1, w, y_bot - 1)
        del painter
        QtGui.QTextBrowser.paintEvent(self, event) 

    def wheelEvent(self, event):
        if event.orientation() == QtCore.Qt.Vertical and self.scrollbar:
            self.scrollbar.wheelEvent(event)
        else:
            QtGui.QTextBrowser.wheelEvent(self, event)

class DiffViewHandle(QtGui.QSplitterHandle):

    def __init__(self, parent=None):
        QtGui.QSplitterHandle.__init__(self, QtCore.Qt.Horizontal, parent)
        self.scrollbar = None
        self.view = parent
        self.clear()
        
    def clear(self):
        self.changes = []
        self.infoBlocks = []

    def paintEvent(self, event):
        painter = QtGui.QPainter(self)
        painter.setClipRect(event.rect())
        frame = QtGui.QApplication.style().pixelMetric(QtGui.QStyle.PM_DefaultFrameWidth)
        ly = self.view.browsers[0].verticalScrollBar().value() - frame
        ry = self.view.browsers[1].verticalScrollBar().value() - frame
        w = self.width()
        h = self.height()
        painter.setRenderHints(QtGui.QPainter.Antialiasing, True)

        C = 16 # Curve factor.

        def create_line(ly, ry, right_to_left=False):
            """
            Create path which represents upper or lower line of change marker.
            """
            line = QtGui.QPainterPath()
            if not right_to_left:
                line.moveTo(0, ly)
                line.cubicTo(C, ly, w - C, ry, w, ry)
            else:
                line.moveTo(w, ry)
                line.cubicTo(w - C, ry, C, ly, 0, ly)
            return line

        pen = QtGui.QPen(QtCore.Qt.black)
        pen.setWidth(2)
        painter.setPen(pen)
        for block_ly, block_ry in self.infoBlocks:
            block_ly -= ly
            block_ry -= ry
            if block_ly < 0 and block_ry < 0:
                continue
            if block_ly > h and block_ry > h:
                break

            painter.drawPath(create_line(block_ly, block_ry))

        for ly_top, ly_bot, ry_top, ry_bot, kind in self.changes:
            ly_top -= ly
            ly_bot -= ly + 1
            ry_top -= ry
            ry_bot -= ry + 1
            
            if ly_top < 0 and ly_bot < 0 and ry_top < 0 and ry_bot < 0:
                continue
            if ly_top > h and ly_bot > h and ry_top > h and ry_bot > h:
                break

            upper_line = create_line(ly_top, ry_top)
            lower_line = create_line(ly_bot, ry_bot, True)

            region = QtGui.QPainterPath()
            region.moveTo(0, ly_top)
            region.connectPath(upper_line)
            region.lineTo(w, ry_bot)
            region.connectPath(lower_line)
            region.closeSubpath()

            painter.fillPath(region, brushes[kind][0])
            painter.setPen(colors[kind][1])
            for path, aa in zip((upper_line, lower_line), 
                                (ly_top != ry_top, ly_bot != ry_bot)):
                painter.setRenderHints(QtGui.QPainter.Antialiasing, aa)
                painter.drawPath(path)
        del painter

    def wheelEvent(self, event):
        if event.orientation() == QtCore.Qt.Vertical:
            self.view.scrollbar.wheelEvent(event)
        else:
            QtGui.QSplitterHandle.wheelEvent(self, event)

class SidebySideDiffView(QtGui.QFrame):
    def __init__(self, parent=None):
        QtGui.QFrame.__init__(self, parent)
        hbox = QtGui.QHBoxLayout(self)
        hbox.setMargin(0)
        hbox.setSpacing(0)
        self.view = _SidebySideDiffView(parent)
        self.browsers = self.view.browsers
        hbox.addWidget(self.view)
        hbox.addWidget(self.view.scrollbar)

    def __getattr__(self, name):
        """Delegate unknown methods to internal diffview."""
        return getattr(self.view, name)


SYNC_POSITION = 0.4

class SidebySideDiffViewScrollBar(QtGui.QScrollBar):
    def __init__(self, handle, browsers):
        QtGui.QScrollBar.__init__(self)
        self.handle = handle
        self.browsers = browsers
        self.total_length = 0
        self.changes = []
        self.complete = False

        for b in browsers:
            b.scrollbar = self

        for i, scbar in enumerate([self] + [b.verticalScrollBar() for b in browsers]):
            self.connect(scbar, QtCore.SIGNAL("valueChanged(int)"), 
                                        lambda value, target=i : self.scrolled(target))

        self.connect(browsers[0], QtCore.SIGNAL("resized()"), self.adjust_range)
        self.setSingleStep(browsers[0].verticalScrollBar().singleStep())
        self.adjust_range()
        self.syncing = False
        self.gap_with_left = 0

    def clear(self):
        self.gap_with_left = 0
        self.total_length = 0
        self.changes = []

    def set_complete(self, complete):
        if self.complete != complete:
            self.complete = complete
            self.clear()

    def adjust_range(self):
        page_step = self.browsers[0].verticalScrollBar().pageStep()
        self.setPageStep(page_step)
        self.setRange(0, self.total_length - page_step + 4)
        self.setVisible(self.total_length > page_step)

    def get_position_info(self, target):
        """
        Get position info should scroll to.
        target: 0 is self, 1 is left browser, 2 is right browser
        """
        basis_y = self.height() * SYNC_POSITION
        if target == 0:
            scbar = self
            changes = self.changes
        else:
            b = self.browsers[target - 1]
            scbar, changes = b.verticalScrollBar(), b.changes

        if not self.complete:
            return 'exact', scbar.value()
        else:
            value = scbar.value() + basis_y
            prev = (0, 0, None)
            for i, ch in enumerate(changes):
                if value <= ch[1]:
                    if ch[0] <= value:
                        ratio = float(value - ch[0]) / (ch[1] - ch[0])
                        return 'in', i, ratio
                    else:
                        offset = value - prev[1]
                        return 'after', i - 1, offset
                    break
                else:
                    prev = ch
            else:
                offset = value - prev[1]
                return 'after', len(self.changes) - 1, offset

    def scroll_to(self, target, position):
        """
        Scroll to specified position.
        target: 0 is self, 1 is left browser, 2 is right browser
        """
        basis_y = self.height() * SYNC_POSITION
        if target == 0:
            scbar, changes = self, self.changes
        else:
            b = self.browsers[target - 1]
            scbar, changes = b.verticalScrollBar(), b.changes
        if position[0] == 'exact':
            scbar.setValue(position[1])
        elif position[0] == 'in':
            change_idx, ratio = position[1:]
            start, end = changes[change_idx][:2]
            scbar.setValue(start + float(end - start) * ratio - basis_y)
        else:
            change_idx, offset = position[1:]
            if change_idx < 0:
                start = 0
            else:
                start = changes[change_idx][1]
            scbar.setValue(start + offset - basis_y)

    def scrolled(self, target):
        if self.syncing:
            return
        try:
            self.syncing = True
            position = self.get_position_info(target)
            for t in range(3):
                if t != target:
                    self.scroll_to(t, position)
            self.handle.update()
        finally:
            self.syncing = False

    def append_change(self, l_top, l_bot, r_top, r_bot, kind):
        if not self.complete:
            return
        changes = self.changes
        height = max(l_bot - l_top, r_bot - r_top)
        top = l_top + self.gap_with_left
        changes.append((top, top + height, kind))
        self.gap_with_left = top + height - l_bot

    def fix_document_length(self, cursors):
        if not self.complete:
            scbar = self.browsers[0].verticalScrollBar()
            self.total_length = scbar.maximum() + scbar.pageStep()
        else:
            l = cursors[0].block().layout()
            self.total_length = l.position().y() + l.boundingRect().height() \
                                 + self.gap_with_left

        self.adjust_range()



def setup_guidebar_entries(gb):
    gb.add_entry('title', QtGui.QColor(80, 80, 80), -1)
    for tag in ('delete', 'insert', 'replace'):
        gb.add_entry(tag, colors[tag][0], 0)

class _SidebySideDiffView(QtGui.QSplitter):
    """Widget to show differences in side-by-side format."""

    def __init__(self, parent=None):
        QtGui.QSplitter.__init__(self, QtCore.Qt.Horizontal, parent)
        self.setHandleWidth(30)
        self.complete = False

        titleFont = QtGui.QFont(self.font())
        titleFont.setPointSize(titleFont.pointSize() * 140 / 100)
        titleFont.setBold(True)
        
        self.monospacedFont = get_monospace_font()
        metadataFont = QtGui.QFont(self.font())
        metadataFont.setPointSize(titleFont.pointSize() * 70 / 100)
        metadataLabelFont = QtGui.QFont(metadataFont)
        metadataLabelFont.setBold(True)
    
        self.monospacedFormat = QtGui.QTextCharFormat()
        self.monospacedFormat.setFont(self.monospacedFont)
        self.ttype_formater = CachedTTypeFormater(
                                QtGui.QTextCharFormat(self.monospacedFormat))
        self.background = self.monospacedFormat.background()
        
        self.titleFormat = QtGui.QTextCharFormat()
        self.titleFormat.setFont(titleFont)
        self.metadataFormat = QtGui.QTextCharFormat()
        self.metadataFormat.setFont(metadataFont)
        self.metadataLabelFormat = QtGui.QTextCharFormat()
        self.metadataLabelFormat.setFont(metadataLabelFont)

        self.docs = (QtGui.QTextDocument(),
                     QtGui.QTextDocument())
        self.browsers = (DiffSourceView(self),
                         DiffSourceView(self))

        self.guidebar_panels = [
            GuideBarPanel(b, align=a)
            for (b, a) in zip(self.browsers, (GBAR_LEFT, GBAR_RIGHT))
        ]
        for g in self.guidebar_panels:
            setup_guidebar_entries(g.bar)

        self.reset_guidebar_data()

        for b in self.browsers:
            b.setVerticalScrollBarPolicy(QtCore.Qt.ScrollBarAlwaysOff)

        self.cursors = [QtGui.QTextCursor(doc) for doc in self.docs]
        
        for i, (panel, doc, cursor) in enumerate(zip(self.guidebar_panels,
                                                     self.docs, self.cursors)):
            doc.setUndoRedoEnabled(False)
            doc.setDefaultFont(self.monospacedFont)
            
            panel.edit.setDocument(doc)
            self.addWidget(panel)
            self.setCollapsible(i, False)

            format = QtGui.QTextCharFormat()
            format.setAnchorNames(["top"])
            cursor.insertText("", format)

        self.scrollbar = SidebySideDiffViewScrollBar(self.handle(1), self.browsers)

        self.ignoreUpdate = False
        self.connect(self.browsers[0].horizontalScrollBar(), QtCore.SIGNAL("valueChanged(int)"), self.syncHorizontalSlider1)
        self.connect(self.browsers[1].horizontalScrollBar(), QtCore.SIGNAL("valueChanged(int)"), self.syncHorizontalSlider2)

        self.rewinded = False
        
        self.lastModifiedLabel = gettext('Last modified:')
        self.statusLabel = gettext('Status:')
        self.kindLabel = gettext('Kind:')
        self.propertiesLabel = gettext('Properties:')
        
        self.image_exts = ['.'+str(i)
            for i in QtGui.QImageReader.supportedImageFormats()]
        
        config = get_qbzr_config()
        self.show_intergroup_colors = config.get_option("diff_show_intergroup_colors") in ("True", "1")

    def setTabStopWidths(self, pixels):
        for (pixel_width, browser) in zip(pixels, self.browsers):
            browser.setTabStopWidth(pixel_width)

    def reset_guidebar_data(self):
        self.guidebar_data = [
            dict(title=[], delete=[], insert=[], replace=[]), # for left view
            dict(title=[], delete=[], insert=[], replace=[]), # for right view
        ]

    def clear(self):
        self.browsers[0].clear()
        self.browsers[1].clear()
        self.handle(1).clear()
        self.scrollbar.clear()
        for doc in self.docs:
            doc.clear()
        self.reset_guidebar_data()
        self.update()

    def set_complete(self, complete):
        if self.complete != complete:
            self.complete = complete
            self.clear()
            self.scrollbar.set_complete(complete)

    def append_diff(self, paths, file_id, kind, status, dates,
                    present, binary, lines, groups, data, properties_changed):
        cursors = self.cursors

        guidebar_data = self.guidebar_data

        for i in range(2):
            cursor = cursors[i]
            guidebar_data[i]['title'].append((cursor.block().blockNumber(), 2))
            cursor.beginEditBlock()
            cursor.insertText(paths[i] or " ", self.titleFormat)    # None or " " => " "
            cursor.insertBlock()
            if present[i]:
                cursor.insertText(self.lastModifiedLabel, self.metadataLabelFormat)
                cursor.insertText(" %s, " % format_timestamp(dates[i]), self.metadataFormat)
                cursor.insertText(self.statusLabel, self.metadataLabelFormat)
                cursor.insertText(" %s, " % gettext(status), self.metadataFormat)
                cursor.insertText(self.kindLabel, self.metadataLabelFormat)
                cursor.insertText(" %s" % gettext(kind[i]), self.metadataFormat)
                if properties_changed:
                    cursor.insertText(", ", self.metadataFormat)
                    cursor.insertText(self.propertiesLabel, self.metadataLabelFormat)
                    cursor.insertText(" ", self.metadataFormat)
                    cursor.insertText(", ".join([p[i] for p in properties_changed]), self.metadataFormat)
            else:
                cursor.insertText(" ", self.metadataFormat)
            cursor.insertBlock()
        
        infoBlocks = (cursors[0].block().layout(),
                      cursors[1].block().layout())
        changes = []
            
        if not binary:
            for cursor in cursors:
                cursor.setCharFormat(self.monospacedFormat)
                cursor.insertBlock()
            
            def fix_last_line(lines):
                """Fix last line if there is no new line.

                @param  lines:  list of lines
                @return:    original lines if lastline is OK,
                            or new list with fixed last line.
                """
                if lines:
                    last = lines[-1]
                    if last and last[-1] not in ('\r', '\n'):
                        lines = lines[:-1] + [last+'\n']
                return lines
            
            lines = [fix_last_line(l) for l in lines]
            if have_pygments:
                use_pygments = True
                try:
                    def getTokens(p, d, path):
                        if not p:
                            return []
                        lexer = get_lexer_for_filename(path, stripnl=False)
                        tokens = []
                        for token in split_tokens_at_lines(lex(d, lexer)):
                            tokens.append(token)
                            if len(token) % 100 == 0:
                                QtCore.QCoreApplication.processEvents()
                        return tokens

                    display_lines = [getTokens(p, d, path)
                                     for p, d, path in zip(present,
                                                           data,
                                                           paths)]
                except ClassNotFound:
                    use_pygments = False
                    display_lines = lines
            else:
                use_pygments = False
                display_lines = lines
            
            def insertLine(cursor, line):
                if use_pygments:
                    for ttype, value in line:
                        format = self.ttype_formater.format(ttype)
                        modifyFormatForTag(format, "equal")
                        cursor.insertText(value, format)
                else:
                    cursor.insertText(line)
            
            def insertIxs(ixs):
                for cursor, line, ix in zip(cursors, display_lines, ixs):
                    for l in line[ix[0]:ix[1]]:
                        insertLine(cursor, l)
            
            def modifyFormatForTag (format, tag):
                if tag == "replace":
                    format.setBackground(interline_changes_background)
                elif tag == "equal":
                    format.setBackground(self.background)
                elif self.show_intergroup_colors:
                    format.setBackground(brushes[tag][0])
                else:
                    format.setBackground(interline_changes_background)
            
            split_words = re.compile(r"\w+|\n\r|\r\n|\W")
            def insertIxsWithChangesHighlighted(ixs):
                texts = ["".join(l[ix[0]:ix[1]]) for l, ix in zip(lines, ixs)]
                if use_pygments:
                    # This is what the pygments lexer does, so we need to do the
                    # same incase we have \r\n line endings.
                    texts = ["\n".join(t.splitlines()) for t in texts]
                
                texts = [split_words.findall(t) for t in texts]
                
                if use_pygments:
                    groups = ([], [])
                    for tag, i0, i1, j0, j1 in SequenceMatcher(None,
                                                                tuple(texts[0]),
                                                                tuple(texts[1]),
                                                                ).get_opcodes():
                        groups[0].append((tag, len("".join(texts[0][i0:i1]))))
                        groups[1].append((tag, len("".join(texts[1][j0:j1]))))
                    for cursor, ls, ix, g in zip(cursors, display_lines, ixs, groups):
                        tag, n = g.pop(0)
                        for l in ls[ix[0]:ix[1]]:
                            for ttype, value in l:
                                while value:
                                    format = self.ttype_formater.format(ttype)
                                    modifyFormatForTag(format, tag)
                                    t = value[0:n]
                                    cursor.insertText(t, format)
                                    value = value[len(t):]
                                    n -= len(t)
                                    if n<=0:
                                        if g:
                                            tag, n = g.pop(0)
                                        else:
                                            # why would this happen?????
                                            tag = 'equal'
                                            n = len(value)
                else:
                    for tag, i0, i1, j0, j1 in SequenceMatcher(None,
                                                               tuple(texts[0]),
                                                               tuple(texts[1]),
                                                               ).get_opcodes():
                        format = QtGui.QTextCharFormat()
                        format.setFont(self.monospacedFont)
                        modifyFormatForTag(format, tag)
                        
                        cursors[0].insertText("".join(texts[0][i0:i1]),format)
                        cursors[1].insertText("".join(texts[1][j0:j1]),format)
                    
                    for cursor in cursors:
                        cursor.setCharFormat (self.monospacedFormat)

            
            for i, group in enumerate(groups):
                if i > 0:
                    y_top = [cursor.block().layout() for cursor in self.cursors]
                    for cursor in cursors:
                        cursor.insertBlock()
                    t_bot = [cursor.block().layout() for cursor in self.cursors]
                    changes.append((y_top[0], t_bot[0], y_top[1], t_bot[1], 'blank'))
                linediff = 0
                for g in group:
                    tag = g[0]
                    # indexes
                    ixs = ((g[1], g[2]), (g[3], g[4]))
                    n = [ix[1]-ix[0] for ix in ixs]
                    if tag == "equal":
                        insertIxs(ixs)
                    else:
                        y_top = [cursor.block().layout() for cursor in self.cursors]
                        g_top = [cursor.block().blockNumber() for cursor in self.cursors]
                        if tag == "replace":
                            insertIxsWithChangesHighlighted(ixs)
                        else:
                            insertIxs(ixs)
                        linediff += n[0] - n[1]
                        y_bot = [cursor.block().layout() for cursor in self.cursors]
                        changes.append((y_top[0], y_bot[0], y_top[1], y_bot[1], tag))

                        g_bot = [cursor.block().blockNumber() for cursor in self.cursors]
                        for data, top, bot in zip(guidebar_data, g_top, g_bot):
                            data[tag].append((top, bot - top))

                if linediff == 0:
                    continue
                if not self.complete:
                    if linediff < 0:
                        i0 = group[-1][2]
                        i1 = i0 - linediff
                        exlines = display_lines[0][i0:i1]
                        linediff = -linediff - len(exlines)
                        cursor = cursors[0]
                    else:
                        j0 = group[-1][4]
                        j1 = j0 + linediff
                        exlines = display_lines[1][j0:j1]
                        linediff = linediff - len(exlines)
                        cursor = cursors[1]
                    for l in exlines:
                        insertLine(cursor, l)

                if i % 100 == 0:
                    QtCore.QCoreApplication.processEvents()
        else:
            y_top = [cursor.block().layout() for cursor in self.cursors]
            heights = [0,0]
            is_images = [False, False]
            for i in range(2):
                if present[i]:
                    ext = file_extension(paths[i]).lower()
                    if ext in self.image_exts:
                        is_images[i] = True
                        image = QtGui.QImage()
                        image.loadFromData(data[i])
                        heights[i] = image.height()
                        self.docs[i].addResource(QtGui.QTextDocument.ImageResource,
                                        QtCore.QUrl(file_id),
                                        QtCore.QVariant(image))
            
            max_height = max(heights)
            for i, cursor in enumerate(self.cursors):
                format = QtGui.QTextBlockFormat()
                format.setBottomMargin((max_height - heights[i])/2)
                format.setTopMargin((max_height - heights[i])/2)
                cursor.insertBlock(format)
                if present[i]:
                    if is_images[i]:
                        cursor.insertImage(file_id)
                    else:
                        cursor.insertText(gettext('[binary file (%d bytes)]') % len(data[i]))
                else:
                    cursor.insertText(" ")
                cursor.insertBlock(QtGui.QTextBlockFormat())
            y_bot = [cursor.block().layout() for cursor in self.cursors]
            changes.append((y_top[0], y_bot[0], y_top[1], y_bot[1], 'dummy'))

        for cursor in cursors:
            cursor.endEditBlock()
            cursor.insertText("\n")
        y_top = [cursor.block().layout() for cursor in self.cursors]
        if not self.complete:
            maxy = max([l.position().y() for l in y_top])
            for cursor in cursors:
                format = QtGui.QTextBlockFormat()
                format.setBottomMargin(maxy-cursor.block().layout().position().y())
                cursor.setBlockFormat(format)
                cursor.insertBlock(QtGui.QTextBlockFormat())

        l_block = infoBlocks[0].position().y()
        r_block = infoBlocks[1].position().y()
        self.browsers[0].infoBlocks.append(l_block)
        self.browsers[1].infoBlocks.append(r_block)
        self.handle(1).infoBlocks.append((l_block, r_block))
        
        for (ly_top, ly_bot, ry_top, ry_bot, kind) in changes:
            ly_top = ly_top.position().y() - 1
            ly_bot = ly_bot.position().y() + 1
            ry_top = ry_top.position().y() - 1
            ry_bot = ry_bot.position().y() + 1
            self.scrollbar.append_change(ly_top, ly_bot, ry_top, ry_bot, kind)
            self.browsers[0].changes.append((ly_top, ly_bot, kind))
            self.browsers[1].changes.append((ry_top, ry_bot, kind))
            self.handle(1).changes.append((ly_top, ly_bot, ry_top, ry_bot, kind))
        self.scrollbar.fix_document_length(cursors)
        
        # check horizontal scrollbars and force both if scrollbar visible only at one side
        if (self.browsers[0].horizontalScrollBar().isVisible()
            or self.browsers[1].horizontalScrollBar().isVisible()):
            self.browsers[0].setHorizontalScrollBarPolicy(QtCore.Qt.ScrollBarAlwaysOn)
            self.browsers[1].setHorizontalScrollBarPolicy(QtCore.Qt.ScrollBarAlwaysOn)

        self.update_guidebar()
        self.update()
    
    def rewind(self):
        if not self.rewinded:
            self.rewinded = True
            self.browsers[0].scrollToAnchor("top")
            self.browsers[1].scrollToAnchor("top")

    def _syncSliders(self, slider1, slider2, value):
        m = slider1.maximum()
        if m:
            value = slider2.minimum() + slider2.maximum() * (value - slider1.minimum()) / m
            self.ignoreUpdate = True
            slider2.setValue(value)
            self.ignoreUpdate = False

    def syncHorizontalSlider1(self, value):
        if not self.ignoreUpdate:
            slider1 = self.browsers[0].horizontalScrollBar()
            slider2 = self.browsers[1].horizontalScrollBar()
            self._syncSliders(slider1, slider2, value)
            self.handle(1).update()

    def syncHorizontalSlider2(self, value):
        if not self.ignoreUpdate:
            slider1 = self.browsers[0].horizontalScrollBar()
            slider2 = self.browsers[1].horizontalScrollBar()
            self._syncSliders(slider2, slider1, value)
            self.handle(1).update()

    def createHandle(self):
        return DiffViewHandle(self)

    def update_guidebar(self):
        for gb, data in zip(self.guidebar_panels, self.guidebar_data):
            gb.bar.update_data(**data)

class SimpleDiffView(GuideBarPanel):
    def __init__(self, parent):
        self.view = _SimpleDiffView(parent)
        GuideBarPanel.__init__(self, self.view, parent=parent)
        setup_guidebar_entries(self)

    def append_diff(self, *args, **kwargs):
        self.view.append_diff(*args, **kwargs)
        self.update_data(**self.view.guidebar_data)

    def __getattr__(self, name):
        """Delegate unknown methods to internal diffview."""
        return getattr(self.view, name)


class _SimpleDiffView(QtGui.QTextBrowser):
    """Widget to show differences in unidiff format."""

    def __init__(self, parent=None):
        QtGui.QTextBrowser.__init__(self, parent)
        self.doc = QtGui.QTextDocument(parent)
        self.doc.setUndoRedoEnabled(False)
        self.setDocument(self.doc)
        option = self.doc.defaultTextOption()
        option.setWrapMode(QtGui.QTextOption.NoWrap)
        self.doc.setDefaultTextOption(option)
        self.rewinded = False
        self.cursor = QtGui.QTextCursor(self.doc)
        format = QtGui.QTextCharFormat()
        format.setAnchorNames(["top"])
        self.cursor.insertText("", format)
        monospacedFont = get_monospace_font()
        self.monospacedFormat = QtGui.QTextCharFormat()
        self.monospacedFormat.setFont(monospacedFont)

        self.monospacedInsertFormat = QtGui.QTextCharFormat(self.monospacedFormat)
        self.monospacedInsertFormat.setForeground(QtGui.QColor(0, 136, 11))
        self.monospacedDeleteFormat = QtGui.QTextCharFormat(self.monospacedFormat)
        self.monospacedDeleteFormat.setForeground(QtGui.QColor(204, 0, 0))
    
        monospacedBoldFont = QtGui.QFont(monospacedFont)
        monospacedBoldFont.setBold(True)
    
        monospacedItalicFont = QtGui.QFont(monospacedFont)
        monospacedItalicFont.setItalic(True)
    
        self.monospacedBoldInsertFormat = QtGui.QTextCharFormat(self.monospacedInsertFormat)
        self.monospacedBoldInsertFormat.setFont(monospacedBoldFont)
        self.monospacedBoldDeleteFormat = QtGui.QTextCharFormat(self.monospacedDeleteFormat)
        self.monospacedBoldDeleteFormat.setFont(monospacedBoldFont)
    
        self.monospacedHeaderFormat = QtGui.QTextCharFormat()
        self.monospacedHeaderFormat.setFont(monospacedBoldFont)
        self.monospacedHeaderFormat.setBackground(QtGui.QColor(246, 245, 238))
        self.monospacedHeaderFormat.setForeground(QtGui.QColor(117, 117, 117))
    
        self.monospacedHunkFormat = QtGui.QTextCharFormat()
        self.monospacedHunkFormat.setFont(monospacedItalicFont)
        self.monospacedHunkFormat.setForeground(QtGui.QColor(153, 30, 199))

        self.reset_guidebar_data()

    def rewind(self):
        if not self.rewinded:
            self.rewinded = True
            self.scrollToAnchor("top")

    def set_complete(self, complete):
        self.clear()

    def append_diff(self, paths, file_id, kind, status, dates,
                    present, binary, lines, groups, data, properties_changed):
        guidebar_data = self.guidebar_data
        guidebar_data['title'].append((self.cursor.block().blockNumber(), 2))
        self.cursor.beginEditBlock()
        path_info = paths[1] or paths[0]
        if status in ('renamed', 'renamed and modified'):
            path_info = paths[0] + ' => ' + paths[1]
        kind_info = kind[0] or kind[1]
        self.cursor.insertText("=== %s %s %s" % (gettext(status),
            gettext(kind_info), path_info),
            self.monospacedHeaderFormat)
        if properties_changed:
            prop_str = []
            for pair in properties_changed:
                if None not in pair:
                    prop_str.append("%s to %s" % pair)
            if prop_str:
                self.cursor.insertText(
                    " (properties changed: %s)" % (", ".join(prop_str)))
        self.cursor.insertText("\n")
        
        # GNU Patch uses the epoch date to detect files that are being added
        # or removed in a diff.
        EPOCH_DATE = '1970-01-01 00:00:00 +0000'
        for i in range(2):
            if present[i]:
                dates[i] = timestamp.format_patch_date(dates[i])
            else:
                paths[i] = paths[(i+1)%2]
                dates[i] = EPOCH_DATE
        
        if not binary:
            self.cursor.insertText('--- %s\t%s\n' % (paths[0], dates[0]),
                                      self.monospacedBoldInsertFormat)
            self.cursor.insertText('+++ %s\t%s\n' % (paths[1], dates[1]),
                                   self.monospacedBoldDeleteFormat)

            def fix_last_line(lines):
                """Fix last line if there is no new line.

                @param  lines:  original list of lines
                @return:    lines if lastline is OK,
                            or new list with fixed last line.
                """
                if lines:
                    last = lines[-1]
                    if last and last[-1] not in ('\r', '\n'):
                        last += ('\n' +
                                 gettext('\\ No newline at end of file') +
                                 '\n')
                        lines = lines[:-1] + [last]
                return lines

            a = fix_last_line(lines[0])
            b = fix_last_line(lines[1])

            for i, group in enumerate(groups):
                if group:
                    i0, i1, j0, j1 = \
                            group[0][1], group[-1][2], group[0][3], group[-1][4]
                    self.cursor.insertText(
                        "@@ -%d,%d +%d,%d @@\n" % (i0+1, i1-i0, j0+1, j1-j0),
                        self.monospacedHunkFormat)
                for tag, i0, i1, j0, j1 in group:
                    if tag == "equal":
                        text = "".join(" " + l for l in a[i0:i1])
                        self.cursor.insertText(text, self.monospacedFormat)
                    else:
                        start = self.cursor.block().blockNumber()
                        text = "".join("-" + l for l in a[i0:i1])
                        self.cursor.insertText(text, self.monospacedDeleteFormat)
                        text = "".join("+" + l for l in b[j0:j1])
                        self.cursor.insertText(text, self.monospacedInsertFormat)
                        end = self.cursor.block().blockNumber()
                        guidebar_data[tag].append((start, end - start))
        else:
            self.cursor.insertText("Binary files %s %s and %s %s differ\n" % \
                                   (paths[0], dates[0], paths[1], dates[1]))
        self.cursor.insertText("\n")
        self.cursor.endEditBlock()
        self.update()

    def clear(self):
        QtGui.QTextBrowser.clear(self)
        self.reset_guidebar_data()

    def reset_guidebar_data(self):
        self.guidebar_data = dict(title=[], delete=[], insert=[], replace=[])

