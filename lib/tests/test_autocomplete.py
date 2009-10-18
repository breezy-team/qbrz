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
from StringIO import StringIO
from bzrlib.plugins.qbzr.lib.autocomplete import get_wordlist_builder


class TestAutocomplete(TestCase):

    def assertIn(self, item, container):
        """Assert that `item` is present in `container`."""
        if item not in container:
            raise AssertionError("value(s) %r not present in container %r" %
                                 (item, container))

    def test_cpp_header(self):
        source = '''
class ClassName {
public:
    ClassName() { calledFunction(); }
};
'''
        words = list(get_wordlist_builder('.h').iter_words(StringIO(source)))
        self.assertIn('ClassName', words)
        self.assertIn('calledFunction', words)

    def test_cpp_header_space_after_name(self):
        # space between function name and opening parenthesis is legal in C
        source = "void  foo_bar (void);"
        words = list(get_wordlist_builder('.h').iter_words(StringIO(source)))
        self.assertIn('foo_bar', words)

    def test_cpp_source(self):
        source = '''
ClassName::function1()
{
    function2()
}
'''
        words = list(get_wordlist_builder('.cpp').iter_words(StringIO(source)))
        self.assertIn('ClassName', words)
        self.assertIn('ClassName::function1', words)
        self.assertIn('function1', words)
        self.assertIn('function2', words)

    def test_c_source_space_after_name(self):
        # space between function name and opening parenthesis is legal in C
        source = """
void  foo_bar (void)
{
    return;
}
"""
        words = list(get_wordlist_builder('.c').iter_words(StringIO(source)))
        self.assertIn('foo_bar', words)

    def test_c_header_with_typedef(self):
        source = """
typedef struct Foo
{
    int i;
} Foo;

typedef union Bar {
    int i;
    float f;
} Bar;
"""
        words = list(get_wordlist_builder('.h').iter_words(StringIO(source)))
        self.assertIn('Foo', words)
        self.assertIn('Bar', words)

    def test_java(self):
        source = '''
package bar.foo;

public class ClassName1 extends ClassName2
{
    public void function1()
    {
    }
}
'''
        words = list(get_wordlist_builder('.java').iter_words(StringIO(source)))
        self.assertIn('ClassName1', words)
        self.assertIn('ClassName2', words)
        self.assertIn('function1', words)

    def test_python(self):
        source = '''
class ClassName(object):

    def function(self):
        self.var = 1
'''
        words = list(get_wordlist_builder('.py').iter_words(StringIO(source)))
        self.assertIn('ClassName', words)
        self.assertIn('function', words)
        self.assertIn('var', words)
