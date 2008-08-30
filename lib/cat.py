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

import sys
from PyQt4 import QtCore, QtGui

from bzrlib.plugins.qbzr.lib.i18n import gettext
from bzrlib.plugins.qbzr.lib.util import (
    BTN_CLOSE,
    QBzrWindow,
    file_extension,
    format_for_ttype,
    )


have_pygments = True
try:
    from pygments import lex
    from pygments.util import ClassNotFound
    from pygments.lexers import get_lexer_for_filename
except ImportError:
    have_pygments = False


def hexdump(data):
    content = []
    for i in range(0, len(data), 16):
        hexdata = []
        chardata = []
        for c in data[i:i+16]:
            j = ord(c)
            hexdata.append('%02x' % j)
            if j >= 32 and j < 128:
                chardata.append(c)
            else:
                chardata.append('.')
        for c in range(16 - len(hexdata)):
            hexdata.append('  ')
            chardata.append(' ')
        line = '%08x  ' % i + ' '.join(hexdata[:8]) + '  ' + ' '.join(hexdata[8:]) + '  |' + ''.join(chardata) + '|'
        content.append(line)
    return '\n'.join(content)


class QBzrCatWindow(QBzrWindow):

    def __init__(self, relpath, text, parent=None, encoding=None, kind='file'):
        """Create qcat window.
        @param  relpath:    file path relative to tree root.
        @param  text:       file content (bytes).
        @param  parent:     parent window.
        @param  encoding:   file text encoding.
        @param  kind:       inventory entry kind (file/directory/symlink).
        """
        type_, fview = self.detect_content_type(relpath, text, kind)

        QBzrWindow.__init__(self, [gettext("View "+type_), relpath], parent)
        self.restoreSize("cat", (780, 580))

        self.encoding = encoding
        fview(relpath, text)

        self.buttonbox = self.create_button_box(BTN_CLOSE)

        vbox = QtGui.QVBoxLayout(self.centralwidget)
        vbox.addWidget(self.browser)
        vbox.addWidget(self.buttonbox)
        # set focus on content
        self.browser.setFocus()

    def detect_content_type(self, relpath, text, kind='file'):
        """Return (file_type, viewer_factory) based on kind, text and relpath.
        Supported file types: text, image, binary
        """
        if kind == 'file':
            if not '\0' in text:
                return 'text file', self._create_text_view
            else:
                ext = file_extension(relpath).lower()
                image_exts = ['.'+str(i)
                    for i in QtGui.QImageReader.supportedImageFormats()]
                if ext in image_exts:
                    return 'image file', self._create_image_view
                else:
                    return 'binary file', self._create_hexdump_view
        else:
            return kind, self._create_symlink_view
    
    def _create_text_browser(self):
        self.browser = QtGui.QTextBrowser()
        self.doc = QtGui.QTextDocument()
        self.doc.setDefaultFont(QtGui.QFont("Courier New,courier", self.browser.font().pointSize()))
    
    def _create_text_view(self, relpath, text):
        self._create_text_browser()
        text = text.decode(self.encoding or 'utf-8', 'replace')
        if not have_pygments:
            self.doc.setPlainText(text)
        else:
            try:
                cursor = QtGui.QTextCursor(self.doc)
                font = self.doc.defaultFont()
                lexer = get_lexer_for_filename(relpath)
                for ttype, value in lex(text, lexer):                    
                    format = QtGui.QTextCharFormat()
                    format.setFont(font)
                    format = format_for_ttype(ttype,format)
                    cursor.insertText(value, format)
                cursor.movePosition (QtGui.QTextCursor.Start)
            except ClassNotFound:
                self.doc.setPlainText(text)
        self.browser.setDocument(self.doc)

    def _create_symlink_view(self, relpath, target):
        self._create_text_browser()
        self.doc.setPlainText('-> ' + target.decode('utf-8', 'replace'))
        self.browser.setDocument(self.doc)

    def _create_hexdump_view(self, relpath, data):
        self._create_text_browser()
        self.doc.setPlainText(hexdump(data))
        self.browser.setDocument(self.doc)

    def _create_image_view(self, relpath, data):
        self.pixmap = QtGui.QPixmap()
        self.pixmap.loadFromData(data)
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
        kind = tree.kind(file_id)
        if kind == 'file':
            text = tree.get_file_text(file_id)
        elif kind == 'symlink':
            text = tree.get_symlink_target(file_id)
        else:
            text = ''
        return QBzrCatWindow(relpath, text, encoding=encoding, kind=kind)
