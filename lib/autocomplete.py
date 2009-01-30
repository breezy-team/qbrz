# -*- coding: utf-8 -*-
#
# QBzr - Qt frontend to Bazaar commands
# Copyright (C) 2007-2008 Lukáš Lalinský <lalinsky@gmail.com>
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

# Based on my old commit code and http://tortoisesvn.tigris.org/svn/tortoisesvn/trunk/src/TortoiseSVNSetup/include/autolist.txt
autolist = [
    (r'^\s*(?:class|typedef|struct|union|namespace)\s+([\w_]+)|\b([\w_]+)\s*\(',
     ('.h', '.hh', '.hpp', '.hxx')),
    (r'(?<=typedef)\s+(?:struct|union)\s+([\w_]+)',
     ('.h', '.hh', '.hpp', '.hxx', '.c')),
    (r'\b(([\w_]+)::([\w_]+))|\b([\w_]+)\s*\(',
     ('.cpp', '.cc', '.c', '.cxx')),
    (r'(?:(?:prototype\.|this\.)(\w+)\s*=\s*)?function\s*(?:(\w*)\s*)\(',
     ('.js',)),
    (r'(\w+)\s+=\s+(?:class|record|interface)|(?:procedure|function|property|constructor)\s+(\w+)',
     ('.pas',)),
    (r'^\s*(?:class|def)\s+(\w+)',
     ('.py', '.pyw', '.rb')),
    (r'(\w+)\s*=\s*',
     ('.py', '.pyw')),
    (r'^\s*sub\s+(\w+)|\s*(?:package|use)\s+([\w\:]+)',
     ('.pl', '.pm')),
    (r'^\s*class\s+(\w+)|^\s*(?:(?:public|private|)\s+function)\s+(\w+)|::(\w+)|->(\w+)',
     ('.php',)),
    (r'(?:class|function|sub)\s+(\w+)(?:\s*(?:[\(\']|$))',
     ('.vb', '.vb6')),
    (r'^\s*(?:(?:Public (?:Default )?|Private )?(?:Sub|Function|Property Get|Property Set|Property Let) ?)(\w+)\(|^Attribute VB_Name = "(\w+)"',
     ('.bas', '.frm', '.cls')),
    (r'(?:public|protected|private|internal)\s+(?:[\w\d_\.]+\s+)*([\w\d_\.]+)',
     ('.cs', '.asp', '.aspx')),
    (r'class\s+([\w_]+)(?:(?:\s+)?(?:extends|implements)(?:\s+)?([\w_]+)?)',
     ('.java',)),
    (r'(?:public|protected|private|internal)\s+(?:[\w\d_\.]+\s+)*([\w\d_\.]+)',
     ('.java',)),
    (r'^.{6} ([A-Z][A-Z0-9-]*)(?: SECTION)?\.',
     ('.cbl', '.cpy')),
    (r'Func\s+([\w_]+)|\$([\w_]+)',
     ('.au3', '.auh')),
    (r'^([\w]+) *',
     ('.asm',)),
]

_autolist_map = {}


class AutocompleteWordListBuilder(object):

    def __init__(self):
        self.regexes = []
        self.compiled_regexes = None

    def compile_regexes(self):
        if self.compiled_regexes is None:
            self.compiled_regexes = map(re.compile, self.regexes)

    def iter_words(self, file):
        self.compile_regexes()
        for line in file:
            for regex in self.compiled_regexes:
                for result in regex.findall(line):
                    if not isinstance(result, tuple):
                        result = (result,)
                    for word in filter(None, result):
                        yield word


def get_wordlist_builder(ext):
    if not _autolist_map:
        for regex, extensions in autolist:
            for extension in extensions:
                if extension not in _autolist_map:
                    _autolist_map[extension] = AutocompleteWordListBuilder()
                _autolist_map[extension].regexes.append(regex)
    return _autolist_map.get(ext)
