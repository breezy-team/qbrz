# -*- coding: utf-8 -*-
#
# QBzr - Qt frontend to Bazaar commands
# Copyright (C) 2006 Lukáš Lalinský <lalinsky@gmail.com>
# Copyright (C) 2006 Jelmer Vernooij <jelmer@samba.org>
# Copyright (C) 2005 Canonical Ltd. (author: Scott James Remnant <scott@ubuntu.com>)
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
from bzrlib.diff import show_diff_trees

def html_escape(string):
    return string.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")

class DiffView(QtGui.QDialog):

    def __init__(self, diff, parent=None):
        QtGui.QDialog.__init__(self, parent)

        self.setWindowTitle(u"Bazaar - Diff")
        icon = QtGui.QIcon()
        icon.addFile(":/bzr-16.png", QtCore.QSize(16, 16))
        icon.addFile(":/bzr-48.png", QtCore.QSize(48, 48))
        self.setWindowIcon(icon)
        self.resize(QtCore.QSize(780, 580).expandedTo(self.minimumSizeHint()))

        vbox = QtGui.QVBoxLayout(self)
        
        self.browser = QtGui.QTextBrowser()
        
        html = []
        for line in diff.split("\n"):
            if line.startswith("=== "):
                prefixes = ["=== modified file ", "=== added file ",
                    "=== removed file ", "=== renames file ",
                    "=== modified directory ", "=== added directory ",
                    "=== removed directory ", "=== renames directory "]
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
                if line.startswith("@@"):
                    style = ' style="background-color:#666666;color:#FFF;font-weight:bold;"'
                elif line.startswith("-"):
                    style = ' style="background-color:#FFDDDD;"'
                elif line.startswith("+"):
                    style = ' style="background-color:#DDFFDD;"'
                html.append(u"<div%s>%s</div>" % (style, html_escape(line)))
        html.append(u"</div>")
        html.append(u"</pre>")

        self.doc = QtGui.QTextDocument()
        self.doc.setHtml("".join(html))

        self.browser = QtGui.QTextBrowser()
        self.browser.setDocument(self.doc)

        vbox.addWidget(self.browser)

        hbox = QtGui.QHBoxLayout()
        hbox.addStretch()
        self.okButton = QtGui.QPushButton(u"&OK", self)
        self.connect(self.okButton, QtCore.SIGNAL("clicked()"), self.accept)
        hbox.addWidget(self.okButton)
        vbox.addLayout(hbox)
        

class cmd_qdiff(Command):
    """Show differences in working tree in a Qt window.
    
    Otherwise, all changes for the tree are listed.
    """
    takes_args = ['filename?']
    takes_options = ['revision']

    def run(self, revision=None, filename=None):
        wt = WorkingTree.open_containing(".")[0]
        branch = wt.branch
        if revision is not None:
            if len(revision) == 1:
                tree1 = wt
                revision_id = revision[0].in_history(branch).rev_id
                tree2 = branch.repository.revision_tree(revision_id)
            elif len(revision) == 2:
                revision_id_0 = revision[0].in_history(branch).rev_id
                tree2 = branch.repository.revision_tree(revision_id_0)
                revision_id_1 = revision[1].in_history(branch).rev_id
                tree1 = branch.repository.revision_tree(revision_id_1)
        else:
            tree1 = wt
            tree2 = tree1.basis_tree()

        s = StringIO()
        show_diff_trees(tree2, tree1, s, None)
        diff = s.getvalue()

        app = QtGui.QApplication(sys.argv)
        dialog = DiffView(s.getvalue().decode("UTF-8", "replace"))
        dialog.exec_()

register_command(cmd_qdiff)

