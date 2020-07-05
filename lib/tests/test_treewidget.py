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

from breezy.tests import TestCase, TestCaseWithTransport
from breezy import tests
from breezy.workingtree import WorkingTree
from breezy.branch import Branch
from breezy.controldir import ControlDir
from breezy.conflicts import TextConflict, ConflictList
from breezy import ignores

from PyQt4 import QtCore, QtGui
from PyQt4.QtTest import QTest
from breezy.plugins.qbrz.lib import tests as qtests
from breezy.plugins.qbrz.lib.treewidget import (
    TreeWidget,
    TreeModel,
    TreeFilterProxyModel,
    ModelItemData,
    InternalItem,
    PersistantItemReference,
    group_large_dirs,
    )
from breezy.plugins.qbrz.lib.tests.modeltest import ModelTest


# The filter_scenarios are at the end of the file
def load_tests(loader, basic_tests, pattern):
    result = loader.suiteClass()

    tree_tests, remaining_tests = tests.split_suite_by_condition(
        basic_tests, tests.condition_isinstance((
                TestTreeWidget,
                )))
    tests.multiply_tests(tree_tests, tree_scenarios, result)

    filter_tests, remaining_tests = tests.split_suite_by_condition(
        remaining_tests, tests.condition_isinstance((
                TestTreeFilterProxyModel,
                )))
    tests.multiply_tests(filter_tests, filter_scenarios, result)

    # No parametrization for the remaining tests
    result.addTests(remaining_tests)

    return result


class TestTreeWidget(qtests.QTestCase):

    # Set by load_tests
    make_tree = None
    modify_tree = None
    changes_mode = False

    def setUp(self):
        super(TestTreeWidget, self).setUp()
        self.tree, self.branch = self.make_tree(self)

    def make_working_tree(self):
        # tree = WorkingTree()
        tree = self.make_branch_and_tree('trunk')
        self.build_tree_contents([('trunk/textconflict', b'base'),])
        tree.add(['textconflict'], [b'textconflict-id'])
        tree.commit('a', rev_id=b'rev-a', committer="joe@foo.com", timestamp=1166046000.00, timezone=0)

        branch_tree = tree.controldir.sprout('branch').open_workingtree()
        self.build_tree_contents([('branch/textconflict', b'other'),])
        branch_tree.commit('b', rev_id=b'rev-b', committer="joe@foo.com", timestamp=1166046000.00, timezone=0)
        self.branch_tree = branch_tree


        self.build_tree(['trunk/dir/'])
        self.build_tree_contents([('trunk/dir/dirchild', b''),
                                  ('trunk/unmodified', b''),
                                  ('trunk/renamed', b''),
                                  ('trunk/moved', b''),
                                  ('trunk/movedandrenamed', b''),
                                  ('trunk/removed', b''),
                                  ('trunk/missing', b''),
                                  ('trunk/modified', b'old'),
                                  ('trunk/textconflict', b'this'),
                                  ])
        tree.add(['dir'], [b'dir-id'])
        tree.add(['dir/dirchild'], [b'dirchild-id'])
        tree.add(['unmodified'], [b'unmodified-id'])
        tree.add(['renamed'], [b'renamed-id'])
        tree.add(['moved'], [b'moved-id'])
        tree.add(['movedandrenamed'], [b'movedandrenamed-id'])
        tree.add(['removed'], [b'removed-id'])
        tree.add(['missing'], [b'missing-id'])
        tree.add(['modified'], [b'modified-id'])
        tree.commit('c', rev_id=b'rev-c', committer="joe@foo.com", timestamp=1166046000.00, timezone=0)

        return tree, tree.branch

    def modify_working_tree(self, tree):
        if 0: tree = WorkingTree()
        # RJLRJL: patched out renames as calls seem to be insoluble
        # and related to a problem with finding the id vs rel_path
        tree.merge_from_branch(self.branch_tree.branch, b'rev-b')

        self.build_tree_contents([('trunk/added', b''),
                                  ('trunk/addedmissing', b''),
                                  ('trunk/modified', b'new'),
                                  ('trunk/unversioned', b''),
                                  ])
        tree.add(['added'], [b'added-id'])
        tree.add(['addedmissing'], [b'addedmissing-id'])
        # tree.rename_one('renamed', 'renamed1')
        # tree.move(('moved',), 'dir')
        # tree.rename_one('movedandrenamed', 'movedandrenamed1')
        # tree.move(('movedandrenamed1',), 'dir')
        tree.remove(('removed',))
        os.remove('trunk/missing')
        os.remove('trunk/addedmissing')

        # test for https://bugs.launchpad.net/qbrz/+bug/538753
        # must sort before trunk/dir
        self.build_tree(['trunk/a-newdir/'])
        self.build_tree_contents([('trunk/a-newdir/newdirchild', b'')])
        tree.add(['a-newdir'], [b'a-newdir-id'])
        tree.add(['a-newdir/newdirchild'], [b'newdirchild-id'])

        # manuly add conflicts for files that don't exist
        # See https://bugs.launchpad.net/qbrz/+bug/528548
        tree.add_conflicts([TextConflict('nofileconflict')])


    def make_rev_tree(self):
        tree = self.make_branch_and_tree('tree')
        self.build_tree(['tree/b/'])
        self.build_tree_contents([('tree/a', b''),
                                  ('tree/b/c', b''),
                                  ])
        tree.add(['a'], [b'a-id'])
        tree.add(['b'], [b'b-id'])
        tree.add(['b/c'], [b'c-id'])
        tree.commit('a', rev_id=b'rev-1', committer="joe@foo.com", timestamp=1166046000.00, timezone=0)
        revtree = tree.branch.repository.revision_tree(b'rev-1')
        return revtree, tree.branch

    def run_model_tests(self):
        # Check that indexes point to their correct items.
        def check_item_children(index):
            item = self.widget.tree_model.inventory_data[index.internalId()]
            if item.children_ids:
                for row, child_id in enumerate(item.children_ids):
                    child_index = self.widget.tree_model.index(row, 0, index)
                    self.assertEqual(child_index.internalId(), child_id)
                    check_item_children(child_index)

        if self.widget.tree_model.inventory_data:
            check_item_children (self.widget.tree_model._index_from_id(0, 0))  # root

        ModelTest(self.widget.tree_model, None)
        ModelTest(self.widget.tree_filter_model, None)

    def test_show_widget(self):
        widget = TreeWidget()
        self.widget = widget
        QTest.qWaitForWindowShown(widget)
        self.run_model_tests()

        self.addCleanup(widget.close)
        # make the widget bigger so that we can see what is going on.
        widget.setGeometry(0,0,500,500)
        widget.show()
        QTest.qWaitForWindowShown(widget)
        QtCore.QCoreApplication.processEvents()
        widget.set_tree(self.tree, self.branch, changes_mode=self.changes_mode)
        self.run_model_tests()

        widget.update()
        QTest.qWaitForWindowShown(widget)
        QtCore.QCoreApplication.processEvents()
        widget.expandAll ()
        QTest.qWaitForWindowShown(widget)
        self.run_model_tests()

        widget.update()
        QTest.qWaitForWindowShown(widget)
        QtCore.QCoreApplication.processEvents()

        self.modify_tree(self, self.tree)
        QTest.qWaitForWindowShown(widget)
        widget.refresh()
        QTest.qWaitForWindowShown(widget)
        self.run_model_tests()

        widget.update()
        QTest.qWaitForWindowShown(widget)
        QtCore.QCoreApplication.processEvents()
        widget.expandAll ()
        QTest.qWaitForWindowShown(widget)
        self.run_model_tests()

        widget.update()
        QTest.qWaitForWindowShown(widget)
        QtCore.QCoreApplication.processEvents()

tree_scenarios = (
    ('Working-Tree',
        {'make_tree': TestTreeWidget.make_working_tree,
         'modify_tree': TestTreeWidget.modify_working_tree,}),
    ('Working-Tree-Changes-Mode',
        {'make_tree': TestTreeWidget.make_working_tree,
         'modify_tree': TestTreeWidget.modify_working_tree,
         'changes_mode': True}),
    ('Revision-Tree',
        {'make_tree': TestTreeWidget.make_rev_tree,
         'modify_tree': lambda self, tree: None,}),
)

class TestTreeFilterProxyModel(qtests.QTestCase):

    # Set by load_tests
    filter = None
    expected_visible = None

    def test_filters(self):
        # print('\n*=*=*= expected', self.expected_visible, type(self.expected_visible))
        tree = self.make_branch_and_tree('tree')

        self.build_tree(['tree/dir-with-unversioned/', 'tree/ignored-dir-with-child/',])
        self.build_tree_contents([('tree/dir-with-unversioned/child', b''),
                                  ('tree/ignored-dir-with-child/child', b''),
                                  ('tree/unchanged', b''),
                                  ('tree/changed', b'old'),
                                  ('tree/unversioned', b''),
                                  ('tree/ignored', b''),
                                  ])
        tree.add(['dir-with-unversioned'], [b'dir-with-unversioned-id'])
        tree.add(['unchanged'], [b'unchanged-id'])
        tree.add(['changed'], [b'changed-id'])
        ignores.tree_ignores_add_patterns(tree, ['ignored-dir-with-child', 'ignored'])

        tree.commit('a', rev_id=b'rev-a', committer="joe@foo.com", timestamp=1166046000.00, timezone=0)

        self.build_tree_contents([('tree/changed', b'bnew')])

        self.model = TreeModel()
        # print('\n\t== self.model is ', self.model, type(self.model))
        load_dirs=[PersistantItemReference(None, 'dir-with-unversioned'),
                   PersistantItemReference(None, 'ignored-dir-with-child')]
        # print('\n set_tree being called')
        self.model.set_tree(tree, branch=tree.branch, load_dirs=load_dirs)
        self.filter_model = TreeFilterProxyModel()
        # print('\nmodel and filter: ', self.model, self.filter)
        self.filter_model.setSourceModel(self.model)
        self.filter_model.setFilters(self.filter)
        self.expected_visible.sort()
        # print('\n*=*=*= after-sort expected', self.expected_visible, type(self.expected_visible))
        self.assertEqual(self.getVisiblePaths(), self.expected_visible)

    def getVisiblePaths(self):
        # print('\n@@@@ getVisiblePaths @@@')
        visible_paths = []
        parent_indexes_to_visit = [QtCore.QModelIndex()]
        pushed_id = None
        while parent_indexes_to_visit:
            parent_index = parent_indexes_to_visit.pop()
            # print('\n\t === was pushed', pushed_id == parent_index, parent_indexes_to_visit)
            # print('\n\t->parent_index', parent_index, 'row count was ', self.filter_model.rowCount(parent_index))
            for row in range(self.filter_model.rowCount(parent_index)):
                index = self.filter_model.index(row, 0, parent_index)
                visible_paths.append(self.filter_model.data(index, self.model.PATH))
                # print('\n\t\t--> row, index, path', row, index, visible_paths)
                if self.filter_model.hasChildren(index):
                    # print('\n\t\t\thasChildren! appending', index)
                    parent_indexes_to_visit.append(index)
                    pushed_id = index
        visible_paths.sort()
        return visible_paths

    def test_unversioned_move_conflict(self):
        """Test for bug reported as lp:557603 lp:712931 lp:815822 lp:876180"""
        tree = self.make_branch_and_tree("parent")
        tree.commit("Base revision")
        childtree = tree.controldir.sprout("child").open_workingtree()
        self.build_tree(["parent/f", "child/f"])
        childtree.add(["f"])
        childtree.commit("Adding f")
        tree.merge_from_branch(childtree.branch)
        self.assertLength(1, tree.conflicts())
        self.assertPathExists("parent/f.moved")
        os.remove("parent/f.moved")
        # At this point, the tree has a pending merge adding 'f' and a removed
        # unversioned duplicate 'f.moved', which is enough to trigger the bug.
        self.model = TreeModel()
        load_dirs = [PersistantItemReference(None, "parent")]
        self.model.set_tree(tree, branch=tree.branch, load_dirs=load_dirs)
        self.filter_model = TreeFilterProxyModel()
        self.filter_model.setSourceModel(self.model)
        self.filter_model.setFilters(self.filter)
        expected_paths = []
        if self.filter[TreeFilterProxyModel.CHANGED]:
            expected_paths.append("f")
        self.assertEqual(self.getVisiblePaths(), expected_paths)


class TestTreeWidgetSelectAll(qtests.QTestCase):

    def setUp(self):
        super(TestTreeWidgetSelectAll, self).setUp()
        tree = self.make_branch_and_tree('tree')

        self.build_tree(['tree/dir-with-unversioned/',
                         'tree/ignored-dir-with-child/',
                         'tree/unversioned-with-ignored/',
                         'tree/unversioned-with-ignored/ignored-dir-with-child/',
                         ])
        self.build_tree_contents([('tree/dir-with-unversioned/child', b''),
                                  ('tree/ignored-dir-with-child/child', b''),
                                  ('tree/unversioned-with-ignored/ignored-dir-with-child/child', b''),
                                  ('tree/unchanged', b''),
                                  ('tree/changed', b'old'),
                                  ('tree/unversioned', b''),
                                  ('tree/ignored', b''),
                                  ])
        tree.add(['dir-with-unversioned'], [b'dir-with-unversioned-id'])
        tree.add(['unchanged'], [b'unchanged-id'])
        tree.add(['changed'], [b'changed-id'])
        ignores.tree_ignores_add_patterns(tree, ['ignored-dir-with-child', 'ignored'])

        tree.commit('a', rev_id=b'rev-a', committer="joe@foo.com", timestamp=1166046000.00, timezone=0)

        self.build_tree_contents([('tree/changed', b'new')])
        self.tree = tree

    def assertSelectedPaths(self, treewidget, paths):
        # print('\n ^^^ assertSelectedPaths called\n')
        if 0: treewidget = TreeWidget()
        # for i in treewidget.tree_model.iter_checked():
        #     print('\n-> is is', i)
        selected = [item.path for item in treewidget.tree_model.iter_checked()]
        # print('\n^^^selected', selected, 'paths', paths)
        # we do not care for the order in this test.
        self.assertEqual(set(selected), set(paths))

    def test_add_selectall(self):
        import breezy.plugins.qbrz.lib.add
        self.win = breezy.plugins.qbrz.lib.add.AddWindow(self.tree, None)
        QTest.qWaitForWindowShown(self.win)
        self.addCleanup(self.cleanup_win)
        self.win.initial_load()
        QTest.qWaitForWindowShown(self.win)
        # print('\ntest_add_select_all', self.win.filelist_widget)
        self.assertSelectedPaths(self.win.filelist_widget, ['dir-with-unversioned/child',
                                                     'unversioned',
                                                     'unversioned-with-ignored'])


    def test_commit_selectall(self):
        import breezy.plugins.qbrz.lib.commit
        self.win = breezy.plugins.qbrz.lib.commit.CommitWindow(self.tree, None)
        self.addCleanup(self.cleanup_win)
        self.win.load()
        self.assertSelectedPaths(self.win.filelist_widget, ['changed'])
        #self.win.show_nonversioned_checkbox.setCheckState(QtCore.Qt.Checked)
        self.win.show_nonversioned_checkbox.click()
        #self.win.selectall_checkbox.setCheckState(QtCore.Qt.Unchecked)
        self.win.selectall_checkbox.click()
        #import pdb; pdb.set_trace()
        self.assertSelectedPaths(self.win.filelist_widget, ['changed',
                                                     'dir-with-unversioned/child',
                                                     'unversioned',
                                                     'unversioned-with-ignored'])

    def test_revert_selectall(self):
        import breezy.plugins.qbrz.lib.revert
        self.win = breezy.plugins.qbrz.lib.revert.RevertWindow(self.tree, None)
        self.addCleanup(self.cleanup_win)
        self.win.initial_load()
        self.win.selectall_checkbox.click()
        self.assertSelectedPaths(self.win.filelist, ['changed'])

    def cleanup_win(self):
        # Sometimes the model was getting deleted before the widget, and the
        # widget was trying to query the model. So we delete everything here.
        self.win.deleteLater()
        try:
            self.win.filelist_widget.deleteLater()
            self.win.filelist_widget.tree_model.deleteLater()
        except AttributeError:
            self.win.filelist.deleteLater()
            self.win.filelist.tree_model.deleteLater()
        QtCore.QCoreApplication.processEvents()


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

# See [[../treewidget.py]] TreeFilterProxyModel
# UNCHANGED, CHANGED, UNVERSIONED, IGNORED
# RJLRJL check for .bzrignore vs .brzignore
filter_scenarios = (
    ('All',
        {'filter': (True, True, True, True),
         'expected_visible': ['dir-with-unversioned',
                              'dir-with-unversioned/child',
                              'ignored-dir-with-child',
                              'ignored-dir-with-child/child',
                              'unchanged',
                              'changed',
                              'unversioned',
                              'ignored',
                              '.bzrignore',
                              ],}),
    ('Unchanged',
        {'filter': (True, False, False, False) ,
         'expected_visible': ['dir-with-unversioned',
                              'unchanged',
                              '.bzrignore',
                              ],}),
    ('Changed',
        {'filter': (False, True, False, False),
         'expected_visible': ['changed', ],}),
    ('Unversioned',
        {'filter': (False, False, True, False),
         'expected_visible': ['dir-with-unversioned',
                              'dir-with-unversioned/child',
                              'unversioned',
                              ],}),
    ('Ignored',
        {'filter': (False, False, False, True),
         'expected_visible': ['ignored-dir-with-child',
                              'ignored',
                              ],}),
    ('Ignored+Unversioned',
        {'filter': (False, False, True, True),
         'expected_visible': ['ignored-dir-with-child/child',
                              'ignored-dir-with-child',
                              'ignored',
                              'dir-with-unversioned',
                              'dir-with-unversioned/child',
                              'unversioned',
                              ],}),
    )


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
            'b',
            'b/1',
            'b/2',
            'b/3',
            'b/4',
            'b/c',
            'b/c/1',
            'b/c/2',
            'b/c/3',
            'b/c/4',
            ])
        self.assertEqual(group_large_dirs(paths),
                         {'': set(['b']),
                          'b': set(['b/1', 'b/2', 'b/3', 'b/4', 'b/c']),
                          'b/c': set(['b/c/1', 'b/c/2', 'b/c/3', 'b/c/4'])})

    def test_bug_580798(self):
        # Test for Bug #580798
        paths = frozenset(('a',
                           'a/b1/c1',
                           'a/b2/d1', 'a/b2/d2', 'a/b2/d3', 'a/b2/d4',
                           ))
        self.assertEqual(group_large_dirs(paths),
                         {'': set(['a']),
                          'a': set(['a/b1/c1', 'a/b2']),
                          'a/b2': set(['a/b2/d1', 'a/b2/d2', 'a/b2/d3', 'a/b2/d4']),
                          })
