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

from PyQt4 import QtCore, QtGui

from bzrlib.plugins.qbzr.lib.i18n import gettext
from bzrlib.plugins.qbzr.lib.util import (
    BTN_CLOSE,
    QBzrWindow,
    file_extension,
    htmlencode,
    )


have_pygments = True
try:
    from pygments import highlight
    from pygments.lexers import get_lexer_for_filename
    from pygments.formatters import HtmlFormatter
except ImportError:
    have_pygments = False


class QBzrCatWindow(QBzrWindow):

    def __init__(self, relpath, text, parent=None, encoding=None):
        QBzrWindow.__init__(self, [gettext("View File"), relpath], parent)
        self.restoreSize("cat", (780, 580))

        if not '\0' in text:
            text = text.decode(encoding or 'utf-8', 'replace')
            self._create_text_view(relpath, text)
        else:
            ext = file_extension(relpath)
            image_exts = ['.'+str(i)
                for i in QtGui.QImageReader.supportedImageFormats()]
            if ext in image_exts:
                self._create_image_view(relpath, text)
            else:
                self._create_text_view(relpath, '[binary file]')

        self.buttonbox = self.create_button_box(BTN_CLOSE)

        vbox = QtGui.QVBoxLayout(self.centralwidget)
        vbox.addWidget(self.browser)
        vbox.addWidget(self.buttonbox)

    def _create_text_view(self, relpath, text):
        if not have_pygments:
            style = ''
            content = htmlencode(text)
        else:
            try:
                lexer = get_lexer_for_filename(relpath)
                formatter = HtmlFormatter()
                style = formatter.get_style_defs()
                content = highlight(text, lexer, formatter)
            except ValueError:
                style = ''
                content = htmlencode(text)

        html = '''<html><head><style>%s
body {white-space:pre;}
</style></head><body>%s</body></html>''' % (style, content)
        self.doc = QtGui.QTextDocument()
        self.doc.setHtml(html)
        self.doc.setDefaultFont(QtGui.QFont("Courier New,courier", 8))

        self.browser = QtGui.QTextBrowser()
        self.browser.setDocument(self.doc)

    def _create_image_view(self, relpath, text):
        self.pixmap = QtGui.QPixmap()
        self.pixmap.loadFromData(text)
        self.item = QtGui.QGraphicsPixmapItem(self.pixmap)
        self.scene = QtGui.QGraphicsScene(self.item.boundingRect())
        self.scene.addItem(self.item)
        self.browser = QtGui.QGraphicsView(self.scene)

    @staticmethod
    def from_tree_and_path(tree, relpath, encoding=None, parent=None):
        file_id = tree.path2id(relpath)
        if file_id is None:
            QtGui.QMessageBox.warning(parent,
                "QBzr - " + gettext("View File"),
                gettext('File "%s" not found in the specified revision.') % (
                    relpath,),
                QtGui.QMessageBox.Ok)
            return None
        text = tree.get_file_text(file_id)
        return QBzrCatWindow(relpath, text)
