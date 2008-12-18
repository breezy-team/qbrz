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

from bzrlib import errors
from bzrlib.plugins.qbzr.lib.i18n import gettext
from bzrlib.branch import Branch
from bzrlib.plugins.qbzr.lib.util import (
    BTN_CLOSE,
    QBzrWindow,
    ThrobberWidget,
    file_extension,
    format_for_ttype,
    get_set_encoding,
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

    def __init__(self, filename=None, revision=None,
                 tree=None, file_id=None, encoding=None,
                 parent=None):
        """Create qcat window."""
        
        self.filename = filename
        self.revision = revision
        self.tree = tree
        self.file_id = file_id
        self.encoding = encoding
        
        if (not self.filename) and self.tree and self.file_id:
            self.filename = self.tree.id2path(self.file_id)
        
        QBzrWindow.__init__(self, [gettext("View"), self.filename], parent)
        self.restoreSize("cat", (780, 580))

        self.throbber = ThrobberWidget(self)
        self.buttonbox = self.create_button_box(BTN_CLOSE)

        self.vbox = QtGui.QVBoxLayout(self.centralwidget)
        self.vbox.addWidget(self.throbber)
        self.vbox.addStretch()
        self.vbox.addWidget(self.buttonbox)
    
    def show(self):
        # we show the bare form as soon as possible.
        QBzrWindow.show(self)
        QtCore.QTimer.singleShot(1, self.load)
    
    def load(self):
        try:
            self.throbber.show()
            self.processEvents()
            try:
                if not self.tree:
                    branch, relpath = Branch.open_containing(self.filename)
                    
                    self.encoding = get_set_encoding(self.encoding, branch)
                    
                    if self.revision is None:
                        self.tree = branch.basis_tree()
                    else:
                        revision_id = self.revision[0].in_branch(branch).rev_id
                        self.tree = branch.repository.revision_tree(revision_id)
                    
                    self.file_id = self.tree.path2id(relpath)
                
                if not self.file_id:
                    self.file_id = self.tree.path2id(self.filename)
                    
                if not self.file_id:
                    raise errors.BzrCommandError(
                        "%r is not present in revision %s" % (
                            self.filename, self.tree.get_revision_id()))
                
                self.tree.lock_read()
                try:
                    kind = self.tree.kind(self.file_id)
                    if kind == 'file':
                        text = self.tree.get_file_text(self.file_id)
                    elif kind == 'symlink':
                        text = self.tree.get_symlink_target(self.file_id)
                    else:
                        text = ''
                finally:
                    self.tree.unlock()
                self.processEvents()
                
                type_, fview = self.detect_content_type(self.filename, text, kind)
                fview(self.filename, text)
                
                self.vbox.insertWidget(1, self.browser, 1)
                # set focus on content
                self.browser.setFocus()
            finally:
                self.throbber.hide()
        except Exception:
            self.report_exception()

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


def cat_to_native_app(tree, relpath):
    """Extract file content to temp directory and then launch
    native application to open it.

    @param  tree:   RevisionTree object.
    @param  relpath:    path to file relative to tree root.
    @raise  KindError:  if relpath entry has not file kind.
    @return:    True if native application was launched.
    """
    file_id = tree.path2id(relpath)
    kind = tree.kind(file_id)
    if kind != 'file':
        raise KindError('cat to native application is not supported '
            'for entry of kind %r' % kind)
    # make temp file
    import os
    import tempfile
    qdir = os.path.join(tempfile.gettempdir(), 'QBzr', 'qcat')
    if not os.path.isdir(qdir):
        os.makedirs(qdir)
    basename = os.path.basename(relpath)
    fname = os.path.join(qdir, basename)
    f = open(fname, 'wb')
    tree.lock_read()
    try:
        f.write(tree.get_file_text(file_id))
    finally:
        tree.unlock()
        f.close()
    # open it
    url = QtCore.QUrl(fname)
    result = QtGui.QDesktopServices.openUrl(url)
    # now application is about to start and user will work with file
    # so we can do cleanup in "background"
    import time
    limit = time.time() - 60    # files older than 1 minute
    files = os.listdir(qdir)
    for i in files[:20]:
        if i == basename:
            continue
        fname = os.path.join(qdir, i)
        st = os.lstat(fname)
        if st.st_mtime > limit:
            continue
        try:
            os.unlink(fname)
        except (OSError, IOError):
            pass
    #
    return result


class KindError(errors.BzrError):
    pass
