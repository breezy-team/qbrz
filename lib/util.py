# -*- coding: utf-8 -*-
#
# QBzr - Qt frontend to Bazaar commands
# Copyright (C) 2006 Lukáš Lalinský <lalinsky@gmail.com>
# Copyright (C) 2007, 2008 Alexander Belchenko
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
import re
import sys
import itertools

from PyQt4 import QtCore, QtGui

from bzrlib.config import (
    GlobalConfig,
    IniBasedConfig,
    config_dir,
    ensure_config_dir_exists,
    )
from bzrlib import (
    lazy_regex,
    osutils,
    urlutils
    )
from bzrlib.util.configobj import configobj

from bzrlib.plugins.qbzr.lib import i18n
from bzrlib.plugins.qbzr.lib.i18n import gettext, N_, ngettext
import bzrlib.plugins.qbzr.lib.resources


_email_re = lazy_regex.lazy_compile(r'([a-z0-9_\-.+]+@[a-z0-9_\-.+]+)', re.IGNORECASE)
_link1_re = lazy_regex.lazy_compile(r'([\s>])(https?)://([^\s<>{}()]+[^\s.,<>{}()])', re.IGNORECASE)
_link2_re = lazy_regex.lazy_compile(r'(\s)www\.([a-z0-9\-]+)\.([a-z0-9\-.\~]+)((?:/[^ <>{}()\n\r]*[^., <>{}()\n\r]?)?)', re.IGNORECASE)
_tag_re = lazy_regex.lazy_compile(r'[, ]')


def htmlize(text):
    text = htmlencode(text)
    text = text.replace("\n", '<br />')
    text = _email_re.sub('<a href="mailto:\\1">\\1</a>', text)
    text = _link1_re.sub('\\1<a href="\\2://\\3">\\2://\\3</a>', text)
    text = _link2_re.sub('\\1<a href="http://www.\\2.\\3\\4">www.\\2.\\3\\4</a>', text)
    return text


# standard buttons with translatable labels
BTN_OK, BTN_CANCEL, BTN_CLOSE, BTN_HELP, BTN_REFRESH = range(5)

class StandardButton(QtGui.QPushButton):

    __types = {
        BTN_OK: (N_('&OK'), 'SP_DialogOkButton'),
        BTN_CANCEL: (N_('&Cancel'), 'SP_DialogCancelButton'),
        BTN_CLOSE: (N_('&Close'), 'SP_DialogCloseButton'),
        BTN_HELP: (N_('&Help'), 'SP_DialogHelpButton'),
        BTN_REFRESH: (N_('&Refresh'), 'view-refresh'),
    }

    def __init__(self, btntype, *args):
        label = gettext(self.__types[btntype][0])
        new_args = [label]
        if sys.platform != 'win32' and sys.platform != 'darwin':
            iconname = self.__types[btntype][1]
            if iconname == 'view-refresh':
                icon = QtGui.QIcon(':/16x16/view-refresh.png')
                new_args = [icon, label]
            elif hasattr(QtGui.QStyle, iconname):
                icon = QtGui.QApplication.style().standardIcon(
                    getattr(QtGui.QStyle, iconname))
                new_args = [icon, label]
        new_args.extend(args)
        QtGui.QPushButton.__init__(self, *new_args)


def config_filename():
    return osutils.pathjoin(config_dir(), 'qbzr.conf')


class Config(object):

    def __init__(self, filename):
        self._filename = filename
        self._configobj = None

    def _load(self):
        if self._configobj is not None:
            return
        self._configobj = configobj.ConfigObj(self._filename,
                                              encoding='utf-8')

    def setOption(self, name, value, section=None):
        self._load()
        if section is None:
            section = 'DEFAULT'
        if section not in self._configobj:
            self._configobj['DEFAULT'] = {}
        self._configobj['DEFAULT'][name] = value

    def getOption(self, name, value, section=None):
        self._load()
        if section is None:
            section = 'DEFAULT'
        try:
            return self._configobj['DEFAULT'][name]
        except KeyError:
            return None

    def setSection(self, name, values):
        self._load()
        self._configobj[name] = values

    def getSection(self, name):
        self._load()
        try:
            return self._configobj[name]
        except KeyError:
            return {}

    def save(self):
        self._load()
        ensure_config_dir_exists(os.path.dirname(self._filename))
        f = open(self._filename, 'wb')
        self._configobj.write(f)
        f.close()


class QBzrConfig(Config):

    def __init__(self):
        super(QBzrConfig, self).__init__(config_filename())

    def getBookmarks(self):
        section = self.getSection('BOOKMARKS')
        i = 0
        while True:
            try:
                location = section['bookmark%d' % i]
            except KeyError:
                break
            name = section.get('bookmark%d_name' % i, location)
            i += 1
            yield name, location

    def setBookmarks(self, bookmarks):
        section = {}
        for i, (name, location) in enumerate(bookmarks):
            section['bookmark%d' % i] = location
            section['bookmark%d_name' % i] = name
        self.setSection('BOOKMARKS', section)

    def addBookmark(self, name, location):
        bookmarks = list(self.getBookmarks())
        bookmarks.append((name, location))
        self.setBookmarks(bookmarks)


class QBzrGlobalConfig(IniBasedConfig):

    def __init__(self):
        super(QBzrGlobalConfig, self).__init__(config_filename)

    def set_user_option(self, option, value):
        """Save option and its value in the configuration."""
        conf_dir = os.path.dirname(self._get_filename())
        ensure_config_dir_exists(conf_dir)
        if 'DEFAULT' not in self._get_parser():
            self._get_parser()['DEFAULT'] = {}
        self._get_parser()['DEFAULT'][option] = value
        f = open(self._get_filename(), 'wb')
        self._get_parser().write(f)
        f.close()


class QBzrWindow(QtGui.QMainWindow):

    def __init__(self, title=[], parent=None):
        QtGui.QMainWindow.__init__(self, parent)

        self.setWindowTitle(" - ".join(["QBzr"] + title))
        icon = QtGui.QIcon()
        icon.addFile(":/bzr-16.png", QtCore.QSize(16, 16))
        icon.addFile(":/bzr-32.png", QtCore.QSize(32, 32))
        icon.addFile(":/bzr-48.png", QtCore.QSize(48, 48))
        self.setWindowIcon(icon)

        self.centralwidget = QtGui.QWidget(self)
        self.setCentralWidget(self.centralwidget)
        self.windows = []

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

    def saveSize(self):
        name = self._window_name
        is_maximized = int(self.windowState()) & QtCore.Qt.WindowMaximized != 0
        if is_maximized:
            # XXX for some reason this doesn't work
            geom = self.normalGeometry()
            size = geom.width(), geom.height()
        else:
            size = self.width(), self.height()
        config = QBzrGlobalConfig()
        config.set_user_option(name + "_window_size", "%dx%d" % size)
        config.set_user_option(name + "_window_maximized", is_maximized)
        return config

    def restoreSize(self, name, defaultSize):
        self._window_name = name
        config = QBzrGlobalConfig()
        size = config.get_user_option(name + "_window_size")
        if size:
            size = size.split("x")
            if len(size) == 2:
                try:
                    size = map(int, size)
                except ValueError:
                    size = defaultSize
                else:
                    if size[0] < 100 or size[1] < 100:
                        size = defaultSize
        else:
            size = defaultSize
        size = QtCore.QSize(size[0], size[1])
        self.resize(size.expandedTo(self.minimumSizeHint()))
        is_maximized = config.get_user_option(name + "_window_maximized")
        if is_maximized in ("True", "1"):
            self.setWindowState(QtCore.Qt.WindowMaximized)
        return config

    def closeEvent(self, event):
        self.saveSize()
        for window in self.windows:
            if window.isVisible():
                window.close()
        event.accept()


class QBzrDialog(QtGui.QDialog):

    # We use these items both as 'flags' and as titles!
    # A directory picker used to select a 'pull' location.
    DIRECTORYPICKER_SOURCE = "Select Source Directory"
    # A directory picker used to select a destination
    DIRECTORYPICKER_TARGET = "Select Target Directory"

    def __init__(self, title=[], parent=None):
        QtGui.QDialog.__init__(self, parent)

        self.setWindowTitle(" - ".join(["QBzr"] + title))
        icon = QtGui.QIcon()
        icon.addFile(":/bzr-16.png", QtCore.QSize(16, 16))
        icon.addFile(":/bzr-32.png", QtCore.QSize(32, 32))
        icon.addFile(":/bzr-48.png", QtCore.QSize(48, 48))
        self.setWindowIcon(icon)

        self.centralwidget = self
        #self.setCentralWidget(self.centralwidget)
        self.windows = []

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

    def saveSize(self):
        name = self._window_name
        is_maximized = int(self.windowState()) & QtCore.Qt.WindowMaximized != 0
        if is_maximized:
            # XXX for some reason this doesn't work
            geom = self.normalGeometry()
            size = geom.width(), geom.height()
        else:
            size = self.width(), self.height()
        config = QBzrGlobalConfig()
        config.set_user_option(name + "_window_size", "%dx%d" % size)
        config.set_user_option(name + "_window_maximized", is_maximized)
        return config

    def restoreSize(self, name, defaultSize):
        self._window_name = name
        config = QBzrGlobalConfig()
        size = config.get_user_option(name + "_window_size")
        if size:
            size = size.split("x")
            if len(size) == 2:
                try:
                    size = map(int, size)
                except ValueError:
                    size = defaultSize
                else:
                    if size[0] < 100 or size[1] < 100:
                        size = defaultSize
        else:
            size = defaultSize
        size = QtCore.QSize(size[0], size[1])
        self.resize(size.expandedTo(self.minimumSizeHint()))
        is_maximized = config.get_user_option(name + "_window_maximized")
        if is_maximized in ("True", "1"):
            self.setWindowState(QtCore.Qt.WindowMaximized)
        return config

    def closeEvent(self, event):
        self.saveSize()
        for window in self.windows:
            if window.isVisible():
                window.close()
        event.accept()

    # Helpers for directory pickers.
    def hookup_directory_picker(self, chooser, target, chooser_type):
        # an inline handler that serves as a 'link' between the widgets.
        caption = gettext(chooser_type)
        def click_handler(dlg=self, chooser=chooser, target=target, caption=caption):
            try:
                # Might be a QComboBox
                getter = target.currentText
                setter = target.setEditText
            except AttributeError:
                # Or a QLineEdit
                getter = target.text
                setter = target.setText
            dir = getter()
            if not os.path.isdir(dir):
                dir = ""
            dir = QtGui.QFileDialog.getExistingDirectory(dlg, caption, dir)
            if dir:
                setter(dir)

        self.connect(chooser, QtCore.SIGNAL("clicked()"), click_handler)


_global_config = None

def get_global_config():
    global _global_config
    if _global_config is None:
        _global_config = GlobalConfig()
    return _global_config


def get_branch_config(branch):
    if branch is not None:
        return branch.get_config()
    else:
        return get_global_config()


def quote_tag(tag):
    if _tag_re.search(tag):
        return '"%s"' % tag
    return tag


def format_revision_html(rev, search_replace=None):
    props = []
    props.append((gettext("Revision:"), "%s revid:%s" % (rev.revno, rev.revision_id)))

    def short_text(summary, length):
        if len(summary) > length:
            return summary[:length-1] + u"\u2026"
        else:
            return summary

    def revision_list_html(revisions):
        return ', '.join('<a href="qlog-revid:%s" title="%s">%s: %s</a>' % (
            (r.revision_id,
             htmlencode(r.get_summary()),
             short_text(r.revno, 10),
             htmlencode(short_text(r.get_summary(), 60)))) for r in revisions)

    parents = getattr(rev, 'parents', None)
    if parents:
        props.append((gettext("Parents:"), revision_list_html(parents)))

    children = getattr(rev, 'children', None)
    if children:
        props.append((gettext("Children:"), revision_list_html(children)))

    props.append((gettext("Committer:"), htmlize(rev.committer)))
    author = rev.properties.get('author')
    if author:
        props.append((gettext("Author:"), htmlize(author)))

    branch_nick = rev.properties.get('branch-nick')
    if branch_nick:
        props.append((gettext("Branch:"), htmlize(branch_nick)))

    tags = getattr(rev, 'tags', None)
    if tags:
        tags = map(quote_tag, tags)
        props.append((gettext("Tags:"), ", ".join(tags)))

    bugs = []
    for bug in rev.properties.get('bugs', '').split('\n'):
        if bug:
            url, status = bug.split(' ')
            bugs.append('<a href="%(url)s">%(url)s</a> %(status)s' % (
                dict(url=url, status=gettext(status))))
    if bugs:
        props.append((ngettext("Bug:", "Bugs:", len(bugs)), ", ".join(bugs)))

    text = []
    text.append('<table style="background:#EDEDED;" width="100%" cellspacing="0" cellpadding="0"><tr><td>')
    text.append('<table cellspacing="0" cellpadding="0">')
    for prop in props:
        # <nobr> needed because in Russian some prop labels has 2 words
        # &nbsp; needed because on Windows + PyQt 4.3.1 style=padding-left:5px does not working
        text.append(('<tr><td style="padding-left:2px;" align="right"><b><nobr>%s </nobr></b></td>'
            '<td>%s</td></tr>') % prop)
    text.append('</table>')
    text.append('</td></tr></table>')

    message = htmlize(rev.message)
    if search_replace:
        for search, replace in search_replace:
            message = re.sub(search, replace, message)
    text.append('<div style="margin:2px;margin-top:0.5em;">%s</div>' % message)

    return "".join(text)


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

def extract_name(author, strict=False):
    m = _extract_name_re.match(author)
    if m:
        name = m.group(1)
    else:
        if strict:
            name = author
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


def is_valid_encoding(encoding):
    import codecs
    try:
        codecs.lookup(encoding)
    except LookupError:
        return False
    return True


def get_set_encoding(encoding, config):
    """Return encoding value from branch config if encoding is None,
    otherwise store encoding value in branch config.
    """
    if encoding is None:
        encoding = config.get_user_option("encoding") or 'utf-8'
        if not is_valid_encoding(encoding):
            from bzrlib.trace import note
            note(('NOTE: Invalid encoding value in branch config: %s\n'
                'utf-8 will be used instead') % encoding)
            encoding = 'utf-8'
    else:
        config.set_user_option("encoding", encoding)
    return encoding

class RevisionMessageBrowser(QtGui.QTextBrowser):

    def setSource(self, uri):
        pass


def file_extension(path):
    """Return extension of the file.
    This function is smarter than standard os.path.splitext,
    because it correctly process filenames with leading dot.
    (e.g. ".bzrignore")
    """
    basename = os.path.basename(path)
    ix = basename.rfind('.')
    if ix > 0:
        ext = basename[ix:]
    else:
        ext = ''
    return ext


class FilterOptions(object):
    """Filter options container."""

    __slots__ = ['deleted', 'added', 'renamed', 'modified']

    def __init__(self, all_enable=False, **kw):
        self.added = False
        self.deleted = False
        self.modified = False
        self.renamed = False
        if all_enable:
            self.added = True
            self.deleted = True
            self.modified = True
            self.renamed = True
        for k in kw:
            setattr(self, k, kw[k])

    def all_enable(self):
        for i in self.__slots__:
            setattr(self, i, True)

    def __nonzero__(self):
        return self.added or self.deleted or self.modified or self.renamed

    def is_all_enable(self):
        return self.added and self.deleted and self.modified and self.renamed

    def to_str(self):
        s = []
        if self.deleted:
            s.append(i18n.gettext('deleted files'))
        if self.added:
            s.append(i18n.gettext('added files'))
        if self.renamed:
            s.append(i18n.gettext('renamed files'))
        if self.modified:
            s.append(i18n.gettext('modified files'))
        return ', '.join(s)

    def check(self, status):
        """Check status (string) and return True if enabled.
        Allowed statuses:
            added, removed, deleted, renamed, modified, 'renamed and modified'

        @raise ValueError:  when unsupported status given.
        """
        if status == 'added':
            return self.added
        elif status in ('removed', 'deleted'):
            return self.deleted
        elif status == 'renamed':
            return self.renamed
        elif status == 'modified':
            return self.modified
        elif status == 'renamed and modified':
            return self.renamed or self.modified
        raise ValueError('unknown status: %r' % status)

def split_tokens_at_lines(tokens):
    currentLine = []
    for ttype, value in tokens:
        vsplit = value.splitlines(True)
        for v in vsplit:
            currentLine.append((ttype, v))
            if v.endswith(('\n','\r')):
                yield currentLine
                currentLine = []

# Some helpers for combo-boxes.  Combos for different purposes (eg, push
# vs pull) have quite different requirements for the combo:
# * When pulling from a branch, if the branch is not related to the existing
#   branch (eg, creating a new one, pulling from non-parent), the branch
#   location entered by the user should be remembered *globally* (ie, for
#   the user rather than just for that branch)
# * Pull dialogs almost always want to offer these remembered locations as
#   options - below the 'related' locations if any exist.
# * Push dialogs almost never want to offer these 'global' options - they
#   only ever want to show 'related' branches plus old push branches
#   remembered against just this branch.
#
# We offer a number of iterators to help enumerate the possibilities,
# and another helper to take these iterators and fill the combo.

def iter_branch_related_locations(branch):
    for location in [branch.get_parent(),
                     branch.get_bound_location(),
                     branch.get_push_location(),
                     branch.get_submit_branch(),
                    ]:
        if location is not None:
            yield urlutils.unescape_for_display(location, 'utf-8')

# Iterate the 'pull' locations we have previously saved for the user.
def iter_saved_pull_locations():
    # XXX - todo
    # let python know its a generator and show how it *would* appear.
    yield u"http://pretend/this/was/a/saved/location"


# A helper to fill a 'pull' combo.
def fill_pull_combo(combo, branch):
    if branch is None:
        p = u''
        related = []
    else:
        p = urlutils.unescape_for_display(branch.get_parent() or '', 'utf-8')
        related = iter_branch_related_locations(branch)
    fill_combo_with(combo, p, related, iter_saved_pull_locations())


# A helper to fill a combo with values.  Example usage:
# fill_combo_with(combo, u'', iter_saved_pull_locations())
def fill_combo_with(combo, default, *iterables):
    done = set()
    for item in itertools.chain([default], *iterables):
        if item is not None and item not in done:
            done.add(item)
            combo.addItem(item)

# Helper to optionally save the 'pull' location a user specified for
# a branch.
def save_pull_location(branch, location):
    # XXX - todo
    # Intent here is first to check that the location isn't related to
    # the branch (ie, if its the branch parent, do don't remember it).
    # Otherwise, the location gets written to our user-prefs file, using
    # an MRU scheme to avoid runaway growth in the saved locations and keeping
    # the most relevant locations at the top.
    pass


have_pygments = True
try:
    from pygments.styles import get_style_by_name
except ImportError:
    have_pygments = False

if have_pygments:
    style = get_style_by_name("default")

def format_for_ttype(ttype, format):
    if have_pygments and ttype:
        font = format.font()
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
        format.setFont(font)
    return format
