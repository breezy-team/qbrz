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

import re
import enchant
from enchant.checker import SpellChecker
from enchant.tokenize import EmailFilter, URLFilter, Filter, tokenize


class camel_case_tokenize(tokenize):

    def next(self):
        offset = self.offset
        text = self._text[offset:]
        if not text:
            raise StopIteration()
        match = re.match('(\w+?)[A-Z]', text)
        if match is None:
            word = text
        else:
            word = match.group(1)
        self.offset += len(word)
        return word, offset


class CamelCaseFilter(Filter):

    def _split(self, word):
        return camel_case_tokenize(word)


class EnchantSpellChecker(object):

    def __init__(self, language):
        try:
            self.dict = enchant.Dict(language)
            self.checker = SpellChecker(language, filters=[EmailFilter, URLFilter, CamelCaseFilter])
        except enchant.DictNotFoundError:
            self.checker = None

    def check(self, text):
        if self.checker is None:
            return
        self.checker.set_text(text)
        for err in self.checker:
            yield err.wordpos, len(err.word)
    
    def suggest(self, text):
        return self.dict.suggest(text)

    @classmethod
    def list_languages(cls):
        return list(set(lang.replace("_", "-") for lang in enchant.list_languages()))
