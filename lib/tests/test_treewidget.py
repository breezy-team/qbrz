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

from bzrlib.tests import TestCase, TestCaseWithTransport
from PyQt4 import QtCore, QtGui
from bzrlib.plugins.qbzr.lib.treewidget import (
    TreeModel,
    ModelItemData,
    InternalItem,
    group_large_dirs,
    )
from bzrlib.plugins.qbzr.lib.tests.modeltest import ModelTest
from bzrlib.plugins.qbzr.lib.tests.excepthookwatcher import TestWatchExceptHook

class TestTreeModel(TestWatchExceptHook, TestCaseWithTransport):
    
    def test_model_working_tree(self):

        tree = self.make_branch_and_tree('tree')
        self.build_tree(['tree/b/', "tree/e/"])
        self.build_tree_contents([('tree/a', ''),
                                  ('tree/b/c', ''),
                                  ('tree/d', ''),
                                  ('tree/e/f', '')])
        tree.add(['a'], ['a-id'])
        tree.add(['b'], ['b-id'])
        tree.add(['b/c'], ['c-id'])
        tree.commit('a', rev_id='rev-1',
                     committer="joe@foo.com",
                     timestamp=1166046000.00, timezone=0)

        model = TreeModel(parent=None)
        modeltest = ModelTest(model, None)

        model.set_tree(tree, tree.branch)

    #def test_model_revision_tree(self):
    #
    #    tree = self.make_branch_and_tree('tree')
    #    self.build_tree(['tree/b/'])
    #    self.build_tree_contents([('tree/a', ''),
    #                              ('tree/b/c', '')])
    #    tree.add(['a'], ['a-id'])
    #    tree.add(['b'], ['b-id'])
    #    tree.add(['b/c'], ['c-id'])
    #    tree.commit('a', rev_id='rev-1',
    #                 committer="joe@foo.com",
    #                 timestamp=1166046000.00, timezone=0)
    #
    #    widget = TreeWidget()
    #    model = widget.model
    #    
    #    revtree = branch.repository.revision_tree('rev-1')
    #    widget.set_tree(revtree, branch)
    #    modeltest = ModelTest(model, None)

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

