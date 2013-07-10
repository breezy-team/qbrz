# -*- coding: utf-8 -*-
#
# QBzr - Qt frontend to Bazaar commands
# Copyright (C) 2013 QBzr Developers
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

"""Only for Windows."""

import ctypes
import platform

def is_vista_or_higher():
    win_ver = platform.win32_ver()[1]
    if win_ver >= '6':
        # Vista and Win7 are v.6.x
        return True
    else:
        return False

def is_aero_enabled():
    if not is_vista_or_higher():
        return False
    try:
        bResult = ctypes.c_int(0)
        # DwmIsCompositionEnabled function should tell us whether aero is enabled
        ctypes.windll.dwmapi.DwmIsCompositionEnabled(ctypes.byref(bResult))
        return bool(bResult.value)
    except Exception:   # that's really bad, I know, shame on me
        return False
