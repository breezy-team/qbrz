# -*- coding: utf-8 -*-
#
# QBzr - Qt frontend to Bazaar commands
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

from PyQt4 import QtCore, QtGui
from bzrlib.plugins.qbzr.lib.i18n import gettext
from bzrlib.plugins.qbzr.lib.util import QBzrWindow

from bzrlib.help import HelpIndices
from bzrlib.errors import NoHelpTopic
try:
    from docutils.core import publish_string
    from docutils.writers.html4css1 import Writer as BaseHTMLWriter
    have_docutils = True
except ImportError:
    have_docutils = False

if have_docutils:
    # We run into issues in Windows binaries where docutils may be in a .zip
    # file, so template and .css files can't be located.  This is OK for now,
    # as the HTML we generate is so basic we don't need stylesheets.
    class CustomWriter(BaseHTMLWriter):
        # This is the context of template.txt from distutils.
        template = """%(head_prefix)s
            %(head)s
            %(stylesheet)s
            %(body_prefix)s
            %(body_pre_docinfo)s
            %(docinfo)s
            %(body)s
            %(body_suffix)s
            """

        def apply_template(self):
            # Docutils expects to find this on disk, but its not there
            subs = self.interpolation_dict()
            return self.template % subs


def get_help_topic_as_html(topic):
    topics = HelpIndices()
    try:
        results = topics.search(topic)
    except NoHelpTopic:
        tpl = gettext("No help can be found for <i>%s</i>")
        return tpl % topic

    # assert len(results)==1, "what does more than one result mean?"
    # An example of when one might get more than one result, is if you have
    # bzrtools plugin install, you will get a second result for it command,
    # if you search for "Branches". We (like bzr help) only want to show the
    # first result.
    
    index, topic = results[0]
    if have_docutils:
        # we can make pretty HTML on the fly
        text = topic.get_help_text(plain=False)
        html = publish_string(text, writer=CustomWriter(),
                              settings_overrides={'stylesheet': None,
                                                  'stylesheet_path': None})
    else:
        # No docutils - we don't try too hard here - installing docutils is
        # easy!  But we do try and make the line-breaks correct at least.
        text = topic.get_help_text(plain=True)
        bits = ['''<p><small>(Please install the Python <i>docutils</i> package for
                improved formatting)</p></small>''']
        bits.append('<pre>%s</pre>' % text)
        html = ' '.join(bits)
    return html


class QBzrHelpWindow(QBzrWindow):

    def __init__(self, parent=None):
        """Create help window.
        @param  parent:   If None, a normal top-level window will be opened.
                          If not None, a 'tool' style window will be opened, be
                          'always on top' of the parent and have no taskbar
                          entry.
        """
        if parent is None:
            # a normal window.
            window_id = "help"
            default_size = (780, 580)
        else:
            # a smallish tooltop window.
            window_id = "help-popup"
            default_size = (500, 400)
        QBzrWindow.__init__(self, [gettext("Help")], parent,
                            centralwidget=QtGui.QTextBrowser())
        self.restoreSize(window_id, default_size)
        if parent is not None:
            # make it a tool window for the parent.
            self.setWindowFlags(QtCore.Qt.Tool)
        # Without this, the window object remains alive even after its closed.
        # There's no good reason for that...
        self.setAttribute(QtCore.Qt.WA_DeleteOnClose)

    def move_next_to(self, parent):
        """Move next to a parent window so we aren't obscuring any widgets"""

        # We move to the right of the parent if room for the window to be
        # full visible on the same screen as the parent.
        # Get the geometry for the screen holding the parent.
        desktop = QtGui.QApplication.desktop()
        geo = desktop.screenGeometry(parent)

        pt = parent.pos()
        parent_size = parent.size()
        my_size = self.size()
        new_pt = QtCore.QPoint(pt.x()+parent_size.width()+15, pt.y())
        if geo.contains(QtCore.QRect(new_pt, my_size)):
            self.move(new_pt)
        else:
            # see if we can make it fit on the left.
            new_pt = QtCore.QPoint(pt.x()-my_size.width()-15, pt.y())
            if geo.contains(QtCore.QRect(new_pt, my_size)):
                self.move(new_pt)
            else:
                # coulnd't fit it to the left *or* right - give up.
                pass

    def load_help_topic(self, topic):
        html = get_help_topic_as_html(topic)
        self.centralwidget.setHtml(html)


def show_help(topic, parent=None):
    """Create a help window displaying the specified topic.
    
    If a parent is given, the window will be a 'tool' window for the parent,
    otherwise a normal MainWindow.
    """
    # find an existing one with the same parent.
    for window in QtGui.QApplication.topLevelWidgets():
        if isinstance(window, QBzrHelpWindow) and window.parentWidget()==parent:
            break
    else:
        # create a new one.
        window = QBzrHelpWindow(parent)

    window.load_help_topic(topic)
    # If a parent is specified and the window isn't visible, move it next to
    # the parent before displaying it.  If the window is visible, its probably
    # exactly where the user wants it already...
    if parent is not None and not window.isVisible():
        window.move_next_to(parent)
    window.show()
    return window
