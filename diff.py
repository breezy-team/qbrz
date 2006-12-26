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
from bzrlib.workingtree import WorkingTree
from bzrlib.plugins.qbzr.util import QBzrWindow


def _get_change_extent(str1, str2):
    """
    Determines the extent of differences between two strings. Returns a tuple
    containing the offset at which the changes start, and the negative offset
    at which the changes end. If the two strings have neither a common prefix
    nor a common suffix, (0, 0) is returned.
    """
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
    line1 = html_escape(line1)
    line2 = html_escape(line2)
    start, end = _get_change_extent(line1[1:], line2[1:])
    if start == 0 and end < 0:
        text = u'<span style="background-color:%s">%s</span>%s' % (color, line1[:end], line1[end:])
    elif start > 0 and end == 0:
        start += 1
        text = u'%s<span style="background-color:%s">%s</span>' % (line1[:start], color, line1[start:])
    elif start > 0 and end < 0:
        start += 1
        text = u'%s<span style="background-color:%s">%s</span>%s' % (line1[:start], color, line1[start:end], line1[end:])
    else:
        text = line1
    return text


def html_escape(string):
    return string.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")


def get_diff_trees(tree1, tree2, **kwargs):
    """Return unified diff between two trees as a string."""
    from bzrlib.diff import show_diff_trees
    output = StringIO()
    show_diff_trees(tree1, tree2, output, **kwargs)
    return output.getvalue().decode("UTF-8", "replace")


class DiffWindow(QBzrWindow):

    def __init__(self, tree1=None, tree2=None, specific_files=None,
                 parent=None, custom_title=None):
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

        diff = get_diff_trees(self.tree1, self.tree2,
                              specific_files=self.specific_files)

        html = []
        lines = diff.split("\n")
        for i in range(len(lines)):
            line = lines[i]
            if line.startswith("=== "):
                prefixes = ["=== modified file ", "=== added file ",
                    "=== removed file ", "=== renamed file ",
                    "=== modified directory ", "=== added directory ",
                    "=== removed directory ", "=== renamed directory "]
                text = line
                for prefix in prefixes:
                    if line.startswith(prefix):
                        text = line[len(prefix)+1:-1]
                        break
                html.append(u"</pre>")
                html.append(u"<div style=\"margin-top:10px;margin-bottom:10px;font-size:16px;font-weight:bold;\">%s</div>" % (text))
                html.append(u"<pre>")
            elif not line.startswith("+++ ") and not line.startswith("--- "):
                style = ""
                text = None
                if line.startswith("@@"):
                    style = ' style="background-color:#666666;color:#FFF;font-weight:bold;"'
                elif line.startswith("-"):
                    style = ' style="background-color:#FFDDDD;"'
                    try:
                        next_line = lines[i+1]
                        if next_line.startswith("+") and not next_line.startswith("+++"):
                            text = markup_intraline_changes(line, next_line, "#EE9999")
                    except IndexError:
                        pass
                elif line.startswith("+"):
                    style = ' style="background-color:#DDFFDD;"'
                    try:
                        prev_line = lines[i-1]
                        if prev_line.startswith("-") and not prev_line.startswith("---"):
                            text = markup_intraline_changes(line, prev_line, "#99EE99")
                    except IndexError:
                        pass
                if text is None:
                    text = html_escape(line)
                html.append(u"<div%s>%s</div>" % (style, text))
        html.append(u"</div>")
        html.append(u"</pre>")

        self.doc = QtGui.QTextDocument()
        self.doc.setHtml("".join(html))

        self.browser = QtGui.QTextBrowser()
        self.browser.setDocument(self.doc)

        buttonbox = QtGui.QDialogButtonBox(
            QtGui.QDialogButtonBox.StandardButtons(
                QtGui.QDialogButtonBox.Close),
            QtCore.Qt.Horizontal,
            self)
        self.connect(buttonbox, QtCore.SIGNAL("rejected()"), self.close)

        vbox = QtGui.QVBoxLayout(self.centralwidget)
        vbox.addWidget(self.browser)
        vbox.addWidget(buttonbox)
