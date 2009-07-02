# -*- coding: utf-8 -*-
#
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

from bzrlib import tests
from bzrlib.plugins.qbzr.lib.loggraphprovider import LogGraphProvider
from bzrlib import errors

class TestLogGraphProvider(tests.TestCaseWithTransport):

    def test_open_branch(self):
        tree = self.make_branch_and_tree("branch")
        
        gp = LogGraphProvider(False)
        gp.open_branch(tree.branch, tree=tree)
        
        self.assertEqual([(tree,
                          tree.branch,
                          None)],
                         gp.branches())
        self.assertLength(1, gp.repos)
        self.assertEqual({tree.branch.repository.base: tree.branch.repository},
                         gp.repos)

    def test_open_branch_without_passing_tree(self):
        tree = self.make_branch_and_tree("branch")
        
        gp = LogGraphProvider(False)
        # If we don't pass the tree, it should open it.
        gp.open_branch(tree.branch)
        
        opened_tree = gp.branches()[0][0]
        self.assertEqual(tree.basedir,
                         opened_tree.basedir)

    def test_open_branch_without_tree(self):
        branch = self.make_branch("branch")
        
        gp = LogGraphProvider(False)
        # If we don't pass the tree, it should open it.
        gp.open_branch(branch)
        
        self.assertEqual([(None, branch, None)],
                         gp.branches())

    def make_branch_and_tree_with_files_and_dir(self):
        tree = self.make_branch_and_tree("branch")
        self.build_tree(['branch/file1', 'branch/dir/', 'branch/file3'])
        tree.add('file1', 'file1-id')
        tree.add('dir', 'dir-id')
        tree.add('file3', 'file3-id')
        tree.commit(message='add files')
        return tree

    def check_open_branch_files(self, tree, branch):
        gp = LogGraphProvider(False)
        
        gp.open_branch(branch, tree=tree, file_ids=['file1-id'])
        self.assertEqual([(tree,
                          branch,
                          None)],
                         gp.branches())
        self.assertEqual(['file1-id'], gp.fileids)
        self.assertFalse(gp.has_dir)
        
        gp.open_branch(branch, tree=tree, file_ids=['dir-id'])
        self.assertEqual([(tree,
                          branch,
                          None)],
                         gp.branches())
        self.assertEqual(['file1-id', 'dir-id'], gp.fileids)
        self.assertTrue(gp.has_dir)
        
        gp.open_branch(branch, tree=tree, file_ids=['file3-id'])
        self.assertEqual([(tree,
                          branch,
                          None)],
                         gp.branches())
        self.assertEqual(['file1-id', 'dir-id','file3-id'], gp.fileids)
        self.assertTrue(gp.has_dir)
    
    def test_open_branch_files(self):
        tree = self.make_branch_and_tree_with_files_and_dir()
        self.check_open_branch_files(tree, tree.branch)

    def test_open_branch_files_with_tree(self):
        tree = self.make_branch_and_tree_with_files_and_dir()
        branch = tree.branch
        tree.bzrdir.destroy_workingtree()
        self.check_open_branch_files(None, branch)
    
    def branches_to_base(self, branches):
        for tree, branch, index in branches:
            if tree is None:
                yield (None, branch.base, index)
            else:
                yield (tree.basedir, branch.base, index)
    
    def test_open_locations_standalone_branches(self):
        branch1 = self.make_branch("branch1")
        tree2 = self.make_branch_and_tree("branch2")
        
        gp = LogGraphProvider(False)
        gp.open_locations(["branch1", "branch2"])
        
        branches = gp.branches()
        
        self.assertEqual(set(((None,          branch1.base, None),
                              (tree2.basedir, tree2.branch.base, None) )),
                         set(self.branches_to_base(gp.branches())))
        
        self.assertLength(2, gp.repos)
        self.assertEqual(branch1.repository.base,
                         gp.repos[branch1.repository.base].base)        
        self.assertEqual(tree2.branch.repository.base,
                         gp.repos[tree2.branch.repository.base].base)
    
    def make_branch_in_shared_repo(self, relpath, format=None):
        """Create a branch on the transport at relpath."""
        made_control = self.make_bzrdir(relpath, format=format)
        return made_control.create_branch()

    def test_open_locations_shared_repo(self):
        self.make_branch = self.make_branch_in_shared_repo
        repo = self.make_repository("repo", shared=True)
        branch1 = self.make_branch("repo/branch1")
        tree2 = self.make_branch_and_tree("repo/branch2")
        
        gp = LogGraphProvider(False)
        gp.open_locations(["repo"])
        
        self.assertEqual(set(((None, branch1.base, None),
                          (tree2.basedir, tree2.branch.base, None))),
                         set(self.branches_to_base(gp.branches())))
    
    def test_open_locations_raise_not_a_branch(self):
        repo = self.make_repository("repo", shared=True)
        gp = LogGraphProvider(False)
        self.assertRaises(errors.NotBranchError,
                          gp.open_locations, ["repo/non_existant_branch"])
        self.assertRaises(errors.NotBranchError,
                          gp.open_locations, ["/non_existant_branch"])

    def check_open_location_files(self):
        gp = LogGraphProvider(False)
        
        gp.open_locations(['branch/file1'])
        self.assertEqual(['file1-id'], gp.fileids)
        self.assertFalse(gp.has_dir)
        
        gp.open_locations(['branch/dir'])
        self.assertEqual(['file1-id', 'dir-id'], gp.fileids)
        self.assertTrue(gp.has_dir)
        
        gp.open_locations(['branch/file3'])
        self.assertEqual(['file1-id', 'dir-id','file3-id'], gp.fileids)
        self.assertTrue(gp.has_dir)
    
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
        
        gp = LogGraphProvider(False)
        
        self.assertRaises(errors.BzrCommandError,
                          gp.open_locations,
                          ["file-that-does-not-exist"])
