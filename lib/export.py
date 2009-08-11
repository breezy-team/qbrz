# -*- coding: utf-8 -*-
#
# QBzr - Qt frontend to Bazaar commands
#
# Contributors:
#  Javier Derderian <javierder@gmail.com>
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

from bzrlib import (
    errors,
    export,
    osutils,
    )
from bzrlib.plugins.qbzr.lib.i18n import gettext
from bzrlib.plugins.qbzr.lib.subprocess import SubProcessDialog
from bzrlib.plugins.qbzr.lib.util import url_for_display


class QBzrExportDialog(SubProcessDialog):

    FORMATS = { # key is archive format, value is tuple of accepted extensions
        'tar': ('tar',),
        'tbz2': ('tar.bz2', 'tbz2'),
        'tgz': ('tar.gz', 'tgz'),
        'zip': ('zip',),
        }

    def __init__(self, dest=None, branch=None, ui_mode=False, parent=None):
        """Create export dialog.
        @param  dest:   path to export to (either archive name or directory).
        @param  branch: exported branch.
        @param  ui_mode:    does dialog should stay on the screen after
            operation completed successfully.
        @param  parent: parent window.
        """
        title = gettext("Export")
        super(QBzrExportDialog, self).__init__(
                                  title,
                                  name = "export",
                                  default_size = (400, 400),
                                  ui_mode = ui_mode,
                                  dialog = True,
                                  parent = parent,
                                  hide_progress=False,
                                  )

        self.branch = branch
        
        gbExportDestination = QtGui.QGroupBox(gettext("Export"), self)
        vboxExportDestination = QtGui.QVBoxLayout(gbExportDestination)
        vboxExportDestination.addStrut(0)
        
        info_hbox = QtGui.QHBoxLayout()
        info_label = QtGui.QLabel(gettext("Branch: %s") % url_for_display(branch.base))
        info_hbox.addWidget(info_label)
        
        vboxExportDestination.addLayout(info_hbox)
        
        exportarch_radio = QtGui.QRadioButton("Export as archive")
        exportarch_radio.setChecked(True)
        self.exportarch_radio = exportarch_radio 
        vboxExportDestination.addWidget(exportarch_radio)
        locationfil_hbox = QtGui.QHBoxLayout()        
        locationfil_label = QtGui.QLabel(gettext("Location:"))
        locationfil_edit = QtGui.QLineEdit()
        
        self.locationfil_edit = locationfil_edit
        self.locationfil_edit = locationfil_edit # to allow access from another function     
        browsefil_button = QtGui.QPushButton(gettext("Browse"))
        QtCore.QObject.connect(browsefil_button,
                               QtCore.SIGNAL("clicked(bool)"),
                               self.browsefil_clicked)
        QtCore.QObject.connect(locationfil_edit,
                               QtCore.SIGNAL("editingFinished()"),
                               self.update_root_n_format)
        
        locationfil_hbox.addSpacing(25)
        locationfil_hbox.addWidget(locationfil_label)
        locationfil_hbox.addWidget(locationfil_edit)
        locationfil_hbox.addWidget(browsefil_button)
        
        locationfil_hbox.setStretchFactor(locationfil_label,0)
        locationfil_hbox.setStretchFactor(locationfil_edit,1)
        locationfil_hbox.setStretchFactor(browsefil_button,0)
        
        vboxExportDestination.addLayout(locationfil_hbox)
        
        folder_hbox = QtGui.QHBoxLayout()
        folder_hbox.addSpacing(25)
        folder_label = QtGui.QLabel(gettext("Root directory name:"))
        folder_edit = QtGui.QLineEdit()
        self.folder_edit = folder_edit
        
        folder_hbox.addWidget(folder_label)
        folder_hbox.addWidget(folder_edit)
        
        vboxExportDestination.addLayout(folder_hbox)
        
        format_hbox = QtGui.QHBoxLayout()
        format_label = QtGui.QLabel(gettext("Archive type:"))
        format_combo = QtGui.QComboBox()

        for ix, k in enumerate(sorted(self.FORMATS.keys())):
            format_combo.insertItem(ix, k)
        self.format_combo = format_combo
        
        format_hbox.addSpacing(25)
        format_hbox.addWidget(format_label)
        format_hbox.addWidget(format_combo)
        format_hbox.setStretchFactor(format_label,0)
        format_hbox.setStretchFactor(format_combo,1)
        
        vboxExportDestination.addLayout(format_hbox)
        
        exportdir_radio = QtGui.QRadioButton("Export as directory")
        self.exportdir_radio = exportdir_radio
        vboxExportDestination.addWidget(exportdir_radio)
        
        locationdir_hbox = QtGui.QHBoxLayout()        
        locationdir_edit = QtGui.QLineEdit()
        self.locationdir_edit = locationdir_edit
        self.locationdir_edit = locationdir_edit # to allow access from another function     
        browsedir_button = QtGui.QPushButton(gettext("Browse"))
        QtCore.QObject.connect(browsedir_button, QtCore.SIGNAL("clicked(bool)"), self.browsedir_clicked)
                    
        locationdir_hbox.addSpacing(25)
        locationdir_hbox.addWidget(locationdir_edit)
        locationdir_hbox.addWidget(browsedir_button)
    
        locationdir_hbox.setStretchFactor(locationdir_edit,1)
        locationdir_hbox.setStretchFactor(browsedir_button,0)
        
        vboxExportDestination.addLayout(locationdir_hbox)

        gbExportOptions = QtGui.QGroupBox(gettext("Options"), self)
        
        vbxExportOptions = QtGui.QVBoxLayout(gbExportOptions)
        
        revisions_box = QtGui.QGridLayout()

        revisions_label = QtGui.QLabel(gettext("Revision:"))
        revisions_tip = QtGui.QRadioButton("Branch tip")
        revisions_tip.setChecked(True)
        self.revisions_tip = revisions_tip
        revisions_box.addWidget(revisions_label,0,0)
        revisions_box.addWidget(revisions_tip,0,1)

        revisions_other = QtGui.QRadioButton("Other")
        self.revisions_other = revisions_other
        
        revisions_edit = QtGui.QLineEdit()
        self.revisions_edit = revisions_edit
        
        revisions_box.addWidget(revisions_other,1,1)
        revisions_box.addWidget(revisions_edit,1,2)
        
        vbxExportOptions.addLayout(revisions_box)

        format_box = QtGui.QGridLayout()

        format_canonical = QtGui.QCheckBox("Apply content filters to files")
        self.format_canonical = format_canonical
        format_box.addWidget(format_canonical,0,0)
        
        vbxExportOptions.addLayout(format_box)

        layout = QtGui.QVBoxLayout(self)

        self.splitter = QtGui.QSplitter(QtCore.Qt.Vertical)
        
        self.splitter.addWidget(gbExportDestination)
        self.splitter.addWidget(gbExportOptions)

        self.splitter.addWidget(self.make_default_status_box())
        
        self.splitter.setStretchFactor(0, 10)
        self.restoreSplitterSizes([150, 150])
        
        layout.addWidget(self.splitter)
        layout.addWidget(self.buttonbox)

        QtCore.QObject.connect(self,
                               QtCore.SIGNAL("disableUi(bool)"),
                               gbExportDestination,
                               QtCore.SLOT("setDisabled(bool)"))
        QtCore.QObject.connect(self,
                               QtCore.SIGNAL("disableUi(bool)"),
                               gbExportOptions,
                               QtCore.SLOT("setDisabled(bool)"))

        locationfil_edit.setFocus()
        if dest is not None:
            if os.path.isdir(dest) or self.detect_format(dest) is None:
                locationdir_edit.setText(osutils.abspath(dest))
                locationdir_edit.setFocus()
                exportdir_radio.setChecked(True)   
            else:
                locationfil_edit.setText(osutils.abspath(dest))
                self.update_root_n_format()
                exportarch_radio.setChecked(True)

    def detect_format(self, path):
        """Return archive type or None."""
        for k, v in self.FORMATS.iteritems():
            for i in v:
                if path.endswith(i):
                    return k
        return None

    def update_root_n_format(self):
        path = unicode(self.locationfil_edit.text())
        format = self.detect_format(path)
        if format is not None:
            ix = sorted(self.FORMATS.keys()).index(format)
            self.format_combo.setCurrentIndex(ix)
        self.folder_edit.setText(export.get_root_name(path))

    def browsedir_clicked(self):
        fileName = QtGui.QFileDialog.getExistingDirectory(self, ("Select save location"));
        if fileName != None:
            self.locationdir_edit.setText(fileName)
            self.exportdir_radio.setChecked(True)
                
    def browsefil_clicked(self):
        fileName = QtGui.QFileDialog.getSaveFileName(self, ("Select save location"));
        if fileName != None:
            self.locationfil_edit.setText(fileName)   
            self.update_root_n_format()
            self.exportarch_radio.setChecked(True)

    def validate(self):
        if self.exportarch_radio.isChecked():
            location = unicode(self.locationfil_edit.text())
            if location == "":
                raise errors.BzrCommandError("Export location is invalid")
        elif self.exportdir_radio.isChecked():
            location = unicode(self.locationdir_edit.text())
            if location == "":
                raise errors.BzrCommandError("Export location is invalid")        
        
        if self.revisions_other.isChecked():
            if str(self.revisions_edit.text()) == "":
                raise errors.BzrCommandError("Export revision is invalid")
        return True

    def do_start(self):
        args = ['export']

        if self.exportarch_radio.isChecked():
            location = unicode(self.locationfil_edit.text())
            format = str(self.format_combo.currentText())
            root = unicode(self.folder_edit.text())
            if root:
                args.append("--root=%s" % root)
            else:
                args.append("--root=")
        else:
            location = unicode(self.locationdir_edit.text())
            format = 'dir'
        args.append(location)
        args.append("--format=%s" % format)

        branch_location = url_for_display(self.branch.base)
        args.append(branch_location)

        if self.revisions_tip.isChecked():
            args.append("--revision=-1")
        else:
            revision = unicode(self.revisions_edit.text())
            args.append("--revision=%s" % revision)

        if self.format_canonical.isChecked():
            args.append("--filters")

        self.process_widget.do_start(None, *args)

    def saveSize(self):
        SubProcessDialog.saveSize(self)
        self.saveSplitterSizes()
