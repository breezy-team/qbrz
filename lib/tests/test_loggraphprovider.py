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

from bzrlib import (
    errors,
    tests,
    )
from bzrlib.transport import memory
from bzrlib.plugins.qbzr.lib.loggraphprovider import LogGraphProvider


class TestLogGraphProvider(tests.TestCaseWithTransport):

    def test_open_branch(self):
        tree = self.make_branch_and_tree("branch")
        
        gp = LogGraphProvider(False)
        gp.open_branch(tree.branch, tree=tree)
        
        self.assertLength(1, gp.branches)
        bi = gp.branches[0]
        self.assertEqual(tree, bi.tree)
        self.assertEqual(tree.branch, bi.branch)
        self.assertEqual(None, bi.index)
        
        self.assertLength(1, gp.repos)
        self.assertEqual({tree.branch.repository.base: tree.branch.repository},
                         gp.repos)

    def test_open_branch_without_passing_tree(self):
        tree = self.make_branch_and_tree("branch")
        
        gp = LogGraphProvider(False)
        # If we don't pass the tree, it should open it.
        gp.open_branch(tree.branch)
        
        self.assertEqual(tree.basedir, gp.branches[0].tree.basedir)

    def test_open_branch_without_tree(self):
        branch = self.make_branch("branch")
        
        gp = LogGraphProvider(False)
        
        gp.open_branch(branch)
        
        bi = gp.branches[0]
        self.assertEqual(None, bi.tree)
        self.assertEqual(branch, bi.branch)
        self.assertEqual(None, bi.index)

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
        
        gp.open_branch(branch, tree=tree, file_ids = ['file1-id'])
        self.assertLength(1, gp.branches)
        bi = gp.branches[0]
        self.assertEqual(tree, bi.tree)
        self.assertEqual(branch, bi.branch)
        self.assertEqual(None, bi.index)

        self.assertEqual(['file1-id'], gp.file_ids)
        
        gp.open_branch(branch, tree=tree, file_ids = ['dir-id'])        
        self.assertEqual(['file1-id', 'dir-id'], gp.file_ids)
        
        # Check that a new branch has not been added.
        self.assertLength(1, gp.branches)
        
        gp.open_branch(branch, tree=tree, file_ids = ['file3-id'])
        self.assertEqual(['file1-id', 'dir-id','file3-id'], gp.file_ids)
        
        # Check that a new branch has not been added.
        self.assertLength(1, gp.branches)
    
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
        
        gp = LogGraphProvider(False)
        gp.open_locations(["branch1", "branch2"])
        
        branches = gp.branches
        
        self.assertEqual(set(((None,          branch1.base, None),
                              (tree2.basedir, tree2.branch.base, None) )),
                         set(self.branches_to_base(gp.branches)))
        
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
                         set(self.branches_to_base(gp.branches)))
    
    def test_open_locations_in_shared_reporaise_not_a_branch(self):
        repo = self.make_repository("repo", shared=True)
        gp = LogGraphProvider(False)
        self.assertRaises(errors.NotBranchError,
                          gp.open_locations, ["repo/non_existant_branch"])

    def test_open_locations_raise_not_a_branch(self):
        self.vfs_transport_factory = memory.MemoryServer
        gp = LogGraphProvider(False)
        self.assertRaises(errors.NotBranchError,
                          gp.open_locations,
                          [self.get_url("non_existant_branch")])

    def check_open_location_files(self):
        gp = LogGraphProvider(False)
        
        gp.open_locations(['branch/file1'])
        self.assertEqual(['file1-id'], gp.file_ids)
        
        gp.open_locations(['branch/dir'])
        self.assertEqual(['file1-id', 'dir-id'], gp.file_ids)
        
        gp.open_locations(['branch/file3'])
        self.assertEqual(['file1-id', 'dir-id','file3-id'], gp.file_ids)
    
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
    
    def test_branch_label_location(self):
        branch = self.make_branch("branch")
        gp = LogGraphProvider(False)
        
        self.assertEqual('path',
                         gp.branch_label('path', branch))

    def test_branch_label_no_location(self):
        branch = self.make_branch("branch")
        gp = LogGraphProvider(False)
        
        # No location, use nick
        self.assertEqual('branch',
                         gp.branch_label(None, branch))
    
    def test_branch_label_path_location(self):
        branch = self.make_branch("branch")
        gp = LogGraphProvider(False)
        
        # Location seems like a path - use it
        self.assertEqual('path-to-branch',
                         gp.branch_label('path-to-branch', branch))

    def test_branch_label_alias_directory(self):
        branch = self.make_branch("branch")
        gp = LogGraphProvider(False)
        
        # show shortcut, and nick
        self.assertEqual(':parent (branch)',
                         gp.branch_label(':parent', branch))
    
    def test_branch_label_no_info_locations(self):
        branch = self.make_branch("branch")
        gp = LogGraphProvider(False)
        
        # locations that don't have alot of info in them should show the nick
        self.assertEqual('. (branch)',
                         gp.branch_label('.', branch))
        self.assertEqual('../ (branch)',
                         gp.branch_label('../', branch))

    def test_branch_label_explict_nick(self):
        branch = self.make_branch("branch")
        branch.nick = "nick"
        gp = LogGraphProvider(False)
        
        self.assertEqual('path (nick)',
                         gp.branch_label('path', branch))

    def test_branch_label_repository(self):
        repo = self.make_repository("repo", shared=True)
        branch = self.make_branch("repo/branch")
        
        gp = LogGraphProvider(False)
        
        self.assertEqual('./branch',
                         gp.branch_label(None, branch, '.', repo))
