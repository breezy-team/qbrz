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

"""check_py24 command for setup.py.
It checks syntax of Python modules by compiling them with Python 2.4.
"""

from distutils.core import Command
from distutils.errors import DistutilsPlatformError
from distutils import log
import os
import sys
import traceback


class check_py24(Command):

    description = ("check syntax of python modules "
                   "by compiling them with Python 2.4")
    user_options = []

    def initialize_options(self):
        pass

    def finalize_options(self):
        if sys.version_info[:2] != (2, 4):
            raise DistutilsPlatformError(
                'check_py24 command require Python 2.4')

    def run(self):
        for root, dirs, files in os.walk('.'):
            for fname in sorted(files):
                if fname.endswith('.py'):
                    fullname = os.path.join(root, fname)[2:]    # first 2 characters is ./
                    # verbose: 0=quiet, 1=normal, 2=verbose
                    if self.verbose:
                        log.info('checking ' + fullname)
                    if not self.dry_run:
                        f = open(fullname, 'rU')    # rU automatically converts CRLF to LF
                        content = f.read()
                        f.close()
                        try:
                            compile(content, fullname, 'exec')
                        except SyntaxError, e:
                            log.error(str(e))
                            if self.verbose:
                                traceback.print_exc(0)
            # skip some directories
            for dname in dirs[:]:
                fullname = os.path.join(root, dname).replace('\\','/')
                if fullname in ('./_lib', './build', './dist', './installer'):
                    dirs.remove(dname)
