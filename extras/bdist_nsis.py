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

"""bdist_nsis command for setup.py (create windows installer with NSIS)"""

from distutils.command.bdist import bdist
from distutils.core import Command
import os
import sys


class bdist_nsis(Command):

    description = "create an executable installer for MS Windows with NSIS"

    user_options = [
        ('nsi-script', None, "NSIS script to compile"),
        ('skip-build', None,
            "skip rebuilding everything (for testing/debugging)"),
        ('nsis-compiler', None, "full path to NSIS compiler executable"),
        ]

    boolean_options = ['skip-build']

    def initialize_options(self):
        self.nsi_script = None
        self.skip_build = False
        self.nsis_compiler = None

    def finalize_options(self):
        if not self.nsi_script:
            name = self.distribution.get_name() or ''
            if name:
                script_name = 'installer/%s-setup.nsi' % name
            else:
                script_name = 'installer/setup.nsi' % name
            print 'NOTE: will use %s script' % script_name
            self.nsi_script = script_name
        if not self.nsis_compiler:
            # auto-detect NSIS
            if sys.platform == 'win32':
                # read path from registry
                import _winreg
                nsis_dir = None
                try:
                    hkey = _winreg.OpenKey(_winreg.HKEY_LOCAL_MACHINE,
                        'SOFTWARE\\NSIS')
                    try:
                        nsis_dir = _winreg.QueryValue(hkey, '')
                    finally:
                        _winreg.CloseKey(hkey)
                except (EnvironmentError, WindowsError):
                    pass
                if nsis_dir:
                    self.nsis_compiler = os.path.join(nsis_dir, 'makensis.exe')
                else:
                    self.nsis_compiler = 'makensis.exe'
            else:
                self.nsis_compiler = 'makensis'

    def run(self):
        if not self.skip_build:
            self.run_command('build')
        print 'Run NSIS compiler'
        self.spawn([self.nsis_compiler, self.nsi_script])


# plug-in our bdist builder to distutils collection
bdist.format_commands.append('nsis')
bdist.format_command['nsis'] = ('bdist_nsis', 'Windows NSIS-based installer')
