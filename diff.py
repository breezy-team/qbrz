# -*- coding: utf-8 -*-
#
# QBzr - Qt frontend to Bazaar commands
# Copyright (C) 2006 Lukáš Lalinský <lalinsky@gmail.com>
# Portions Copyright (C) 2006 Jelmer Vernooij <jelmer@samba.org>
# Portions Copyright (C) 2005 Canonical Ltd. (author: Scott James Remnant <scott@ubuntu.com>)
# Portions Copyright (C) 2004-2006 Christopher Lenz <cmlenz@gmx.de>
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
from cStringIO import StringIO
from PyQt4 import QtCore, QtGui
from bzrlib.commands import Command, register_command
from bzrlib.diff import show_diff_trees
from bzrlib.workingtree import WorkingTree
from bzrlib.plugins.qbzr.util import QBzrWindow
from bzrlib import textfile, patiencediff


STYLES = {
    'hunk': 'background-color:#666666;color:#FFF;font-weight:bold;',
    'delete': 'background-color:#FFDDDD',
    'insert': 'background-color:#DDFFDD',
    'missing': 'background-color:#E0E0E0',
    'title': 'margin-top:10px;margin-bottom:10px;font-size:16px;font-weight:bold;',
}


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
    line1 = htmlencode(line1)
    line2 = htmlencode(line2)
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
    return text


def htmlencode(string):
    return string.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")


def markup_line(line, style='', encode=True):
    if encode:
        line = htmlencode(line)
    if style:
        style = ' style="%s"' % style
    return '<div%s>%s</div>' % (style, line or '&nbsp;')


def html_diff_lines(data, html1, html2, inline=True):
    if not data:
        return
    a, b, groups = data
    a = [a.decode("utf-8", "replace").rstrip("\n") for a in a]
    b = [b.decode("utf-8", "replace").rstrip("\n") for b in b]
    for group in groups:
        i1, i2, j1, j2 = group[0][1], group[-1][2], group[0][3], group[-1][4]
        hunk = "@@ -%d,%d +%d,%d @@" % (i1+1, i2-i1, j1+1, j2-j1)
        html1.append('<div style="%s">%s</div>' % (STYLES['hunk'], htmlencode(hunk)))
        if not inline:
            html2.append('<div style="%s">%s</div>' % (STYLES['hunk'], htmlencode(hunk)))
        for tag, i1, i2, j1, j2 in group:
            if tag == 'equal':
                for line in a[i1:i2]:
                    line = markup_line(line)
                    html1.append(line)
                    if not inline:
                        html2.append(line)
            elif tag == 'replace':
                d = (i2 - i1) - (j2 - j1)
                if d == 0:
                    for i in range(i2 - i1):
                        linea = a[i1 + i]
                        lineb = b[j1 + i]
                        linea = markup_intraline_changes(linea, lineb, '#EE9999')
                        lineb = markup_intraline_changes(lineb, linea, '#99EE99')
                        html1.append(markup_line(linea, STYLES['delete'], encode=False))
                        html2.append(markup_line(lineb, STYLES['insert'], encode=False))
                else:
                    for line in a[i1:i2]:
                        html1.append(markup_line(line, STYLES['delete']))
                    for line in b[j1:j2]:
                        html2.append(markup_line(line, STYLES['insert']))
                    if not inline:
                        if d < 0:
                            for i in range(-d):
                                html1.append(markup_line('', STYLES['missing']))
                        else:
                            for i in range(d):
                                html2.append(markup_line('', STYLES['missing']))
            elif tag == 'insert':
                for line in b[j1:j2]:
                    if not inline:
                        html1.append(markup_line('', STYLES['missing']))
                    html2.append(markup_line(line, STYLES['insert']))
            elif tag == 'delete':
                for line in a[i1:i2]:
                    html1.append(markup_line(line, STYLES['delete']))
                    if not inline:
                        html2.append(markup_line('', STYLES['missing']))
    html1.append('</pre>')
    html2.append('</pre>')


def make_sidebyside_html(data):
    """Make HTML for side-by-side diff view."""
    lines1 = []
    lines2 = []
    html_diff_lines(data, lines1, lines2, inline=False)
    return '<pre>%s</pre>' % ''.join(lines1), '<pre>%s</pre>' % ''.join(lines2)


def make_inline_html(data):
    """Make HTML for in-line diff view."""
    lines = []
    html_diff_lines(data, lines, lines, inline=True)
    return '<pre>%s</pre>' % ''.join(lines)


_complete = False

def _internal_diff(old_filename, oldlines, new_filename, newlines, output,
                  allow_binary=False, sequence_matcher=None,
                  path_encoding='utf8'):
    global _complete
    if allow_binary is False:
        textfile.check_text_lines(oldlines)
        textfile.check_text_lines(newlines)
    if sequence_matcher is None:
        sequence_matcher = patiencediff.PatienceSequenceMatcher
    if not _complete:
        groups = sequence_matcher(None, oldlines, newlines).get_grouped_opcodes()
    else:
        groups = [sequence_matcher(None, oldlines, newlines).get_opcodes()]
    output.extend([oldlines, newlines, groups])


def get_diff_trees(old_tree, new_tree, specific_files=None, old_label='a/',
                   new_label='b/', complete=False):
    from bzrlib.diff import _patch_header_date, _maybe_diff_file_or_symlink
    diffs = []
    delta = new_tree.changes_from(old_tree,
        specific_files=specific_files, require_versioned=True)

    global _complete
    _complete = complete

    for path, file_id, kind in delta.removed:
        output = []
        old_tree.inventory[file_id].diff(_internal_diff, None, old_tree,
                                         None, None, None, output)
        diffs.append(('removed', path, output))

    for path, file_id, kind in delta.added:
        output = []
        new_tree.inventory[file_id].diff(_internal_diff, None, new_tree,
                                         None, None, None, output,
                                         reverse=True)
        diffs.append(('added', path, output))

    for (old_path, new_path, file_id, kind,
         text_modified, meta_modified) in delta.renamed:
        output = []
        _maybe_diff_file_or_symlink(None, old_tree, file_id,
                                    None, new_tree,
                                    text_modified, kind, output, _internal_diff)
        diffs.append(('renamed', u'%s \u2192 %s' % (old_path, new_path), output))

    for path, file_id, kind, text_modified, meta_modified in delta.modified:
        old_name = '%s%s' % (old_label, path)
        new_name = '%s%ss' % (new_label, path)
        output = []
        if text_modified:
            _maybe_diff_file_or_symlink(None, old_tree, file_id,
                                        None, new_tree, True, kind,
                                        output, _internal_diff)
        diffs.append(('modified', path, output))

    return diffs


class DiffWindow(QBzrWindow):

    def __init__(self, tree1=None, tree2=None, specific_files=None,
                 parent=None, custom_title=None, inline=False, complete=False):
        title = ["Diff"]
        if custom_title:
            title.append(custom_title)
        if specific_files:
            if len(specific_files) > 2:
                title.append("%s files" % len(specific_files))
            else:
                title.append(", ".join(specific_files))
        QBzrWindow.__init__(self, title, (780, 580), parent)

        self.tree1 = tree1
        self.tree2 = tree2
        self.specific_files = specific_files

        self.browser = QtGui.QTextBrowser()

        if inline:
            html = []
        else:
            html1 = []
            html2 = []

        diffs = get_diff_trees(self.tree1, self.tree2, complete=complete,
                               specific_files=self.specific_files)
        for change, name, data in diffs:
            title = name
            if inline:
                html.append('<div style="%s">%s %s</div>' % (STYLES['title'], change, name))
                html.append(make_inline_html(data))
            else:
                html1.append('<div style="%s">%s %s</div>' % (STYLES['title'], change, name))
                html2.append('<div style="%s">%s %s</div>' % (STYLES['title'], change, name))
                lines1, lines2 = make_sidebyside_html(data)
                html1.append(lines1)
                html2.append(lines2)

        hbox = QtGui.QHBoxLayout()
        if inline:
            self.doc = QtGui.QTextDocument()
            self.doc.setHtml("".join(html))
            self.browser = QtGui.QTextBrowser()
            self.browser.setDocument(self.doc)
            hbox.addWidget(self.browser)
        else:
            self.doc1 = QtGui.QTextDocument()
            self.doc1.setHtml("".join(html1))
            self.doc2 = QtGui.QTextDocument()
            self.doc2.setHtml("".join(html2))
            self.browser1 = QtGui.QTextBrowser()
            self.browser1.setDocument(self.doc1)
            self.browser2 = QtGui.QTextBrowser()
            self.browser2.setDocument(self.doc2)
            self.connect(self.browser1.verticalScrollBar(),
                         QtCore.SIGNAL("valueChanged(int)"),
                         self.browser2.verticalScrollBar(),
                         QtCore.SLOT("setValue(int)"))
            self.connect(self.browser1.horizontalScrollBar(),
                         QtCore.SIGNAL("valueChanged(int)"),
                         self.browser2.horizontalScrollBar(),
                         QtCore.SLOT("setValue(int)"))
            self.connect(self.browser2.verticalScrollBar(),
                         QtCore.SIGNAL("valueChanged(int)"),
                         self.browser1.verticalScrollBar(),
                         QtCore.SLOT("setValue(int)"))
            self.connect(self.browser2.horizontalScrollBar(),
                         QtCore.SIGNAL("valueChanged(int)"),
                         self.browser1.horizontalScrollBar(),
                         QtCore.SLOT("setValue(int)"))
            hbox.addWidget(self.browser1)
            hbox.addWidget(self.browser2)

        buttonbox = QtGui.QDialogButtonBox(
            QtGui.QDialogButtonBox.StandardButtons(
                QtGui.QDialogButtonBox.Close),
            QtCore.Qt.Horizontal,
            self)
        self.connect(buttonbox, QtCore.SIGNAL("rejected()"), self.close)

        vbox = QtGui.QVBoxLayout(self.centralwidget)
        vbox.addLayout(hbox)
        vbox.addWidget(buttonbox)
