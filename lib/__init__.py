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

# XXX maybe extract this into compatibility.py ?
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


# Features dictionary:
# keys are feature names, values are optional parameters for those features.
# the meaning of parameters depend on the feature, so it's more like config.
# The keys names can use namespaces in the form 'domain.option'.
#
# Intended usage of this dict by the external code:
#
# if feature_name in FEATURES: then_do_something(); else: backward_compatible_code()
#
# or
#
# feature_value = FEATURES.get(feature_name); if feature_value == XXX: then_do_something()
#
# NOTE: No external code should add the keys or change the values to this dict!!!
#
FEATURES = dict(
    # feature_name=None,        # for features without extra parameters
    # feature_name='1.2.3',     # to specify optional version or parameter
    # feature_name=[some list], # to specify the list of parameters
    # etc.
    qignore=None,       # we have qignore
    )
