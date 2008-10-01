# -*- coding: utf-8 -*-
#
# QBzr - Qt frontend to Bazaar commands
# Copyright (C) 2008 Lukáš Lalinský et al.
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
from bzrlib.plugins.qbzr.lib.subprocess import SubProcessDialog
from bzrlib.plugins.qbzr.lib.ui_tag import Ui_TagForm
from bzrlib.plugins.qbzr.lib.util import url_for_display


class TagWindow(SubProcessDialog):

    # indices of actions in action combo box
    IX_CREATE = 0
    IX_REPLACE = 1
    IX_DELETE = 2

    def __init__(self, branch, action=None, tag_name=None, revision=None,
        parent=None, ui_mode=False):

        super(TagWindow, self).__init__(name="tag", ui_mode=ui_mode,
            dialog=True, parent=parent)

        self.ui = Ui_TagForm()
        self.ui.setupUi(self)
        self.last_action = self.ui.cb_action.currentIndex()

        # and add the subprocess widgets.
        for w in self.make_default_layout_widgets():
            self.layout().addWidget(w)
        self.process_widget.hide_progress()

        self.set_branch(branch)

        # setup signals
        QtCore.QObject.connect(self.ui.cb_action,
            QtCore.SIGNAL("currentIndexChanged(int)"),
            self.on_action_changed)
        QtCore.QObject.connect(self.ui.cb_tag,
            QtCore.SIGNAL("currentIndexChanged(int)"),
            self.on_tag_changed)
        QtCore.QObject.connect(self.ui.cb_tag.lineEdit(),
            QtCore.SIGNAL("editingFinished()"),
            self.on_tag_changed)
        # groupbox gets disabled as we are executing.
        QtCore.QObject.connect(self,
                               QtCore.SIGNAL("subprocessStarted(bool)"),
                               self.ui.tag_group,
                               QtCore.SLOT("setDisabled(bool)"))

    def set_branch(self, branch):
        self.branch = branch
        self.tags = branch.tags.get_tag_dict()
        self.revno_map = None
        self.rev_text = {}
        # update ui
        self.ui.branch_location.setText(url_for_display(branch.base))
        self.ui.cb_tag.clear()
        self.ui.cb_tag.addItems(QtCore.QStringList(sorted(self.tags.keys())))
        self.ui.cb_tag.setEditText("")
        self.ui.cb_tag.setCurrentIndex(-1)

    def setup_initial_values(self, action=None, tag_name=None, revision=None):
        pass

    def on_action_changed(self, index):
        self.ui.cb_tag.setEditText("")
        self.ui.cb_tag.setCurrentIndex(-1)
        self.rev_text[self.last_action] = self.ui.rev_edit.text()
        self.ui.rev_edit.setDisabled(index == self.IX_DELETE)
        self.ui.rev_edit.setText(self.rev_text.get(index, ''))
        self.last_action = index
        self.on_tag_changed()

    def on_tag_changed(self, index=None):
        if self.ui.cb_action.currentIndex() == self.IX_DELETE:
            tag = unicode(self.ui.cb_tag.currentText())
            revid = self.tags.get(tag)
            if revid:
                # get revno
                if self.revno_map is None:
                    self.revno_map = self.branch.get_revision_id_to_revno_map()
                rt = self.revno_map.get(revid)
                if rt:
                    rev_str = '.'.join(map(str, rt))
                else:
                    rev_str = 'revid:'+revid
            else:
                rev_str = ''
            self.ui.rev_edit.setText(rev_str)

    def validate(self):
        action = self.ui.cb_action.currentIndex()
        title = self.ui.cb_action.currentText()
        tag = unicode(self.ui.cb_tag.lineEdit().text())
        has_tag = tag in self.tags
        rev = unicode(self.ui.rev_edit.text())
        if not tag:
            QtGui.QMessageBox.critical(self, title,
                gettext('You should specify tag name'),
                gettext('&Close'))
            return False
        if action == self.IX_CREATE and has_tag:
            btn = QtGui.QMessageBox.question(self, title,
                gettext(
                    'Tag "%s" already exists.\n'
                    'Do you want to replace existing tag?'
                    ) % tag,
                gettext('&Replace'), gettext("&Cancel"), '',
                0, 1)
            if btn == 0:    # replace
                action = self.IX_REPLACE
                title = self.ui.cb_action.itemText(action)
            else:   # cancel
                return False
        if action == self.IX_REPLACE and not has_tag:
            btn = QtGui.QMessageBox.question(self, title,
                gettext(
                    'Tag "%s" does not exists yet.\n'
                    'Do you want to create new tag?'
                    ) % tag,
                gettext('Cre&ate'), gettext("&Cancel"), '',
                0, 1)
            if btn == 0:    # create
                action = self.IX_CREATE
                title = self.ui.cb_action.itemText(action)
            else:   # cancel
                return False
        if action == self.IX_DELETE and not has_tag:
            QtGui.QMessageBox.critical(self, title,
                gettext('Tag "%s" does not exists') % tag,
                gettext('&Close'))
            return False
        # create args to run subprocess
        args = ['tag']
        if action != self.IX_CREATE:
            args.append({self.IX_REPLACE: '--force',
                         self.IX_DELETE: '--delete'
                        }[action])
        if action != self.IX_DELETE:
            args.append('--revision')
            args.append(rev or '-1')
        args.append(tag)
        self.args = args    # subprocess uses self.args to run command
        # go!
        return True
