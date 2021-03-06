# Copyright (C) 2009 Canonical Ltd
#
# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation; either version 2 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program; if not, write to the Free Software
# Foundation, Inc., 59 Temple Place, Suite 330, Boston, MA  02111-1307  USA


from PyQt5 import QtGui, QtWidgets
from PyQt5.QtCore import Qt


class QBzrConditionalDataView(QtWidgets.QFrame):
    """A list/table/tree with a label.

    Only the label is shown when the data model is empty.
    """

    def __init__(self, type, listmode_or_headers, label_text,
            details, parent=None):
        """Construct the view.

        :param type: one of list, table, tree
        :param listmode_or_headers: For lists, set the initial list view
          mode: True => list, False => icon.
          For tables and trees, the list of headers.
        :param label_text: text for label. May contain %(rows)d to substitute
          the row count.
        :param details: if non-None, a QWidget to show in a details panel.
        :param parent: parent widget
        """
        QtWidgets.QFrame.__init__(self, parent)

        # Build the model & view for the data
        self._type = type
        columns = listmode_or_headers
        if type == 'list':
            self._view = QtWidgets.QListView()
            self._view.setSectionResizeMode(QtWidgets.QListView.Adjust)
            self._view.setWrapping(True)
            if listmode_or_headers:
                self._view.setViewMode(QtWidgets.QListView.ListMode)
            else:
                self._view.setViewMode(QtWidgets.QListView.IconMode)
            columns = ['Name']
            # TODO: we could add a combo-box here letting the user decide
            # on list vs icons. Would we need a way to switch it off?
        elif type == 'tree':
            self._view = QtWidgets.QTreeView()
        elif type == 'table':
            self._view = QtWidgets.QTableView()
        self._model = QtGui.QStandardItemModel(0, len(columns))
        self._model.setHorizontalHeaderLabels(columns)
        # Make the view read-only, and enable multi-selection of items
        self._view.setEditTriggers(QtWidgets.QAbstractItemView.NoEditTriggers)
        self._view.setSelectionBehavior(QtWidgets.QAbstractItemView.SelectRows)
        self._view.setSelectionMode(QtWidgets.QAbstractItemView.ExtendedSelection)
        self._view.setModel(self._model)

        # Build the label
        self._label_text = label_text
        if label_text:
            self._label = QtWidgets.QLabel()
            self._update_label_text()

        # Put them together
        layout = QtWidgets.QVBoxLayout()
        if details:
            splitter = QtWidgets.QSplitter()
            splitter.setOrientation(Qt.Vertical)
            splitter.addWidget(self._view)
            splitter.addWidget(details)
            layout.addWidget(splitter)
        else:
            layout.addWidget(self._view)
        if label_text:
            layout.addWidget(self._label)
        self.setLayout(layout)

    def view(self):
        """Get the view object (QAbstractItemView)."""
        return self._view

    def label(self):
        """Get the label object (QLabel)."""
        return self._label

    def setData(self, tuple_list, decoration_provider=None):
        """Reset the model to have the data shown.

        :param tuple_list: a list of tuples. Each tuple should have
          len(headers) items.
        :param decoration_provider: a callable taking the row number
          and record. It returns the icon to display in the first column
          or None if none.
        """
        # Update the model
        row_count = len(tuple_list)
        model = self._model
        model.setRowCount(row_count)
        cell_role = Qt.DisplayRole
        for row, record in enumerate(tuple_list):
            if decoration_provider:
                icon = decoration_provider(row, record)
                if icon:
                    index = model.index(row, 0)
                    model.setData(index, icon, Qt.DecorationRole)
            for col, value in enumerate(record):
                #print "putting %s into %d,%d" % (value, row, col)
                index = model.index(row, col)
                model.setData(index, value or '', cell_role)

        # Update the view & label
        self._view.setVisible(row_count > 0)
        if self._type in ['tree', 'table']:
            self._view.resizeColumnToContents(0)
        self._update_label_text(row_count)

    def _update_label_text(self, row_count=0):
        if self._label_text:
            text = self._label_text % {'rows': row_count}
            self._label.setText(text)
