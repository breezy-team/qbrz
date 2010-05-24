# -*- coding: utf-8 -*-
#
# QBzr - Qt frontend to Bazaar commands
#
# Contributors:
#   Alexander Belchenko, 2009
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

from bzrlib.tests import TestCase
from bzrlib.plugins.qbzr.lib.subprocess import (
    bdecode_prompt,
    bencode_prompt,
    bencode_unicode,
    encode_unicode_escape,
    decode_unicode_escape,
    )


class TestBencode(TestCase):

    def test_bencode_unicode(self):
        self.assertEqual(u"l7:versione", bencode_unicode(["version"]))
        self.assertEqual(u"l3:add3:\u1234e", 
            bencode_unicode([u"add", u"\u1234"]))

    def test_bencode_prompt(self):
        self.assertEqual("4:spam", bencode_prompt('spam'))
        self.assertEqual("10:spam\\neggs", bencode_prompt('spam'+'\n'+'eggs'))
        self.assertEqual("14:\\u0420\\n\\u0421",
            bencode_prompt(u'\u0420\n\u0421'))

    def test_bdecode_prompt(self):
        self.assertEqual('spam', bdecode_prompt("4:spam"))
        self.assertEqual('spam'+'\n'+'eggs', bdecode_prompt("10:spam\\neggs"))
        self.assertEqual(u'\u0420\n\u0421',
            bdecode_prompt("14:\\u0420\\n\\u0421"))

    def test_encode_unicode_escape_dict(self):
        self.assertEqual({'key': 'foo\\nbar', 'ukey': u'\\u1234'},
            encode_unicode_escape({'key': 'foo\nbar', 'ukey': u'\u1234'}))

    def test_decode_unicode_escape_dict(self):
        self.assertEqual({'key': 'foo\nbar', 'ukey': u'\u1234'},
            decode_unicode_escape({'key': 'foo\\nbar', 'ukey': u'\\u1234'}))
