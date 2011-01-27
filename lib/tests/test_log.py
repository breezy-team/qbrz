# -*- coding: utf-8 -*-
#
# Copyright (C) 2009 Gary van der Merwe <garyvdm@gmail.com>
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

from bzrlib.tests import TestCase, TestCaseWithTransport
from bzrlib import errors
from bzrlib.transport import memory

from PyQt4 import QtCore, QtGui

from bzrlib.plugins.qbzr.lib import tests as qtests
from bzrlib.plugins.qbzr.lib.log import LogWindow

class TestLogSmokeTests(qtests.QTestCase):

    def test_show_log_blank_branch(self):
        tree1 = self.make_branch_and_tree('tree1')

        win = LogWindow(['tree1'], None)
        self.addCleanup(win.close)
        win.show()
        QtCore.QCoreApplication.processEvents()
        QtCore.QCoreApplication.processEvents()

    def test_show_log_simple_commit(self):
        wt = self.make_branch_and_tree('.')
        wt.commit('empty commit')
        self.build_tree(['hello'])
        wt.add('hello')
        wt.commit('add one file',
                  committer=u'\u013d\xf3r\xe9m \xcdp\u0161\xfam '
                            u'<test@example.com>')

        win = LogWindow(['.'], None)
        self.addCleanup(win.close)
        win.show()
        QtCore.QCoreApplication.processEvents()
        QtCore.QCoreApplication.processEvents()


class TestLogGetBranchesAndFileIds(qtests.QTestCase):

    def test_with_branch(self):
        tree = self.make_branch_and_tree("branch")

        win = LogWindow(branch=tree.branch, tree=tree)
        branches, primary_bi, file_ids = win.get_branches_and_file_ids()

        self.assertLength(1, branches)
        bi = branches[0]

        # this is broken because we can't pass a tree to LogWindow
        self.assertEqual(tree, bi.tree)
        self.assertEqual(tree.branch, bi.branch)
        #self.assertEqual(None, bi.index)

        self.assertEqual(branches[0], primary_bi)
        self.assertEqual(None, file_ids)

    def test_open_branch_without_passing_tree(self):
        tree = self.make_branch_and_tree("branch")

        win = LogWindow(branch=tree.branch)
        branches, primary_bi, file_ids = win.get_branches_and_file_ids()

        self.assertEqual(tree.basedir, branches[0].tree.basedir)

    def test_open_branch_without_tree(self):
        branch = self.make_branch("branch")

        win = LogWindow(branch=branch)
        branches, primary_bi, file_ids = win.get_branches_and_file_ids()

        bi = branches[0]
        self.assertEqual(None, bi.tree)
        self.assertEqual(branch, bi.branch)

    def make_branch_and_tree_with_files_and_dir(self):
        tree = self.make_branch_and_tree("branch")
        self.build_tree(['branch/file1', 'branch/dir/', 'branch/file3'])
        tree.add('file1', 'file1-id')
        tree.add('dir', 'dir-id')
        tree.add('file3', 'file3-id')
        tree.commit(message='add files')
        return tree

    def check_open_branch_files(self, tree, branch):
        win = LogWindow(branch=branch, specific_file_ids = ['file1-id']) 
        branches, primary_bi, file_ids = win.get_branches_and_file_ids()

        self.assertLength(1, branches)
        bi = branches[0]
        self.assertEqual(branch, bi.branch)

        self.assertEqual(['file1-id'], file_ids)

    def test_open_branch_files(self):
        tree = self.make_branch_and_tree_with_files_and_dir()
        self.check_open_branch_files(tree, tree.branch)

    def test_open_branch_files_with_tree(self):
        tree = self.make_branch_and_tree_with_files_and_dir()
        branch = tree.branch
        tree.bzrdir.destroy_workingtree()
        self.check_open_branch_files(None, branch)

    def branches_to_base(self, branches):
        for bi in branches:
            if  bi.tree is None:
                yield (None, bi.branch.base, bi.index)
            else:
                yield (bi.tree.basedir, bi.branch.base, bi.index)

    def test_open_locations_standalone_branches(self):
        branch1 = self.make_branch("branch1")
        tree2 = self.make_branch_and_tree("branch2")

        win = LogWindow(locations=["branch1", "branch2"])
        branches, primary_bi, file_ids = win.get_branches_and_file_ids()

        self.assertEqual(set(((None,          branch1.base, None),
                              (tree2.basedir, tree2.branch.base, None) )),
                         set(self.branches_to_base(branches)))

    def make_branch_in_shared_repo(self, relpath, format=None):
        """Create a branch on the transport at relpath."""
        made_control = self.make_bzrdir(relpath, format=format)
        return made_control.create_branch()

    def test_open_locations_shared_repo(self):
        self.make_branch = self.make_branch_in_shared_repo
        repo = self.make_repository("repo", shared=True)
        branch1 = self.make_branch("repo/branch1")
        tree2 = self.make_branch_and_tree("repo/branch2")

        win = LogWindow(locations=["repo"])
        branches, primary_bi, file_ids = win.get_branches_and_file_ids()

        self.assertEqual(set(((None, branch1.base, None),
                          (tree2.basedir, tree2.branch.base, None))),
                         set(self.branches_to_base(branches)))

    def test_open_locations_in_shared_reporaise_not_a_branch(self):
        repo = self.make_repository("repo", shared=True)
        win = LogWindow(locations=["repo"])
        self.assertRaises(errors.NotBranchError,
                          win.get_branches_and_file_ids)

    def test_open_locations_raise_not_a_branch(self):
        self.vfs_transport_factory = memory.MemoryServer
        win = LogWindow(locations=[self.get_url("non_existant_branch")])
        self.assertRaises(errors.NotBranchError,
                          win.get_branches_and_file_ids)

    def check_open_location_files(self):
        win = LogWindow(locations=["branch/file1", 'branch/dir'])
        branches, primary_bi, file_ids = win.get_branches_and_file_ids()

        self.assertEqual(['file1-id', 'dir-id'], file_ids)

    def test_open_locations_files(self):
        tree = self.make_branch_and_tree_with_files_and_dir()
        self.check_open_location_files()

    def test_open_locations_files_without_tree(self):
        tree = self.make_branch_and_tree_with_files_and_dir()
        branch = tree.branch
        tree.bzrdir.destroy_workingtree()
        self.check_open_location_files()

    def test_open_locations_raise_not_versioned(self):
        branch = self.make_branch("branch")
        win = LogWindow(locations=["file-that-does-not-exist"])
        self.assertRaises(errors.BzrCommandError,
                          win.get_branches_and_file_ids)

    def test_branch_label_location(self):
        branch = self.make_branch("branch")
        win = LogWindow()

        self.assertEqual('path',
                         win.branch_label('path', branch))

    def test_branch_label_no_location(self):
        branch = self.make_branch("branch")
        win = LogWindow()

        # No location, use nick
        self.assertEqual('branch',
                         win.branch_label(None, branch))

    def test_branch_label_path_location(self):
        branch = self.make_branch("branch")
        win = LogWindow()

        # Location seems like a path - use it
        self.assertEqual('path-to-branch',
                         win.branch_label('path-to-branch', branch))

    def test_branch_label_alias_directory(self):
        branch = self.make_branch("branch")
        win = LogWindow()

        # show shortcut, and nick
        self.assertEqual(':parent (branch)',
                         win.branch_label(':parent', branch))

    def test_branch_label_no_info_locations(self):
        branch = self.make_branch("branch")
        win = LogWindow()

        # locations that don't have alot of info in them should show the nick
        self.assertEqual('. (branch)',
                         win.branch_label('.', branch))
        self.assertEqual('../ (branch)',
                         win.branch_label('../', branch))

    def test_branch_label_explict_nick(self):
        branch = self.make_branch("branch")
        branch.nick = "nick"
        win = LogWindow()

        self.assertEqual('path (nick)',
                         win.branch_label('path', branch))

    def test_branch_label_repository(self):
        repo = self.make_repository("repo", shared=True)
        branch = self.make_branch("repo/branch")

        win = LogWindow()

        self.assertEqual('./branch',
                         win.branch_label(None, branch, '.', repo))
