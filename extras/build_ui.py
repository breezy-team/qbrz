# -*- coding: utf-8 -*-
#
# QBzr - Qt frontend to Bazaar commands
# Copyright (C) 2007 Lukáš Lalinský <lalinsky@gmail.com>
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

from distutils import log
from PyQt5.QtWidgets import *
from distutils.core import Command
from distutils.dep_util import newer
from io import StringIO
import glob
import os
import re


_translate_re = re.compile(r'QtGui\.QCoreApplication.translate\(.*?, (.*?), None, QtGui\.QApplication\)')
_import_re = re.compile(r'(from PyQt5 import QtCore, QtGui)')


class build_ui(Command):
    description = "build Qt UI files"
    user_options = [
        ('force', 'f', 'Force creation of ui files'),
        ('module=', 'm', 'Specify UI module to (re)build'),
        ]
    boolean_options = ['force']

    def initialize_options(self):
        self.force = None
        self.module = None

    def finalize_options(self):
        if not self.module:
            self.module = glob.glob("ui/*.ui")
        else:
            self.module = ['ui/%s.ui' % self.module]

    def run(self):
        from PyQt5 import uic
        # project name based on `name` argument in setup() call
        prj_name = self.distribution.get_name() or '?'

        for uifile in self.module:
            uifile = uifile.replace('\\', '/')
            pyfile = "lib/ui_%s.py" % os.path.splitext(os.path.basename(uifile))[0]
            if self.force or newer(uifile, pyfile):
                log.info("compiling %s -> %s", uifile, pyfile)
                tmp = StringIO()
                uic.compileUi(uifile, tmp)
                source = _translate_re.sub(r'gettext(\1)', tmp.getvalue())
                source = source.replace("from PyQt5 import QtCore, QtGui, QtWidgets",
                    "from PyQt5 import QtCore, QtGui, QtWidgets\n"
                    "from breezy.plugins.%s.lib.i18n import gettext\n" % prj_name)
                # f = open(pyfile, "wb")
                f = open(pyfile, "w")
                f.write(source)
                f.close()
