from PyQt4 import QtGui, QtCore
from bzrlib.plugins.qbzr.lib.i18n import gettext, ngettext, N_
from bzrlib.plugins.qbzr.lib.util import is_valid_encoding
import sys

class EncodingSelector(QtGui.QWidget):
    encodings = [
            'UTF-8', 'UTF-16BE', 'UTF-16LE', 'UTF-32BE', 'UTF-32LE', #Unicode.
            'ascii', 'latin-1', # 7/8bit codes.
            'cp932', 'euc_jp', 'iso-2022-jp', # japanese common codecs.
            # todo: preset another codecs.
            ]
    encodings = filter(is_valid_encoding, encodings)

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

        self.setLayout(layout)

    def setEncoding(self, encoding):
        self.chooser.setEditText(QtCore.QString(encoding))

    def getEncoding(self):
        return str(self.chooser.currentText())

    encoding = property(getEncoding, setEncoding)

    def _on_encoding_changed(self, encoding):
        try:
            encoding = str(encoding)
            if is_valid_encoding(encoding):
                self.onChanged(encoding)
        except UnicodeException:
            # when non-ascii string is inputted the box.
            pass

    def onChanged(self, encoding):
        """Public event handler. Override this."""
        pass
