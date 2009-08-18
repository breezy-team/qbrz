# -*- coding: utf-8 -*-
#
# QBzr - Qt frontend to Bazaar commands
# Copyright (C) 2006-2008 Lukáš Lalinský <lalinsky@gmail.com>
# Copyright (C) 2008, 2009 Alexander Belchenko
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

import os, sys

if getattr(sys, "frozen", None):
    # Add our required extra libraries for the standalone bzr.exe to path
    sys.path.append(os.path.normpath(os.path.join(os.path.dirname(__file__), '..', '_lib')))

if sys.version_info < (2, 5):
    def _all_2_4_compat(iterable):
        for element in iterable:
            if not element:
                return False
        return True
        
    def _any_2_4_compat(iterable):
        for element in iterable:
            if element:
                return True
        return False

    import __builtin__
    __builtin__.all = _all_2_4_compat
    __builtin__.any = _any_2_4_compat

# Special constant
MS_WINDOWS = (sys.platform == 'win32')
