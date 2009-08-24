# -*- coding: utf-8 -*-
#
# QBzr - Qt frontend to Bazaar commands
#
# Author: Alexander Belchenko, 2009
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

"""Copy additional (3rd party) libraries before building windows qbzr installer.
(These libs are required for custom bzr.exe).
"""

import os
import shutil
import sys


LIBDIR = os.path.join(os.path.dirname(__file__), '_lib')

def copy_pyqt4():
    print '*** Copy PyQt4 libs ***'
    import PyQt4
    from PyQt4 import QtCore
    if QtCore.PYQT_VERSION_STR != '4.4.3':
        raise ValueError('ERROR: This script should works ony with PyQt4 '
            'v.4.4.3; '
            'imported %s instead.' % QtCore.PYQT_VERSION_STR)
    sitedir = os.path.join(os.path.dirname(os.__file__),
                           'site-packages')
    print "Copy PyQt4 libs from", sitedir
    # sip.pyd
    basename = 'sip.pyd'
    src = os.path.join(sitedir, basename)
    dst = os.path.join(LIBDIR, basename)
    print 'Copying sip.pyd: %s -> %s' % (src, dst)
    shutil.copyfile(src, dst)
    # PyQt4 package
    print 'Copy minimal set of PyQt4 libs'
    files = (   # minimal set of required libs
        '__init__.py',
        'mingwm10.dll',
        'Qt.pyd',
        'QtCore.pyd',
        'QtCore4.dll',
        'QtGui.pyd',
        'QtGui4.dll',
        )
    basedir = os.path.dirname(PyQt4.__file__)
    for f in files:
        src = os.path.join(basedir, f)
        dst = os.path.join(LIBDIR, 'PyQt4', f)
        dstdir = os.path.dirname(dst)
        if not os.path.isdir(dstdir):
            print 'Creating directory %s' % dstdir
            os.mkdir(dstdir)
        print 'Copy %s -> %s' % (src, dst)
        shutil.copyfile(src, dst)

def copy_python_package(pkg):
    sitedir = os.path.join(os.path.dirname(os.__file__),
                           'site-packages')
    prefix = len(sitedir) + 1
    for root, dirs, files in os.walk(pkg):
        for i in files:
            ext = os.path.splitext(i)[1]
            if ext in ('.py', '.pyd'):
                src = os.path.join(root, i)
                dst = os.path.join(LIBDIR, root[prefix:], i)
                dstdir = os.path.dirname(dst)
                if not os.path.isdir(dstdir):
                    print 'Creating directory %s' % dstdir
                    os.mkdir(dstdir)
                print 'Copy %s -> %s' % (src, dst)
                shutil.copyfile(src, dst)

def copy_pygments():
    # copy pygments package
    print '*** Copy Pygments package ***'
    import pygments
    pkg = os.path.dirname(pygments.__file__)
    assert pkg.endswith('pygments')
    copy_python_package(pkg)
    # copy std lib module commands.py
    import commands
    src = os.path.splitext(commands.__file__)[0] + '.py'
    dst = os.path.join(LIBDIR, os.path.basename(src))
    print 'Copy %s -> %s' % (src, dst)
    shutil.copyfile(src, dst)

def copy_ctypes():
    # copy ctypes python package
    print '*** Copy ctypes package ***'
    import ctypes
    pkg = os.path.dirname(ctypes.__file__)
    assert pkg.endswith('ctypes')
    files = os.listdir(pkg)
    for f in files:
        if f.endswith('.py'):
            src = os.path.join(pkg, f)
            dst = os.path.join(LIBDIR, 'ctypes', f)
            dstdir = os.path.dirname(dst)
            if not os.path.isdir(dstdir):
                print 'Creating directory %s' % dstdir
                os.mkdir(dstdir)
            print 'Copy %s -> %s' % (src, dst)
            shutil.copyfile(src, dst)

def copy_win32event():
    # copy win32event.pyd C-extension (from pywin32)
    print '*** Copy ctypes package ***'
    import win32event
    src = win32event.__file__
    dst = os.path.join(LIBDIR, os.path.basename(src))
    print 'Copy %s -> %s' % (src, dst)
    shutil.copyfile(src, dst)


def main():
    if sys.platform != 'win32':
        print 'ERROR: This script should work only on Windows.'
        return 1
    if sys.version_info[:2] != (2, 5):
        print 'ERROR: This script intended to work with Python 2.5.'
        return 1
    try:
        copy_pyqt4()
    except ValueError, e:
        print str(e)
        return 2
    copy_pygments()
    copy_ctypes()
    copy_win32event()
    print '*** Done. ***'
    return 0

if __name__ == '__main__':
    sys.exit(main())