from PyQt4 import QtGui, QtCore
from bzrlib.plugins.qbzr.lib.i18n import gettext, ngettext, N_
from bzrlib.plugins.qbzr.lib.util import is_valid_encoding
from bzrlib.osutils import get_user_encoding, get_terminal_encoding
import sys

# encodings found in encodings package.
python_encodings = """
utf_8
ascii
latin_1
big5
big5hkscs
cp037
cp1006
cp1026
cp1140
cp1250
cp1251
cp1252
cp1253
cp1254
cp1255
cp1256
cp1257
cp1258
cp424
cp437
cp500
cp737
cp775
cp850
cp852
cp855
cp856
cp857
cp860
cp861
cp862
cp863
cp864
cp865
cp866
cp869
cp874
cp875
cp932
cp949
cp950
euc_jisx0213
euc_jis_2004
euc_jp
euc_kr
gb18030
gb2312
gbk
hp_roman8
hz
idna
iso2022_jp
iso2022_jp_1
iso2022_jp_2
iso2022_jp_2004
iso2022_jp_3
iso2022_jp_ext
iso2022_kr
iso8859_1
iso8859_10
iso8859_11
iso8859_13
iso8859_14
iso8859_15
iso8859_16
iso8859_2
iso8859_3
iso8859_4
iso8859_5
iso8859_6
iso8859_7
iso8859_8
iso8859_9
johab
koi8_r
koi8_u
mac_arabic
mac_centeuro
mac_croatian
mac_cyrillic
mac_farsi
mac_greek
mac_iceland
mac_latin2
mac_roman
mac_romanian
mac_turkish
palmos
ptcp154
quopri_codec
shift_jis
shift_jisx0213
shift_jis_2004
tis_620
utf_16
utf_16_be
utf_16_le
utf_32
utf_32_be
utf_32_le
utf_7
utf_8_sig
""".split()

class EncodingSelector(QtGui.QWidget):
    encodings = list(set([get_user_encoding(), get_terminal_encoding(), "utf-8"])) + python_encodings
    encodings = filter(is_valid_encoding, encodings)

    def __init__(self, initial_encoding="utf-8", label_text="Encoding:", *args):
        QtGui.QWidget.__init__(self, *args)
        self._label = label_text
        layout = QtGui.QHBoxLayout()

        self._label = QtGui.QLabel(label_text)
        layout.addWidget(self._label)

        encodings = self.encodings
        if initial_encoding and initial_encoding not in encodings:
            encodings.insert(0, initial_encoding)
        else:
            initial_encoding = 'utf-8'

        self.chooser = QtGui.QComboBox()
        self.chooser.addItems(encodings)
        self.chooser.setEditable(True)
        self.chooser.setEditText(QtCore.QString(initial_encoding))
        self.connect(self.chooser, QtCore.SIGNAL("activated(QString)"),
                     lambda x: self.onChanged(str(x)))
        layout.addWidget(self.chooser)

        self.setLayout(layout)

    def getEncoding(self):
        return str(self.chooser.currentText())

    def setEncoding(self, encoding):
        self.chooser.setEditText(QtCore.QString(encoding))

    encoding = property(getEncoding, setEncoding)

    def getLabel(self):
        return unicode(self._label.text())

    def setLabel(self, new_label):
        self._label.setText(new_label)

    label = property(getLabel, setLabel)

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
