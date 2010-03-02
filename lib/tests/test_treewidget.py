# -*- coding: utf-8 -*-
#
# Copyright (C) 2009 Gary van der Merwe <garyvdm@gmail.com>
#
# This program is free software; you can redistribute it and/or
# modify it under the terms of the GNU General Public License
# as published by the Free Software Foundation; either versio0n 2
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

from bzrlib.tests import TestCase, TestCaseWithTransport
from bzrlib import tests
from bzrlib.workingtree import WorkingTree
from bzrlib.branch import Branch
from bzrlib.bzrdir import BzrDir

from PyQt4 import QtCore, QtGui
from bzrlib.plugins.qbzr.lib.treewidget import (
    TreeWidget,
    TreeModel,
    ModelItemData,
    InternalItem,
    group_large_dirs,
    )
from bzrlib.plugins.qbzr.lib.tests.modeltest import ModelTest
from bzrlib.plugins.qbzr.lib.tests.excepthookwatcher import TestWatchExceptHook

def load_tests(standard_tests, module, loader):
    result = loader.suiteClass()

    tree_scenarios = (
        ('Working Tree',
            {'make_tree': make_working_tree,
             'modify_tree': modify_working_tree,}),
        ('Working Tree Changes Mode',
            {'make_tree': make_working_tree,
             'modify_tree': modify_working_tree,
             'changes_mode': False}),
        ('Revision Tree',
            {'make_tree': make_rev_tree,}),
    )
    sp_tests, remaining_tests = tests.split_suite_by_condition(
        standard_tests, tests.condition_isinstance((
                TestTreeWidget,
                )))
    tests.multiply_tests(sp_tests, tree_scenarios, result)

    # No parametrization for the remaining tests
    result.addTests(remaining_tests)

    return result

def make_working_tree(test):
    #tree = WorkingTree()
    tree = test.make_branch_and_tree('trunk')
    test.build_tree_contents([('trunk/textconflict', 'base'),])
    tree.add(['textconflict'], ['textconflict-id'])
    tree.commit('a', rev_id='rev-a',
                committer="joe@foo.com",
                timestamp=1166046000.00, timezone=0)
    
    branch_tree = tree.bzrdir.sprout('branch').open_workingtree()
    test.build_tree_contents([('branch/textconflict', 'other'),])
    branch_tree.commit('b', rev_id='rev-b',
                       committer="joe@foo.com",
                       timestamp=1166046000.00, timezone=0)
    test.branch_tree = branch_tree
    
    
    test.build_tree(['trunk/dir/'])
    test.build_tree_contents([('trunk/unmodified', ''),
                              ('trunk/renamed', ''),
                              ('trunk/moved', ''),
                              ('trunk/movedandrenamed', ''),
                              ('trunk/removed', ''),
                              ('trunk/missing', ''),
                              ('trunk/modified', 'old'),
                              ('trunk/textconflict', 'this'),
                              ])
    tree.add(['dir'], ['dir-id'])
    tree.add(['unmodified'], ['unmodified-id'])
    tree.add(['renamed'], ['renamed-id'])
    tree.add(['moved'], ['moved-id'])
    tree.add(['movedandrenamed'], ['movedandrenamed-id'])
    tree.add(['removed'], ['removed-id'])
    tree.add(['missing'], ['missing-id'])
    tree.add(['modified'], ['modified-id'])
    tree.commit('c', rev_id='rev-c',
                committer="joe@foo.com",
                timestamp=1166046000.00, timezone=0)
    
    return tree, tree.branch

def modify_working_tree(test, tree):
    if 0: tree = WorkingTree()
    tree.merge_from_branch(test.branch_tree.branch, 'rev-b')

    
    test.build_tree_contents([('trunk/added', ''),
                              ('trunk/addedmissing', ''),
                              ('trunk/modified', 'new'),
                              ('trunk/unversioned', ''),
                              ])
    tree.add(['added'], ['added-id'])
    tree.add(['addedmissing'], ['addedmissing-id'])
    tree.rename_one('renamed', 'renamed1')
    tree.move(('moved',), 'dir')
    tree.rename_one('movedandrenamed', 'movedandrenamed1')
    tree.move(('movedandrenamed1',), 'dir')
    tree.remove(('removed',))
    os.remove('trunk/missing')
    os.remove('trunk/addedmissing')


def make_rev_tree(test):
    tree = test.make_branch_and_tree('tree')
    test.build_tree(['tree/b/'])
    test.build_tree_contents([('tree/a', ''),
                              ('tree/b/c', ''),
                              ])
    tree.add(['a'], ['a-id'])
    tree.add(['b'], ['b-id'])
    tree.add(['b/c'], ['c-id'])
    tree.commit('a', rev_id='rev-1',
                committer="joe@foo.com",
                timestamp=1166046000.00, timezone=0)
    revtree = tree.branch.repository.revision_tree('rev-1')
    return revtree, tree.branch
    

class TestTreeWidget(TestWatchExceptHook, TestCaseWithTransport):
    
    # Set by load_tests
    make_tree = None
    modify_tree = None
    changes_mode = False
    
    def setUp(self):
        super(TestTreeWidget, self).setUp()
        self.tree, self.branch = self.make_tree(self)
    
    def run_model_tests(self):
        ModelTest(self.widget.tree_model, None)
        ModelTest(self.widget.tree_filter_model, None)
    
    def test_show_widget(self):
        widget = TreeWidget()
        self.widget = widget
        self.run_model_tests()
        
        self.addCleanup(widget.close)
        # make the widget bigger so that we can see what is going on.
        widget.setGeometry(0,0,500,500)
        widget.show()
        QtCore.QCoreApplication.processEvents()
        widget.set_tree(self.tree, self.branch,
                        changes_mode=self.changes_mode)
        self.run_model_tests()
        
        widget.update()
        QtCore.QCoreApplication.processEvents()
        widget.expandAll ()
        self.run_model_tests()
        
        widget.update()
        QtCore.QCoreApplication.processEvents()
        if self.modify_tree:
            self.modify_tree(self, self.tree)
            widget.refresh()
            self.run_model_tests()
            
            widget.update()
            QtCore.QCoreApplication.processEvents()
            widget.expandAll ()
            self.run_model_tests()
            
            widget.update()
            QtCore.QCoreApplication.processEvents()
        x=1


class TestModelItemData(TestCase):

    def _make_unversioned_model_list(self, iterable):
        return [ModelItemData(path, InternalItem(path, kind, None))
            for path, kind in iterable]

    def test_sort_key_one_dir(self):
        models = self._make_unversioned_model_list((
            ("b", "directory"),
            ("d", "directory"),
            ("a", "file"),
            ("c", "file")))
        self.assertEqual(models, sorted(reversed(models),
            key=ModelItemData.dirs_first_sort_key))

    def test_sort_key_sub_dirs(self):
        models = self._make_unversioned_model_list((
            ('a', 'directory'),
            ('a/f', 'file'),
            ('b', 'directory'),
            ('b/f', 'file')))
        self.assertEqual(models, sorted(reversed(models),
            key=ModelItemData.dirs_first_sort_key))

        models = self._make_unversioned_model_list((
            ('b', 'directory'),
            ('b/y', 'directory'),
            ('b/y/z', 'file'),
            ('b/x', 'file'),
            ('a', 'file'),
            ('c', 'file')))
        self.assertEqual(models, sorted(reversed(models),
            key=ModelItemData.dirs_first_sort_key))

class TestGroupLargeDirs(TestCase):
    
    def test_no_group_small(self):
        paths = frozenset(("a/1", "a/2", "a/3", "b"))
        self.assertEqual(group_large_dirs(paths), {"":paths})

    def test_no_group_no_parents_with_others(self):
        paths = frozenset(("a/1", "a/2", "a/3", "a/4"))
        self.assertEqual(group_large_dirs(paths), {"":paths})

    def test_group_large_and_parents_with_others(self):
        paths = frozenset(("a/1", "a/2", "a/3", "a/4", "b"))
        self.assertEqual(group_large_dirs(paths),
                         {'': set(['a', 'b']),
                          'a': set(['a/1', 'a/2', 'a/3', 'a/4'])})

    def test_group_container(self):
        paths = frozenset(("a/1", "a/2", "a/3", "a", ))
        self.assertEqual(group_large_dirs(paths),
                          {'': set(['a']),
                           'a': set(['a/1', 'a/2', 'a/3'])})

    def test_no_paths(self):
        paths = frozenset()
        self.assertEqual(group_large_dirs(paths),
                         {'': set([])})
    
    def test_group_deeper_dir(self):
        paths = frozenset(("a/b/1", "a/b/2", "a/b/3", "a/b/4", "c"))
        self.assertEqual(group_large_dirs(paths),
                         {'': set(['a/b', 'c']),
                          'a/b': set(['a/b/1', 'a/b/2', 'a/b/3', 'a/b/4'])}) 
    
    def test_subdir_included(self):
        paths = frozenset([
            u'b',
            u'b/1',
            u'b/2',
            u'b/3',
            u'b/4',
            u'b/c', 
            u'b/c/1',
            u'b/c/2',
            u'b/c/3',
            u'b/c/4',
            ])
        self.assertEqual(group_large_dirs(paths),
                         {'': set([u'b']),
                          u'b': set([u'b/1', u'b/2', u'b/3', u'b/4', u'b/c']),
                          u'b/c': set([u'b/c/1', u'b/c/2', u'b/c/3', u'b/c/4'])})

