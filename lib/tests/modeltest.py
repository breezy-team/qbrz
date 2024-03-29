#############################################################################
##
## Copyright (C) 2007 Trolltech ASA. All rights reserved.
##
## This file is part of the Qt Concurrent project on Trolltech Labs.
##
## This file may be used under the terms of the GNU General Public
## License version 2.0 as published by the Free Software Foundation
## and appearing in the file LICENSE.GPL included in the packaging of
## this file.  Please review the following information to ensure GNU
## General Public Licensing requirements will be met:
## http://www.trolltech.com/products/qt/opensource.html
##
## If you are unsure which license is appropriate for your use, please
## review the following information:
## http://www.trolltech.com/products/qt/licensing.html or contact the
## sales department at sales@trolltech.com.
##
## This file is provided AS IS with NO WARRANTY OF ANY KIND, INCLUDING THE
## WARRANTY OF DESIGN, MERCHANTABILITY AND FITNESS FOR A PARTICULAR PURPOSE.
##
#############################################################################


from PyQt5 import sip
from PyQt5 import QtCore


class ModelTest(QtCore.QObject):
    def __init__(self, _model, parent):
        """
        Connect to all of the models signals, Whenever anything happens recheck everything.
        """
        QtCore.QObject.__init__(self,parent)
        self._model = _model
        # QAbstractItemModel gives us a simple table of rows and columns. Each item in it (cell)
        # has a unique index via QtCore.QModelIndex with row, colum
        # for example:
        #   0 1 2
        # 0 . , ,
        # 1 . . X  <-- this X is at row:1, column:2
        # 2 . . .
        #
        # Any data associated with X can be retrieved via the data() function
        # passing it the 'role' that the data plays. The data is set via setData().
        #
        self.model = sip.cast(_model, QtCore.QAbstractItemModel)
        self.insert = []
        self.remove = []
        self.fetchingMore = False
        assert self.model

        self.model.columnsAboutToBeInserted[QtCore.QModelIndex, int, int].connect(self.runAllTests)
        self.model.columnsAboutToBeRemoved[QtCore.QModelIndex, int, int].connect(self.runAllTests)
        self.model.columnsInserted[QtCore.QModelIndex, int, int].connect(self.runAllTests)
        self.model.columnsRemoved[QtCore.QModelIndex, int, int].connect(self.runAllTests)

        # self.model.dataChanged[QtCore.QModelIndex, QtCore.QModelIndex].connect(self.runAllTests)

        self.model.headerDataChanged[QtCore.Qt.Orientation, int, int].connect(self.runAllTests)
        self.model.layoutAboutToBeChanged.connect(self.runAllTests)
        self.model.layoutChanged.connect(self.runAllTests)
        self.model.modelReset.connect(self.runAllTests)
        self.model.rowsAboutToBeInserted[QtCore.QModelIndex, int, int].connect(self.runAllTests)
        self.model.rowsAboutToBeRemoved[QtCore.QModelIndex, int, int].connect(self.runAllTests)
        self.model.rowsInserted[QtCore.QModelIndex, int, int].connect(self.runAllTests)
        self.model.rowsRemoved[QtCore.QModelIndex, int, int].connect(self.runAllTests)

        # Special checks for inserting/removing
        self.model.rowsAboutToBeInserted[QtCore.QModelIndex, int, int].connect(self.rowsAboutToBeInserted)
        self.model.rowsAboutToBeRemoved[QtCore.QModelIndex, int, int].connect(self.rowsAboutToBeRemoved)
        self.model.rowsInserted[QtCore.QModelIndex, int, int].connect(self.rowsInserted)
        self.model.rowsRemoved[QtCore.QModelIndex, int, int].connect(self.rowsRemoved)
        self.runAllTests()

    def nonDestructiveBasicTest(self):
        """
        nonDestructiveBasicTest tries to call a number of the basic functions (not all)
        to make sure the model doesn't outright segfault, testing the functions that makes sense.
        """
        assert(self.model.buddy(QtCore.QModelIndex()) == QtCore.QModelIndex())
        self.model.canFetchMore(QtCore.QModelIndex())
        assert(self.model.columnCount(QtCore.QModelIndex()) >= 0)
        # Try to fetch something from nothing - this:
        #
        #   self.model.data(QtCore.QModelIndex(), QtCore.Qt.DisplayRole)
        #
        # reads as:
        #
        #   from the (.data) table at (an invalid QtCore.QModelIndex) try to get a DisplayRole
        #
        # A bare QtCore.QModelIndex() creates a new empty index, and will be invalid: asking for the
        # displayRole will bring back (or used to bring back) an invalid QVariant rather than
        # raising an exception. With QVariant(2) set via sip, we don't get QVariants at all
        # but a NoneType.
        # Was: assert(self.model.data(QtCore.QModelIndex(), QtCore.Qt.DisplayRole) == QtCore.QVariant())
        assert(self.model.data(QtCore.QModelIndex(), QtCore.Qt.DisplayRole) is None)
        self.fetchingMore = True
        self.model.fetchMore(QtCore.QModelIndex())
        self.fetchingMore = False
        flags = self.model.flags(QtCore.QModelIndex())
        assert(int(flags & QtCore.Qt.ItemIsEnabled) == QtCore.Qt.ItemIsEnabled or int(flags & QtCore.Qt.ItemIsEnabled) == 0)
        self.model.hasChildren(QtCore.QModelIndex())
        self.model.hasIndex(0,0)
        self.model.headerData(0,QtCore.Qt.Horizontal, QtCore.Qt.DisplayRole)
        self.model.index(0,0, QtCore.QModelIndex())
        self.model.itemData(QtCore.QModelIndex())
        # Match returns indices for items were the data role (e.g. DisplayRole) matches the value (QVariant)
        #
        # so, this:
        #       cache = QtCore.QVariant()
        #       self.model.match(QtCore.QModelIndex(), -1, cache)
        # reads as:
        #   Try to get things from the table that match the (non-existent) -1 'role'
        #   where the data stored there matches Qvariant
        # We haven't got QVariants any more, so just pass anything
        self.model.match(QtCore.QModelIndex(), -1, 'a string')
        self.model.mimeTypes()
        assert(self.model.parent(QtCore.QModelIndex()) == QtCore.QModelIndex())
        assert(self.model.rowCount(QtCore.QModelIndex()) >= 0)
        # setData(index, value, role) sets the (role) data at the index to value.
        # so, this:
        #       variant = QtCore.QVariant()
        #       self.model.setData(QtCore.QModelIndex(), variant, -1)
        # reads as:
        #   Put an empty QVariant() at an invalid index as an invalid role
        self.model.setData(QtCore.QModelIndex(), 'a string', -1)
        # Sets the data a dummy horizontal section (-1) to an empty QVariant...
        #   self.model.setHeaderData(-1, QtCore.Qt.Horizontal, QtCore.QVariant())
        # ...and for section zero
        #   self.model.setHeaderData(0, QtCore.Qt.Horizontal, QtCore.QVariant())
        # and for section 999999
        #   self.model.setHeaderData(999999, QtCore.Qt.Horizontal, QtCore.QVariant())
        self.model.setHeaderData(-1, QtCore.Qt.Horizontal, 'a string')
        self.model.setHeaderData(0, QtCore.Qt.Horizontal, 'a string')
        self.model.setHeaderData(999999, QtCore.Qt.Horizontal, 'a string')
        self.model.sibling(0,0,QtCore.QModelIndex())
        self.model.span(QtCore.QModelIndex())
        self.model.supportedDropActions()

    def rowCount(self):
        """
        Tests self.model's implementation of QtCore.QAbstractItemModel::rowCount() and hasChildren()

        self.models that are dynamically populated are not as fully tested here.
        """
        # check top row
        topindex = self.model.index(0,0,QtCore.QModelIndex())
        rows = self.model.rowCount(topindex)
        assert(rows >= 0)
        if rows > 0:
            assert(self.model.hasChildren(topindex) is True)

        secondlvl = self.model.index(0,0,topindex)
        if secondlvl.isValid():
            # check a row count where parent is valid
            rows = self.model.rowCount(secondlvl)
            assert(rows >= 0)
            if rows > 0:
                assert(self.model.hasChildren(secondlvl) is True)

        # The self.models rowCount() is tested more extensively in checkChildren,
        # but this catches the big mistakes

    def columnCount(self):
        """
        Tests self.model's implementation of QtCore.QAbstractItemModel::columnCount() and hasChildren()
        """
        # check top row
        topidx = self.model.index(0,0,QtCore.QModelIndex())
        assert(self.model.columnCount(topidx) >= 0)

        # check a column count where parent is valid
        childidx = self.model.index(0,0,topidx)
        if childidx.isValid() :
            assert(self.model.columnCount(childidx) >= 0)

        # columnCount() is tested more extensively in checkChildren,
        # but this catches the big mistakes

    def hasIndex(self):
        """
        Tests self.model's implementation of QtCore.QAbstractItemModel::hasIndex()
        """
        # Make sure that invalid values returns an invalid index
        assert(self.model.hasIndex(-2,-2) == False)
        assert(self.model.hasIndex(-2,0) == False)
        assert(self.model.hasIndex(0,-2) == False)

        rows = self.model.rowCount(QtCore.QModelIndex())
        cols = self.model.columnCount(QtCore.QModelIndex())

        # check out of bounds
        assert(self.model.hasIndex(rows,cols) == False)
        assert(self.model.hasIndex(rows+1,cols+1) == False)

        if rows > 0:
            assert(self.model.hasIndex(0,0) == True)

        # hasIndex() is tested more extensively in checkChildren()
        # but this catches the big mistakes

    def index(self):
        """
        Tests self.model's implementation of QtCore.QAbstractItemModel::index()
        """
        # Make sure that invalid values returns an invalid index
        assert(self.model.index(-2,-2, QtCore.QModelIndex()) == QtCore.QModelIndex())
        assert(self.model.index(-2,0, QtCore.QModelIndex()) == QtCore.QModelIndex())
        assert(self.model.index(0,-2, QtCore.QModelIndex()) == QtCore.QModelIndex())

        rows = self.model.rowCount(QtCore.QModelIndex())
        cols = self.model.columnCount(QtCore.QModelIndex())

        if rows == 0:
            return

        # Catch off by one errors
        assert(self.model.index(rows,cols, QtCore.QModelIndex()) == QtCore.QModelIndex())
        assert(self.model.index(0,0, QtCore.QModelIndex()).isValid() == True)

        # Make sure that the same index is *always* returned
        a = self.model.index(0,0, QtCore.QModelIndex())
        b = self.model.index(0,0, QtCore.QModelIndex())
        assert(a==b)

        # index() is tested more extensively in checkChildren()
        # but this catches the big mistakes

    def parent(self):
        """
        Tests self.model's implementation of QtCore.QAbstractItemModel::parent()
        """
        # Make sure the self.model wont crash and will return an invalid QtCore.QModelIndex
        # when asked for the parent of an invalid index
        assert(self.model.parent(QtCore.QModelIndex()) == QtCore.QModelIndex())

        if self.model.rowCount(QtCore.QModelIndex()) == 0:
            return;

        # Column 0              | Column 1  |
        # QtCore.Qself.modelIndex()         |           |
        #    \- topidx          | topidx1   |
        #         \- childix    | childidx1 |

        # Common error test #1, make sure that a top level index has a parent
        # that is an invalid QtCore.Qself.modelIndex
        topidx = self.model.index(0,0,QtCore.QModelIndex())
        assert(self.model.parent(topidx) == QtCore.QModelIndex())

        # Common error test #2, make sure that a second level index has a parent
        # that is the first level index
        if self.model.rowCount(topidx) > 0 :
            childidx = self.model.index(0,0,topidx)
            assert(self.model.parent(childidx) == topidx)

        # Common error test #3, the second column should NOT have the same children
        # as the first column in a row
        # Usually the second column shouldn't have children
        topidx1 = self.model.index(0,1,QtCore.QModelIndex())
        if self.model.rowCount(topidx1) > 0:
            childidx = self.model.index(0,0,topidx)
            childidx1 = self.model.index(0,0,topidx1)
            assert(childidx != childidx1)

        # Full test, walk n levels deep through the self.model making sure that all
        # parent's children correctly specify their parent
        self.checkChildren(QtCore.QModelIndex())

    def data(self):
        """
        Tests self.model's implementation of QtCore.QAbstractItemModel::data()
        """
        # Invalid index should return an invalid qvariant
        # assert( not self.model.data(QtCore.QModelIndex(), QtCore.Qt.DisplayRole).isValid())
        #
        # The above is no longer true: it should return None...
        assert(self.model.data(QtCore.QModelIndex(), QtCore.Qt.DisplayRole) is None)

        if self.model.rowCount(QtCore.QModelIndex()) == 0:
            return

        # A valid index should have a valid QtCore.QVariant data
        assert(self.model.index(0,0, QtCore.QModelIndex()) is not None)

        # shouldn't be able to set data on an invalid index
        assert(self.model.setData(QtCore.QModelIndex(), "foo", QtCore.Qt.DisplayRole) is False)

        # General Purpose roles that should return a QString
        variant = self.model.data(self.model.index(0,0,QtCore.QModelIndex()), QtCore.Qt.ToolTipRole)
        # We no longer use isValid(), so just test it exists
        if variant:
            assert( variant.canConvert( QtCore.QVariant.String ) )
        variant = self.model.data(self.model.index(0,0,QtCore.QModelIndex()), QtCore.Qt.StatusTipRole)
        if variant:
            assert( variant.canConvert( QtCore.QVariant.String ) )
        variant = self.model.data(self.model.index(0,0,QtCore.QModelIndex()), QtCore.Qt.WhatsThisRole)
        if variant:
            assert( variant.canConvert( QtCore.QVariant.String ) )

        # General Purpose roles that should return a QSize
        variant = self.model.data(self.model.index(0,0,QtCore.QModelIndex()), QtCore.Qt.SizeHintRole)
        if variant:
            assert( variant.canConvert( QtCore.QVariant.Size ) )

        # General Purpose roles that should return a QFont
        variant = self.model.data(self.model.index(0,0,QtCore.QModelIndex()), QtCore.Qt.FontRole)
        if variant:
            assert( variant.canConvert( QtCore.QVariant.Font ) )

        # Check that the alignment is one we know about
        variant = self.model.data(self.model.index(0,0,QtCore.QModelIndex()), QtCore.Qt.TextAlignmentRole)
        if variant:
            # alignment = variant.toInt()[0]
            alignment = int(variant)
            assert( alignment == QtCore.Qt.AlignLeft or
                alignment == QtCore.Qt.AlignRight or
                alignment == QtCore.Qt.AlignHCenter or
                alignment == QtCore.Qt.AlignJustify)

        # General Purpose roles that should return a QColor
        variant = self.model.data(self.model.index(0,0,QtCore.QModelIndex()), QtCore.Qt.BackgroundColorRole)
        if variant:
            assert(variant.canConvert( QtCore.QVariant.Color ))
        variant = self.model.data(self.model.index(0,0,QtCore.QModelIndex()), QtCore.Qt.TextColorRole)
        if variant:
            assert(variant.canConvert( QtCore.QVariant.Color ))

        # Check that the "check state" is one we know about.
        variant = self.model.data(self.model.index(0,0,QtCore.QModelIndex()), QtCore.Qt.CheckStateRole)
        if variant:
            # state = variant.toInt()[0]
            state = int(variant)
            assert( state == QtCore.Qt.Unchecked or
                state == QtCore.Qt.PartiallyChecked or
                state == QtCore.Qt.Checked )

    def runAllTests(self):
        if self.fetchingMore:
            return
        self.nonDestructiveBasicTest()
        self.rowCount()
        self.columnCount()
        self.hasIndex()
        self.index()
        self.parent()
        self.data()

    def rowsAboutToBeInserted(self, parent, start, end):
        """
        Store what is about to be inserted to make sure it actually happens
        """
        c = {}
        c['parent'] = parent
        c['oldSize'] = self.model.rowCount(parent)
        c['last'] = self.model.data(model.index(start-1, 0, parent))
        c['next'] = self.model.data(model.index(start, 0, parent))
        insert.append(c)

    def rowsInserted(self, parent, start, end):
        """
        Confirm that what was said was going to happen actually did
        """
        c = insert.pop()
        assert(c['parent'] == parent)
        assert(c['oldSize'] + (end - start + 1) == self.model.rowCount(parent))
        assert(c['last'] == self.model.data(model.index(start-1, 0, c['parent'])))

        # if c['next'] != self.model.data(model.index(end+1, 0, c['parent'])):
        #   qDebug << start << end
        #   for i in range(0, self.model.rowCount(QtCore.QModelIndex())):
        #       qDebug << self.model.index(i, 0).data().toString()
        #   qDebug() << c['next'] << self.model.data(model.index(end+1, 0, c['parent']))

        assert(c['next'] == self.model.data(model.index(end+1, 0, c['parent'])))

    def rowsAboutToBeRemoved(self, parent, start, end):
        """
        Store what is about to be inserted to make sure it actually happens
        """
        c = {}
        c['parent'] = parent
        c['oldSize'] = self.model.rowCount(parent)
        c['last'] = self.model.data(model.index(start-1, 0, parent))
        c['next'] = self.model.data(model.index(end+1, 0, parent))
        remove.append(c)

    def rowsRemoved(self, parent, start, end):
        """
        Confirm that what was said was going to happen actually did
        """
        c = remove.pop()
        assert(c['parent'] == parent)
        assert(c['oldSize'] - (end - start + 1) == self.model.rowCount(parent))
        assert(c['last'] == self.model.data(model.index(start-1, 0, c['parent'])))
        assert(c['next'] == self.model.data(model.index(start, 0, c['parent'])))

    def checkChildren(self, parent, depth = 0):
        """
        Called from parent() test.

        A self.model that returns an index of parent X should also return X when asking
        for the parent of the index

        This recursive function does pretty extensive testing on the whole self.model in an
        effort to catch edge cases.

        This function assumes that rowCount(QtCore.QModelIndex()), columnCount(QtCore.QModelIndex()) and index() already work.
        If they have a bug it will point it out, but the above tests should have already
        found the basic bugs because it is easier to figure out the problem in
        those tests then this one
        """
        # First just try walking back up the tree.
        p = parent;
        while p.isValid():
            p = p.parent()

        #For self.models that are dynamically populated
        if self.model.canFetchMore( parent ):
            self.fetchingMore = True
            self.model.fetchMore(parent)
            self.fetchingMore = False

        rows = self.model.rowCount(parent)
        cols = self.model.columnCount(parent)

        if rows > 0:
            assert(self.model.hasChildren(parent))

        # Some further testing against rows(), columns, and hasChildren()
        assert( rows >= 0 )
        assert( cols >= 0 )

        if rows > 0:
            assert(self.model.hasChildren(parent) == True)

        # qDebug() << "parent:" << self.model.data(parent).toString() << "rows:" << rows
        #          << "columns:" << cols << "parent column:" << parent.column()

        assert( self.model.hasIndex( rows+1, 0, parent) == False)
        for r in range(0,rows):
            if self.model.canFetchMore(parent):
                self.fetchingMore = True
                self.model.fetchMore(parent)
                self.fetchingMore = False
            assert(self.model.hasIndex(r,cols+1,parent) == False)
            for c in range(0,cols):
                assert(self.model.hasIndex(r,c,parent))
                index = self.model.index(r,c,parent)
                # rowCount(QtCore.QModelIndex()) and columnCount(QtCore.QModelIndex()) said that it existed...
                assert(index.isValid() == True)

                # index() should always return the same index when called twice in a row
                modIdx = self.model.index(r,c,parent)
                assert(index == modIdx)

                # Make sure we get the same index if we request it twice in a row
                a = self.model.index(r,c,parent)
                b = self.model.index(r,c,parent)
                assert( a == b )

                # Some basic checking on the index that is returned
                # assert( index.model() == self.model )
                # This raises an error that is not part of the qbrz code.
                # see http://www.opensubscriber.com/message/pyqt@riverbankcomputing.com/10335500.html
                assert( index.row() == r )
                assert( index.column() == c )
                # While you can technically return a QtCore.QVariant usually this is a sign
                # if an bug in data() Disable if this really is ok in your self.model
                # assert( self.model.data(index, QtCore.Qt.DisplayRole).isValid() == True )
                #
                # We no longer check isValid(), just make sure it's not None
                assert( self.model.data(index, QtCore.Qt.DisplayRole) is not None)

                #if the next test fails here is some somehwat useful debug you play with
                # if self.model.parent(index) != parent:
                #   qDebug() << r << c << depth << self.model.data(index).toString()
                #        << self.model.data(parent).toString()
                #   qDebug() << index << parent << self.model.parent(index)
                #   # And a view that you can even use to show the self.model
                #   # view = QtGui.QTreeView()
                #   # view.setself.model(model)
                #   # view.show()
                #

                # Check that we can get back our real parent
                p = self.model.parent( index )
                assert( p.internalId() == parent.internalId() )
                assert( p.row() == parent.row() )

                # recursively go down the children
                if self.model.hasChildren(index) and depth < 10:
                    # qDebug() << r << c << "hasChildren" << self.model.rowCount(index)
                    self.checkChildren(index, ++depth)
                #else:
                #   if depth >= 10:
                #       qDebug() << "checked 10 deep"

                # Make sure that after testing the children that the index doesn't change
                newIdx = self.model.index(r,c,parent)
                assert(index == newIdx)
