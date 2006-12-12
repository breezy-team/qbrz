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

import sys
from PyQt4 import QtCore, QtGui
from bzrlib.commands import Command, register_command
from bzrlib.workingtree import WorkingTree

have_pygments = True
try:
    from pygments import highlight
    from pygments.lexers import get_lexer_for_filename
    from pygments.formatters import HtmlFormatter
except ImportError:
    have_pygments = False

class AnnotateWindow(QtGui.QMainWindow):

    def __init__(self, filename, lines, parent=None):
        QtGui.QMainWindow.__init__(self, parent)

        title = "QBzr - Annotate - %s" % filename
        self.setWindowTitle(title)

        icon = QtGui.QIcon()
        icon.addFile(":/bzr-16.png", QtCore.QSize(16, 16))
        icon.addFile(":/bzr-48.png", QtCore.QSize(48, 48))
        self.setWindowIcon(icon)
        self.resize(QtCore.QSize(780, 580).expandedTo(self.minimumSizeHint()))

        self.centralWidget = QtGui.QWidget(self)
        self.setCentralWidget(self.centralWidget)
        vbox = QtGui.QVBoxLayout(self.centralWidget)
        
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

        self.browser = QtGui.QTextBrowser()
        self.browser.setDocument(self.doc)

        vbox.addWidget(self.browser)

        hbox = QtGui.QHBoxLayout()
        hbox.addStretch()
        self.closeButton = QtGui.QPushButton(u"&Close", self)
        self.connect(self.closeButton, QtCore.SIGNAL("clicked()"), self.close)
        hbox.addWidget(self.closeButton)
        vbox.addLayout(hbox)

class cmd_qannotate(Command):
    """Show the origin of each line in a file.
    """
    takes_args = ['filename?']
    takes_options = ['revision']
    aliases = ['qann', 'qblame']

    def run(self, filename=None, revision=None):
        from bzrlib.annotate import _annotate_file
        tree, relpath = WorkingTree.open_containing(filename)
        branch = tree.branch
        branch.lock_read()
        try:
            if revision is None:
                revision_id = branch.last_revision()
            elif len(revision) != 1:
                raise errors.BzrCommandError('bzr qannotate --revision takes exactly 1 argument')
            else:
                revision_id = revision[0].in_history(branch).rev_id
            file_id = tree.inventory.path2id(relpath)
            tree = branch.repository.revision_tree(revision_id)
            file_version = tree.inventory[file_id].revision
            lines = list(_annotate_file(branch, file_version, file_id))
        finally:
            branch.unlock()

        app = QtGui.QApplication(sys.argv)
        win = AnnotateWindow(filename, lines)
        win.show()
        app.exec_()

register_command(cmd_qannotate)

