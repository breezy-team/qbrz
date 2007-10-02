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

import os
from PyQt4 import QtCore, QtGui
from bzrlib.config import GlobalConfig
from bzrlib import lazy_regex


_email_re = lazy_regex.lazy_compile(r'([a-z0-9_\-.+]+@[a-z0-9_\-.+]+)')
_link1_re = lazy_regex.lazy_compile(r'([\s>])(https?)://([^\s<>{}()]+[^\s.,<>{}()])')
_link2_re = lazy_regex.lazy_compile(r'(\s)www\.([a-z0-9\-]+)\.([a-z0-9\-.\~]+)((?:/[^ <>{}()\n\r]*[^., <>{}()\n\r]?)?)')


def htmlize(text):
    text = text.replace('&', '&amp;').replace('<', '&lt;').replace('>', '&gt;').replace("\n", '<br />')
    text = _email_re.sub('<a href="mailto:\\1">\\1</a>', text)
    text = _link1_re.sub('\\1<a href="\\2://\\3">\\2://\\3</a>', text)
    text = _link2_re.sub('\\1<a href="http://www.\\2.\\3\\4">www.\\2.\\3\\4</a>', text)
    return text


class QBzrWindow(QtGui.QMainWindow):

    def __init__(self, title=[], size=(540, 500), parent=None):
        QtGui.QMainWindow.__init__(self, parent)

        self.setWindowTitle(" - ".join(["QBzr"] + title))
        icon = QtGui.QIcon()
        icon.addFile(":/bzr-16.png", QtCore.QSize(16, 16))
        icon.addFile(":/bzr-48.png", QtCore.QSize(48, 48))
        self.setWindowIcon(icon)
        self.resize(QtCore.QSize(size[0], size[1]).expandedTo(self.minimumSizeHint()))

        self.centralwidget = QtGui.QWidget(self)
        self.setCentralWidget(self.centralwidget)


def get_branch_config(branch):
    if branch is not None:
        return branch.get_config()
    else:
        return GlobalConfig()


def format_revision_html(rev):
    text = []
    text.append("<b>Revision:</b> " + rev.revision_id)

    parent_ids = rev.parent_ids
    if parent_ids:
        text.append("<b>Parent revisions:</b> " + ", ".join('<a href="qlog-revid:%s">%s</a>' % (a, a) for a in parent_ids))

    text.append('<b>Author:</b> ' + htmlize(rev.committer))

    branch_nick = rev.properties.get('branch-nick')
    if branch_nick:
        text.append('<b>Branch nick:</b> ' + branch_nick)

    tags = getattr(rev, 'tags', None)
    if tags:
        text.append('<b>Tags:</b> ' + ', '.join(tags))

    message = htmlize(rev.message)
    text.append("")
    text.append(message)

    return "<br />".join(text)


def open_browser(url):
    try:
        import webbrowser
        open_func = webbrowser.open
    except ImportError:
        try:
            open_func = os.startfile
        except AttributeError:
            open_func = lambda x: None
    open_func(url)
