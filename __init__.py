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

"""QBzr - Qt-based frontend for Bazaar

Provided commands:
    qannotate, qbrowse, qcat, qcommit, qconfig, qdiff, qlog, qpull, qpush.
"""

from bzrlib.commands import register_command


version_info = (0, 9, 4, 'dev', 0)
__version__ = '.'.join(map(str, version_info))


class LazyCommand(object):

    def __init__(self, module, name, aliases):
        self._module = module
        self._name = name
        self.aliases = aliases
        self.__name__ = name

    def __call__(self, *args, **kwargs):
        mod = __import__(self._module, globals(), locals(), [1])
        return getattr(mod, self._name)(*args, **kwargs)


def register_command_lazy(module, name, aliases):
    register_command(LazyCommand(module, name, aliases))


register_command_lazy('bzrlib.plugins.qbzr.lib.commands', 'cmd_merge', [])
register_command_lazy('bzrlib.plugins.qbzr.lib.commands', 'cmd_qannotate', ['qann', 'qblame'])
register_command_lazy('bzrlib.plugins.qbzr.lib.commands', 'cmd_qbranch', [])
register_command_lazy('bzrlib.plugins.qbzr.lib.commands', 'cmd_qbrowse', ['qbw'])
register_command_lazy('bzrlib.plugins.qbzr.lib.commands', 'cmd_qbzr', [])
register_command_lazy('bzrlib.plugins.qbzr.lib.commands', 'cmd_qcat', [])
register_command_lazy('bzrlib.plugins.qbzr.lib.commands', 'cmd_qcommit', ['qci'])
register_command_lazy('bzrlib.plugins.qbzr.lib.commands', 'cmd_qconfig', ['qconfigure'])
register_command_lazy('bzrlib.plugins.qbzr.lib.commands', 'cmd_qdiff', ['qdi'])
register_command_lazy('bzrlib.plugins.qbzr.lib.commands', 'cmd_qinfo', [])
register_command_lazy('bzrlib.plugins.qbzr.lib.commands', 'cmd_qlog', [])
register_command_lazy('bzrlib.plugins.qbzr.lib.commands', 'cmd_qmerge', [])
register_command_lazy('bzrlib.plugins.qbzr.lib.commands', 'cmd_qpull', [])
register_command_lazy('bzrlib.plugins.qbzr.lib.commands', 'cmd_qpush', [])
register_command_lazy('bzrlib.plugins.qbzr.lib.commands', 'cmd_qsubprocess', [])


def test_suite():
    # disable gettext
    from bzrlib.plugins.qbzr.lib import i18n
    i18n.disable()
    # load tests
    from bzrlib.tests import TestUtil
    suite = TestUtil.TestSuite()
    loader = TestUtil.TestLoader()
    testmod_names = ['test_util', 'test_diffview', 'test_autocomplete']
    suite.addTest(loader.loadTestsFromModuleNames(
            ["%s.lib.%s" % (__name__, name) for name in testmod_names]))
    return suite
