if __name__=='__main__':
    import bzrlib
    bzrlib.initialize()
    try:
        from bzrlib.commands import _register_builtin_commands
        _register_builtin_commands()
    except ImportError:
        pass
    import bzrlib.plugin
    bzrlib.plugin.set_plugins_path()
    bzrlib.plugin.load_plugins()

from bzrlib.plugins.qbzr.lib.tests import QTestCase
from PyQt4 import QtCore
from PyQt4.QtTest import QTest

from bzrlib.plugins.qbzr.lib.diffwindow import DiffWindow
from bzrlib.plugins.qbzr.lib.shelvewindow import ShelveWindow
from bzrlib.plugins.qbzr.lib.annotate import AnnotateWindow


class WtDiffArgProvider(object):
    def __init__(self, tree):
        self.tree = tree

    def get_diff_window_args(self, processEvents, add_cleanup):
        return dict(
            old_tree=self.tree.basis_tree(),
            new_tree=self.tree,
            old_branch=self.tree.branch,
            new_branch=self.tree.branch
        )

CONTENT = \
"""a b c d e f g h i j k l m n
o p q r s t u v w x y z""".replace(" ", "\n")

NEW_CONTENT = \
"""a b c d e ff g h i J-1 J-2 J-3 k l MN
o p s t 1 2 3 u v w x y z""".replace(" ", "\n")

DIFF = [
    (['f'], ['ff']),
    (['j'], ['J-1', 'J-2', 'J-3']),
    (['m', 'n'], ['MN']),
    (['q', 'r'], []),
    ([], ['1', '2', '3']),
]

DIFF_BY_TAGS = dict(
                replace=[x for x in DIFF if len(x[0]) > 0 and len(x[1]) > 0],
                delete =[x for x in DIFF if len(x[1]) == 0],
                insert =[x for x in DIFF if len(x[0]) == 0],
            )

class TestGuideBarBase(QTestCase):
    def setUp(self):
        QTestCase.setUp(self)
        self.tree = self.make_branch_and_tree('tree')

        self.build_tree_contents([('tree/a', CONTENT)])
        self.tree.add(['a'])
        self.tree.commit(message='1')

        self.build_tree_contents([('tree/a', NEW_CONTENT)])

    def assert_sidebyside_view(self, panels):
        for pos, panel in enumerate(panels):
            bar = panel.bar
            doc = panel.edit.document()
            # Title
            self.waitUntil(lambda:len(bar.entries['title'].data) > 0, 500)
            self.assertEqual(bar.entries['title'].data, [(0, 2)])
            # Replace/Delete/Insert

            for tag, expected in DIFF_BY_TAGS.iteritems():
                data = bar.entries[tag].data

                self.assertEqual(len(data), len(expected))

                for texts, (block_no, block_num) in zip(expected, data):
                    self.assertEqual(len(texts[pos]), block_num)
                    for j in range(block_num):
                        text = str(doc.findBlockByNumber(block_no + j).text())
                        self.assertEqual(texts[pos][j], text,
                                         '%s, %s, %r' % (tag, "RL"[pos], data))

    def assert_unidiff_view(self, panel):
        bar = panel.bar
        doc = panel.edit.document()
        # Title
        self.waitUntil(lambda:len(bar.entries['title'].data) > 0, 500)
        self.assertEqual(bar.entries['title'].data, [(0, 2)])
        # Replace/Delete/Insert
        for tag, expected in DIFF_BY_TAGS.iteritems():
            data = bar.entries[tag].data
            self.assertEqual(len(data), len(expected))
            for texts, (block_no, block_num) in zip(expected, data):
                unidiff_texts = ['-' + x for x in texts[0]] + \
                                ['+' + x for x in texts[1]]
                self.assertEqual(len(unidiff_texts), block_num)
                for j in range(block_num):
                    text = str(doc.findBlockByNumber(block_no + j).text())
                    self.assertEqual(unidiff_texts[j], text,
                                     '%s, %s, %r' % (tag, "U", data))

    def set_find_text(self, find_toolbar, text):
        find_toolbar.show_action_toggle(True)
        find_toolbar.find_text.setText(text)

    def assert_find(self, text, bar, edit, expected_num=None):
        self.waitUntil(lambda:bar.entries['find'].data, 500)
        # Check side by side view
        data = bar.entries['find'].data
        if expected_num is not None:
            self.assertEqual(len(data), expected_num)
        for block_no, block_num in data:
            self.assertEqual(block_num, 1)
            block_text = str(edit.document().findBlockByNumber(block_no).text())
            self.assertTrue(block_text.lower().find(text.lower()) >= 0)

class TestQDiff(TestGuideBarBase):

    def setUp(self):
        TestGuideBarBase.setUp(self)

        self.win = DiffWindow(WtDiffArgProvider(self.tree))
        self.addCleanup(self.win.close)
        self.win.show()
        self.waitUntil(lambda:self.win.view_refresh.isEnabled(), 500)

    def test_sidebyside(self):
        self.assert_sidebyside_view(self.win.diffview.guidebar_panels)

        # show complete
        self.win.click_complete(True)
        self.waitUntil(lambda:self.win.view_refresh.isEnabled(), 500)
        self.assert_sidebyside_view(self.win.diffview.guidebar_panels)

    def test_unidiff(self):
        # show unidiff
        self.win.click_toggle_view_mode(True)
        self.assert_unidiff_view(self.win.sdiffview)

        # show complete
        self.win.click_complete(True)
        self.waitUntil(lambda:self.win.view_refresh.isEnabled(), 500)
        self.assert_unidiff_view(self.win.sdiffview)

    def test_find(self):
        self.set_find_text(self.win.find_toolbar, "j")
        panels = self.win.diffview.guidebar_panels
        # Check side by side view
        self.assert_find("j", panels[0].bar, panels[0].edit, 1)
        self.assert_find("j", panels[1].bar, panels[1].edit, 3)

        # Check unidiff view
        self.win.click_toggle_view_mode(True)
        panel = self.win.sdiffview
        self.waitUntil(lambda:panel.bar.entries['find'].data, 500)
        self.assert_find("j", panel.bar, panel.edit, 4)

class TestQShelve(TestGuideBarBase):

    def setUp(self):
        TestGuideBarBase.setUp(self)

        self.win = ShelveWindow(directory=self.tree.abspath(''))
        self.addCleanup(self.win.close)
        self.win.show()
        self.main_widget = self.win.tab.widget(0)
        self.waitUntil(lambda:self.main_widget.loaded, 500)

    def test_hunk(self):
        self.main_widget.file_view.topLevelItem(0).setSelected(True)
        guidebar = self.main_widget.hunk_view.guidebar
        # hunk guide is shown only when complete mode.
        self.assertEqual(len(guidebar.entries['hunk'].data), 0)
        self.main_widget.complete_toggled(True)
        self.waitUntil(lambda:len(guidebar.entries['hunk'].data) > 0, 500)

    def test_find(self):
        self.waitUntil(lambda:self.main_widget.loaded, 500)
        self.main_widget.file_view.topLevelItem(0).setSelected(True)
        self.set_find_text(self.main_widget.find_toolbar, "j")
        guidebar = self.main_widget.hunk_view.guidebar
        edit = self.main_widget.hunk_view.browser
        self.assert_find("j", guidebar, edit)

class TestQUnshelve(TestGuideBarBase):
    def setUp(self):
        TestGuideBarBase.setUp(self)
        self.run_bzr(['shelve', '--all'], working_dir=self.tree.abspath(''))

        self.win = ShelveWindow(directory=self.tree.abspath(''),
                                initial_tab=1)
        self.addCleanup(self.win.close)
        self.win.show()
        self.main_widget = self.win.tab.widget(1)
        self.waitUntil(lambda:self.main_widget.loaded, 500)
        self.main_widget.shelve_view.topLevelItem(0).setSelected(True)

    def test_sidebyside(self):
        diffviews = self.main_widget.diffviews
        self.assert_sidebyside_view(diffviews[0].guidebar_panels)

        # show complete
        self.main_widget.complete_toggled(True)
        self.assert_sidebyside_view(diffviews[0].guidebar_panels)

    def test_unidiff(self):
        diffviews = self.main_widget.diffviews
        self.main_widget.unidiff_toggled(True)
        self.assert_unidiff_view(diffviews[1])

        # show complete
        self.main_widget.complete_toggled(True)
        self.assert_unidiff_view(diffviews[1])

    def test_find(self):
        diffviews = self.main_widget.diffviews
        self.set_find_text(self.main_widget.find_toolbar, "j")
        panels = diffviews[0].guidebar_panels
        # Check side by side view
        self.assert_find("j", panels[0].bar, panels[0].edit, 1)
        self.assert_find("j", panels[1].bar, panels[1].edit, 3)

        # Check unidiff view
        self.main_widget.unidiff_toggled(True)
        self.waitUntil(lambda:diffviews[1].bar.entries['find'].data, 500)
        self.assert_find("j", diffviews[1].bar, diffviews[1].edit, 4)

class TestQAnnotate(TestGuideBarBase):
    def load(self):
        tree = self.tree
        return tree.branch, tree, tree, 'a', tree.path2id('a')

    def setUp(self):
        TestGuideBarBase.setUp(self)
        self.tree.commit(message='2')
        self.win = AnnotateWindow(None, None, None, None, None,
                                  loader=self.load, loader_args=[])
        self.addCleanup(self.win.close)
        self.win.show()
        QTest.qWait(50)
        self.waitUntil(lambda:self.win.throbber.isVisible() == False, 500)

    def test_annotate(self):
        self.win.log_list.select_revid(self.tree.branch.get_rev_id(2))
        QTest.qWait(50)
        doc = self.win.guidebar_panel.edit.document()
        data = self.win.guidebar_panel.bar.entries['annotate'].data
        expected = [x[1] for x in DIFF if len(x[1]) > 0]
        self.assertEqual(len(data), len(expected))
        for (block_no, num), lines in zip(data, expected):
            self.assertEqual(num, len(lines))
            for i in range(num):
                text = str(doc.findBlockByNumber(block_no+i).text())
                self.assertEqual(text, lines[i])

    def test_find(self):
        self.set_find_text(self.win.find_toolbar, "j")
        guidebar = self.win.guidebar_panel.bar
        edit = self.win.guidebar_panel.edit
        self.assert_find("j", guidebar, edit)



if __name__=='__main__':
    import unittest
    unittest.main()

