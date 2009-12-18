# -*- coding: utf-8 -*-
#
# QBzr - Qt frontend to Bazaar commands
# Copyright (C) 2008 Lukáš Lalinský <lalinsky@gmail.com>
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

from PyQt4 import QtGui

# TODO Enchant supports OpenOffice dictionaries, make it easy to use them on Windows
# TODO custom words
# TODO integrate into the text editor's context menu


class SpellCheckHighlighter(QtGui.QSyntaxHighlighter):

    def __init__(self, document, checker):
        QtGui.QSyntaxHighlighter.__init__(self, document)
        self.checker = checker
        self.format = QtGui.QTextCharFormat()
        self.format.setUnderlineColor(QtGui.QColor('red'))
        self.format.setUnderlineStyle(QtGui.QTextCharFormat.SpellCheckUnderline)

    def highlightBlock(self, text):
        for index, length in self.checker.check(unicode(text)):
            self.setFormat(index, length, self.format)


class DummySpellChecker(object):

    def __init__(self, language):
        pass

    def check(self, text):
        return []
    
    def suggest(self, text):
        return []

    @classmethod
    def list_languages(cls):
        return []


try:
    from bzrlib.plugins.qbzr.lib.spellcheck_enchant import EnchantSpellChecker as SpellChecker
except ImportError:
    SpellChecker = DummySpellChecker 
