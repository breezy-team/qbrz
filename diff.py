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

import locale
import sys
import time
from cStringIO import StringIO

from PyQt4 import QtCore, QtGui

from bzrlib.errors import BinaryFile, NoSuchId
from bzrlib.textfile import check_text_lines
from bzrlib.config import GlobalConfig
from bzrlib.diff import show_diff_trees
from bzrlib.workingtree import WorkingTree
from bzrlib.patiencediff import PatienceSequenceMatcher as SequenceMatcher

from bzrlib.plugins.qbzr.i18n import _, ngettext
from bzrlib.plugins.qbzr.util import (
    BTN_CLOSE,
    QBzrWindow,
    format_timestamp,
    get_branch_config,
    )
from bzrlib.plugins.qbzr.diffview import (
    DiffView,
    SimpleDiffView
)


STYLES = {
    'hunk': 'background-color:#666666;color:#FFF;font-weight:bold;',
    'delete': 'background-color:#FFDDDD',
    'insert': 'background-color:#DDFFDD',
    'missing': 'background-color:#E0E0E0',
    'title': 'margin-top: 10px; font-size: 14px; font-weight: bold;',
    'metainfo': 'font-size: 9px; margin-bottom: 10px;',
}


def get_file_lines_from_tree(tree, file_id):
    try:
        return tree.get_file_lines(file_id)
    except AttributeError:
        return tree.get_file(file_id).readlines()


def htmlencode(string):
    return string.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")


def markup_line(line, style='', encode=True):
    if encode:
        line = htmlencode(line)
    if style:
        style = ' style="%s"' % style
    return '<div%s>%s</div>' % (style, line.rstrip() or '&nbsp;')


class FileDiff(object):

    status_msg = {
        'renamed':  _('renamed'),
        'removed':  _('removed'),
        'added':    _('added'),
        'modified': _('modified'),
    }

    def __init__(self, status, path):
        self.status = status
        self.path = path
        self.binary = False
        self.old_lines = []
        self.new_lines = []
        self.groups = []
        self.status_msg = FileDiff.status_msg[status]

    def make_diff(self, old_lines, new_lines, complete, encoding='utf-8'):
        try:
            check_text_lines(old_lines)
            check_text_lines(new_lines)
        except BinaryFile:
            self.binary = True
        else:
            self.old_lines = old_lines
            self.new_lines = new_lines
            if old_lines and not new_lines:
                self.groups = [[('delete', 0, len(old_lines), 0, 0)]]
            elif not old_lines and new_lines:
                self.groups = [[('insert', 0, 0, 0, len(new_lines))]]
            else:
                matcher = SequenceMatcher(None, old_lines, new_lines)
                if complete:
                    self.groups = list([matcher.get_opcodes()])
                else:
                    self.groups = list(matcher.get_grouped_opcodes())
            self.old_lines = [i.decode(encoding,'replace') for i in old_lines]
            self.new_lines = [i.decode(encoding,'replace') for i in new_lines]

    def html_diff_lines(self, html1, html2, inline=True):
        a = self.old_lines
        b = self.new_lines
        groups = self.groups
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
                            lineb = markup_intraline_changes(lineb, linea, '#99EE93')
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

    def txt_unidiff(self):
        return '\n'.join(self.unidiff_list(lineterm=''))+'\n'

    def unidiff_list(self, n=3, lineterm='\n'):
        """Create an unidiff output"""

        a = self.old_lines
        fromfiledate = self.old_date
        fromfile = self.old_path

        b = self.new_lines
        tofiledate = self.new_date
        tofile = self.new_path

        a = [a.rstrip("\n") for a in a]
        b = [b.rstrip("\n") for b in b]

        started = False
        if self.status == 'renamed':
            yield "=== renamed %s '%s' => '%s'"%(self.kind, fromfile, tofile)
        elif self.status == 'modified':
            yield "=== modified %s '%s'"%(self.kind, fromfile)
        elif self.status == 'removed':
            yield "=== removed %s '%s'"%(self.kind, fromfile)
        elif self.status == 'added':
            yield "=== added %s '%s'"%(self.kind, fromfile)
        if self.binary:
            yield "=== binary file"
            yield '--- %s %s%s' % (fromfile, fromfiledate, lineterm)
            yield '+++ %s %s%s' % (tofile, tofiledate, lineterm)
            return
        for group in self.groups:
            if not started:
                yield '--- %s %s%s' % (fromfile, fromfiledate, lineterm)
                yield '+++ %s %s%s' % (tofile, tofiledate, lineterm)
                started = True
            i1, i2, j1, j2 = group[0][1], group[-1][2], group[0][3], group[-1][4]
            yield "@@ -%d,%d +%d,%d @@%s" % (i1+1, i2-i1, j1+1, j2-j1, lineterm)
            for tag, i1, i2, j1, j2 in group:
                if tag == 'equal':
                    for line in a[i1:i2]:
                        yield ' ' + line
                    continue
                if tag == 'replace' or tag == 'delete':
                    for line in a[i1:i2]:
                        yield '-' + line
                if tag == 'replace' or tag == 'insert':
                    for line in b[j1:j2]:
                        yield '+' + line

    def html_unidiff(self):
        style = {
            '---': 'background-color:#c5e3f7; color:black',
            '+++': 'background-color:#c5e3f7; color:black',
            '-':   'background-color:#FFDDDD; color:black',
            '+':   'background-color:#DDFFDD; color:black',
            '@':   'background-color:#c5e3f7; color:black',
            '=':   'background-color:#c5e3f7; color:black',
        }
        defaultstyle = 'background-color:#ffffff; color=black',
        res ='<span style="font-size:12px">'
        keys = style.keys( )
        keys.sort(reverse=True) # so '---' is before '-'
        for l in self.unidiff_list(lineterm=''):
            for k in keys:
                if l.startswith(k):
                    res += markup_line(l, style[k])
                    break
            else:
                res += markup_line(l, defaultstyle)
        res += '</span>'
        return res

    def html_side_by_side(self):
        """Make HTML for side-by-side diff view."""
        if self.binary:
            line = '<p>%s</p>' % _('[binary file]')
            return line, line
        else:
            lines1 = []
            lines2 = []
            self.html_diff_lines(lines1, lines2, inline=False)
            return '<pre>%s</pre>' % ''.join(lines1), '<pre>%s</pre>' % ''.join(lines2)

    def html_inline(self):
        """Make HTML for in-line diff view."""
        if self.binary:
            line = '<p>%s</p>' % _('[binary file]')
            return line, line
        else:
            lines = []
            self.html_diff_lines(lines, lines, inline=True)
            return '<pre>%s</pre>' % ''.join(lines)


class TreeDiff(list):

    def _date(self, tree, file_id, path, secs=None):
        if secs is None:
            try:
                secs = tree.get_file_mtime(file_id, path)
            except (NoSuchId, OSError):
                secs = 0
        return format_timestamp(secs)

    def _make_diff(self, old_tree, new_tree, specific_files=[], complete=False,
                   encoding='utf-8'):
        delta = new_tree.changes_from(old_tree, specific_files=specific_files,
                                      require_versioned=True)

        for path, file_id, kind in delta.removed:
            diff = FileDiff('removed', path)
            diff.kind = kind
            diff.old_date = self._date(old_tree, file_id, path)
            diff.new_date = self._date(new_tree, file_id, path)
            diff.old_path = path
            diff.new_path = path
            if diff.kind != 'directory':
                diff.make_diff(get_file_lines_from_tree(old_tree, file_id),
                               [], complete, encoding)
            self.append(diff)

        for path, file_id, kind in delta.added:
            diff = FileDiff('added', path)
            diff.kind = kind
            diff.old_date = self._date(old_tree, file_id, path, 0)
            diff.new_date = self._date(new_tree, file_id, path)
            diff.old_path = path
            diff.new_path = path
            if diff.kind != 'directory':
                diff.make_diff([], get_file_lines_from_tree(new_tree, file_id),
                               complete, encoding)
            self.append(diff)

        for old_path, new_path, file_id, kind, text_modified, meta_modified in delta.renamed:
            diff = FileDiff('renamed', u'%s \u2192 %s' % (old_path, new_path))
            diff.kind = kind
            diff.old_date = self._date(old_tree, file_id, old_path)
            diff.new_date = self._date(new_tree, file_id, new_path)
            diff.old_path = old_path
            diff.new_path = new_path
            if text_modified:
                old_lines = get_file_lines_from_tree(old_tree, file_id)
                new_lines = get_file_lines_from_tree(new_tree, file_id)
                diff.make_diff(old_lines, new_lines, complete, encoding)
            self.append(diff)

        for path, file_id, kind, text_modified, meta_modified in delta.modified:
            diff = FileDiff('modified', path)
            diff.kind = kind
            diff.old_date = self._date(old_tree, file_id, path)
            diff.new_date = self._date(new_tree, file_id, path)
            diff.old_path = path
            diff.new_path = path
            if text_modified:
                old_lines = get_file_lines_from_tree(old_tree, file_id)
                new_lines = get_file_lines_from_tree(new_tree, file_id)
                diff.make_diff(old_lines, new_lines, complete, encoding)
            self.append(diff)

    def __init__(self, old_tree, new_tree, specific_files=[], complete=False,
                 encoding='utf-8'):
        self._metainfo_template = None
        old_tree.lock_read()
        new_tree.lock_read()
        try:
            self._make_diff(old_tree, new_tree, specific_files, complete,
                            encoding)
        finally:
            old_tree.unlock()
            new_tree.unlock()

    def _get_metainfo_template(self):
        if self._metainfo_template is None:
            self._metainfo_template = (
                '<div style="%%s"><small>'
                '<b>%s</b> %%s, '
                '<b>%s</b> %%s, '
                '<b>%s</b> %%s'
                '</small></div>') % (_('Last modified:'),
                                     _('Status:'),
                                     _('Kind:'))
        return self._metainfo_template

    def html_inline(self):
        html = []
        for diff in self:
            html.append('<div style="%s">%s</div>' % (STYLES['title'], diff.path))
            html.append(self._get_metainfo_template() % (STYLES['metainfo'],
                                                         diff.old_date,
                                                         diff.status_msg,
                                                         diff.kind))
            html.append(diff.html_inline())
        return ''.join(html)

    def txt_unidiff(self):
        res = []
        for diff in self:
            res.append(diff.txt_unidiff())
        return '\n'.join(res)

    def html_unidiff(self):
        res = []
        for diff in self:
            res.append(diff.html_unidiff())
        return ''.join(res)

    def html_side_by_side(self):
        html1 = []
        html2 = []
        for diff in self:
            html1.append('<div style="%s">%s</div>' % (STYLES['title'], diff.path))
            html1.append(self._get_metainfo_template() % (STYLES['metainfo'],
                                                          diff.old_date,
                                                          diff.status_msg,
                                                          diff.kind))
            html2.append('<div style="%s">%s</div>' % (STYLES['title'], diff.path))
            html2.append(self._get_metainfo_template() % (STYLES['metainfo'],
                                                          diff.new_date,
                                                          diff.status_msg,
                                                          diff.kind))
            lines1, lines2 = diff.html_side_by_side()
            html1.append(lines1)
            html2.append(lines2)
        return ''.join(html1), ''.join(html2)


class DiffWindow(QBzrWindow):

    def __init__(self, tree1=None, tree2=None, specific_files=None,
                 parent=None, custom_title=None, inline=False,
                 complete=False, branch=None, encoding=None):
        title = [_("Diff")]
        if custom_title:
            title.append(custom_title)
        if specific_files:
            nfiles = len(specific_files)
            if nfiles > 2:
                title.append(
                    ngettext("%d file", "%d files", nfiles) % nfiles)
            else:
                title.append(", ".join(specific_files))

        config = get_branch_config(branch)

        size = (780, 580)
        try:
            size_str = config.get_user_option("qdiff_window_size")
            if size_str:
                size = map(int, size_str.split("x", 2))
        except:
            pass

        if encoding is None:
            encoding = config.get_user_option("encoding") or 'utf-8'
        else:
            config.set_user_option('encoding', encoding)

        QBzrWindow.__init__(self, title, size, parent)

        self.tree1 = tree1
        self.tree2 = tree2
        self.specific_files = specific_files

        treediff = TreeDiff(self.tree1, self.tree2, self.specific_files,
                            complete, encoding)
        self.diffview = DiffView(treediff, self)

        self.sdiffview = SimpleDiffView(treediff, self)
        self.sdiffview.setVisible(False)

        self.stack = QtGui.QStackedWidget(self.centralwidget)
        self.stack.addWidget(self.diffview)
        self.stack.addWidget(self.sdiffview)

        vbox = QtGui.QVBoxLayout(self.centralwidget)
        vbox.addWidget(self.stack)

        diffsidebyside = QtGui.QRadioButton(_("Side by side"), self.centralwidget)
        self.connect(diffsidebyside,
                     QtCore.SIGNAL("clicked(bool)"),
                     self.click_diffsidebyside)
        diffsidebyside.setChecked(True);

        unidiff = QtGui.QRadioButton(_("Unidiff"), self.centralwidget)
        self.connect(unidiff,
                     QtCore.SIGNAL("clicked(bool)"),
                     self.click_unidiff)

        buttonbox = self.create_button_box(BTN_CLOSE)

        hbox = QtGui.QHBoxLayout()
        hbox.addWidget(diffsidebyside)
        hbox.addWidget(unidiff)
        hbox.addWidget(buttonbox)
        vbox.addLayout(hbox)

    def click_unidiff(self, checked):
        if(checked):
            self.stack.setCurrentIndex(1)

    def click_diffsidebyside(self, checked):
        if(checked):
            self.stack.setCurrentIndex(0)
