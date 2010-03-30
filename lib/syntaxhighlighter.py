# -*- coding: utf-8 -*-
#
# QBzr - Qt frontend to Bazaar commands
# Copyright (C) 2009 Gary van der Merwe <garyvdm@gmail.com>
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

_have_pygments = None
def have_pygments():
    global _have_pygments
    global ClassNotFound
    global get_lexer_for_filename
    global get_style_by_name
    global lex
    
    if _have_pygments is None:
        try:
            from pygments.util import ClassNotFound
            from pygments.styles import get_style_by_name
            from pygments import lex
            from pygments.lexers import get_lexer_for_filename
        except ImportError:
            _have_pygments = False
        else:
            _have_pygments = True
    return _have_pygments


def highlight_document(edit, filename):
    doc = edit.document()
    
    if not have_pygments():
        return
    
    try:
        lexer = get_lexer_for_filename(filename, stripnl=False)
    except ClassNotFound:
        return

    style = get_style_by_name("default")
    
    font = doc.defaultFont()
    base_format = QtGui.QTextCharFormat()
    base_format.setFont(font)
    token_formats = {}
    
    window = edit.window()
    if hasattr(window, "processEvents"):
        processEvents = window.processEvents
    else:
        processEvents = QtCore.QCoreApplication.processEvents
    
    def get_token_format(token):
        if token in token_formats:
            return token_formats[token]
        
        if token.parent:
            parent_format = get_token_format(token.parent)
        else:
            parent_format = base_format
        
        format = QtGui.QTextCharFormat(parent_format)
        font = format.font()
        if style.styles_token(token):
            tstyle = style.style_for_token(token)
            if tstyle['color']:
                format.setForeground (QtGui.QColor("#"+tstyle['color']))
            if tstyle['bold']: font.setWeight(QtGui.QFont.Bold)
            if tstyle['italic']: font.setItalic (True)
            if tstyle['underline']: format.setFontUnderline(True)
            if tstyle['bgcolor']: format.setBackground (QtGui.QColor("#"+tstyle['bgcolor']))
            # No way to set this for a QTextCharFormat
            #if tstyle['border']: format.
        token_formats[token] = format
        return format
    
    text = unicode(doc.toPlainText())
    
    block_count = 0
    block = doc.firstBlock()
    assert(isinstance(block, QtGui.QTextBlock))
    block_pos = 0
    block_len = block.length()
    block_formats = []
    
    for token, ttext in lex(text, lexer):
        format_len = len(ttext)
        format = get_token_format(token)
        while format_len > 0:
            format_range = QtGui.QTextLayout.FormatRange()
            format_range.start = block_pos
            format_range.length = min(format_len, block_len)
            format_range.format = format
            block_formats.append(format_range)
            block_len -= format_range.length
            format_len -= format_range.length
            block_pos += format_range.length
            if block_len == 0:
                block.layout().setAdditionalFormats(block_formats)
                doc.markContentsDirty(block.position(), block.length())
                block = block.next()
                block_pos = 0
                block_len = block.length()                    
                block_formats = []
                
                block_count += 1
                if block_count % 100 == 0:
                    processEvents()


if __name__ == "__main__":
    import sys
    app = QtGui.QApplication(sys.argv)

    python = QtGui.QPlainTextEdit()
    f = open('syntaxhighlighter.py', 'r')
    python.setPlainText(f.read())
    f.close()

    python.setWindowTitle('python')
    python.show()
    highlight_document(python, 'syntaxhighlighter.py')

    sys.exit(app.exec_())


def format_for_ttype(ttype, format, style=None):
    if have_pygments() and ttype:
        if style is None:
            style = get_style_by_name("default")
        
        font = format.font()
        
        # If there is no style, use the parent type's style.
        # It fixes bug 347333 - GaryvdM
        while not style.styles_token(ttype) and ttype.parent:
            ttype = ttype.parent
        
        tstyle = style.style_for_token(ttype)
        if tstyle['color']:
            if isinstance(format, QtGui.QPainter):
                format.setPen (QtGui.QColor("#"+tstyle['color']))
            else:
                format.setForeground (QtGui.QColor("#"+tstyle['color']))
        if tstyle['bold']: font.setWeight(QtGui.QFont.Bold)
        if tstyle['italic']: font.setItalic (True)
        # Can't get this not to affect line height.
        #if tstyle['underline']: format.setFontUnderline(True)
        if tstyle['bgcolor']: format.setBackground (QtGui.QColor("#"+tstyle['bgcolor']))
        # No way to set this for a QTextCharFormat
        #if tstyle['border']: format.
    return format

class CachedTTypeFormater(object):
    def __init__(self, base_format):
        self.base_format = base_format
        self._cache = {}
        if have_pygments():
            self.style = get_style_by_name("default")
    
    def format(self, ttype):
        if not have_pygments() or not ttype:
            return self.base_format
        if ttype in self._cache:
            format = self._cache[ttype]
        else:
            format = QtGui.QTextCharFormat(self.base_format)
            self._cache[ttype] = format
            
            # If there is no style, use the parent type's style.
            # It fixes bug 347333 - GaryvdM
            while not self.style.styles_token(ttype) and ttype.parent:
                ttype = ttype.parent
                self._cache[ttype] = format
            
            format_for_ttype(ttype, format, self.style)
        
        return format

def split_tokens_at_lines(tokens):
    currentLine = []
    for ttype, value in tokens:
        vsplit = value.splitlines(True)
        for v in vsplit:
            currentLine.append((ttype, v))
            if v[-1:] in ('\n','\r'):
                yield currentLine
                currentLine = []
    yield currentLine