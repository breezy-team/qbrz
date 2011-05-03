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

import os
from PyQt4 import QtCore, QtGui

from bzrlib import errors, osutils
from bzrlib.branch import Branch

from bzrlib.plugins.qbzr.lib.i18n import gettext
from bzrlib.plugins.qbzr.lib.util import (
    BTN_CLOSE,
    QBzrWindow,
    ThrobberWidget,
    file_extension,
    get_monospace_font,
    get_set_encoding,
    get_tab_width_pixels,
    runs_in_loading_queue,
    )
from bzrlib.plugins.qbzr.lib.encoding_selector import EncodingSelector
from bzrlib.plugins.qbzr.lib.fake_branch import FakeBranch
from bzrlib.plugins.qbzr.lib.syntaxhighlighter import highlight_document
from bzrlib.plugins.qbzr.lib.texteditannotate import LineNumberEditerFrame
from bzrlib.plugins.qbzr.lib.trace import reports_exception
from bzrlib.plugins.qbzr.lib.uifactory import ui_current_widget


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
    """Show content of versioned file/symlink."""

    def __init__(self, filename=None, revision=None,
                 tree=None, file_id=None, encoding=None,
                 parent=None):
        """Create qcat window."""
        
        self.filename = filename
        self.revision = revision
        self.tree = tree
        if tree:
            self.branch = getattr(tree, 'branch', None)
            if self.branch is None:
                self.branch = FakeBranch()
        self.file_id = file_id
        self.encoding = encoding

        if (not self.filename) and self.tree and self.file_id:
            self.filename = self.tree.id2path(self.file_id)

        QBzrWindow.__init__(self, [gettext("View"), self.filename], parent)
        self.restoreSize("cat", (780, 580))

        self.throbber = ThrobberWidget(self)
        self.buttonbox = self.create_button_box(BTN_CLOSE)
        self.encoding_selector = self._create_encoding_selector()

        self.vbox = QtGui.QVBoxLayout(self.centralwidget)
        self.vbox.addWidget(self.throbber)
        self.vbox.addStretch()

        hbox = QtGui.QHBoxLayout()
        hbox.addWidget(self.encoding_selector)
        hbox.addWidget(self.buttonbox)
        self.vbox.addLayout(hbox)

    def _create_encoding_selector(self):
        encoding_selector = EncodingSelector(self.encoding,
            gettext("Encoding:"),
            self._on_encoding_changed)
        # disable encoding selector,
        # it will be enabled later only for text files
        encoding_selector.setDisabled(True)
        return encoding_selector

    def show(self):
        # we show the bare form as soon as possible.
        QBzrWindow.show(self)
        QtCore.QTimer.singleShot(0, self.load)
    
    @runs_in_loading_queue
    @ui_current_widget
    @reports_exception()
    def load(self):
        self.throbber.show()
        self.processEvents()
        try:
            if not self.tree:
                branch, relpath = Branch.open_containing(self.filename)
                self.branch = branch
                self.encoding = get_set_encoding(self.encoding, branch)
                self.encoding_selector.encoding = self.encoding

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

            self.text = text
            self.kind = kind
            self._create_and_show_browser(self.filename, text, kind)
        finally:
            self.throbber.hide()

    def _create_and_show_browser(self, filename, text, kind):
        """Create browser object for given file and then attach it to GUI.

        @param  filename:   filename used for differentiate between images
                            and simply binary files.
        @param  text:       raw file content.
        @param  kind:       filesystem kind: file, symlink, directory
        """
        type_, fview = self.detect_content_type(filename, text, kind)
        # update title
        title = "View " + type_
        self.set_title([gettext(title), filename])
        # create and show browser
        self.browser = fview(filename, text)
        self.vbox.insertWidget(1, self.browser, 1)
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

    def _set_text(self, edit_widget, relpath, text, encoding=None):
        """Set plain text to widget, as unicode.

        @param edit_widget: edit widget to view the text.
        @param relpath: filename (required for syntax highlighting to detect
            file type).
        @param text: plain non-unicode text (bytes).
        @param encoding: text encoding (default: utf-8).
        """
        text = text.decode(encoding or 'utf-8', 'replace')
        edit_widget.setPlainText(text)
        highlight_document(edit_widget, relpath)

    def _create_text_view(self, relpath, text):
        """Create widget to show text files.
        @return: created widget with loaded text.
        """
        browser = LineNumberEditerFrame(self)
        edit = browser.edit
        edit.setReadOnly(True)
        edit.document().setDefaultFont(get_monospace_font())

        edit.setTabStopWidth(get_tab_width_pixels(self.branch))

        self._set_text(edit, relpath, text, self.encoding)
        self.encoding_selector.setEnabled(True)
        return browser

    def _on_encoding_changed(self, encoding):
        """Event handler for EncodingSelector.
        It sets file text to browser again with new encoding.
        """
        self.encoding = encoding
        branch = self.branch
        if branch is None:
            branch = Branch.open_containing(self.filename)[0]
        if branch:
            get_set_encoding(encoding, branch)
        self._set_text(self.browser.edit, self.filename, self.text, self.encoding)

    def _create_simple_text_browser(self):
        """Create and return simple widget to show text-like content."""
        browser = QtGui.QPlainTextEdit(self)
        browser.setReadOnly(True)
        browser.document().setDefaultFont(get_monospace_font())
        return browser

    def _create_symlink_view(self, relpath, target):
        """Create widget to show symlink target.
        @return: created widget with loaded content.
        """
        browser = self._create_simple_text_browser()
        browser.setPlainText('-> ' + target.decode('utf-8', 'replace'))
        return browser

    def _create_hexdump_view(self, relpath, data):
        """Create widget to show content of binary files.
        @return: created widget with loaded content.
        """
        browser = self._create_simple_text_browser()
        browser.setPlainText(hexdump(data))
        return browser

    def _create_image_view(self, relpath, data):
        """Create widget to show image file.
        @return: created widget with loaded image.
        """
        self.pixmap = QtGui.QPixmap()
        self.pixmap.loadFromData(data)
        self.item = QtGui.QGraphicsPixmapItem(self.pixmap)
        self.scene = QtGui.QGraphicsScene(self.item.boundingRect())
        self.scene.addItem(self.item)
        return QtGui.QGraphicsView(self.scene)


class QBzrViewWindow(QBzrCatWindow):
    """Show content of file/symlink from the disk."""

    def __init__(self, filename=None, encoding=None, parent=None):
        """Construct GUI.

        @param  filename:   filesystem object to view.
        @param  encoding:   use this encoding to decode text file content
                            to unicode.
        @param  parent:     parent widget.
        """
        QBzrWindow.__init__(self, [gettext("View"), filename], parent)
        self.restoreSize("cat", (780, 580))

        self.filename = filename
        self.encoding = encoding

        self.buttonbox = self.create_button_box(BTN_CLOSE)
        self.encoding_selector = self._create_encoding_selector()
        self.branch = FakeBranch()

        self.vbox = QtGui.QVBoxLayout(self.centralwidget)
        self.vbox.addStretch()
        hbox = QtGui.QHBoxLayout()
        hbox.addWidget(self.encoding_selector)
        hbox.addWidget(self.buttonbox)
        self.vbox.addLayout(hbox)

    def load(self):
        kind = osutils.file_kind(self.filename)
        text = ''
        if kind == 'file':
            f = open(self.filename, 'rb')
            try:
                text = f.read()
            finally:
                f.close()
        elif kind == 'symlink':
            text = os.readlink(self.filename)
        self.text = text
        self._create_and_show_browser(self.filename, text, kind)


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
    url = QtCore.QUrl.fromLocalFile(fname)
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
