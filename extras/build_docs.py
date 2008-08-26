# -*- coding: utf-8 -*-
#
# QBzr - Qt frontend to Bazaar commands
# Copyright (C) 2008 Alexander Belchenko <bialix@ukr.net>
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

"""build_docs command for setup.py"""

from distutils.core import Command
from distutils.dep_util import newer
from distutils import log
import os
import sys


class build_docs(Command):

    description = 'translate txt files from docs/ to html with docutils'

    # List of options:
    #   - long name,
    #   - short name (None if no short name),
    #   - help string.
    user_options = [('output-dir=', 'o', 'Directory for output html files'),
                    ('force', 'f', 'Force creation of html files'),
                    ('clean', None, 'Clean html files'),
                   ]
    boolean_options = ['force', 'clean']

    def initialize_options(self):
        self.output_dir = None
        self.force = None
        self.clean = None

    def finalize_options(self):
        pass

    def iter_txt_files(self, from_dir, out_dir=None):
        """For each txt file yields 2 paths: source txt and target html."""
        if out_dir is None:
            out_dir = from_dir
        if not from_dir.endswith(os.sep):
            from_dir = from_dir + os.sep
        n = len(from_dir)
        for root, dirs, files in os.walk(from_dir):
            for f in files:
                if f.endswith('.txt'):
                    source = os.path.join(root, f)
                    relpath = source[n:]
                    target = os.path.join(out_dir, relpath[:-3]+'html')
                    yield source, target

    def do_clean(self):
        """Clean all generated html files"""
        for source, target in self.iter_txt_files('docs', self.output_dir):
            if os.path.isfile(target):
                log.info('removing ' + target)
                os.remove(target)

    def run(self):
        """Run rst2html for each txt file"""
        if self.clean:
            self.do_clean()
            return

        rst2html = ['rst2html.py']
        if sys.platform == 'win32':
            rst2html = ['python',
                os.path.join(sys.prefix, 'Scripts', 'rst2html.py')]

        for source, target in self.iter_txt_files('docs', self.output_dir):
            if self.force or newer(source, target):
                log.info('translating ' + source)
                self.spawn(rst2html + [source, target])
