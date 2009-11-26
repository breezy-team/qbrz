# -*- coding: utf-8 -*-
#
# Contributors:
#   Alexander Belchenko
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


from bzrlib import (
    tests,
    )
from bzrlib.plugins.qbzr.lib.revisionmessagebrowser import (
    htmlencode,
    htmlize,
    )


class TestHtmlUtils(tests.TestCase):

    def test_htmlencode(self):
        self.assertEquals('&quot;&amp;&lt;&gt;', htmlencode('"&<>'))
        self.assertEquals('\n', htmlencode('\n'))

    def test_htmlize_convert_leading_spaces_to_nbsp(self):
        self.assertEqual('foo bar', htmlize('foo bar'))
        self.assertEqual("0<br />"
                         "&nbsp;1<br />"
                         "&nbsp;&nbsp;2<br />"
                         "0",
                         htmlize("0\n 1\n  2\n0"))
        self.assertEqual('&nbsp;foo bar', htmlize(' foo bar'))
