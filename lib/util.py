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
import shlex
import sys
import itertools


from PyQt4 import QtCore, QtGui

from bzrlib.revision import Revision
from bzrlib.config import (
    GlobalConfig,
    config_dir,
    ensure_config_dir_exists,
    config_filename,
    )
from bzrlib import lazy_regex


from bzrlib.plugins.qbzr.lib import MS_WINDOWS

from bzrlib.plugins.qbzr.lib.i18n import gettext, N_

# pyflakes says this is not needed, but it is.
import bzrlib.plugins.qbzr.lib.resources

from bzrlib import errors

from bzrlib.lazy_import import lazy_import
lazy_import(globals(), '''
from bzrlib import (
    osutils,
    urlutils,
    ui,
)
from bzrlib.plugins.qbzr.lib import trace
from bzrlib.workingtree import WorkingTree
from bzrlib.transport import get_transport
from bzrlib.lockdir import LockDir

from bzrlib.plugins.qbzr.lib.compatibility import configobj
''')

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
        dir = osutils.dirname(osutils.safe_unicode(filename))
        transport = get_transport(dir)
        self._lock = LockDir(transport, 'lock')
    
    def _load(self):
        if self._configobj is not None:
            return
        self._configobj = configobj.ConfigObj(self._filename,
                                              encoding='utf-8')

    def set_option(self, name, value, section=None):
        self._load()
        if section is None:
            section = 'DEFAULT'
        if section not in self._configobj:
            self._configobj[section] = {}
        if value:
            if not isinstance(value, (str,unicode)):
                # [bialix 2011/02/11] related to bug #716384: if value is bool
                # then sometimes configobj lost it in the output file
                value = str(value)
            self._configobj[section][name] = value
        else:
            if name in self._configobj[section]:
                del self._configobj[section][name] 

    def get_option(self, name, section=None):
        self._load()
        if section is None:
            section = 'DEFAULT'
        try:
            return self._configobj[section][name]
        except KeyError:
            return None

    def get_option_as_bool(self, name, section=None):
        # imitate the code from bzrlib.config to read option as boolean
        # until we will switch to use bzrlib.config instead of our re-implementation
        value_maybe_str_or_bool = self.get_option(name, section)
        if value_maybe_str_or_bool not in (None, ''):
            value = ui.bool_from_string(value_maybe_str_or_bool)
            return value

    def set_section(self, name, values):
        self._load()
        self._configobj[name] = values

    def get_section(self, name):
        self._load()
        try:
            return self._configobj[name]
        except KeyError:
            return {}

    def save(self):
        ensure_config_dir_exists(os.path.dirname(self._filename))
        self._lock.lock_write()
        try:
            self._load()
            f = open(self._filename, 'wb')
            self._configobj.write(f)
            f.close()
        finally:
            self._lock.unlock()


class QBzrConfig(Config):

    def __init__(self):
        super(QBzrConfig, self).__init__(config_filename())

    def get_bookmarks(self):
        section = self.get_section('BOOKMARKS')
        i = 0
        while True:
            try:
                location = section['bookmark%d' % i]
            except KeyError:
                break
            name = section.get('bookmark%d_name' % i, location)
            i += 1
            yield name, location

    def set_bookmarks(self, bookmarks):
        section = {}
        for i, (name, location) in enumerate(bookmarks):
            section['bookmark%d' % i] = location
            section['bookmark%d_name' % i] = name
        self.set_section('BOOKMARKS', section)

    def add_bookmark(self, name, location):
        bookmarks = list(self.getBookmarks())
        bookmarks.append((name, location))
        self.setBookmarks(bookmarks)
        
    def get_color(self, name, section=None):
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
            
        val = self.get_option(name, section)
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


_global_config = None
def get_global_config():
    global _global_config
    
    if (_global_config is None or
        _check_global_config_filename_valid(_global_config)):
        _global_config = GlobalConfig()
    return _global_config

def _check_global_config_filename_valid(config):
    # before bzr 2.3, there was no file_name attrib, only _get_filename, and
    # checking that would be meaningless.
    if hasattr(config, 'file_name'):
        return not config.file_name == config_filename()
    else:
        return False


_qbzr_config = None
def get_qbzr_config():
    global _qbzr_config
    if (_qbzr_config is None or
        not _qbzr_config._filename == config_filename()):
        _qbzr_config = QBzrConfig()
    return _qbzr_config

def get_branch_config(branch):
    if branch: # we should check boolean branch value to support 2 fake branch cases: branch is None, branch is FakeBranch
        return branch.get_config()
    else:
        return get_global_config()


class _QBzrWindowBase(object):

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
                "accepted()", "do_accept"),
            BTN_CANCEL: (QtGui.QDialogButtonBox.RejectRole,
                "rejected()", "do_reject"),
            BTN_CLOSE: (QtGui.QDialogButtonBox.RejectRole,
                "rejected()", "do_close"),
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

    def _saveSize(self, config):
        name = self._window_name
        is_maximized = int(self.windowState()) & QtCore.Qt.WindowMaximized != 0
        if is_maximized:
            # XXX for some reason this doesn't work
            geom = self.normalGeometry()
            size = geom.width(), geom.height()
        else:
            size = self.width(), self.height()
        config.set_option(name + "_window_size", "%dx%d" % size)
        config.set_option(name + "_window_maximized", is_maximized)
    
    def saveSize(self):
        config = get_qbzr_config()
        self._saveSize(config)
        config.save()

    def restoreSize(self, name, defaultSize):
        self._window_name = name
        config = get_qbzr_config()
        size = config.get_option(name + "_window_size")
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

        is_maximized = config.get_option_as_bool(name + "_window_maximized")
        if is_maximized:
            self.setWindowState(QtCore.Qt.WindowMaximized)
        return config

    def _saveSplitterSizes(self, config, splitter):
        name = self._window_name
        sizes = ':'.join(map(str, splitter.sizes()))
        config.set_option(name + "_splitter_sizes", sizes)

    def restoreSplitterSizes(self, default_sizes=None):
        name = self._window_name
        config = get_qbzr_config()
        sizes = config.get_option(name + "_splitter_sizes")
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

    def do_close(self):
        self.close()

    def operation_blocked(self, message):
        """Use self.operation_blocked in validate methods of q-dialogs
        to show error message about incorrect or missing parameters.

        We can easily switch between show_error and show_warning
        inside this method if we want to change the overall qbzr behavior.
        """
        self.show_warning(message)

    def show_error(self, message):
        QtGui.QMessageBox.critical(self,
            gettext("Error"),
            message)

    def show_warning(self, message):
        QtGui.QMessageBox.warning(self,
            gettext("Warning"),
            message)

    def ask_confirmation(self, message, type='question'):
        """Return True if user selected Yes.
        Optional parameter type selects dialog type. Valid values: question, warning.
        """
        klass = QtGui.QMessageBox.question
        if type == 'warning':
            klass = QtGui.QMessageBox.warning
        button = klass(self,
            gettext("Confirm"),
            message,
            QtGui.QMessageBox.Yes | QtGui.QMessageBox.No,
            QtGui.QMessageBox.No)
        if button == QtGui.QMessageBox.Yes:
            return True
        else:
            return False


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

    def show(self):
        QtGui.QMainWindow.show(self)
        self.raise_()	# Make sure it displays in the foreground


class QBzrDialog(QtGui.QDialog, _QBzrWindowBase):

    def __init__(self, title=None, parent=None, ui_mode=True):
        self.ui_mode = ui_mode
        QtGui.QDialog.__init__(self, parent)
        
        self.set_title_and_icon(title)
        
        self.windows = []
        self.closing = False
        
        # Even though this is a dialog, make it like a window. This allows us
        # to have the best of both worlds, e.g. Default buttons from dialogs,
        # and max and min buttons from window.
        # It also fixes https://bugs.launchpad.net/qbzr/+bug/421039
        self.setWindowFlags(QtCore.Qt.Window)

    def do_accept(self):
        self.accept()

    def do_reject(self):
        self.reject()

    def reject(self):
        self.saveSize()
        QtGui.QDialog.reject(self)

    def show(self):
        QtGui.QMainWindow.show(self)
        self.raise_()	# Make sure it displays in the foreground

throber_movie = None

class ThrobberWidget(QtGui.QWidget):
    """A widget that indicates activity."""

    def __init__(self, parent, timeout=500):
        QtGui.QWidget.__init__(self, parent)
        global throber_movie
        if not throber_movie:
            throber_movie = QtGui.QMovie(":/16x16/process-working.gif")
            throber_movie.start()
        
        self.spinner = QtGui.QLabel("", self)    
        self.spinner.setMovie(throber_movie)
        
        self.message = QtGui.QLabel(gettext("Loading..."), self)
        #self.progress = QtGui.QProgressBar(self)
        #self.progress.setTextVisible (False)
        #self.progress.hide()
        #self.progress.setMaximum(sys.maxint)
        self.transport = QtGui.QLabel("", self)
        for widget in (self.spinner,
                       self.message,
                       #self.progress,
                       self.transport):
            widget.hide()
        
        self.widgets = []
        self.set_layout()
        self.num_show = 0

    def set_layout(self):
        layout = QtGui.QHBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        
        layout.addWidget(self.spinner)
        #layout.addWidget(self.progress)
        layout.addWidget(self.message, 1)
        layout.addWidget(self.transport)
        
        self.widgets.append(self.spinner)
        #self.widgets.append(self.progress)
        self.widgets.append(self.message)
        self.widgets.append(self.transport)

    def hide(self):
        #if self.is_shown:
            #QtGui.QApplication.restoreOverrideCursor()
        self.num_show -= 1
        if self.num_show <= 0:
            self.num_show = 0
            QtGui.QWidget.hide(self)
            for widget in self.widgets:
                widget.hide()
    
    def show(self):
        #QtGui.QApplication.setOverrideCursor(QtCore.Qt.WaitCursor)
        # and show ourselves.
        self.num_show += 1
        QtGui.QWidget.show(self)
        for widget in self.widgets:
            widget.show()
    

class ToolBarThrobberWidget(ThrobberWidget):
    """A widget that indicates activity. Smaller than ThrobberWidget, designed
    for use on a toolbar."""

    def set_layout(self):
        layout = QtGui.QHBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        
        layout.addWidget(self.transport)
        layout.addWidget(self.spinner)
        #layout.addWidget(self.progress)
        #layout.addWidget(self.message, 1)
        
        self.widgets.append(self.spinner)
        #self.widgets.append(self.progress)
        #self.widgets.append(self.message)
        self.widgets.append(self.transport)


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
        dir = unicode(getter())
        if not os.path.isdir(dir):
            dir = ""
        dir = QtGui.QFileDialog.getExistingDirectory(dlg, caption, dir)
        if dir:
            setter(dir)

    dialog.connect(chooser, QtCore.SIGNAL("clicked()"), click_handler)


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
        if branch: # we should check boolean branch value to support 2 fake branch cases: branch is None, branch is FakeBranch
            branch.get_config().set_user_option("encoding", encoding)
    return encoding


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
            s.append(gettext('deleted files'))
        if self.added:
            s.append(gettext('added files'))
        if self.renamed:
            s.append(gettext('renamed files'))
        if self.modified:
            s.append(gettext('modified files'))
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

# A helper to fill a 'pull' combo. Returns the default value.
def fill_pull_combo(combo, branch):
    if branch is None:
        p = u''
        related = []
    else:
        p = url_for_display(branch.get_parent() or '')
        related = iter_branch_related_locations(branch)
    fill_combo_with(combo, p, related, iter_saved_pull_locations())
    return p


# A helper to fill a combo with values.  Example usage:
# fill_combo_with(combo, u'', iter_saved_pull_locations())
def fill_combo_with(combo, default, *iterables):
    done = set()
    for item in itertools.chain([default], *iterables):
        if item is not None and item not in done:
            done.add(item)
            combo.addItem(item)

def show_shortcut_hint(action):
    """Show this action's shortcut, if any, as part of the tooltip.
    
    Make sure to set the shortcut and tooltip *before* calling this.
    """
    shortcut = action.shortcut()
    if shortcut and shortcut.toString():
        toolTip = action.toolTip()
        action.setToolTip("%s (%s)" % (toolTip, shortcut.toString()))

def iter_saved_pull_locations():
    """ Iterate the 'pull' locations we have previously saved for the user.
    """
    config = get_qbzr_config()
    try:
        sect = config.get_section('Pull Locations')
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

    config = get_qbzr_config()
    # and save it to the ini
    section = {}
    for i, save_location in enumerate(existing):
        # Use a 'sortable string' as the ID to save needing to do an int()
        # before sorting (you never know what might end up there if the user
        # edits it)
        key = "%04d" % i
        section[key] = save_location
    config.set_section('Pull Locations', section)
    config.save()


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
    but should rather update the ui themselves. Methods decorated with this
    should detect, and stop if their execution is no longer required.
    
    """
    
    def decorate(*args, **kargs):
        run_in_loading_queue(f, *args, **kargs)
    
    return decorate

def run_in_loading_queue(cur_f, *cur_args, **cur_kargs):
    global loading_queue
    if loading_queue is None:
        loading_queue = []
        try:
            loading_queue.append((cur_f, cur_args, cur_kargs))
            
            while len(loading_queue):
                try:
                    f, args, kargs = loading_queue.pop(0)
                    f(*args, **kargs)
                except:
                    trace.report_exception()
        finally:
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

def get_summary(rev):
    if rev.message is None:
        return gettext('(no message)')
    return rev.get_summary() or gettext('(no message)')

def get_message(rev):
    return rev.message or gettext('(no message)')

def ensure_unicode(s, encoding='ascii'):
    """Convert s to unicode if s is plain string.
    Using encoding for unicode decode.

    In the case when s is not string, return it
    without any changes.
    """
    if isinstance(s, str):
        return s.decode(encoding)
    return s


def open_tree(directory, ui_mode=False,
    _critical_dialog=QtGui.QMessageBox.critical):
    """Open working tree with its root at specified directory or above
    (similar to WorkingTree.open_containing).
    If there is no working tree and ui_mode is True then show GUI dialog
    with error message and None will be returned. Otherwise errors
    (NotBranchError or NoWorkingTree) will be propagated to caller.

    If directory is None then current directory will be used.

    @param _critical_dialog: could be used to provide mock object for testing.
    """
    if directory is None:
        directory = u'.'
    try:
        return WorkingTree.open_containing(directory)[0]
    except errors.NotBranchError:
        if ui_mode:
            _critical_dialog(None,
                gettext("Error"),
                gettext('Not a branch "%s"'
                    ) % os.path.abspath(directory),
                gettext('&Close'))
            return None
        else:
            raise
    except errors.NoWorkingTree:
        if ui_mode:
            _critical_dialog(None,
                gettext("Error"),
                gettext('No working tree exists for "%s"'
                    ) % os.path.abspath(directory),
                gettext('&Close'))
            return None
        else:
            raise


def launchpad_project_from_url(url):
    """If url is a Launchpad code URL, get the project name.

    @return: project name or None
    """
    # The format ought to be one of the following:
    #   scheme://host/~user-id/project-name/branch-name
    #   scheme://host/+branch/project-name
    #   scheme://host/+branch/project-name/series-name
    # there could be distro branches, they are very complex,
    # so we only support upstream branches based on source package
    #   scheme://host/+branch/DISTRO/SOURCEPACKAGE
    #   scheme://host/+branch/DISTRO/SERIES/SOURCEPACKAGE
    #   scheme://host/+branch/DISTRO/POCKET/SOURCEPACKAGE
    #   scheme://host/~USER/DISTRO/SERIES/SOURCEPACKAGE/BRANCHNAME
    DISTROS = ('debian', 'ubuntu')
    from urlparse import urlsplit
    scheme, host, path = urlsplit(url)[:3]
    # Sanity check the host
    if (host in ('bazaar.launchpad.net',
                 'bazaar.launchpad.dev',
                 'bazaar.qastaging.launchpad.net',
                 'bazaar.staging.launchpad.net')):
        parts = path.strip('/').split('/')
        if parts[0].startswith('~'):
            if len(parts) == 3 and parts[1] not in DISTROS:
                # scheme://host/~user-id/project-name/branch-name/
                return parts[1]
            elif len(parts) == 5 and parts[1] in DISTROS:
                # scheme://host/~USER/DISTRO/SERIES/SOURCEPACKAGE/BRANCHNAME
                return parts[-2]
        elif parts[0] in ('%2Bbranch', '+branch'):
            n = len(parts)
            if n >= 2:
                part1 = parts[1]
                if n in (2,3) and part1 not in DISTROS:
                    # scheme://host/+branch/project-name
                    # scheme://host/+branch/project-name/series-name
                    return part1
                elif n in (3,4) and part1 in DISTROS:
                    # scheme://host/+branch/DISTRO/SOURCEPACKAGE
                    # scheme://host/+branch/DISTRO/SERIES/SOURCEPACKAGE
                    # scheme://host/+branch/DISTRO/POCKET/SOURCEPACKAGE
                    return parts[-1]
    return None


def _shlex_split_unicode_linux(unicode_string):
    """Split unicode string to list of unicode arguments."""
    return [unicode(p,'utf8') for p in shlex.split(unicode_string.encode('utf-8'))]

def _shlex_split_unicode_windows(unicode_string):
    """Split unicode string to list of unicode arguments.
    Take care about backslashes as valid path separators.
    """
    utf8_string = unicode_string.replace('\\', '\\\\').encode('utf-8')
    return [unicode(p,'utf8') for p in shlex.split(utf8_string)]

if MS_WINDOWS:
    shlex_split_unicode = _shlex_split_unicode_windows
else:
    shlex_split_unicode = _shlex_split_unicode_linux

def get_icon(name, size=22):
    # TODO: Load multiple sizes
    # TODO: Try load from system theme
    return QtGui.QIcon(":/%dx%d/%s.png" % (size, size, name))


class InfoWidget(QtGui.QFrame):
    def __init__(self, parent=None):
        QtGui.QFrame.__init__(self, parent)
        self.setFrameShape(QtGui.QFrame.StyledPanel)
        
        self.setAutoFillBackground(True)
        self.setBackgroundRole(QtGui.QPalette.ToolTipBase) 
        self.setForegroundRole(QtGui.QPalette.ToolTipText)

# Hackish test for monospace. Run bzr qcat lib/util.py to check.
#888888888888888888888888888888888888888888888888888888888888888888888888888888
#                                                                             8

monospace_font = None
def get_monospace_font():
    global monospace_font
    if monospace_font is None:
        monospace_font = _get_monospace_font()
    return monospace_font

def _get_monospace_font():
    # TODO: Get font from system settings for Gnome, KDE, Mac.
    # (no windows option as far as I am aware)
    # Maybe have our own config setting.
    
    # Get the defaul font size
    size = QtGui.QApplication.font().pointSize()
    
    for font_family in ("Monospace", "Courier New"):
        font = QtGui.QFont(font_family, size)
        # check that this is really a monospace font
        if QtGui.QFontInfo(font).fixedPitch():
            return font
    
    # try use style hints to find font.
    font = QtGui.QFont("", size)
    font.setFixedPitch(True)
    return font

def get_set_tab_width_chars(branch=None, tab_width_chars=None):
    """Function to get the tab width in characters from the configuration.

    @param branch: Use branch.conf as well as bazaar.conf if this is provided.
    @param tab_width_chars: Number of characters to use as tab width: if branch
        is provided, the tab width will be stored in branch.conf

    Both arguments are optional, but if tab_width_chars is provided and branch is
    not, nothing will be done.
    
    @return: Tab width, in characters.
    """
    if tab_width_chars is None:
        config = get_branch_config(branch)
        try:
            tab_width_chars = int(config.get_user_option('tab_width'))
            if tab_width_chars < 0:
                raise TypeError("Invalid tab width")
        except TypeError:
            tab_width_chars = 8
    else:
        if branch:
            branch.get_config().set_user_option("tab_width", str(tab_width_chars))

    return tab_width_chars

def get_tab_width_pixels(branch=None, tab_width_chars=None):
    """Function to get the tab width in pixels based on a monospaced font.

    If tab_width_chars is provided, it is simply converted to a value in pixels.  If
    it is not provided, the configuration is retrieved from bazaar.conf.  If branch is
    provided (and tab_width_chars is not), branch.conf is also checked.

    @param tab_width_chars: Number of characters of tab width to convert to pixels.
    @param branch: Branch to use when retrieving tab width from configuration.
    
    @return: Tab width, in pixels.
    """
    monospacedFont = get_monospace_font()
    char_width = QtGui.QFontMetrics(monospacedFont).width(" ")
    if tab_width_chars is None:
        tab_width_chars = get_set_tab_width_chars(branch=branch)
    return char_width*tab_width_chars
