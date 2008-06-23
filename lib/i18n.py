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

"""I18N and L10N support for QBzr"""

import gettext as _gettext
import os
import sys


# Windows does not use $LANG by default
if sys.platform == 'win32':
    for i in ('LANGUAGE','LC_ALL','LC_MESSAGES','LANG'):
        if os.environ.get(i):
            break
    else:
        lang = None
        import locale
        try:
            import ctypes
        except ImportError:
            # use only user's default locale
            lang = locale.getdefaultlocale()[0]
        else:
            # using ctypes to determine all locales
            lcid_user = ctypes.windll.kernel32.GetUserDefaultLCID()
            lcid_system = ctypes.windll.kernel32.GetSystemDefaultLCID()
            if lcid_user != lcid_system:
                lcid = [lcid_user, lcid_system]
            else:
                lcid = [lcid_user]
            lang = [locale.windows_locale.get(i) for i in lcid]
            lang = ':'.join([i for i in lang if i])
        # set lang code for gettext
        if lang:
            os.environ['LANGUAGE'] = lang


d = os.path.join(os.path.realpath(os.path.dirname(__file__)), '..', 'locale')
t = _gettext.translation('qbzr', localedir=d, fallback=True)

# functions for interface translation
ngettext = t.ungettext
gettext = t.ugettext
N_ = lambda x: x


def disable():
    """Disable translations (e.g. for unit tests)"""
    global ngettext, gettext
    ngettext = N_
    gettext = N_


# additional strings for translation
if 0:
    # file kinds
    N_('file')
    N_('directory')
    N_('symlink')
    # bugs status
    N_('fixed')
