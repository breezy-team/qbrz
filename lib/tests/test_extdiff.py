if __name__=='__main__':
    import bzrlib
    bzrlib.initialize()
    import bzrlib.plugin
    bzrlib.plugin.set_plugins_path()
    bzrlib.plugin.load_plugins()

import os
from bzrlib.plugins.qbzr.lib.tests import QTestCase
from bzrlib.plugins.qbzr.lib.tests.mock import MockFunction
from bzrlib.plugins.qbzr.lib import diff
from bzrlib.workingtree import WorkingTree

class TestCommandString(QTestCase):
    def setUp(self):
        QTestCase.setUp(self)
        self.tree = self.make_branch_and_tree('tree')
        self.build_tree_contents([('tree/a', "content")])
        self.tree.add(["a"])
        self.tree.commit(message='1')
        self.differ = diff._ExtDiffer("test", self.tree.basis_tree(), self.tree)
        self.addCleanup(self.differ.finish)

    def test_no_arguments(self):
        self.differ.set_command_string("test")
        self.assertEqual(self.differ.command_template,
                         ["test", "@old_path", "@new_path"])

    def test_has_arguments(self):
        self.differ.set_command_string("test --old @old_path --new @new_path")
        self.assertEqual(self.differ.command_template,
                         ["test", "--old", "@old_path", "--new", "@new_path"])

class TestPrefix(QTestCase):
    def setUp(self):
        QTestCase.setUp(self)
        self.tree = self.make_branch_and_tree('tree')
        self.build_tree_contents([('tree/a', "content")])
        self.tree.add(["a"])
        self.tree.commit(message='1')
        self.build_tree_contents([('tree/a', "new content")])
        self.tree.commit(message='2')
        self.differ = diff._ExtDiffer("test", self.tree.basis_tree(), self.tree)
        self.addCleanup(self.differ.finish)

    def test_same_prefix_for_same_workingtree(self):
        prefix = self.differ.get_prefix(self.tree)
        tree2 = WorkingTree.open(self.tree.abspath(""))
        self.assertEqual(self.differ.get_prefix(tree2), prefix)

    def test_another_prefix_for_another_workingtree(self):
        tree2 = self.make_branch_and_tree('tree2')
        prefix = self.differ.get_prefix(self.tree)
        self.assertNotEqual(self.differ.get_prefix(tree2), prefix)

    def test_same_prefix_for_same_revisiontree(self):
        self.differ = diff._ExtDiffer("test", self.tree.basis_tree(), self.tree)
        tree1 = self.tree.basis_tree()
        tree2 = self.tree.basis_tree()
        self.assertNotEqual(tree1, tree2)
        prefix = self.differ.get_prefix(tree1)
        self.assertEqual(self.differ.get_prefix(tree2), prefix)
        self.assertNotEqual(self.differ.get_prefix(self.tree), prefix)

    def test_another_prefix_for_another_revtree(self):
        b = self.tree.branch
        trees = [b.repository.revision_tree(b.get_rev_id(no)) for no in (1,2)]
        prefix = self.differ.get_prefix(trees[0])
        self.assertNotEqual(self.differ.get_prefix(trees[1]), prefix)

    def test_same_prefix_for_same_object(self):
        obj = object()
        prefix = self.differ.get_prefix(obj)
        self.assertEqual(self.differ.get_prefix(obj), prefix)

    def test_another_prefix_for_another_object(self):
        obj = object()
        prefix = self.differ.get_prefix(obj)
        self.assertNotEqual(self.differ.get_prefix(object()), prefix)

class TestExtDiff(QTestCase):
    def setUp(self):
        QTestCase.setUp(self)
        self.popen_mock = MockFunction()
        popen =diff.subprocess
        diff.subprocess.Popen = self.popen_mock
        def restore():
            diff.subprocess.Popen = popen
        self.addCleanup(restore)

        self.tree = self.make_branch_and_tree('tree')
        self.build_tree(['tree/dir1/', 'tree/dir2/'])
        self.build_tree_contents([
            ('tree/a', "a"),
            ('tree/dir1/b', "b"),
            ('tree/dir1/c', "c"),
            ('tree/dir1/d', "d"),
            ('tree/dir2/e', "e"),
            ('tree/dir2/f', "f"),
        ])
        self.tree.add(["a", "dir1", "dir2",
                       "dir1/b", "dir1/c", "dir1/d",
                       "dir2/e", "dir2/f"])
        self.tree.commit(message='1')
        self.build_tree_contents([
            ('tree/a', "A"),
            ('tree/dir1/b', "B"),
            ('tree/dir1/c', "C"),
            ('tree/dir2/e', "E"),
        ])

        self.context = diff.ExtDiffContext(None)
        self.context.setup("diff.exe", self.tree.basis_tree(), self.tree)
        self.addCleanup(self.context.finish)

    def assertFileContent(self, path, content):
        self.assertTrue(os.path.isfile(path))
        f = open(path)
        self.assertEqual("\n".join(f.readlines()), content)
        f.close()

    def assertPopen(self, paths, old_contents):
        self.assertEqual(self.popen_mock.count, len(paths))

        for args, path, old_content in zip(self.popen_mock.args,
                                           paths, old_contents):
            tool, old_path, new_path = args[0][0]
            self.assertEqual(tool, "diff.exe")
            self.assertFileContent(old_path, old_content)
            self.assertEqual(new_path, self.tree.abspath(path))

    def test_diff_ids(self):
        ctx = self.context
        paths = ['a', 'dir1/b']
        ctx.diff_ids([self.tree.path2id(p) for p in paths])
        self.assertPopen(paths, ["a", "b"])

    def test_diff_paths(self):
        ctx = self.context
        paths = ['a', 'dir1/b']
        ctx.diff_paths(paths)
        self.assertPopen(paths, ["a", "b"])

    def test_diff_paths_for_dir(self):
        ctx = self.context
        paths = ['dir1/b', 'dir1/c']
        ctx.diff_paths(['dir1'])
        self.assertPopen(paths, ["b", "c"])

    def test_diff_tree(self):
        ctx = self.context
        paths = ['a', 'dir1/b', 'dir1/c', 'dir2/e']
        old_contents = ['a', 'b', 'c', 'e']
        ctx.diff_tree()
        self.assertPopen(paths, old_contents)

    def test_diff_tree_for_dir(self):
        ctx = self.context
        paths = ['dir1/b', 'dir1/c']
        ctx.diff_tree(specific_files=['dir1'])
        self.assertPopen(paths, ["b", "c"])

if __name__=='__main__':
    import unittest
    unittest.main()

