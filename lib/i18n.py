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

"""I18N and L10N support"""

import gettext as _gettext
import os
import sys

_null_translation = _gettext.NullTranslations()
_translation = _null_translation


def gettext(s):
    return _translation.ugettext(s)

def ngettext(s, p, n):
    return _translation.ungettext(s, p, n)

def N_(s):
    return s


def install():
    global _translation
    if not os.environ.get('LANGUAGE'):
        from bzrlib import config
        lang = config.GlobalConfig().get_user_option('language')
        if lang:
            os.environ['LANGUAGE'] = lang
    if sys.platform == 'win32':
        _check_win32_locale()
    _translation = _gettext.translation('qbzr', localedir=_get_locale_dir(), fallback=True)


def uninstall():
    global _translation
    _translation = _null_translation


def _get_locale_dir():
    localedir = os.path.join(os.path.realpath(os.path.dirname(__file__)), '..', 'locale')
    if sys.platform.startswith('linux'):
        if not os.access(localedir, os.R_OK | os.X_OK):
            localedir = '/usr/share/locale'
    return localedir

def _check_win32_locale():
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


# additional strings for translation
if 0:
    # file kinds
    N_('file')
    N_('directory')
    N_('symlink')
    # bugs status
    N_('fixed')
    # qcat titles for various file types
    N_('View text file')
    N_('View image file')
    N_('View binary file')
    N_('View symlink')
    N_('View directory')
    #
    N_("No changes selected to commit")
    N_("No changes selected to revert")
