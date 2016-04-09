# -*- coding: utf-8 -*-
#
# QBzr - Qt frontend to Bazaar commands
# Copyright (C) 2008 Lukáš Lalinský <lalinsky@gmail.com>
# Copyright (C) 2009-2016 QBzr Developers
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
 * qignore - Ignore files or patterns.
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
 * qverify-signatures - Show digital signatures information
 * qversion - Show version/system information.

Hybrid dialogs:

 * qgetnew - Creates a new working tree (either a checkout or full branch).
 * qgetupdates - Fetches external changes into the working tree.

Additional commands:

 * qbrowse - Show inventory or working tree.
 * qconfig - Configure Bazaar and QBzr.
 * qrun - Run arbitrary bzr command.
 * qviewer - Simple file viewer.

Miscellaneous:

 * bug-url - print full URL to a specific bug, or open it in your browser.
"""

from __future__ import absolute_import

version_info = (0,23,2,'final',0)
__version__ = '.'.join(map(str, version_info))


import bzrlib
from bzrlib import api

def require_mimimum_api(object_with_api, wanted_mimimum_api):
    """Check if object_with_api supports the mimimum api version
    wanted_mimimum_api.

    :param object_with_api: An object which exports an API minimum and current
        version. See get_minimum_api_version and get_current_api_version for
        details.
    :param wanted_mimimum_api: The API version for which support is required.
    :return: None
    :raises IncompatibleAPI: When the wanted_api is not supported by
        object_with_api.
    """
    current = api.get_current_api_version(object_with_api)
    minimum = api.get_minimum_api_version(object_with_api)
    if wanted_mimimum_api > minimum:
        from bzrlib.errors import IncompatibleAPI
        raise IncompatibleAPI(object_with_api, wanted_mimimum_api,
                              minimum, current)

require_mimimum_api(bzrlib, (2, 1, 0))

from bzrlib.commands import plugin_cmds


# merge --qpreview disabled for 0.14 because it makes qbzr incompatible with bzr-pipeline plugin
# see bug https://bugs.launchpad.net/bugs/395817
#register_lazy_command('bzrlib.plugins.qbzr.lib.commands', 'cmd_merge', [], decorate=True)  # provides merge --qpreview

lazy_commands = (
    # module, command, [aliases]
    ('bzrlib.plugins.qbzr.lib.commands', 'cmd_qadd', []),
    ('bzrlib.plugins.qbzr.lib.commands', 'cmd_qannotate', ['qann', 'qblame']),
    ('bzrlib.plugins.qbzr.lib.commands', 'cmd_qbind', []),
    ('bzrlib.plugins.qbzr.lib.commands', 'cmd_qbranch', []),
    ('bzrlib.plugins.qbzr.lib.commands', 'cmd_qbrowse', ['qbw']),
    ('bzrlib.plugins.qbzr.lib.commands', 'cmd_qmain', []),
    ('bzrlib.plugins.qbzr.lib.commands', 'cmd_qcat', []),
    ('bzrlib.plugins.qbzr.lib.commands', 'cmd_qcommit', ['qci']),
    ('bzrlib.plugins.qbzr.lib.commands', 'cmd_qconfig', ['qconfigure']),
    ('bzrlib.plugins.qbzr.lib.commands', 'cmd_qconflicts', ['qresolve']),
    ('bzrlib.plugins.qbzr.lib.commands', 'cmd_qdiff', ['qdi']),
    ('bzrlib.plugins.qbzr.lib.commands', 'cmd_qexport', []),
    ('bzrlib.plugins.qbzr.lib.commands', 'cmd_qgetnew', ['qgetn']),
    ('bzrlib.plugins.qbzr.lib.commands', 'cmd_qgetupdates', ['qgetu', 'qgetup']),
    ('bzrlib.plugins.qbzr.lib.commands', 'cmd_qhelp', []),
    ('bzrlib.plugins.qbzr.lib.commands', 'cmd_qignore', []),
    ('bzrlib.plugins.qbzr.lib.commands', 'cmd_qinfo', []),
    ('bzrlib.plugins.qbzr.lib.commands', 'cmd_qinit', []),
    ('bzrlib.plugins.qbzr.lib.commands', 'cmd_qlog', []),
    ('bzrlib.plugins.qbzr.lib.commands', 'cmd_qmerge', []),
    ('bzrlib.plugins.qbzr.lib.commands', 'cmd_qplugins', []),
    ('bzrlib.plugins.qbzr.lib.commands', 'cmd_qpull', []),
    ('bzrlib.plugins.qbzr.lib.commands', 'cmd_qpush', []),
    ('bzrlib.plugins.qbzr.lib.commands', 'cmd_qrevert', []),
    ('bzrlib.plugins.qbzr.lib.commands', 'cmd_qrun', ['qcmd']),
    ('bzrlib.plugins.qbzr.lib.commands', 'cmd_qshelve', []),
    ('bzrlib.plugins.qbzr.lib.commands', 'cmd_qunshelve', []),
    ('bzrlib.plugins.qbzr.lib.commands', 'cmd_qtag', []),
    ('bzrlib.plugins.qbzr.lib.commands', 'cmd_quncommit', []),
    ('bzrlib.plugins.qbzr.lib.commands', 'cmd_qupdate', ['qup']),
    ('bzrlib.plugins.qbzr.lib.commands', 'cmd_qverify_signatures', []),
    ('bzrlib.plugins.qbzr.lib.commands', 'cmd_qversion', ['qsysinfo']),
    ('bzrlib.plugins.qbzr.lib.commands', 'cmd_qviewer', []),
    ('bzrlib.plugins.qbzr.lib.commands', 'cmd_qsend', ['qsend']),
    ('bzrlib.plugins.qbzr.lib.commands', 'cmd_qswitch', []),
    ('bzrlib.plugins.qbzr.lib.commands', 'cmd_qunbind', []),
    # extra commands
    ('bzrlib.plugins.qbzr.lib.extra.bugurl', 'cmd_bug_url', []),
    ('bzrlib.plugins.qbzr.lib.extra.isignored', 'cmd_is_ignored', []),
    ('bzrlib.plugins.qbzr.lib.extra.isversioned', 'cmd_is_versioned', []),
    # hidden power of qbzr ;-)
    ('bzrlib.plugins.qbzr.lib.commands', 'cmd_qsubprocess', []),
)

for module, name, aliases in lazy_commands:
    plugin_cmds.register_lazy(name, aliases, module)


def post_uncommit_hook(local, master, old_revno, old_tip, new_revno, hook_new_tip):
    from bzrlib.plugins.qbzr.lib.commit_data import QBzrCommitData
    branch = local or master
    ci_data = QBzrCommitData(branch=branch)
    ci_data.set_data_on_uncommit(old_tip, hook_new_tip)
    ci_data.save()


try:
    from bzrlib.hooks import install_lazy_named_hook
except ImportError:
    from bzrlib.branch import Branch
    Branch.hooks.install_named_hook('post_uncommit', post_uncommit_hook,
        'Remember uncomitted revision data for qcommit')
else:
    install_lazy_named_hook("bzrlib.branch", "Branch.hooks", 'post_uncommit',
        post_uncommit_hook, 'Remember uncomitted revision data for qcommit')


def load_tests(basic_tests, module, loader):
    from bzrlib.plugins.qbzr.lib.tests import load_tests
    return load_tests(basic_tests, module, loader)
