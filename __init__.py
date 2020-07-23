#!/usr/bin/python3 -bb
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

RJL 2020:
This is the updated version for QBrz
"""

import sys

if sys.version_info < (3,4,0):
    sys.stderr.write("You need python 3.4.0 or later to run this script\n")
    exit(1)
if sys.flags.bytes_warning < 2:
    sys.stderr.write("You must run the script with at least the -bb flag\n")
    exit(1)


# RJL to speed development, retain Qt4 for now: use ``sip.setapi`` to request
# version 1 behaviour for ``QVariant`` (otherwise it's not available for python3)
import sip
sip.setapi('QVariant', 2)

# RJL: set to 0,3,1 to match br
# version_info = (0,23,2,'final',0)
version_info = (0,3,1,'dev',0)
__version__ = '.'.join(map(str, version_info))


import breezy

from breezy.commands import plugin_cmds

# merge --qpreview disabled for 0.14 because it makes qbrz incompatible with bzr-pipeline plugin
# see bug https://bugs.launchpad.net/bugs/395817
#register_lazy_command('breezy.plugins.qbrz.lib.commands', 'cmd_merge', [], decorate=True)  # provides merge --qpreview

lazy_commands = (
    # module, command, [aliases]
    ('breezy.plugins.qbrz.lib.commands', 'cmd_qadd', []),
    ('breezy.plugins.qbrz.lib.commands', 'cmd_qannotate', ['qann', 'qblame']),
    ('breezy.plugins.qbrz.lib.commands', 'cmd_qbind', []),
    ('breezy.plugins.qbrz.lib.commands', 'cmd_qbranch', []),
    ('breezy.plugins.qbrz.lib.commands', 'cmd_qbrowse', ['qbw']),
    ('breezy.plugins.qbrz.lib.commands', 'cmd_qmain', []),
    ('breezy.plugins.qbrz.lib.commands', 'cmd_qcat', []),
    ('breezy.plugins.qbrz.lib.commands', 'cmd_qcommit', ['qci']),
    ('breezy.plugins.qbrz.lib.commands', 'cmd_qconfig', ['qconfigure']),
    ('breezy.plugins.qbrz.lib.commands', 'cmd_qconflicts', ['qresolve']),
    ('breezy.plugins.qbrz.lib.commands', 'cmd_qdiff', ['qdi']),
    ('breezy.plugins.qbrz.lib.commands', 'cmd_qexport', []),
    ('breezy.plugins.qbrz.lib.commands', 'cmd_qgetnew', ['qgetn']),
    ('breezy.plugins.qbrz.lib.commands', 'cmd_qgetupdates', ['qgetu', 'qgetup']),
    ('breezy.plugins.qbrz.lib.commands', 'cmd_qhelp', []),
    ('breezy.plugins.qbrz.lib.commands', 'cmd_qignore', []),
    ('breezy.plugins.qbrz.lib.commands', 'cmd_qinfo', []),
    ('breezy.plugins.qbrz.lib.commands', 'cmd_qinit', []),
    ('breezy.plugins.qbrz.lib.commands', 'cmd_qlog', []),
    ('breezy.plugins.qbrz.lib.commands', 'cmd_qmerge', []),
    ('breezy.plugins.qbrz.lib.commands', 'cmd_qplugins', []),
    ('breezy.plugins.qbrz.lib.commands', 'cmd_qpull', []),
    ('breezy.plugins.qbrz.lib.commands', 'cmd_qpush', []),
    ('breezy.plugins.qbrz.lib.commands', 'cmd_qrevert', []),
    ('breezy.plugins.qbrz.lib.commands', 'cmd_qrun', ['qcmd']),
    ('breezy.plugins.qbrz.lib.commands', 'cmd_qshelve', []),
    ('breezy.plugins.qbrz.lib.commands', 'cmd_qunshelve', []),
    ('breezy.plugins.qbrz.lib.commands', 'cmd_qtag', []),
    ('breezy.plugins.qbrz.lib.commands', 'cmd_quncommit', []),
    ('breezy.plugins.qbrz.lib.commands', 'cmd_qupdate', ['qup']),
    ('breezy.plugins.qbrz.lib.commands', 'cmd_qverify_signatures', []),
    ('breezy.plugins.qbrz.lib.commands', 'cmd_qversion', ['qsysinfo']),
    ('breezy.plugins.qbrz.lib.commands', 'cmd_qviewer', []),
    ('breezy.plugins.qbrz.lib.commands', 'cmd_qsend', ['qsend']),
    ('breezy.plugins.qbrz.lib.commands', 'cmd_qswitch', []),
    ('breezy.plugins.qbrz.lib.commands', 'cmd_qunbind', []),
    # extra commands
    ('breezy.plugins.qbrz.lib.extra.bugurl', 'cmd_bug_url', []),
    ('breezy.plugins.qbrz.lib.extra.isignored', 'cmd_is_ignored', []),
    ('breezy.plugins.qbrz.lib.extra.isversioned', 'cmd_is_versioned', []),
    # hidden power of qbrz ;-)
    ('breezy.plugins.qbrz.lib.commands', 'cmd_qsubprocess', []),
)

for module, name, aliases in lazy_commands:
    plugin_cmds.register_lazy(name, aliases, module)


def post_uncommit_hook(local, master, old_revno, old_tip, new_revno, hook_new_tip):
    from breezy.plugins.qbrz.lib.commit_data import QBzrCommitData
    branch = local or master
    ci_data = QBzrCommitData(branch=branch)
    ci_data.set_data_on_uncommit(old_tip, hook_new_tip)
    ci_data.save()


try:
    from breezy.hooks import install_lazy_named_hook
except ImportError:
    from breezy.branch import Branch
    Branch.hooks.install_named_hook('post_uncommit', post_uncommit_hook,
        'Remember uncomitted revision data for qcommit')
else:
    install_lazy_named_hook("breezy.branch", "Branch.hooks", 'post_uncommit',
        post_uncommit_hook, 'Remember uncomitted revision data for qcommit')


def load_tests(basic_tests, module, loader):
    from breezy.plugins.qbrz.lib.tests import load_tests
    return load_tests(basic_tests, module, loader)
