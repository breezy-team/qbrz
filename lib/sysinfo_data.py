# -*- coding: utf-8 -*-
#
# QBzr - Qt frontend to Bazaar commands
# Copyright (C) 2009 Lukáš Lalinský <lalinsky@gmail.com>
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

import bzrlib
from bzrlib import bzrdir, config, errors, osutils, trace


def get_sys_info():
    """Get the system information.

    :return: a dictionary mapping fields to values. Field names are:
      * bzr-version - version of Bazaar
      * bzr-lib-path - paths to bzrlib roots (a list)
      * bzr-source-tree - source tree holding Bazaar (None or a Tree object)
      * bzr-config-dir - configuration directory holding bazaar.conf, etc.
      * bzr-log-file - path to bzr.log file
      * python-file - path to Python interpreter
      * python-version - version of Python interpreter
      * python-lib-dir - path to Python standard library
    """
    result = {}

    # Bazaar installation
    result["bzr-version"] = bzrlib.__version__
    result["bzr-lib-path"] = bzrlib.__path__
    # is bzrlib itself in a branch?
    source_tree = None  #_get_bzr_source_tree()
    if source_tree:
        result["bzr-source-tree"] = _source_tree_details()
    else:
        result["bzr-source-tree"] = None

    # Bazaar configuration
    config_dir = os.path.normpath(config.config_dir())  # use native slashes
    if not isinstance(config_dir, unicode):
        config_dir = config_dir.decode(osutils.get_user_encoding())
    result["bzr-config-dir"] = config_dir
    result["bzr-log-file"] = trace._bzr_log_filename

    # Python installation
    # (bzr.exe use python interpreter from pythonXY.dll
    # but sys.executable point to bzr.exe itself)
    if not hasattr(sys, 'frozen'):  # check for bzr.exe
        # python executable
        py_file = sys.executable
    else:
        # pythonXY.dll
        basedir = os.path.dirname(sys.executable)
        python_dll = "python%d%d.dll" % sys.version_info[:2]
        py_file = os.path.join(basedir, python_dll)
    result["python-file"] = py_file
    result["python-version"] = bzrlib._format_version_tuple(sys.version_info)
    result["python-lib-dir"] = os.path.dirname(os.__file__)
    return result


def _get_bzr_source_tree():
    """Return the WorkingTree for bzr source, if any.

    If bzr is not being run from its working tree, returns None.
    """
    try:
        control = bzrdir.BzrDir.open_containing(__file__)[0]
        return control.open_workingtree(recommend_upgrade=False)
    except (errors.NotBranchError, errors.UnknownFormatError,
            errors.NoWorkingTree):
        return None


def _source_tree_details(src_tree):
    """Get details about a source tree.

    :return: dictionary with keys of path, revno, revision-id, branch-nick.
    """
    result = {}
    src_revision_id = src_tree.last_revision()
    revno = src_tree.branch.revision_id_to_revno(src_revision_id)
    result["path"] = src_tree.basedir
    result["revno"] = revno
    result["revision-id"] = src_revision_id
    result["branch-nick"] = src_tree.branch.nick
    return result
