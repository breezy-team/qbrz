# -*- coding: utf-8 -*-
#
# QBzr - Qt frontend to Bazaar commands
# Copyright (C) 2007 Lukáš Lalinský <lalinsky@gmail.com>
# Copyright (C) 2007 Alexander Belchenko <bialix@ukr.net>
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

"""build_pot command for setup.py"""

import glob
from distutils import log
from distutils.core import Command
from distutils.errors import DistutilsOptionError


class build_pot(Command):
    """Distutils command build_pot"""

    description = 'extract strings from python sources for translation'

    # List of options:
    #   - long name,
    #   - short name (None if no short name),
    #   - help string.
    user_options = [('build-dir=', 'd', 'Directory to put POT file'),
                    ('output=', 'o', 'POT filename'),
                    ('lang=', None, 'Comma-separated list of languages '
                                    'to update po-files'),
                    ('no-lang', 'N', "Don't update po-files"),
                    ('english', 'E', 'Regenerate English PO file'),
                   ]
    boolean_options = ['no-lang', 'english']

    def initialize_options(self):
        self.build_dir = None
        self.output = None
        self.lang = None
        self.no_lang = False
        self.english = False

    def finalize_options(self):
        if self.build_dir is None:
            self.build_dir = 'po'
        if not self.output:
            self.output = (self.distribution.get_name() or 'messages')+'.pot'
        if self.lang is not None:
            self.lang = [i.strip() for i in self.lang.split(',') if i.strip()]
        if self.lang and self.no_lang:
            raise DistutilsOptionError("You can't use options "
                "--lang=XXX and --no-lang in the same time.")

    def _force_LF(self, src, dst=None):
        f = open(src, 'rU')
        try:
            content = f.read()
        finally:
            f.close()
        if dst is None:
            dst = src
        f = open(dst, 'wb')
        try:
            f.write(content)
        finally:
            f.close()

    def run(self):
        """Run xgettext for project sources"""
        import glob
        import os
        # project name based on `name` argument in setup() call
        prj_name = self.distribution.get_name()
        # output file
        if self.build_dir != '.':
            fullname = os.path.join(self.build_dir, self.output)
        else:
            fullname = self.output
        log.info('Generate POT file: ' + fullname)
        if not os.path.isdir(self.build_dir):
            log.info('Make directory: ' + self.build_dir)
            os.makedirs(self.build_dir)
        self.spawn(['xgettext',
                    '--keyword=N_',
                    '-p', self.build_dir,
                    '-o', self.output,
                    '__init__.py',
                    ] + glob.glob('lib/*.py'))
        self._force_LF(fullname)
        # regenerate english PO
        if self.english:
            log.info('Regenerating English PO file...')
            if prj_name:
                en_po = prj_name + '-' + 'en.po'
            else:
                en_po = 'en.po'
            self.spawn(['msginit',
                '--no-translator',
                '-l', 'en',
                '-i', os.path.join(self.build_dir, self.output),
                '-o', os.path.join(self.build_dir, en_po),
                ])
        # search and update all po-files
        if self.no_lang:
            return
        for po in glob.glob(os.path.join(self.build_dir,'*.po')):
            if self.lang is not None:
                po_lang = os.path.splitext(os.path.basename(po))[0]
                if prj_name and po_lang.startswith(prj_name+'-'):
                    po_lang = po_lang[5:]
                if po_lang not in self.lang:
                    continue
            new_po = po + ".new"
            cmd = "msgmerge %s %s -o %s" % (po, fullname, new_po)
            self.spawn(cmd.split())
            # force LF line-endings
            log.info("%s --> %s" % (new_po, po))
            self._force_LF(new_po, po)
            os.unlink(new_po)
