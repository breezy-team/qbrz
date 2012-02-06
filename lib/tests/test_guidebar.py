if __name__=='__main__':
    import bzrlib.plugin
    bzrlib.plugin.set_plugins_path()
    bzrlib.plugin.load_plugins()

from bzrlib.plugins.qbzr.lib.tests import QTestCase
from PyQt4 import QtCore
from PyQt4.QtTest import QTest

from bzrlib.plugins.qbzr.lib.diffwindow import DiffWindow
from bzrlib.plugins.qbzr.lib.shelvewindow import ShelveWindow

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

class TestQDiff(TestGuideBarBase):

    def setUp(self):
        TestGuideBarBase.setUp(self)

        self.win = DiffWindow(WtDiffArgProvider(self.tree))
        self.addCleanup(self.win.close)

    def assert_sidebyside_view(self):
        for pos, panel in enumerate(self.win.diffview.guidebar_panels):
            bar = panel.bar
            doc = panel.edit.document()
            # Title
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

    def assert_unidiff_view(self):
        bar = self.win.sdiffview.bar
        doc = self.win.sdiffview.edit.document()
        # Title
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

    def test_sidebyside(self):
        win = self.win
        win.show()
        self.waitUntil(lambda:win.view_refresh.isEnabled(), 1000)
        QTest.qWait(200)
        self.assert_sidebyside_view()

        # show complete
        win.click_complete(True)
        self.waitUntil(lambda:win.view_refresh.isEnabled(), 1000)
        QTest.qWait(200)
        self.assert_sidebyside_view()

    def test_unidiff(self):
        win = self.win
        win.show()
        self.waitUntil(lambda:win.view_refresh.isEnabled(), 1000)
        # show unidiff
        win.click_toggle_view_mode(True)
        QTest.qWait(200)
        self.assert_unidiff_view()

        # show complete
        win.click_complete(True)
        self.waitUntil(lambda:win.view_refresh.isEnabled(), 1000)
        QTest.qWait(200)
        self.assert_unidiff_view()

    def test_find(self):
        win = self.win
        win.show()
        self.waitUntil(lambda:win.view_refresh.isEnabled(), 1000)
        win.find_toolbar.show_action_toggle(True)
        win.find_toolbar.find_text.setText("j")
        panels = win.diffview.guidebar_panels
        self.waitUntil(lambda:panels[0].bar.entries['find'].data, 1000)
        # Check side by side view
        for p, expected_num in zip(panels, (1, 3)):
            data = p.bar.entries['find'].data
            self.assertEqual(len(data), expected_num)
            for block_no, block_num in data:
                self.assertEqual(block_num, 1)
                text = str(p.edit.document().findBlockByNumber(block_no).text())
                self.assertTrue(text.lower().find("j") >= 0)

        # Check unidiff view
        win.click_toggle_view_mode(True)
        self.waitUntil(lambda:win.sdiffview.bar.entries['find'].data, 1000)
        QTest.qWait(200)
        data = win.sdiffview.bar.entries['find'].data
        self.assertEqual(len(data), 4)
        for block_no, block_num in data:
            self.assertEqual(block_num, 1)
            text = str(win.sdiffview.edit.document().findBlockByNumber(block_no).text())
            self.assertTrue(text.lower().find("j") >= 0)

class TestQShelve(TestGuideBarBase):

    def setUp(self):
        TestGuideBarBase.setUp(self)

        self.win = ShelveWindow(directory=self.tree.abspath(''))
        self.addCleanup(self.win.close)

    def test_hunk(self):
        self.win.show()
        shelve_widget = self.win.tab.widget(0)
        self.waitUntil(lambda:shelve_widget.loaded, 1000)
        shelve_widget.file_view.topLevelItem(0).setSelected(True)
        guidebar = shelve_widget.hunk_view.guidebar
        # hunk guide is shown only when complete mode.
        self.assertEqual(len(guidebar.entries['hunk'].data), 0)
        shelve_widget.complete_toggled(True)
        QTest.qWait(200)
        self.assertTrue(len(guidebar.entries['hunk'].data) > 0)

    def test_find(self):
        self.win.show()
        shelve_widget = self.win.tab.widget(0)
        self.waitUntil(lambda:shelve_widget.loaded, 1000)
        shelve_widget.file_view.topLevelItem(0).setSelected(True)
        shelve_widget.find_toolbar.show_action_toggle(True)
        shelve_widget.find_toolbar.find_text.setText("j")
        guidebar = shelve_widget.hunk_view.guidebar
        edit = shelve_widget.hunk_view.browser
        self.waitUntil(lambda:len(guidebar.entries['find'].data) > 0, 1000)
        for block_no, block_num in guidebar.entries['find'].data:
            self.assertEqual(block_num, 1)
            text = str(edit.document().findBlockByNumber(block_no).text())
            self.assertTrue(text.lower().find("j") >= 0)

if __name__=='__main__':
    import unittest
    unittest.main()

