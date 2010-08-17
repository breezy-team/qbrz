# -*- coding: utf-8 -*-
#
# QBzr - Qt frontend to Bazaar commands
# Copyright (C) 2007 Lukáš Lalinský <lalinsky@gmail.com>
# Copyright (C) 2007,2009 Alexander Belchenko <bialix@ukr.net>
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

"""build_mo command for setup.py"""

from distutils import log
from distutils.command.build import build
from distutils.core import Command
from distutils.dep_util import newer
from distutils.spawn import find_executable
import os
import re

from en_po import regenerate_en


class build_mo(Command):
    """Subcommand of build command: build_mo"""

    description = 'compile po files to mo files'

    # List of options:
    #   - long name,
    #   - short name (None if no short name),
    #   - help string.
    user_options = [('build-dir=', 'd', 'Directory to build locale files'),
                    ('output-base=', 'o', 'mo-files base name'),
                    ('source-dir=', None, 'Directory with sources po files'),
                    ('force', 'f', 'Force creation of mo files'),
                    ('lang=', None, 'Comma-separated list of languages '
                                    'to process'),
                   ]

    boolean_options = ['force']

    def initialize_options(self):
        self.build_dir = None
        self.output_base = None
        self.source_dir = None
        self.force = None
        self.lang = None

    def finalize_options(self):
        self.set_undefined_options('build', ('force', 'force'))
        self.prj_name = self.distribution.get_name()
        if self.build_dir is None:
            self.build_dir = 'locale'
        if not self.output_base:
            self.output_base = self.prj_name or 'messages'
        if self.source_dir is None:
            self.source_dir = 'po'
        if self.lang is None:
            if self.prj_name:
                re_po = re.compile(r'^(?:%s-)?([a-zA-Z_]+)\.po$' % self.prj_name)
            else:
                re_po = re.compile(r'^([a-zA-Z_]+)\.po$')
            self.lang = []
            for i in os.listdir(self.source_dir):
                mo = re_po.match(i)
                if mo:
                    self.lang.append(mo.group(1))
        else:
            self.lang = [i.strip() for i in self.lang.split(',') if i.strip()]

    def run(self):
        """Run msgfmt for each language"""
        if not self.lang:
            return

        if find_executable('msgfmt') is None:
            log.warn("GNU gettext msgfmt utility not found!")
            log.warn("Skip compiling po files.")
            return

        if 'en' in self.lang:
            if find_executable('msginit') is None:
                log.warn("GNU gettext msginit utility not found!")
                log.warn("Skip creating English PO file.")
            else:
                log.info('Creating English PO file...')
                pot = (self.prj_name or 'messages') + '.pot'
                regenerate_en(self.prj_name, self.source_dir, pot, self.spawn)

        basename = self.output_base
        if not basename.endswith('.mo'):
            basename += '.mo'

        po_prefix = ''
        if self.prj_name:
            po_prefix = self.prj_name + '-'
        for lang in self.lang:
            po = os.path.join('po', lang + '.po')
            if not os.path.isfile(po):
                po = os.path.join('po', po_prefix + lang + '.po')
            dir_ = os.path.join(self.build_dir, lang, 'LC_MESSAGES')
            self.mkpath(dir_)
            mo = os.path.join(dir_, basename)
            if self.force or newer(po, mo):
                log.info('Compile: %s -> %s' % (po, mo))
                self.spawn(['msgfmt', '-o', mo, po])


build.sub_commands.insert(0, ('build_mo', None))
