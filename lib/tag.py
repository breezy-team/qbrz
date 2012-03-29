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
from bzrlib.branch import Branch
from bzrlib import (
    errors,
    )
from bzrlib.plugins.qbzr.lib.i18n import gettext
from bzrlib.plugins.qbzr.lib.subprocess import SubProcessDialog
from bzrlib.plugins.qbzr.lib.ui_tag import Ui_TagForm
from bzrlib.plugins.qbzr.lib.util import url_for_display


class TagWindow(SubProcessDialog):

    # indices of actions in action combo box
    IX_CREATE = 0
    IX_MOVE = 1
    IX_DELETE = 2

    def __init__(self, branch, action=None, tag_name=None, revision=None,
        parent=None, ui_mode=False):
        """Create tag edit window.
        @param  action:     default action (create, move, delete)
        """
        super(TagWindow, self).__init__(name="tag", ui_mode=ui_mode,
            dialog=True, parent=parent)

        self.ui = Ui_TagForm()
        self.ui.setupUi(self)
        # keep this after self.ui.setupUi
        self.restoreSize("tag", (340, 220))
        # and add the subprocess widgets.
        for w in self.make_default_layout_widgets():
            self.layout().addWidget(w)
        self.process_widget.hide_progress()
        self.ui.cb_tag.setFocus()

        self.set_branch(branch)
        self.setup_initial_values(action, tag_name, revision)

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
        QtCore.QObject.connect(self.ui.branch_browse,
            QtCore.SIGNAL("clicked()"),
            self.on_browse)
        QtCore.QObject.connect(self.ui.branch_location,
            QtCore.SIGNAL("editingFinished()"),
            self.on_editing_branch)

    def set_branch(self, branch):
        self.branch = branch
        self.tags = branch.tags.get_tag_dict()
        self.revno_map = None
        # update ui
        self.ui.branch_location.setText(url_for_display(branch.base))
        self.ui.cb_tag.clear()
        self.ui.cb_tag.addItems(QtCore.QStringList(sorted(self.tags.keys(),
                                                          key=unicode.lower)))
        self.ui.cb_tag.setEditText("")
        self.ui.cb_tag.setCurrentIndex(-1)

    def setup_initial_values(self, action=None, tag_name=None, revision=None):
        action_index = {'create': self.IX_CREATE, 'move': self.IX_MOVE,
            'delete': self.IX_DELETE}.get(action)
        if action_index is not None:
            self.ui.cb_action.setCurrentIndex(action_index)
            self.on_action_changed(action_index)
        if tag_name:
            if tag_name not in self.tags:
                self.ui.cb_tag.setCurrentIndex(-1)
            self.ui.cb_tag.setEditText(tag_name)
            self.on_tag_changed()
        if revision and action_index != self.IX_DELETE:
            self.ui.rev_edit.setText(revision[0].user_spec)

    def on_action_changed(self, index):
        self.ui.cb_tag.setEditText("")
        self.ui.cb_tag.setCurrentIndex(-1)
        self.ui.rev_edit.setReadOnly(index == self.IX_DELETE)
        self.ui.rev_edit.setText('')

    def on_tag_changed(self, index=None):
        if self.ui.cb_action.currentIndex() == self.IX_DELETE:
            tag = unicode(self.ui.cb_tag.currentText())
            revid = self.tags.get(tag)
            rev_str = ''
            tooltip = ''
            if revid:
                # get revno
                if self.revno_map is None:
                    # XXX perhaps we need to run this operation in a thread,
                    # because it might take a while for big history
                    self.revno_map = self.branch.get_revision_id_to_revno_map()
                rt = self.revno_map.get(revid)
                if rt:
                    rev_str = '.'.join(map(str, rt))
                else:
                    rev_str = 'revid:'+revid
                    tooltip = rev_str
            self.ui.rev_edit.setText(rev_str)
            self.ui.rev_edit.setToolTip(tooltip)

    def validate(self):
        action = self.ui.cb_action.currentIndex()
        title = self.ui.cb_action.currentText()
        tag = unicode(self.ui.cb_tag.lineEdit().text())
        has_tag = tag in self.tags
        rev = unicode(self.ui.rev_edit.text())
        if not tag:
            self.operation_blocked(gettext('You should specify tag name'))
            return False
        if action == self.IX_CREATE and has_tag:
            if self.ask_confirmation(gettext(
                    'Tag "%s" already exists.\n'
                    'Do you want to move existing tag?'
                    ) % tag):
                # move
                action = self.IX_MOVE
                title = self.ui.cb_action.itemText(action)
            else:   # cancel
                return False
        if action == self.IX_MOVE and not has_tag:
            if self.ask_confirmation(gettext(
                    'Tag "%s" does not exists yet.\n'
                    'Do you want to create new tag?'
                    ) % tag):
                # create
                action = self.IX_CREATE
                title = self.ui.cb_action.itemText(action)
            else:   # cancel
                return False
        if action == self.IX_DELETE and not has_tag:
            self.operation_blocked(gettext('Tag "%s" does not exists') % tag)
            return False
        # create args to run subprocess
        args = ['tag']
        args.append('--directory')
        args.append(unicode(self.ui.branch_location.text()))
        if action != self.IX_CREATE:
            args.append({self.IX_MOVE: '--force',
                         self.IX_DELETE: '--delete'
                        }[action])
        if action != self.IX_DELETE:
            args.append('--revision')
            args.append(rev or '-1')
        args.append(tag)
        self.args = args    # subprocess uses self.args to run command
        # go!
        return True

    def on_browse(self):
        # browse button clicked
        directory = QtGui.QFileDialog.getExistingDirectory(self,
            gettext('Select branch location'),
            self.ui.branch_location.text())
        self._try_to_open_branch(directory)

    def on_editing_branch(self):
        self._try_to_open_branch(self.ui.branch_location.text())

    def _try_to_open_branch(self, location):
        if location:
            location = unicode(location)
            try:
                branch = Branch.open_containing(location)[0]
            except errors.NotBranchError:
                QtGui.QMessageBox.critical(self,
                    gettext('Error'),
                    gettext('Not a branch:\n%s') % location,
                    gettext('&Close'))
                return
            self.set_branch(branch)

    @staticmethod
    def action_from_options(force=None, delete=None):
        action = 'create'
        if force:
            action = 'move'
        if delete:
            action = 'delete'
        return action


class CallBackTagWindow(TagWindow):

    def __init__(self, branch, closing_function, action=None, tag_name=None, revision=None,
        parent=None, ui_mode=False):
        super(CallBackTagWindow, self).__init__(branch, action=action,
            tag_name=tag_name, revision=revision,
            parent=parent, ui_mode=ui_mode)
        self.closing_function = closing_function

    def closeEvent(self, event):
        super(CallBackTagWindow, self).closeEvent(event);
        if self.closing_function:
            self.closing_function()
