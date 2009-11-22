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

have_pygments = True
try:
    from pygments.styles import get_style_by_name
    from pygments import lex
    from pygments.util import ClassNotFound
    from pygments.lexers import get_lexer_for_filename
except ImportError:
    have_pygments = False

def highlight_document(edit, filename):
    doc = edit.document()
    
    if not have_pygments:
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
        tstyle = style.style_for_token(token)
        if tstyle:
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
                
                block = block.next()
                block_pos = 0
                block_len = block.length()                    
                block_formats = []
                
                block_count += 1
                if block_count % 100 == 0:
                    edit.update()
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