from PyQt4 import QtGui, QtCore

colors = {
    'delete': (QtGui.QColor(255, 216, 216), QtGui.QColor(243, 61, 61)),
    'insert': (QtGui.QColor(216, 255, 216), QtGui.QColor(156, 222, 156)),
    'replace': (QtGui.QColor(221, 238, 255), QtGui.QColor(171, 193, 222)),
    'blank': (QtGui.QColor(238, 238, 238), QtGui.QColor(171, 171, 171)),
}

brushes = {}
for kind, cols in colors.items():
    brushes[kind] = (QtGui.QBrush(cols[0]), QtGui.QBrush(cols[1]))


class DiffSourceView(QtGui.QTextBrowser):

    def __init__(self, font, titleFont, metainfoFont, metainfoTitleFont, lineHeight, parent=None):
        QtGui.QTextBrowser.__init__(self, parent)
        self.font = font
        self.titleFont = titleFont
        self.lineHeight = lineHeight
        self.metainfoFont = metainfoFont
        self.metainfoTitleFont = metainfoTitleFont
        self.setLineWrapMode(QtGui.QTextEdit.NoWrap)
        #self.setViewportMargins(40, 0, 0, 0)

    def setData(self, text, titles, changes):
        self.doc = QtGui.QTextDocument()
        self.doc.setDefaultFont(self.font)
        self.doc.setHtml(text)
        self.setDocument(self.doc)
        self.changes = changes
        self.titles = titles
        self.update()

    def paintEvent(self, event):
        w = self.width()

        x = 1 - self.horizontalScrollBar().value()
        y = 1 - self.verticalScrollBar().value()

        painter = QtGui.QPainter(self.viewport())
        painter.setClipRect(event.rect())

        pen = QtGui.QPen(QtCore.Qt.black)
        pen.setWidth(2)
        painter.setPen(pen)

        for pos, title, metainfo in self.titles:
            painter.setFont(self.titleFont)
            fm = painter.fontMetrics()
            x1 = x + 2
            y1 = y + self.lineHeight * pos
            painter.drawText(x1, y1 + fm.ascent(), title)
            y1 += fm.height()
            painter.setFont(self.metainfoTitleFont)
            fm = painter.fontMetrics()
            y1 += fm.ascent()
            for name, value in metainfo:
                painter.setFont(self.metainfoTitleFont)
                painter.drawText(x1, y1, name)
                x1 += fm.width(name)
                painter.setFont(self.metainfoFont)
                painter.drawText(x1, y1, value)
                x1 += painter.fontMetrics().width(value)
            y1 += fm.descent()
            painter.drawLine(0, y1 + 2, w, y1 + 2)

        for pos, nlines, kind in self.changes:
            y1 = y + self.lineHeight * pos
            y2 = y1 + self.lineHeight * nlines
            painter.fillRect(0, y1, w, y2 - y1 + 1, brushes[kind][0])
            painter.setPen(colors[kind][1])
            painter.drawLine(0, y1, w, y1)
            if y1 != y2:
                painter.drawLine(0, y2, w, y2)

        QtGui.QTextBrowser.paintEvent(self, event)


class DiffViewHandle(QtGui.QSplitterHandle):

    def __init__(self, lineHeight, parent=None):
        QtGui.QSplitterHandle.__init__(self, QtCore.Qt.Horizontal, parent)
        self.lineHeight = lineHeight
        self.view = parent

    def setData(self, changes):
        self.changes = changes
        self.update()

    def paintEvent(self, event):
        painter = QtGui.QPainter(self)

        value1 = self.view.browser1.verticalScrollBar().value()
        value2 = self.view.browser2.verticalScrollBar().value()

        w = self.width()
        frame = QtGui.QApplication.style().pixelMetric(QtGui.QStyle.PM_DefaultFrameWidth) + 1

        for pos1, nlines1, pos2, nlines2, kind in self.changes:
            #if kind == 'blank' and nlines1 == 0 or nlines2 == 0:
            #    continue

            ly1 = frame + self.lineHeight * pos1 - value1
            ly2 = ly1 + self.lineHeight * nlines1
            ry1 = frame + self.lineHeight * pos2 - value2
            ry2 = ry1 + self.lineHeight * nlines2

            polygon = QtGui.QPolygon(4)
            polygon.setPoints(
                0, ly1,
                w, ry1,
                w, ry2,
                0, ly2)
            painter.setPen(QtCore.Qt.NoPen)
            painter.setBrush(brushes[kind][0])
            painter.drawConvexPolygon(polygon)

            painter.setPen(colors[kind][1])
            painter.setRenderHints(QtGui.QPainter.Antialiasing, ly1 != ry1)
            painter.drawLine(0, ly1, w, ry1)
            painter.setRenderHints(QtGui.QPainter.Antialiasing, ly2 != ry2)
            painter.drawLine(0, ly2, w, ry2)



def htmlencode(string):
    return string.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")


def markup_line(line, encode=True):
    if encode:
        line = htmlencode(line)
    return line.rstrip("\n").replace("\t", "&nbsp;" * 8).decode("utf-8", "replace")



def get_change_extent(str1, str2):
    start = 0
    limit = min(len(str1), len(str2))
    while start < limit and str1[start] == str2[start]:
        start += 1
    end = -1
    limit = limit - start
    while -end <= limit and str1[end] == str2[end]:
        end -= 1
    return (start, end + 1)


def markup_intraline_changes(line1, line2, color):
    line1 = line1.replace("&", "\1").replace("<", "\2").replace(">", "\3")
    line2 = line2.replace("&", "\1").replace("<", "\2").replace(">", "\3")
    start, end = get_change_extent(line1[1:], line2[1:])
    if start == 0 and end < 0:
        text = '<span style="background-color:%s">%s</span>%s' % (color, line1[:end], line1[end:])
    elif start > 0 and end == 0:
        start += 1
        text = '%s<span style="background-color:%s">%s</span>' % (line1[:start], color, line1[start:])
    elif start > 0 and end < 0:
        start += 1
        text = '%s<span style="background-color:%s">%s</span>%s' % (line1[:start], color, line1[start:end], line1[end:])
    else:
        text = line1
    text = text.replace("\1", "&amp;").replace("\2", "&lt;").replace("\3", "&gt;")
    return text


STYLES = {
    'hunk': 'background-color:#666666;color:#FFF;font-weight:bold;',
    'delete': 'background-color:#FFDDDD',
    'insert': 'background-color:#DDFFDD',
    'missing': 'background-color:#E0E0E0',
    'title': 'font-size:14px; font-weight:bold;',
    'metainfo': 'font-size:9px;',
}


class DiffView(QtGui.QSplitter):

    def __init__(self, treediff, parent=None):
        QtGui.QSplitter.__init__(self, QtCore.Qt.Horizontal, parent)
        self.setHandleWidth(30)

        font = QtGui.QFont("Courier New,courier", 8)
        self.lineHeight = QtGui.QFontMetrics(font).height()

        titleFont = QtGui.QFont(self.font())
        titleFont.setBold(True)
        titleFont.setPixelSize(14)

        metainfoFont = QtGui.QFont(self.font())
        metainfoFont.setPixelSize(9)

        metainfoTitleFont = QtGui.QFont(metainfoFont)
        metainfoTitleFont.setBold(True)

        self.browser1 = DiffSourceView(font, titleFont, metainfoFont, metainfoTitleFont, self.lineHeight, self)
        self.browser2 = DiffSourceView(font, titleFont, metainfoFont, metainfoTitleFont, self.lineHeight, self)

        self.ignoreUpdate = False
        self.connect(self.browser1.verticalScrollBar(), QtCore.SIGNAL("valueChanged(int)"), self.updateHandle1)
        self.connect(self.browser2.verticalScrollBar(), QtCore.SIGNAL("valueChanged(int)"), self.updateHandle2)
        self.connect(self.browser1.horizontalScrollBar(), QtCore.SIGNAL("valueChanged(int)"), self.syncHorizontalSlider1)
        self.connect(self.browser2.horizontalScrollBar(), QtCore.SIGNAL("valueChanged(int)"), self.syncHorizontalSlider2)

        self.addWidget(self.browser1)
        self.addWidget(self.browser2)

        self.setCollapsible(0, False)
        self.setCollapsible(1, False)

        self.treediff = treediff
        self.displayCombined(expand=False)
        #self.displayFull(1)

    def _syncSliders(self, slider1, slider2, value):
        m = slider1.maximum()
        if m:
            value = slider2.minimum() + slider2.maximum() * (value - slider1.minimum()) / m
            self.ignoreUpdate = True
            slider2.setValue(value)
            self.ignoreUpdate = False

    def updateHandle1(self, value):
        if not self.ignoreUpdate:
            slider1 = self.browser1.verticalScrollBar()
            slider2 = self.browser2.verticalScrollBar()
            self._syncSliders(slider1, slider2, value)
            self.handle(1).update()

    def updateHandle2(self, value):
        if not self.ignoreUpdate:
            slider1 = self.browser1.verticalScrollBar()
            slider2 = self.browser2.verticalScrollBar()
            self._syncSliders(slider2, slider1, value)
            self.handle(1).update()

    def syncHorizontalSlider1(self, value):
        if not self.ignoreUpdate:
            slider1 = self.browser1.horizontalScrollBar()
            slider2 = self.browser2.horizontalScrollBar()
            self._syncSliders(slider1, slider2, value)
            self.handle(1).update()

    def syncHorizontalSlider2(self, value):
        if not self.ignoreUpdate:
            slider1 = self.browser1.horizontalScrollBar()
            slider2 = self.browser2.horizontalScrollBar()
            self._syncSliders(slider2, slider1, value)
            self.handle(1).update()

    def createHandle(self):
        return DiffViewHandle(self.lineHeight, self)

    def displayCombined(self, expand=False):
        lines1 = []
        lines2 = []
        changes = []
        titles1 = []
        titles2 = []
        for diff in self.treediff:
            titles1.append((len(lines1), diff.path, (('Last modified: ', diff.old_date + ', '), ('Status ', diff.status + ', '), ('Kind: ', diff.kind))))
            titles2.append((len(lines2), diff.path, (('Last modified: ', diff.old_date + ', '), ('Status ', diff.status + ', '), ('Kind: ', diff.kind))))
            #lines1.append('<span style="font-family:%s;%s">%s</span>' % (self.ff, STYLES['title'], diff.path))
            #lines1.append('<span style="font-family:%s;%s"><b>Last modified:</b> %s, <b>Status:</b> %s, <b>Kind:</b> %s</span>' % (self.ff, STYLES['metainfo'], diff.old_date, diff.status, diff.kind))
            #lines2.append('<span style="font-family:%s;%s">%s</span>' % (self.ff, STYLES['title'], diff.path))
            #lines2.append('<span style="font-family:%s;%s"><b>Last modified:</b> %s, <b>Status:</b> %s, <b>Kind:</b> %s</span>' % (self.ff, STYLES['metainfo'], diff.new_date, diff.status, diff.kind))
            lines1.append('')
            lines1.append('')
            lines1.append('')
            lines2.append('')
            lines2.append('')
            lines2.append('')
            a = diff.old_lines
            b = diff.new_lines
            for i, group in enumerate(diff.groups):
                if i > 0:
                    pos1 = len(lines1)
                    pos2 = len(lines2)
                    changes.append((pos1, 1, pos2, 1, 'blank'))
                    lines1.append("")
                    lines2.append("")

                for tag, i1, i2, j1, j2 in group:
                    ni = i2 - i1
                    nj = j2 - j1
                    pos1 = len(lines1)
                    pos2 = len(lines2)
                    if tag == 'equal':
                        lines = map(markup_line, a[i1:i2])
                        lines1.extend(lines)
                        lines2.extend(lines)
                    else:
                        changes.append((pos1, ni, pos2, nj, tag))
                        if ni == nj:
                            for i in range(ni):
                                linea = a[i1 + i]
                                lineb = b[j1 + i]
                                linea = markup_intraline_changes(linea, lineb, '#ABC1DE')
                                lineb = markup_intraline_changes(lineb, linea, '#ABC1DE')
                                lines1.append(markup_line(linea, encode=False))
                                lines2.append(markup_line(lineb, encode=False))
                        else:
                            lines1.extend(map(markup_line, a[i1:i2]))
                            lines2.extend(map(markup_line, b[j1:j2]))
                            if expand:
                                pos1 = len(lines1)
                                pos2 = len(lines2)
                                nd = ni - nj;
                                if nd < 0:
                                    nd = -nd
                                    changes.append((pos1, nd, pos2, 0, 'blank'))
                                    lines1.extend([""] * nd)
                                elif nd > 0:
                                    pos2 = len(lines2)
                                    changes.append((pos1, 0, pos2, nd, 'blank'))
                                    lines2.extend([""] * nd)

                lend = len(lines1) - len(lines2)
                if lend < 0:
                    i1 = group[-1][2]
                    i2 = i1 - lend
                    lines1.extend(map(markup_line, a[i1:i2]))
                if lend > 0:
                    j1 = group[-1][4]
                    j2 = j1 + lend
                    lines2.extend(map(markup_line, b[j1:j2]))
                lend = len(lines1) - len(lines2)
                if lend < 0:
                    lines1.extend([''] * -lend)
                if lend > 0:
                    lines2.extend([''] * lend)
            lines1.append('')
            lines2.append('')

        text1 = '<div style="white-space:pre">' + '<br/>'.join(lines1) + '</div>'
        text2 = '<div style="white-space:pre">' + '<br/>'.join(lines2) + '</div>'
        changes1 = [(line[0], line[1], line[4]) for line in changes]
        changes2 = [(line[2], line[3], line[4]) for line in changes]

        self.browser1.setData(text1, titles1, changes1)
        self.browser2.setData(text2, titles2, changes2)
        self.handle(1).setData(changes)
        self.browser1.verticalScrollBar().setValue(0)

    def displayFull(self, index=0):
        changes = []
        diff = self.treediff[index]

        for i, group in enumerate(diff.groups):
            for tag, i1, i2, j1, j2 in group:
                if tag != 'equal':
                    ni = i2 - i1
                    nj = j2 - j1
                    changes.append((i1, ni, j1, nj, tag))

        text1 = "<br>".join(map(markup_line, diff.old_lines))
        text2 = "<br>".join(map(markup_line, diff.new_lines))
        changes1 = [(line[0], line[1], line[4]) for line in changes]
        changes2 = [(line[2], line[3], line[4]) for line in changes]

        self.browser1.setData(text1, changes1)
        self.browser2.setData(text2, changes2)
        self.handle(1).setData(changes)