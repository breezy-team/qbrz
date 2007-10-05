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

from distutils.core import Command


class build_pot(Command):
    """Distutils command build_pot"""

    description = 'Extract strings from python sources for translation'

    # List of options:
    #   - long name,
    #   - short name (None if no short name),
    #   - help string.
    user_options = [('build-dir=', 'd', 'Directory to put POT file'),
                    ('output=', 'o', 'POT filename'),
                   ]

    def initialize_options(self):
        self.build_dir = None
        self.output = None

    def finalize_options(self):
        if self.build_dir is None:
            self.build_dir = 'po'
        if not self.output:
            self.output = (self.distribution.get_name() or 'messages')+'.pot'

    def run(self):
        """Run pygettext.py for QBzr sources"""
        import glob
        import os
        import shutil
        # output file
        if self.build_dir != '.':
            fullname = os.path.join(self.build_dir, self.output)
        else:
            fullname = self.output
        print 'Generate POT file:', fullname
        if not os.path.isdir(self.build_dir):
            print 'Make directory:', self.build_dir
            os.makedirs(self.build_dir)
        self.spawn(['python',
                    'extras/pygettext.py',
                    '-p', self.build_dir,
                    '-o', self.output,
                    '*.py'
                    ])
        # search and update all po-files
        for po in glob.glob(os.path.join(self.build_dir,'*.po')):
            cmd = "msgmerge %s %s -o %s.new" % (po, fullname, po)
            self.spawn(cmd.split())
            print "%s.new --> %s" % (po, po)
            shutil.move("%s.new" % po, po)
