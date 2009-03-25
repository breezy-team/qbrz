# -*- coding: utf-8 -*-
#
# QBzr - Qt frontend to Bazaar commands
# Copyright (C) 2009 Alexander Belchenko <bialix@ukr.net>
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

"""import PO-files from launchpad-export.tar.gz (extra command for setup.py)"""

from distutils import log
from distutils.core import Command


class import_po(Command):
    """Distutils command build_pot"""

    description = 'import PO-files from launchpad-export.tar.gz'

    # List of options:
    #   - long name,
    #   - short name (None if no short name),
    #   - help string.
    user_options = [('tarball=', 'F', 'path to launchpad-export.tar.gz file'),
                    ('output-dir=', 'O', 'output directory (default: po)'),
                   ]
    boolean_options = []

    def initialize_options(self):
        self.tarball = None
        self.output_dir = None

    def finalize_options(self):
        if self.tarball is None:
            self.tarball = 'launchpad-export.tar.gz'
        if self.output_dir is None:
            self.output_dir = 'po'

    def run(self):
        """Unpack tarball with PO-files."""
        import os
        import tarfile

        log.info('Inspecting tarball...')
        t = tarfile.open(self.tarball)
        names = t.getnames()
        # filter names
        # names could have 'qbzr/' or '/' prefix,
        # also there is some strange entries as './' (wtf lp?)
        # see https://bugs.launchpad.net/rosetta/+bug/148271
        entries = []    # 2-tuple (archive name, output file name)
        for n in names:
            fn = n
            if n == './':
                continue
            elif n.startswith('/'):
                fn = n[1:]
            elif n.startswith('qbzr/'):
                fn = n[5:]
            if not fn:
                continue
            entries.append((n, os.path.join(self.output_dir, fn)))
        log.info('Extracting...')
        for n, fn in entries:
            log.info('  %s -> %s' % (n, fn))
            ft = t.extractfile(n)
            fd = open(fn, 'wb')
            try:
                fd.write(ft.read())
            finally:
                fd.close()
        log.info('Done.')
