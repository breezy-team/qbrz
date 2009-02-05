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

"""check_utf8 command for setup.py.
It checks contents of source files to be UTF-8 encoded.
"""

from distutils.core import Command
from distutils.errors import DistutilsPlatformError
from distutils import log
import os
import sys


class check_utf8(Command):

    description = ("check contents of source files to be UTF-8 encoded")
    user_options = []

    def initialize_options(self):
        pass

    def finalize_options(self):
        pass

    def run(self):
        for root, dirs, files in os.walk('.'):
            for fname in sorted(files):
                ext = os.path.splitext(fname)[1].lower()
                if ext in ('.py', '.txt', '.ui'):
                    fullname = os.path.join(root, fname)[2:]    # first 2 characters is ./
                    # verbose: 0=quiet, 1=normal, 2=verbose
                    if self.verbose:
                        log.info('checking ' + fullname)
                    if not self.dry_run:
                        f = open(fullname, 'rb')
                        content = f.read()
                        f.close()
                        try:
                            content.decode('utf-8')
                        except UnicodeDecodeError, e:
                            log.error(fullname + ': ' + str(e))
            # skip some directories
            for dname in dirs[:]:
                fullname = os.path.join(root, dname).replace('\\','/')
                if fullname in ('./_lib', './build', './dist', './installer'):
                    dirs.remove(dname)
