# -*- coding: utf-8 -*-
#
# QBzr - Qt frontend to Bazaar commands
# Copyright (C) 2006 Lukáš Lalinský <lalinsky@gmail.com>
# Porions Copyright (C) 2004, 2005, 2006 by Canonical Ltd 
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

import sys
from PyQt4 import QtCore, QtGui
from bzrlib import bzrdir
from bzrlib.commands import Command, register_command
from bzrlib.option import Option 
from bzrlib.errors import NotVersionedError, BzrCommandError, NoSuchFile
from bzrlib.workingtree import WorkingTree 

class LogWindow(QtGui.QMainWindow):

    def __init__(self, log, location, parent=None):
        QtGui.QMainWindow.__init__(self, parent)

        if location:
            self.setWindowTitle(u"QBzr - Log - %s" % location)
        else:
            self.setWindowTitle(u"QBzr - Log")
        icon = QtGui.QIcon()
        icon.addFile(":/bzr-16.png", QtCore.QSize(16, 16))
        icon.addFile(":/bzr-48.png", QtCore.QSize(48, 48))
        self.setWindowIcon(icon)
        self.resize(QtCore.QSize(710, 580).expandedTo(self.minimumSizeHint()))

        self.centralWidget = QtGui.QWidget(self)
        self.setCentralWidget(self.centralWidget)
        self.vboxlayout = QtGui.QVBoxLayout(self.centralWidget)

        splitter = QtGui.QSplitter(QtCore.Qt.Vertical)

        groupBox = QtGui.QGroupBox(u"Log", splitter)
        splitter.addWidget(groupBox)

        self.changesList = QtGui.QTreeWidget(groupBox)
        self.changesList.setHeaderLabels([u"Rev", u"Date", u"Comitter", u"Message"])
        self.changesList.setRootIsDecorated(False)
        header = self.changesList.header()
        header.resizeSection(0, 30)
        header.resizeSection(1, 110)
        header.resizeSection(2, 190)
        self.connect(self.changesList, QtCore.SIGNAL("itemSelectionChanged()"), self.updateSelection)
        
        vbox1 = QtGui.QVBoxLayout(groupBox)
        vbox1.addWidget(self.changesList)

        self.itemToObj = {}
        for entry in log:
            revno, rev, delta = entry
            item = QtGui.QTreeWidgetItem(self.changesList)
            item.setText(0, str(revno))
            date = QtCore.QDateTime()
            date.setTime_t(int(rev.timestamp))
            item.setText(1, date.toString(QtCore.Qt.LocalDate))
            item.setText(2, rev.committer)
            item.setText(3, rev.message.split("\n")[0])
            self.itemToObj[item] = entry

        groupBox = QtGui.QGroupBox(u"Details", splitter)
        splitter.addWidget(groupBox)

        splitter.setStretchFactor(0, 5)
        splitter.setStretchFactor(1, 1)
        
        gridLayout = QtGui.QGridLayout(groupBox)
        gridLayout.setColumnStretch(0, 0)
        gridLayout.setColumnStretch(1, 3)
        gridLayout.setColumnStretch(2, 1)
        
        gridLayout.addWidget(QtGui.QLabel(u"Revision:", groupBox), 0, 0)
        self.revisionEdit = QtGui.QLineEdit(u"", groupBox)
        self.revisionEdit.setReadOnly(True)
        gridLayout.addWidget(self.revisionEdit, 0, 1)

        gridLayout.addWidget(QtGui.QLabel(u"Parents:", groupBox), 1, 0)
        self.parentsEdit = QtGui.QLineEdit(u"", groupBox)
        self.parentsEdit.setReadOnly(True)
        gridLayout.addWidget(self.parentsEdit, 1, 1)

        gridLayout.addWidget(QtGui.QLabel(u"Message:", groupBox), 2, 0)
        self.messageEdit = QtGui.QTextEdit(u"", groupBox)
        self.messageEdit.setReadOnly(True)
        self.messageDocument = QtGui.QTextDocument()
        self.messageEdit.setDocument(self.messageDocument)
        gridLayout.addWidget(self.messageEdit, 2, 1)

        self.fileList = QtGui.QListWidget(groupBox)
        gridLayout.addWidget(self.fileList, 0, 2, 3, 1)
        
        self.vboxlayout.addWidget(splitter)
        
        self.hboxlayout = QtGui.QHBoxLayout()
        self.hboxlayout.addStretch()

        self.closeButton = QtGui.QPushButton(u"&Close", self)
        self.hboxlayout.addWidget(self.closeButton)

        self.vboxlayout.addLayout(self.hboxlayout)
        
        self.connect(self.closeButton, QtCore.SIGNAL("clicked()"), self.close)

    def anchorClicked(self, url):
        print url
        
    def updateSelection(self):
        item = self.changesList.selectedItems()[0]
        revno, rev, delta = self.itemToObj[item]
        
        self.revisionEdit.setText(rev.revision_id)
        self.parentsEdit.setText(u", ".join(rev.parent_ids))
        self.messageDocument.setPlainText(rev.message)
        
        self.fileList.clear()
        
        for path, _, _ in delta.added:
            item = QtGui.QListWidgetItem(path, self.fileList)
            item.setTextColor(QtGui.QColor("blue"))
            
        for path, _, _, _, _ in delta.modified:
            item = QtGui.QListWidgetItem(path, self.fileList)
            
        for path, _, _ in delta.removed:
            item = QtGui.QListWidgetItem(path, self.fileList)
            item.setTextColor(QtGui.QColor("red"))
            
        for oldpath, _, _, _, _, _ in delta.renamed:
            item = QtGui.QListWidgetItem(path, self.fileList)
            item.setTextColor(QtGui.QColor("purple"))
        
class cmd_qlog(Command):
    """Show log of a branch, file, or directory in a Qt window.

    By default show the log of the branch containing the working directory."""
    
    takes_args = ['location?']
    takes_options = [Option('forward', 
                            help='show from oldest to newest'),
                     'timezone', 
                     'show-ids', 'revision',
                     'log-format',
                     'line', 'long', 
                     Option('message',
                            help='show revisions whose message matches this regexp',
                            type=str),
                     ]
    
    def run(self, location=None, revision=None):
                
        from bzrlib.log import log_formatter, show_log, LogFormatter
        from bzrlib.builtins import get_log_format
        
        # log everything
        file_id = None
        if location:
            # find the file id to log:

            dir, fp = bzrdir.BzrDir.open_containing(location)
            b = dir.open_branch()
            if fp != '':
                try:
                    # might be a tree:
                    inv = dir.open_workingtree().inventory
                except (errors.NotBranchError, errors.NotLocalUrl):
                    # either no tree, or is remote.
                    inv = b.basis_tree().inventory
                file_id = inv.path2id(fp)
        else:
            # local dir only
            # FIXME ? log the current subdir only RBC 20060203 
            dir, relpath = bzrdir.BzrDir.open_containing('.')
            b = dir.open_branch()

        if revision is None:
            rev1 = None
            rev2 = None
        elif len(revision) == 1:
            rev1 = rev2 = revision[0].in_history(b).revno
        elif len(revision) == 2:
            if revision[0].spec is None:
                # missing begin-range means first revision
                rev1 = 1
            else:
                rev1 = revision[0].in_history(b).revno

            if revision[1].spec is None:
                # missing end-range means last known revision
                rev2 = b.revno()
            else:
                rev2 = revision[1].in_history(b).revno
        else:
            raise BzrCommandError('bzr log --revision takes one or two values.')

        # By this point, the revision numbers are converted to the +ve
        # form if they were supplied in the -ve form, so we can do
        # this comparison in relative safety
        if rev1 > rev2:
            (rev2, rev1) = (rev1, rev2)

        class QLogFormatter(LogFormatter):

            def __init__(self):
                LogFormatter.__init__(self, None)
                self.log = []

            def show(self, revno, rev, delta):
                from bzrlib.osutils import format_date
                self.log.append((revno, rev, delta))

        lf = QLogFormatter()

        show_log(b,
                 lf,
                 file_id,
                 verbose=True,
                 start_revision=rev1,
                 end_revision=rev2)
                 
        app = QtGui.QApplication(sys.argv)
        window = LogWindow(lf.log, location)
        window.show()
        app.exec_()

register_command(cmd_qlog)
