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

from bzrlib.revision import Revision
from bzrlib.config import (
    GlobalConfig,
    IniBasedConfig,
    config_dir,
    ensure_config_dir_exists,
    )
from bzrlib import (
    lazy_regex,
    osutils,
    urlutils,
    )
from bzrlib.util.configobj import configobj

from bzrlib.plugins.qbzr.lib import trace
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
            self._configobj[section] = {}
        self._configobj[section][name] = value

    def getOption(self, name, section=None):
        self._load()
        if section is None:
            section = 'DEFAULT'
        try:
            return self._configobj[section][name]
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
        
    def getColor(self, name, section=None):
        """
          Get a color entry from the config file.
          Color entries have the syntax:
            name = R, G, B
          Where the color components are integers in the range 0..255.
          
          Colors are returned as QtGui.QColor.
          
          If input is erroneous, ErrorValue exception is raised.
          
          e.g.
            replace_fill = 255, 0, 128
        """
        #utility functions.
        if None == section:
          name_str = '[DEFAULT]:' + name
        else:
          name_str = "[" + section + "]:" + name
          
        color_format_err_msg = lambda given:\
            "Illegal color format for " + name_str +\
            ". Given '"+ given + "' expected '<red>, <green>, <blue>'."
            
        color_range_err_msg = lambda given:\
            "Color components for " + name_str +\
            " should be in the range 0..255 only. Given: "+ given +"."
            
        val = self.getOption(name, section)
        if None == val:
          return None
          
        if list != type(val):
          raise ValueError(color_format_err_msg(val))
        if 3 != len(val) or not \
          reduce(lambda x,y: x and y.isdigit(), val, True):
              raise ValueError(color_format_err_msg(", ".join(val)))
          
        #Being here guarantees that color_value is a list
        #of three elements that represent numbers.
        color_components = map(int, val)
        if not reduce(lambda x,y: x and y < 256, color_components, True):
            raise ValueError(
              color_range_err_msg(", ".join(val)))
            
        #Now we know the given color is safe to use.
        return QtGui.QColor(*color_components)


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

class _QBzrWindowBase:

    def set_title(self, title=None):
        if title:
            if isinstance(title, basestring):
                self.setWindowTitle(title)
            elif isinstance(title, (list, tuple)):
                self.setWindowTitle(" - ".join(title))

    def set_title_and_icon(self, title=None):
        """Set window title (from string or list) and bzr icon"""
        self.set_title(title)
        icon = QtGui.QIcon()
        icon.addFile(":/bzr-16.png", QtCore.QSize(16, 16))
        icon.addFile(":/bzr-32.png", QtCore.QSize(32, 32))
        icon.addFile(":/bzr-48.png", QtCore.QSize(48, 48))
        self.setWindowIcon(icon)

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
        buttonbox = QtGui.QDialogButtonBox(self)
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
        if size:
            size = QtCore.QSize(size[0], size[1])
            self.resize(size.expandedTo(self.minimumSizeHint()))
        self._restore_size = size

        is_maximized = config.get_user_option(name + "_window_maximized")
        if is_maximized in ("True", "1"):
            self.setWindowState(QtCore.Qt.WindowMaximized)
        return config

    def saveSplitterSizes(self):
        name = self._window_name
        config = QBzrGlobalConfig()
        sizes = ':'.join(map(str, self.splitter.sizes()))
        config.set_user_option(name + "_splitter_sizes", sizes)

    def restoreSplitterSizes(self, default_sizes=None):
        name = self._window_name
        config = QBzrGlobalConfig()
        sizes = config.get_user_option(name + "_splitter_sizes")
        n = len(self.splitter.sizes())
        if sizes:
            sizes = map(int, sizes.split(':'))
            if len(sizes) != n:
                sizes = None
        if not sizes and default_sizes and len(default_sizes) == n:
            sizes = default_sizes
        if sizes:
            self.splitter.setSizes(sizes)

    def closeEvent(self, event):
        self.closing = True
        self.saveSize()
        for window in self.windows:
            if window.isVisible():
                window.close()
        event.accept()

    # custom signal slots.
    def linkActivated(self, target):
        """Sent by labels or other rich-text enabled widgets when a link
        is clicked.
        """
        # Our help links all are of the form 'bzrtopic:topic-name'
        scheme, link = unicode(target).split(":", 1)
        if scheme != "bzrtopic":
            raise RuntimeError, "unknown scheme"
        from bzrlib.plugins.qbzr.lib.help import show_help
        show_help(link, self)
    
    def processEvents(self, flags=QtCore.QEventLoop.AllEvents):
        QtCore.QCoreApplication.processEvents(flags)
        if self.closing:
            raise trace.StopException()

class QBzrWindow(QtGui.QMainWindow, _QBzrWindowBase):

    def __init__(self, title=None, parent=None, centralwidget=None, ui_mode=True):
        QtGui.QMainWindow.__init__(self, parent)
        self.ui_mode = ui_mode

        self.set_title_and_icon(title)

        if centralwidget is None:
            centralwidget = QtGui.QWidget(self)
        self.centralwidget = centralwidget
        self.setCentralWidget(self.centralwidget)
        self.windows = []
        self.closing = False

class QBzrDialog(QtGui.QDialog, _QBzrWindowBase):

    def __init__(self, title=None, parent=None, ui_mode=True):
        self.ui_mode = ui_mode
        QtGui.QDialog.__init__(self, parent)
        
        self.set_title_and_icon(title)
        
        self.windows = []
        self.closing = False

throber_movie = None

class ThrobberWidget(QtGui.QWidget):
    """A window that displays a simple throbber over its parent."""

    def __init__(self, parent, timeout=500):
        QtGui.QWidget.__init__(self, parent)
        self.create_ui()
        self.num_show = 0
        
        
        # create a timer that displays our window after the timeout.
        #QtCore.QTimer.singleShot(timeout, self.show)

    def create_ui(self):
        # a couple of widgets
        layout = QtGui.QHBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        
        self.spinner = QtGui.QLabel("", self)    
        global throber_movie
        if not throber_movie:
            throber_movie = QtGui.QMovie(":/16x16/process-working.gif")
            throber_movie.start()
        self.spinner.setMovie(throber_movie)
        
        self.message = QtGui.QLabel(gettext("Loading..."), self)
        #self.progress = QtGui.QProgressBar(self)
        #self.progress.setTextVisible (False)
        #self.progress.hide()
        #self.progress.setMaximum(sys.maxint)
        self.transport = QtGui.QLabel("", self)
        
        layout.addWidget(self.spinner)
        #layout.addWidget(self.progress)
        layout.addWidget(self.message, 1)
        layout.addWidget(self.transport)

    def hide(self):
        #if self.is_shown:
            #QtGui.QApplication.restoreOverrideCursor()
        self.num_show -= 1
        if self.num_show <= 0:
            self.num_show = 0
            QtGui.QWidget.hide(self)

    def show(self):
        #QtGui.QApplication.setOverrideCursor(QtCore.Qt.WaitCursor)
        # and show ourselves.
        QtGui.QWidget.show(self)
        self.num_show += 1

# Helpers for directory pickers.
# We use these items both as 'flags' and as titles!
# A directory picker used to select a 'pull' location.
DIRECTORYPICKER_SOURCE = N_("Select Source Directory")
# A directory picker used to select a destination
DIRECTORYPICKER_TARGET = N_("Select Target Directory")

def hookup_directory_picker(dialog, chooser, target, chooser_type):
    """An inline handler that serves as a 'link' between the widgets.
    @param  dialog:     dialog window object
    @param  chooser:    usually 'Browse' button in a dialog
    @param  target:     QLineEdit or QComboBox where location will be shown
    @param  chooser_type:   caption string for directory selector dialog
    """
    caption = gettext(chooser_type)
    def click_handler(dlg=dialog, chooser=chooser, target=target, caption=caption):
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

    dialog.connect(chooser, QtCore.SIGNAL("clicked()"), click_handler)


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


def format_revision_html(rev, search_replace=None, show_timestamp=False):
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

    if show_timestamp:
        props.append((gettext("Date:"), format_timestamp(rev.timestamp)))

    props.append((gettext("Committer:"), htmlize(rev.committer)))
    author = rev.properties.get('author')
    if author:
        props.append((gettext("Author:"), htmlize(author)))
    else:
        authors = rev.properties.get('authors')
        if authors:
            for author in authors.split('\n'):
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
    return string.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;").replace("\"", "&quot;")


def is_valid_encoding(encoding):
    import codecs
    try:
        codecs.lookup(encoding)
    except LookupError:
        return False
    return True


def get_set_encoding(encoding, branch):
    """Return encoding value from branch config if encoding is None,
    otherwise store encoding value in branch config.
    """
    if encoding is None:
        config = get_branch_config(branch)
        encoding = config.get_user_option("encoding") or 'utf-8'
        if not is_valid_encoding(encoding):
            from bzrlib.trace import note
            note(('NOTE: Invalid encoding value in branch config: %s\n'
                'utf-8 will be used instead') % encoding)
            encoding = 'utf-8'
    else:
        if branch is not None:
            branch.get_config().set_user_option("encoding", encoding)
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
            yield url_for_display(location)

# A helper to fill a 'pull' combo.
def fill_pull_combo(combo, branch):
    if branch is None:
        p = u''
        related = []
    else:
        p = url_for_display(branch.get_parent() or '')
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


def iter_saved_pull_locations():
    """ Iterate the 'pull' locations we have previously saved for the user.
    """
    config = QBzrConfig()
    try:
        sect = config.getSection('Pull Locations')
    except KeyError:
        return []
    items = sorted(sect.items())
    return [i[1] for i in items]


def save_pull_location(branch, location):
    """ Helper to optionally save the 'pull' location a user specified for
    a branch. Uses an MRU scheme to avoid runaway growth in the saved locations
    and keeping the most relevant locations at the top.

    The location is *not* saved if:

    * It is related to a branch (ie, the parent)
    * It is a directory
    """
    if branch is not None and location in iter_branch_related_locations(branch):
        return
    if os.path.isdir(location):
        return
    existing = list(iter_saved_pull_locations())
    try:
        existing.remove(location)
    except ValueError:
        pass
    existing.insert(0, location)
    # XXX - the number to save should itself be a preference???
    max_items = 20
    existing = existing[:max_items]

    config = QBzrConfig()
    # and save it to the ini
    section = {}
    for i, save_location in enumerate(existing):
        # Use a 'sortable string' as the ID to save needing to do an int()
        # before sorting (you never know what might end up there if the user
        # edits it)
        key = "%04d" % i
        section[key] = save_location
    config.setSection('Pull Locations', section)
    config.save()


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


def url_for_display(url):
    """Return human-readable URL or local path for file:/// URLs.
    Wrapper around bzrlib.urlutils.unescape_for_display
    """
    if not url:
        return url
    return urlutils.unescape_for_display(url, 'utf-8')


def is_binary_content(lines):
    """Check list of lines for binary content
    (i.e. presence of 0x00 byte there).
    @return: True if 0x00 byte found.
    """
    for s in lines:
        if '\x00' in s:
            return True
    return False

class BackgroundJob(object):
    
    def __init__(self, parent):
        self.is_running = False
        self.stoping = False
        self.parent = parent
        self.restart_timeout = None
    
    def run(self):
        pass
    
    def run_wrapper(self):
        try:
            self.run()
        except:
            self.parent.report_exception()
        self.is_running = False
        
        if self.restart_timeout:
            self.start(self.restart_timeout)
    
    def restart(self, timeout=0):
        self.restart_timeout = timeout
        raise trace.StopException()
    
    def start(self, timeout=0):
        if not self.is_running:
            self.is_running = True
            self.stoping = False
            QtCore.QTimer.singleShot(timeout, self.run_wrapper)
    
    def stop(self):
        self.stoping = True

    def processEvents(self, flags=QtCore.QEventLoop.AllEvents):
        self.parent.processEvents(flags)
        if self.stoping:
            self.stoping = False
            raise trace.StopException()

loading_queue = None

def runs_in_loading_queue(f):
    """Methods decorated with this will not run at the same time, but will be
    queued. Methods decorated with this will not be able to return results,
    but should rather update the ui themselfs. Methods decorated with this
    should detect, and stop if their execution is no longer requires.
    
    """
    
    def decorate(*args, **kargs):
        run_in_loading_queue(f, *args, **kargs)
    
    return decorate

def run_in_loading_queue(cur_f, *cur_args, **cur_kargs):
    global loading_queue
    if loading_queue is None:
        loading_queue = []
        loading_queue.append((cur_f, cur_args, cur_kargs))
        
        while len(loading_queue):
            f, args, kargs = loading_queue.pop(0)
            f(*args, **kargs)
        
        loading_queue = None
    else:
        loading_queue.append((cur_f, cur_args, cur_kargs))


def get_apparent_authors_new(rev):
    return rev.get_apparent_authors()

def get_apparent_authors_old(rev):
    return [rev.properties.get('author', rev.committer)]

if hasattr(Revision, 'get_apparent_authors'):
    get_apparent_authors = get_apparent_authors_new
else:
    get_apparent_authors = get_apparent_authors_old


def get_apparent_author(rev):
    return ', '.join(get_apparent_authors(rev))


def get_apparent_author_name(rev):
    return ', '.join(map(extract_name, get_apparent_authors(rev)))
