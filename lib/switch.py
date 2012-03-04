# -*- coding: utf-8 -*-
#
# QBzr - Qt frontend to Bazaar commands
#
# Contributors:
#  Javier Der Derian <javierder@gmail.com>
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

from bzrlib import errors, osutils

from bzrlib.plugins.qbzr.lib.i18n import gettext
from bzrlib.plugins.qbzr.lib.subprocess import SubProcessDialog
from bzrlib.plugins.qbzr.lib.util import (
    url_for_display,
    QBzrDialog,
    runs_in_loading_queue,
    ThrobberWidget
    )
from bzrlib.plugins.qbzr.lib.uifactory import ui_current_widget
from bzrlib.plugins.qbzr.lib.trace import (
   reports_exception,
   SUB_LOAD_METHOD)


class QBzrSwitchWindow(SubProcessDialog):

    def __init__(self, branch, bzrdir, location, ui_mode = None):

        super(QBzrSwitchWindow, self).__init__(
                                  gettext("Switch"),
                                  name = "switch",
                                  default_size = (400, 400),
                                  ui_mode = ui_mode,
                                  dialog = True,
                                  parent = None,
                                  hide_progress=False,
                                  )

        self.branch = branch

        gbSwitch = QtGui.QGroupBox(gettext("Switch checkout"), self)

        switch_box = QtGui.QFormLayout(gbSwitch)

        branchbase = None

        boundloc = branch.get_bound_location()
        if boundloc is not None:
            label = gettext("Heavyweight checkout:")
            branchbase = branch.base
        else:
            if bzrdir.root_transport.base != branch.bzrdir.root_transport.base:
                label = gettext("Lightweight checkout:")
                boundloc = branch.bzrdir.root_transport.base
                branchbase = bzrdir.root_transport.base
            else:
                raise errors.BzrError("This branch is not checkout.")

        switch_box.addRow(label, QtGui.QLabel(url_for_display(branchbase)))
        switch_box.addRow(gettext("Checkout of branch:"),
                          QtGui.QLabel(url_for_display(boundloc)))
        self.boundloc = url_for_display(boundloc)

        throb_hbox = QtGui.QHBoxLayout()

        self.throbber = ThrobberWidget(self)
        throb_hbox.addWidget(self.throbber)
        self.throbber.hide()
        switch_box.addRow(throb_hbox)

        switch_hbox = QtGui.QHBoxLayout()

        branch_label = QtGui.QLabel(gettext("Switch to branch:"))
        branch_combo = QtGui.QComboBox()   
        branch_combo.setEditable(True)

        self.branch_combo = branch_combo

        if location is not None:
            branch_combo.addItem(osutils.abspath(location))
        elif boundloc is not None:
            branch_combo.addItem(url_for_display(boundloc))

        browse_button = QtGui.QPushButton(gettext("Browse"))
        QtCore.QObject.connect(browse_button, QtCore.SIGNAL("clicked(bool)"), self.browse_clicked)

        switch_hbox.addWidget(branch_label)
        switch_hbox.addWidget(branch_combo)
        switch_hbox.addWidget(browse_button)

        switch_hbox.setStretchFactor(branch_label,0)
        switch_hbox.setStretchFactor(branch_combo,1)
        switch_hbox.setStretchFactor(browse_button,0)

        switch_box.addRow(switch_hbox)

        create_branch_box = QtGui.QCheckBox(gettext("Create Branch before switching"))
        create_branch_box.setChecked(False)
        switch_box.addRow(create_branch_box)
        self.create_branch_box = create_branch_box

        layout = QtGui.QVBoxLayout(self)

        layout.addWidget(gbSwitch)

        layout.addWidget(self.make_default_status_box())
        layout.addWidget(self.buttonbox)
        self.branch_combo.setFocus()

    def show(self):
        QBzrDialog.show(self)
        QtCore.QTimer.singleShot(0, self.initial_load)

    def exec_(self):
        QtCore.QTimer.singleShot(0, self.initial_load)
        return QBzrDialog.exec_(self)

    def _load_branch_names(self):
        branch_combo = self.branch_combo
        repo = self.branch.bzrdir.find_repository()
        if repo is not None:
            if getattr(repo, "iter_branches", None):
                for br in repo.iter_branches():
                    self.processEvents()
                    branch_combo.addItem(url_for_display(br.base))

    @runs_in_loading_queue
    @ui_current_widget
    @reports_exception(type=SUB_LOAD_METHOD)   
    def initial_load(self):
        
        self.throbber.show()
        self._load_branch_names()
        self.throbber.hide()

    def browse_clicked(self):
        if os.path.exists(self.boundloc):
            directory = self.boundloc
        else:
            directory = os.getcwdu()
        fileName = QtGui.QFileDialog.getExistingDirectory(self,
            gettext("Select branch location"),
            directory,
            )
        if fileName:
            self.branch_combo.insertItem(0,fileName)
            self.branch_combo.setCurrentIndex(0)

    def validate(self):
        location = unicode(self.branch_combo.currentText())
        if not location:
            self.operation_blocked(gettext("Branch location not specified."))
            return False
        return True

    def do_start(self):
        location = unicode(self.branch_combo.currentText())
        if self.create_branch_box.isChecked():
            self.process_widget.do_start(None, 'switch', '--create-branch', location)
        else:
            self.process_widget.do_start(None, 'switch', location)
