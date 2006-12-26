# -*- coding: utf-8 -*-
#
# QBzr - Qt frontend to Bazaar commands
# Copyright (C) 2006 Lukáš Lalinský <lalinsky@gmail.com>
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
from bzrlib.plugins.qbzr.util import QBzrWindow

have_pygments = True
try:
    from pygments import highlight
    from pygments.lexers import get_lexer_for_filename
    from pygments.formatters import HtmlFormatter
except ImportError:
    have_pygments = False

class AnnotateWindow(QBzrWindow):

    def __init__(self, filename, lines, parent=None):
        QBzrWindow.__init__(self, ["Annotate", filename], (780, 580), parent)

        self.browser = QtGui.QTextBrowser()
        code = []
        ann = []
        for revno_str, author, date_str, origin, text in lines:
            ann.append("%5s %-7s " % (revno_str, author[:7]))
            code.append(text)
        ann_html = "\n".join(ann)
        code = "\n".join(code)
        try:
            code = code.decode('utf-8', 'errors')
        except UnicodeError:
            code = code.decode('iso-8859-1', 'replace')

        if not have_pygments:
            style = ''
            code_html = '<pre>%s</pre>' % code
        else:
            lexer = get_lexer_for_filename(filename)
            formatter = HtmlFormatter()
            style = formatter.get_style_defs()
            code_html = highlight(code, lexer, formatter)

        html = '''<html><head><style>%s
.margin { background: #DDD; }
</style></head><body><table><tr>
<td class="margin" align="right"><pre>%s</pre></td>
<td>%s</td>
</tr></table></body></html>''' % (style, ann_html, code_html)
        self.doc = QtGui.QTextDocument()
        self.doc.setHtml(html)

        browser = QtGui.QTextBrowser()
        browser.setDocument(self.doc)

        buttonbox = QtGui.QDialogButtonBox(
            QtGui.QDialogButtonBox.StandardButtons(
                QtGui.QDialogButtonBox.Close),
            QtCore.Qt.Horizontal,
            self)
        self.connect(buttonbox, QtCore.SIGNAL("rejected()"), self.close)

        vbox = QtGui.QVBoxLayout(self.centralwidget)
        vbox.addWidget(browser)
        vbox.addWidget(buttonbox)
