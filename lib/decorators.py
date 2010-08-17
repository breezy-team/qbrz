# -*- coding: utf-8 -*-
#
# QBzr - Qt frontend to Bazaar commands
# Copyright (C) 2010 QBzr Developers
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

"""Decorators for debugging and maybe main work mode."""

def print_in_out(unbound):
    """Decorator to print input arguments and return value of the function."""
    def _run(*args, **kwargs):
        from bzrlib.trace import mutter
        a = ','.join(repr(i) for i in args)
        b = ','.join('%s=%r' % (i,j) for (i,j) in kwargs.iteritems())
        if a and b:
            a = a + ',' + b
        else:
            a = a or b
        func_name = unbound.func_name
        mutter('Called %s(%s)' % (func_name, a))
        result = unbound(*args, **kwargs)
        mutter('%s returned %r' % (func_name, result))
        return result
    return _run
