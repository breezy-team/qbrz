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

class TestLogGraphProvider(tests.TestCaseWithTransport):

    def test_open_branch(self):
        tree = self.make_branch_and_tree("branch")
        
        gp = LogGraphProvider(False)
        gp.open_branch(tree.branch, tree=tree)
        
        self.assertEqual([(tree,
                          tree.branch,
                          None)],
                         gp.branches())
        self.assertEqual({tree.branch.repository.base: tree.branch.repository},
                         gp.repos)

    def test_open_branch_without_tree(self):
        tree = self.make_branch_and_tree("branch")
        
        gp = LogGraphProvider(False)
        # If we don't pass the tree, it should open it.
        gp.open_branch(tree.branch)
        
        self.assertEqual(tree.basedir,
                         gp.branches()[0][0].basedir)
    
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
        
        self.assertEqual(set(((None, branch1.base, None),
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
