# -*- coding: utf-8 -*-
#
# QBzr - Qt frontend to Bazaar commands
# Copyright (C) 2008 Lukáš Lalinský <lalinsky@gmail.com>
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

import os
import sys

if hasattr(sys, "frozen"):
    # "hack in" our PyQt4 binaries
    sys.path.append(os.path.normpath(os.path.join(
        os.path.dirname(__file__), '..', '..', '_lib')))


def load_tests(basic_tests, module, loader):
    testmod_names = [
        'test_autocomplete',
        #'test_diffview', - broken by API changes
        'test_extra_isignored',
        'test_extra_isversioned',
        'test_logmodel',
        'test_spellcheck',
        'test_util',
    ]
    basic_tests.addTests(loader.loadTestsFromModuleNames(
        ["%s.%s" % (__name__, name) for name in testmod_names]))
    return basic_tests
