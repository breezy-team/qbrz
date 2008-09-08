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

from bzrlib import commands, workingtree, errors, trace

class cmd_is_versioned(commands.Command):
    """Check if a path is versioned.

    :Exit values:
        0 - not versioned
        1 - versioned
        3 - error
    """

    takes_args = ['filename']
    hidden = True

    def run(self, filename):
        tree, relpath = workingtree.WorkingTree.open_containing(filename)
        if tree.path2id(relpath):
            if not trace.is_quiet():
                print >>self.outf, 'versioned'
            return 1
        else:
            if not trace.is_quiet():
                print >>self.outf, 'not versioned'
            return 0
