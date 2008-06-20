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
from distutils.errors import DistutilsPlatformError
from distutils import log
import os
import shutil
import sys


class bdist_nsis(Command):

    description = "create an executable installer for MS Windows with NSIS"

    user_options = [
        ('nsi-script', None, "NSIS script to compile"),
        ('skip-build', None,
            "skip rebuilding everything (for testing/debugging)"),
        ('nsis-compiler', None, "full path to NSIS compiler executable"),
        ('copy-pyqt4', None, "copy PyQt4 libs from Python 2.5 site-packages"),
        ]

    boolean_options = ['skip-build', 'copy-pyqt4']

    def initialize_options(self):
        self.nsi_script = None
        self.skip_build = False
        self.nsis_compiler = None
        self.copy_pyqt4 = False

    def finalize_options(self):
        if not self.nsi_script:
            name = self.distribution.get_name() or ''
            if name:
                script_name = 'installer/%s-setup.nsi' % name
            else:
                script_name = 'installer/setup.nsi'
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
        if self.copy_pyqt4:
            if sys.platform != 'win32':
                raise DistutilsPlatformError(
                    '--copy-pyqt4 option supported only on Windows.')
            if sys.version_info[:2] != (2, 5):
                raise DistutilsPlatformError(
                    '--copy-pyqt4 option require Python 2.5')

    def _do_copy_pyqt4(self):
        import PyQt4
        sitedir = os.path.join(os.path.dirname(os.__file__),
                               'site-packages')
        print "Copy PyQt4 libs from", sitedir
        # sip.pyd
        basename = 'sip.pyd'
        src = os.path.join(sitedir, basename)
        dst = os.path.join('installer', '_lib', basename)
        log.info('copying sip.pyd: %s -> %s', src, dst)
        shutil.copyfile(src, dst)
        # PyQt4 package
        log.info('copying PyQt4 package')
        pkg = os.path.join(sitedir, 'PyQt4')
        prefix = len(sitedir) + 1
        for root, dirs, files in os.walk(pkg):
            for i in files:
                ext = os.path.splitext(i)[1]
                if ext in ('.py', '.pyd'):
                    src = os.path.join(root, i)
                    dst = os.path.join('installer', '_lib', root[prefix:], i)
                    dstdir = os.path.dirname(dst)
                    if not os.path.isdir(dstdir):
                        log.info('Creating directory %s', dstdir)
                        os.mkdir(dstdir)
                    log.info('Copying %s -> %s', src, dst)
                    shutil.copyfile(src, dst)

    def run(self):
        if not self.skip_build:
            self.run_command('build')
        if self.copy_pyqt4:
            self._do_copy_pyqt4()
        print 'Run NSIS compiler'
        self.spawn([self.nsis_compiler, self.nsi_script])


# plug-in our bdist builder to distutils collection
bdist.format_commands.append('nsis')
bdist.format_command['nsis'] = ('bdist_nsis', 'Windows NSIS-based installer')
