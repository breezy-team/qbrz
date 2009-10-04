from PyQt4 import QtGui, QtCore
from bzrlib.plugins.qbzr.lib.i18n import gettext, ngettext, N_
import sys

class EncodingSelector(QtGui.QWidget):
    encodings = [
            'UTF-8', 'UTF-16BE', 'UTF-16LE', 'UTF-32BE', 'UTF-32LE', #Unicode.
            'ascii', 'latin-1', # 7/8bit codes.
            'cp932', 'euc_jp', 'iso-2022-jp', # japanese common codecs.
            # todo: preset another codecs.
            ]

    def __init__(self, initial_encoding = "UTF-8", label_text="Encoding:", *args):
        QtGui.QWidget.__init__(self, *args)
        layout = QtGui.QHBoxLayout()

        label = QtGui.QLabel(label_text)
        layout.addWidget(label)

        self.chooser = QtGui.QComboBox()
        self.chooser.addItems(self.encodings)
        self.chooser.setEditable(True)
        if not initial_encoding:
            initial_encoding = "UTF-8"
        self.chooser.setEditText(QtCore.QString(initial_encoding))
        self.connect(self.chooser, QtCore.SIGNAL("activated(QString)"),
                lambda x: self.onChanged(str(x)))
        layout.addWidget(self.chooser)

        # default encoding should be changed in Config window?
        #setbutton = QtGui.QPushButton(u"Make Default")
        #layout.addWidget(setbutton)

        self.setLayout(layout)

    def setEncoding(self, encoding):
        self.chooser.setEditText(QtCore.QString(encoding))

    def getEncoding(self):
        return str(self.chooser.getEditText())

    encoding = property(getEncoding, setEncoding)

    def onChanged(self, encoding):
        """Override this."""
        pass
