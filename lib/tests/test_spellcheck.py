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

"""Tests for QBzr plugin."""

from bzrlib.tests import TestCase
try:
    from bzrlib.tests.features import Feature
except ImportError: # bzr < 2.5
    from bzrlib.tests import Feature
from bzrlib.plugins.qbzr.lib.spellcheck import SpellChecker


class _PyEnchantFeature(Feature):

    def _probe(self):
        try:
            from bzrlib.plugins.qbzr.lib.spellcheck_enchant import EnchantSpellChecker
        except ImportError:
            return False
        if "en-US" not in EnchantSpellChecker.list_languages():
            return False
        return True

PyEnchantFeature = _PyEnchantFeature()


class TestSpellcheck(TestCase):

    _test_needs_features = [PyEnchantFeature]

    def setUp(self):
        super(TestSpellcheck, self).setUp()
        def cleanup():
            del self.checker
        self.checker = SpellChecker("en-US")
        self.addCleanup(cleanup)

    def test_correct(self):
        result = list(self.checker.check("yes"))
        self.assertEquals([], result)

    def test_incorrect(self):
        result = list(self.checker.check("yess"))
        self.assertEquals([(0, 4)], result)

    def test_camel_case(self):
        result = list(self.checker.check("YesNo"))
        self.assertEquals([], result)

    def test_camel_case_2(self):
        result = list(self.checker.check("yesNo"))
        self.assertEquals([], result)

    def test_underscores(self):
        result = list(self.checker.check("Yes_No"))
        self.assertEquals([], result)

    def test_email(self):
        result = list(self.checker.check("yes name@example.com no"))
        self.assertEquals([], result)

    def test_url(self):
        result = list(self.checker.check("yes http://example.com/foo/bar no"))
        self.assertEquals([], result)
