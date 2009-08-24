# -*- coding: utf-8 -*-
#
# QBzr - Qt frontend to Bazaar commands
# Copyright (C) 2007 Lukáš Lalinský <lalinsky@gmail.com>
# Copyright (C) 2007, 2008 Alexander Belchenko <bialix@ukr.net>
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

from build_docs import build_docs
from build_mo import build_mo
from build_pot import build_pot
from build_ui import build_ui
from check_py24 import check_py24
from check_utf8 import check_utf8
from import_po import import_po


cmdclass = {
    'build_docs': build_docs,
    'build_mo': build_mo,
    'build_pot': build_pot,
    'build_ui': build_ui,
    'check_py24': check_py24,
    'check_utf8': check_utf8,
    'import_po': import_po,
}
