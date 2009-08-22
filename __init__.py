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

QBzr is a cross platform, Qt-based front-end for Bazaar, providing GUI
applications for many core bzr commands. In addition, it provides several
special dialogs and helper commands. Equivalents for core bzr commands have
the same names as CLI commands but with a prefix of "q".
QBzr requires Qt/PyQt 4.4.x or later to be installed.

Basic q-commands:

 * qadd - GUI for adding files or directories.
 * qannotate - Show the origin of each line in a file.
 * qbind - Convert the current branch into a checkout of the supplied branch.
 * qbranch - Create a new copy of a branch.
 * qcat - View the contents of a file as of a given revision.
 * qcommit - GUI for committing revisions.
 * qconflicts - Show conflicts.
 * qdiff - Show differences in working tree in a GUI window.
 * qexport - Export current or past revision to a destination directory or archive.
 * qinfo - Shows information about the current location.
 * qinit - Initializes a new branch or shared repository.
 * qlog - Show log of a repository, branch, file, or directory in a Qt window.
 * qmerge - Perform a three-way merge.
 * qplugins - Display information about installed plugins.
 * qpull - Turn this branch into a mirror of another branch.
 * qpush - Update a mirror of this branch.
 * qrevert - Revert changes files.
 * qsend - Mail or create a merge-directive for submitting changes.
 * qswitch - Set the branch of a checkout and update.
 * qtag - Edit tags.
 * qunbind - Convert the current checkout into a regular branch.
 * quncommit - Move the tip of a branch to an earlier revision.
 * qupdate - Update working tree with latest changes in the branch.
 * qversion - Show version/system information.

Hybrid dialogs:

 * qgetnew - Creates a new working tree (either a checkout or full branch).
 * qgetupdates - Fetches external changes into the working tree.

Additional commands:

 * qbrowse - Show inventory or working tree.
 * qconfig - Configure Bazaar and QBzr.
 * qviewer - Simple file viewer.

Miscellaneous:

 * bug-url - print full URL to a specific bug, or open it in your browser.
"""

version_info = (0, 15, 0, 'dev', 0)
__version__ = '.'.join(map(str, version_info))


from bzrlib import registry
from bzrlib.commands import register_command, plugin_cmds


class LazyCommandProxy(registry._LazyObjectGetter):

    def __init__(self, module, name, aliases):
        super(LazyCommandProxy, self).__init__(module, name)
        self.aliases = aliases
        self.__name__ = name

    def __call__(self, *args, **kwargs):
        return self.get_obj()(*args, **kwargs)

    def __getattr__(self, name):
        return getattr(self.get_obj(), name)


def register_lazy_command(module, name, aliases, decorate=False):
    """Lazily register a command.

    :param module: Name of the module where is the command defined
    :param name: Name of the command class; this Command subclass must
        exist in `module`
    :param aliases: List of command aliases
    :param decorate: If true, allow overriding an existing command
        of the same name; the old command is returned by this function.
        Otherwise it is an error to try to override an existing command.
    """
    #try:
        ## FIXME can't overwrite existing command
        #plugin_cmds.register_lazy(name, aliases, module)
    #except AttributeError:
    register_command(LazyCommandProxy(module, name, aliases), decorate)

# merge --qpreview disabled for 0.14 because it makes qbzr incompatible with bzr-pipeline plugin
# see bug https://bugs.launchpad.net/bugs/395817
#register_lazy_command('bzrlib.plugins.qbzr.lib.commands', 'cmd_merge', [], decorate=True)  # provides merge --qpreview
register_lazy_command('bzrlib.plugins.qbzr.lib.commands', 'cmd_qadd', [])
register_lazy_command('bzrlib.plugins.qbzr.lib.commands', 'cmd_qannotate', ['qann', 'qblame'])
register_lazy_command('bzrlib.plugins.qbzr.lib.commands', 'cmd_qbind', [])
register_lazy_command('bzrlib.plugins.qbzr.lib.commands', 'cmd_qbranch', [])
register_lazy_command('bzrlib.plugins.qbzr.lib.commands', 'cmd_qbrowse', ['qbw'])
register_lazy_command('bzrlib.plugins.qbzr.lib.commands', 'cmd_qmain', [])
register_lazy_command('bzrlib.plugins.qbzr.lib.commands', 'cmd_qcat', [])
register_lazy_command('bzrlib.plugins.qbzr.lib.commands', 'cmd_qcommit', ['qci'])
register_lazy_command('bzrlib.plugins.qbzr.lib.commands', 'cmd_qconfig', ['qconfigure'])
register_lazy_command('bzrlib.plugins.qbzr.lib.commands', 'cmd_qconflicts', ['qresolve'])
register_lazy_command('bzrlib.plugins.qbzr.lib.commands', 'cmd_qdiff', ['qdi'])
register_lazy_command('bzrlib.plugins.qbzr.lib.commands', 'cmd_qexport', [])
register_lazy_command('bzrlib.plugins.qbzr.lib.commands', 'cmd_qgetnew', ['qgetn'])
register_lazy_command('bzrlib.plugins.qbzr.lib.commands', 'cmd_qgetupdates', ['qgetu', 'qgetup'])
register_lazy_command('bzrlib.plugins.qbzr.lib.commands', 'cmd_qhelp', [])
register_lazy_command('bzrlib.plugins.qbzr.lib.commands', 'cmd_qinfo', [])
register_lazy_command('bzrlib.plugins.qbzr.lib.commands', 'cmd_qinit', [])
register_lazy_command('bzrlib.plugins.qbzr.lib.commands', 'cmd_qlog', [])
register_lazy_command('bzrlib.plugins.qbzr.lib.commands', 'cmd_qmerge', [])
register_lazy_command('bzrlib.plugins.qbzr.lib.commands', 'cmd_qplugins', [])
register_lazy_command('bzrlib.plugins.qbzr.lib.commands', 'cmd_qpull', [])
register_lazy_command('bzrlib.plugins.qbzr.lib.commands', 'cmd_qpush', [])
register_lazy_command('bzrlib.plugins.qbzr.lib.commands', 'cmd_qrevert', [])
register_lazy_command('bzrlib.plugins.qbzr.lib.commands', 'cmd_qsubprocess', [])
register_lazy_command('bzrlib.plugins.qbzr.lib.commands', 'cmd_qtag', [])
register_lazy_command('bzrlib.plugins.qbzr.lib.commands', 'cmd_quncommit', [])
register_lazy_command('bzrlib.plugins.qbzr.lib.commands', 'cmd_qupdate', ['qup'])
register_lazy_command('bzrlib.plugins.qbzr.lib.commands', 'cmd_qversion', ['qsysinfo'])
register_lazy_command('bzrlib.plugins.qbzr.lib.commands', 'cmd_qviewer', [])
register_lazy_command('bzrlib.plugins.qbzr.lib.commands', 'cmd_qsend', ['qsend'])
register_lazy_command('bzrlib.plugins.qbzr.lib.commands', 'cmd_qswitch', [])
register_lazy_command('bzrlib.plugins.qbzr.lib.commands', 'cmd_qunbind', [])

register_lazy_command('bzrlib.plugins.qbzr.lib.extra.bugurl', 'cmd_bug_url', [])
register_lazy_command('bzrlib.plugins.qbzr.lib.extra.isignored', 'cmd_is_ignored', [])
register_lazy_command('bzrlib.plugins.qbzr.lib.extra.isversioned', 'cmd_is_versioned', [])


def post_uncommit_hook(local, master, old_revno, old_tip, new_revno, hook_new_tip):
    from bzrlib.plugins.qbzr.lib.commit_data import QBzrCommitData
    branch = local or master
    ci_data = QBzrCommitData(branch=branch)
    ci_data.set_data_on_uncommit(old_tip, hook_new_tip)
    ci_data.save()

from bzrlib.branch import Branch
Branch.hooks.install_named_hook('post_uncommit', post_uncommit_hook,
    'Remember uncomitted revision data for qcommit')


def load_tests(basic_tests, module, loader):
    from bzrlib.plugins.qbzr.lib.tests import load_tests
    return load_tests(basic_tests, module, loader)
