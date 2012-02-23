if __name__=='__main__':
    import bzrlib
    bzrlib.initialize()
    import bzrlib.plugin
    bzrlib.plugin.set_plugins_path()
    bzrlib.plugin.load_plugins()

import os, tempfile
from bzrlib.plugins.qbzr.lib.tests import QTestCase
from bzrlib.plugins.qbzr.lib.tests.mock import MockFunction
from bzrlib.plugins.qbzr.lib import diff
from bzrlib.workingtree import WorkingTree
from contextlib import contextmanager


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

class TestExtDiffBase(QTestCase):
    def setUp(self):
        QTestCase.setUp(self)
        self.popen_mock = MockFunction()
        popen = diff.subprocess.Popen
        diff.subprocess.Popen = self.popen_mock
        def restore():
            diff.subprocess.Popen = popen
        self.addCleanup(restore)
        self.tree = self.make_branch_and_tree('tree')
        self.ctx = self.create_context()
        self.addCleanup(self.ctx.finish)

    def create_context(self, parent=None):
        ctx = diff.ExtDiffContext(parent)
        self.addCleanup(ctx.finish)
        return ctx

    def assertFileContent(self, path, content):
        self.assertTrue(os.path.isfile(path))
        f = open(path)
        self.assertEqual("\n".join(f.readlines()), content)
        f.close()

class TestCleanup(TestExtDiffBase):
    def setUp(self):
        TestExtDiffBase.setUp(self)
        self.build_tree_contents([('tree/a', "a")])
        self.tree.add(['a'])
        self.tree.commit(message='1')
        self.build_tree_contents([('tree/a', "aa")])

    def test_remove_root(self):
        self.ctx.setup("diff.txt", self.tree.basis_tree(), self.tree)
        rootdir = self.ctx.rootdir
        self.assertTrue(len(rootdir) > 0)
        self.assertTrue(os.path.isdir(rootdir))
        self.ctx.finish()
        self.assertTrue(self.ctx.rootdir is None)
        self.assertFalse(os.path.exists(rootdir))

    def test_dont_remove_root_of_other_context(self):
        self.ctx.setup("diff.txt", self.tree.basis_tree(), self.tree)
        ctx2 = self.create_context()
        ctx2.setup("diff.txt", self.tree.basis_tree(), self.tree)
        rootdir = self.ctx.rootdir
        self.assertNotEqual(rootdir, ctx2.rootdir)
        self.ctx.finish()
        self.assertTrue(self.ctx.rootdir is None)
        self.assertTrue(os.path.exists(ctx2.rootdir))
    
    @contextmanager
    def invalidate_rmtree(self):
        rmtree = diff.osutils.rmtree
        def rmtree_mock(path):
            raise IOError("osutils.rmtree is now invalidated.")
        try:
            diff.osutils.rmtree = MockFunction(func=rmtree_mock)
            yield
        finally:
            diff.osutils.rmtree = rmtree

    def test_mark_deletable_if_delete_failed(self):
        # If failed to delete tempdir, mark it deletable to delete later.
        self.ctx.setup("diff.txt", self.tree.basis_tree(), self.tree)
        rootdir = self.ctx.rootdir
        self.assertTrue(len(rootdir) > 0)
        self.assertTrue(os.path.isdir(rootdir))
        with self.invalidate_rmtree():
            self.ctx.finish()
        self.assertTrue(self.ctx.rootdir is None)
        self.assertTrue(os.path.isfile(os.path.join(rootdir, ".delete")))

    def test_cleanup_deletable_roots(self):
        ctx2 = self.create_context()
        ctx3 = self.create_context()
        self.ctx.setup("diff.txt", self.tree.basis_tree(), self.tree)
        ctx2.setup("diff.txt", self.tree.basis_tree(), self.tree)
        ctx3.setup("diff.txt", self.tree.basis_tree(), self.tree)
        root = self.ctx.rootdir
        root2 = ctx2.rootdir
        root3 = ctx3.rootdir
        with self.invalidate_rmtree():
            self.ctx.finish()
        self.assertTrue(os.path.isfile(os.path.join(root, ".delete")))
        os.chdir(tempfile.gettempdir())
        ctx2.finish()
        self.assertFalse(os.path.exists(root))
        self.assertFalse(os.path.exists(root2))
        self.assertTrue(os.path.exists(root3))

    def test_finish_lazy(self):
        self.ctx.setup("diff.txt", self.tree.basis_tree(), self.tree)
        rootdir = self.ctx.rootdir
        self.assertTrue(len(rootdir) > 0)
        self.assertTrue(os.path.isdir(rootdir))
        self.ctx.finish_lazy()
        self.assertTrue(self.ctx.rootdir is None)
        self.assertTrue(os.path.isfile(os.path.join(rootdir, ".delete")))


    def test_cleanup_deletable_roots_by_finish_lazy(self):
        ctx2 = self.create_context()
        ctx3 = self.create_context()
        self.ctx.setup("diff.txt", self.tree.basis_tree(), self.tree)
        ctx2.setup("diff.txt", self.tree.basis_tree(), self.tree)
        ctx3.setup("diff.txt", self.tree.basis_tree(), self.tree)
        root = self.ctx.rootdir
        root2 = ctx2.rootdir
        root3 = ctx3.rootdir
        self.ctx.finish_lazy()
        ctx2.finish()
        self.assertFalse(os.path.exists(root))
        self.assertFalse(os.path.exists(root2))
        self.assertTrue(os.path.exists(root3))

class TestWorkingTreeDiff(TestExtDiffBase):
    def setUp(self):
        TestExtDiffBase.setUp(self)

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
        self.ctx.setup("diff.exe", self.tree.basis_tree(), self.tree)

    def assertPopen(self, paths, old_contents):
        self.assertEqual(self.popen_mock.count, len(paths))

        for args, path, old_content in zip(self.popen_mock.args,
                                           paths, old_contents):
            tool, old_path, new_path = args[0][0]
            self.assertEqual(tool, "diff.exe")
            self.assertFileContent(old_path, old_content)
            self.assertEqual(new_path, self.tree.abspath(path))

    def test_diff_ids(self):
        paths = ['a', 'dir1/b']
        self.ctx.diff_ids([self.tree.path2id(p) for p in paths])
        self.assertPopen(paths, ["a", "b"])

    def test_diff_paths(self):
        paths = ['a', 'dir1/b']
        self.ctx.diff_paths(paths)
        self.assertPopen(paths, ["a", "b"])

    def test_diff_paths_for_dir(self):
        paths = ['dir1/b', 'dir1/c']
        self.ctx.diff_paths(['dir1'])
        self.assertPopen(paths, ["b", "c"])

    def test_diff_tree(self):
        paths = ['a', 'dir1/b', 'dir1/c', 'dir2/e']
        old_contents = ['a', 'b', 'c', 'e']
        self.ctx.diff_tree()
        self.assertPopen(paths, old_contents)

    def test_diff_tree_for_dir(self):
        paths = ['dir1/b', 'dir1/c']
        self.ctx.diff_tree(specific_files=['dir1'])
        self.assertPopen(paths, ["b", "c"])

    def test_diff_for_renamed_files(self):
        self.tree.rename_one('a', 'a2')
        paths = ['a2']
        self.ctx.diff_paths(['a2'])
        self.assertPopen(paths, ["a"])

    def test_skip_added_file(self):
        self.build_tree_contents([
            ('tree/a2', "a"),
        ])
        self.tree.add(['a2'])
        self.ctx.diff_paths(['a2'])
        self.assertPopen([], [])


    def test_skip_removed_file_1(self):
        self.tree.remove(['a'], keep_files=True)
        self.ctx.diff_paths(['a'])
        self.assertPopen([], [])

    def test_skip_removed_file_2(self):
        self.tree.remove(['a'], keep_files=False)
        self.ctx.diff_paths(['a'])
        self.assertPopen([], [])

if __name__=='__main__':
    import unittest
    unittest.main()

