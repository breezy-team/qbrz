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

"""build_pot command for setup.py"""

import glob
from distutils import log
from distutils.core import Command
from distutils.errors import DistutilsOptionError

from .en_po import regenerate_en


class build_pot(Command):
    """Distutils command build_pot"""

    description = 'extract strings from python sources for translation'

    # List of options:
    #   - long name,
    #   - short name (None if no short name),
    #   - help string.
    user_options = [('build-dir=', 'd', 'Directory to put POT file'),
                    ('output=', 'o', 'POT filename'),
                    ('lang=', None, 'Comma-separated list of languages to update po-files'),
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
            self.output = (self.distribution.get_name() or 'messages')+ '.pot'
        if self.lang is not None:
            self.lang = [i.strip() for i in self.lang.split(',') if i.strip()]
        if self.lang and self.no_lang:
            raise DistutilsOptionError("You can't use options --lang=XXX and --no-lang in the same time.")

    def _force_LF(self, src, dst=None):
        with open(src, 'rU') as f:
            content = f.read()
        if dst is None:
            dst = src
        with open(dst, 'wb') as f:
            f.write(content)

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


        # RJLRJL: TODO: bypassed for now, to not shred what we have
        # self.spawn(['xgettext',
        #             '--keyword=N_',
        #             '-p', self.build_dir,
        #             '-o', self.output,
        #             '__init__.py',
        #             ] + glob.glob('lib/*.py') + glob.glob('lib/widgets/*.py')
        #             )
        # self._force_LF(fullname)

        # regenerate english PO
        print('self.english is ', self.english, 'project is ', prj_name)
        if self.english:
            log.info('Regenerating English PO file...')
            log.info(' project: {0}, build_dir {1}, output {2}'.format(prj_name, self.build_dir, self.output))
            print('Regenerating English PO file...')
            print(' project: {0}, build_dir {1}, output {2}'.format(prj_name, self.build_dir, self.output))
            regenerate_en(prj_name, self.build_dir, self.output, self.spawn)
        # search and update all po-files
        if self.no_lang:
            print('No language: stopping')
            return
        for po in glob.glob(os.path.join(self.build_dir,'*.po')):
            print('\tworking on ', po)
            if self.lang is not None:
                po_lang = os.path.splitext(os.path.basename(po))[0]
                if prj_name and po_lang.startswith(prj_name + '-'):
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
