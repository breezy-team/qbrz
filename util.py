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
import sys
from PyQt4 import QtCore, QtGui
from bzrlib.config import GlobalConfig
from bzrlib import lazy_regex
from bzrlib.plugins.qbzr.i18n import _, N_


_email_re = lazy_regex.lazy_compile(r'([a-z0-9_\-.+]+@[a-z0-9_\-.+]+)')
_link1_re = lazy_regex.lazy_compile(r'([\s>])(https?)://([^\s<>{}()]+[^\s.,<>{}()])')
_link2_re = lazy_regex.lazy_compile(r'(\s)www\.([a-z0-9\-]+)\.([a-z0-9\-.\~]+)((?:/[^ <>{}()\n\r]*[^., <>{}()\n\r]?)?)')


def htmlize(text):
    text = text.replace('&', '&amp;').replace('<', '&lt;').replace('>', '&gt;').replace("\n", '<br />')
    text = _email_re.sub('<a href="mailto:\\1">\\1</a>', text)
    text = _link1_re.sub('\\1<a href="\\2://\\3">\\2://\\3</a>', text)
    text = _link2_re.sub('\\1<a href="http://www.\\2.\\3\\4">www.\\2.\\3\\4</a>', text)
    return text


# standard buttons with translatable labels
BTN_OK, BTN_CANCEL, BTN_CLOSE, BTN_HELP = range(4)

class StandardButton(QtGui.QPushButton):

    __types = {
        BTN_OK: (N_('&OK'), 'SP_DialogOkButton'),
        BTN_CANCEL: (N_('&Cancel'), 'SP_DialogCancelButton'),
        BTN_CLOSE: (N_('&Close'), 'SP_DialogCloseButton'),
        BTN_HELP: (N_('&Help'), 'SP_DialogHelpButton'),
    }

    def __init__(self, btntype, *args):
        label = _(self.__types[btntype][0])
        new_args = [label]
        if sys.platform != 'win32' and sys.platform != 'darwin':
            iconname = self.__types[btntype][1]
            if hasattr(QtGui.QStyle, iconname):
                icon = QtGui.QApplication.style().standardIcon(
                    getattr(QtGui.QStyle, iconname))
                new_args = [icon, label]
        new_args.extend(args)
        QtGui.QPushButton.__init__(self, *new_args)


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

    def create_button_box(self, *buttons):
        """Create and return button box with pseudo-standard buttons
        @param  buttons:    any from BTN_OK, BTN_CANCEL, BTN_CLOSE, BTN_HELP
        @return:    QtGui.QDialogButtonBox with attached buttons and signals
        """
        ROLES = {
            BTN_OK: (QtGui.QDialogButtonBox.AcceptRole,
                "accepted()", "accept"),
            BTN_CANCEL: (QtGui.QDialogButtonBox.RejectRole,
                "rejected()", "reject"),
            BTN_CLOSE: (QtGui.QDialogButtonBox.RejectRole,
                "rejected()", "close"),
            # XXX support for HelpRole
            }
        buttonbox = QtGui.QDialogButtonBox(self.centralwidget)
        for i in buttons:
            btn = StandardButton(i)
            role, signal_name, method_name = ROLES[i]
            buttonbox.addButton(btn, role)
            self.connect(buttonbox,
                QtCore.SIGNAL(signal_name), getattr(self, method_name))
        return buttonbox


def get_branch_config(branch):
    if branch is not None:
        return branch.get_config()
    else:
        return GlobalConfig()


def format_revision_html(rev, search_replace=None):
    text = []
    text.append("<b>%s</b> %s" % (_("Revision:"), rev.revision_id))

    parent_ids = rev.parent_ids
    if parent_ids:
        text.append("<b>%s</b> %s" % (_("Parent revisions:"),
            ", ".join('<a href="qlog-revid:%s">%s</a>' % (a, a) for a in parent_ids)))

    text.append('<b>%s</b> %s' % (_("Committer:"), htmlize(rev.committer)))
    author = rev.properties.get('author')
    if author:
        text.append('<b>%s</b> %s' % (_("Author:"), htmlize(author)))

    branch_nick = rev.properties.get('branch-nick')
    if branch_nick:
        text.append('<b>%s</b> %s' % (_("Branch nick:"), branch_nick))

    tags = getattr(rev, 'tags', None)
    if tags:
        text.append('<b>%s</b> %s' % (_("Tags:"), ', '.join(tags)))

    bugs = []
    for bug in rev.properties.get('bugs', '').split('\n'):
        if bug:
            url, status = bug.split(' ')
            bugs.append('<a href="%(url)s">%(url)s</a> %(status)s' % (
                dict(url=url, status=status)))
    if bugs:
        text.append('<b>%s</b> %s' % (_("Bugs:"), ', '.join(bugs)))

    message = htmlize(rev.message)
    if search_replace:
        for search, replace in search_replace:
            message = re.sub(search, replace, message)
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


def get_apparent_author(rev):
    return rev.properties.get('author', rev.committer)


_extract_name_re = lazy_regex.lazy_compile('(.*?) <.*?@.*?>')
_extract_email_re = lazy_regex.lazy_compile('<(.*?@.*?)>')

def extract_name(author):
    m = _extract_name_re.match(author)
    if m:
        name = m.group(1)
    else:
        m = _extract_email_re.match(author)
        if m:
            name = m.group(1)
        else:
            name = author
    return name.strip()


def format_timestamp(timestamp):
    """Returns unicode string representation of timestamp
    formatted in user locale"""
    date = QtCore.QDateTime()
    date.setTime_t(int(timestamp))
    return unicode(date.toString(QtCore.Qt.LocalDate))


def htmlencode(string):
    return string.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")
