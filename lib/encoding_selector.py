# -*- coding: utf-8 -*-
#
# QBzr - Qt frontend to Bazaar commands
# Contributors:
#   INADA Naoki, 2009
#   Alexander Belchenko, 2009
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

import codecs
from PyQt5 import QtCore, QtGui, QtWidgets

from breezy.plugins.qbrz.lib.i18n import gettext
from breezy.plugins.qbrz.lib.util import is_valid_encoding
from breezy.osutils import get_user_encoding, get_terminal_encoding


class UniqueList(object):
    """List-like object with unique-only append."""

    def __init__(self, data=None):
        self._data = []
        if data:
            self._data.extend(data)

    def append(self, item):
        if item not in self._data:
            self._data.append(item)

    def __add__(self, other):
        for item in other:
            self.append(item)
        return UniqueList(self._data)

    def __iter__(self):
        return iter(self._data)


class BaseEncodingSelector(object):

    def init_encodings(self, initial_encoding=None):
        _encodings = UniqueList()
        if initial_encoding:
            _encodings.append(initial_encoding)
        _encodings.append(get_user_encoding())
        _encodings.append(get_terminal_encoding())
        _encodings += python_encodings
        self.encodings = list(filter(is_valid_encoding, _encodings))

        if initial_encoding:
            if initial_encoding not in self.encodings:
                self.encodings.insert(0, initial_encoding)
        else:
            initial_encoding = 'utf-8'
        self._encoding = initial_encoding

    def _encodingChanged(self, encoding):
        try:
            encoding = str(encoding)    # may raise UnicodeError
            codecs.lookup(encoding)     # may raise LookupError
            self._encoding = encoding
            self.onChanged(encoding)
        except (UnicodeError, LookupError):
            QtWidgets.QMessageBox.critical(self, gettext("Wrong encoding"),
                gettext('Encoding "%s" is invalid or not supported.') % str(encoding))
            self.setEncoding(self._encoding)

    def getEncoding(self):
        return self._encoding

    def setEncoding(self, encoding):
        if is_valid_encoding(encoding):
            self._encoding = encoding
            self._setEncoding(encoding)

    def _setEncoding(self, encoding):
        pass

    encoding = property(getEncoding, setEncoding)


class EncodingSelector(QtWidgets.QWidget, BaseEncodingSelector):
    """Widget to control encoding of text."""

    def __init__(self, initial_encoding=None, label_text=None, onChanged=None,
        *args):
        """Create widget: label + combobox.
        @param initial_encoding: initially selected encoding (default: utf-8).
        @param label_text: text for label (default: "Encoding:").
        @param onChanged: callback to processing encoding change.
        @param args: additional arguments to initialize QWidget.
        """
        QtWidgets.QWidget.__init__(self, *args)
        self.init_encodings(initial_encoding)
        self.onChanged = onChanged
        if onChanged is None:
            self.onChanged = lambda encoding: None

        layout = QtWidgets.QHBoxLayout()

        if label_text is None:
            label_text = gettext("Encoding:")
        self._label = QtWidgets.QLabel(label_text)
        layout.addWidget(self._label)

        self.chooser = QtWidgets.QComboBox()
        self.chooser.addItems(self.encodings)
        self.chooser.setEditable(True)
        self.chooser.setEditText(self.encoding)
        self.chooser.currentIndexChanged['QString'].connect(self._encodingChanged)
        self.chooser.focusOutEvent = self._focusOut
        layout.addWidget(self.chooser)

        self.setLayout(layout)

    def _focusOut(self, ev):
        encoding = self.chooser.currentText()
        if self._encoding != encoding:
            self._encodingChanged(encoding)
        QtWidgets.QComboBox.focusOutEvent(self.chooser, ev)

    def _setEncoding(self, encoding):
        self.chooser.setEditText(encoding)

    def getLabel(self):
        return str(self._label.text())

    def setLabel(self, new_label):
        self._label.setText(new_label)

    label = property(getLabel, setLabel)


class EncodingMenuSelector(QtWidgets.QMenu, BaseEncodingSelector):
    """Menu to control encoding of text."""

    def __init__(self, initial_encoding=None, label_text=None, onChanged=None,
        *args):
        """Create widget: label + combobox.
        @param initial_encoding: initially selected encoding (default: utf-8).
        @param label_text: text for label (default: "Encoding:").
        @param onChanged: callback to processing encoding change.
        @param args: additional arguments to initialize QWidget.
        """
        QtWidgets.QMenu.__init__(self, *args)
        self.init_encodings(initial_encoding)
        self.onChanged = onChanged
        if onChanged is None:
            self.onChanged = lambda encoding: None

        self.setTitle(label_text)
        self.setStyleSheet("QMenu { menu-scrollable: 1; }")

        self.action_group = QtWidgets.QActionGroup(self)

        self.encoding_actions = {}
        for encoding in self.encodings:
            action = QtWidgets.QAction(encoding, self.action_group)
            action.setCheckable(True)
            action.setData(encoding)
            self.addAction(action)
            self.encoding_actions[encoding] = action

        self._setEncoding(self.encoding)
        # RJLRJL changed triggered to _triggered
        self.triggered[QtWidgets.QAction].connect(self._triggered)

    def _triggered(self, action):
        encoding = action.data()
        self._encodingChanged(encoding)

    def _setEncoding(self, encoding):
        if encoding in self.encoding_actions:
            self.encoding_actions[encoding].setChecked(True)

    def getLabel(self):
        return str(self.title())

    def setLabel(self, new_label):
        self.setTitle(new_label)

    label = property(getLabel, setLabel)


# The 'python_encodings' horror below changes underscores to dashes and them makes a list.
# What you actually get is:
#
# ['utf-8', 'ascii', 'latin-1', 'big5', 'big5hkscs', 'cp037', 'cp1006', 'cp1026', 'cp1140', 'cp1250', 'cp1251',
# 'cp1252', 'cp1253', 'cp1254', 'cp1255', 'cp1256', 'cp1257', 'cp1258', 'cp424', 'cp437', 'cp500', 'cp737', 'cp775',
# 'cp850', 'cp852', 'cp855', 'cp856', 'cp857', 'cp860', 'cp861', 'cp862', 'cp863', 'cp864', 'cp865', 'cp866', 'cp869',
# 'cp874', 'cp875', 'cp932', 'cp949', 'cp950', 'euc-jisx0213', 'euc-jis-2004', 'euc-jp', 'euc-kr', 'gb18030', 'gb2312',
# 'gbk', 'hp-roman8', 'hz', 'iso2022-jp', 'iso2022-jp-1', 'iso2022-jp-2', 'iso2022-jp-2004', 'iso2022-jp-3',
# 'iso2022-jp-ext', 'iso2022-kr', 'iso8859-1', 'iso8859-10', 'iso8859-11', 'iso8859-13', 'iso8859-14', 'iso8859-15',
# 'iso8859-16', 'iso8859-2', 'iso8859-3', 'iso8859-4', 'iso8859-5', 'iso8859-6', 'iso8859-7', 'iso8859-8', 'iso8859-9',
# 'johab', 'koi8-r', 'koi8-u', 'mac-arabic', 'mac-centeuro', 'mac-croatian', 'mac-cyrillic', 'mac-farsi', 'mac-greek',
# 'mac-iceland', 'mac-latin2', 'mac-roman', 'mac-romanian', 'mac-turkish', 'ptcp154', 'shift-jis', 'shift-jisx0213',
# 'shift-jis-2004', 'tis-620', 'utf-16', 'utf-16-be', 'utf-16-le', 'utf-32', 'utf-32-be', 'utf-32-le', 'utf-7', 'utf-8-sig']
#
# ...and before you ask, no, I don't know why they didn't just do that either. What larks!

# human encodings found in standard Python encodings package.
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
ptcp154
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
""".replace('_','-').split()
