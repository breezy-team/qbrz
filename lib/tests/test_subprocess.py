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

from io import StringIO

from breezy import (
    bencode,
    errors,
    progress,
    urlutils,
    )
from breezy.tests import (
    TestCase,
    features,
    )
from breezy.plugins.qbrz.lib.subprocess import (
    bittorrent_b_decode_prompt,
    bittorrent_b_encode_prompt,
    bittorrent_b_encode_unicode,
    bittorrent_b_encode_exception_instance,
    bittorrent_b_decode_exception_instance,
    # bittorrent_b_encode_unicode_escape,
    # bittorrent_b_decode_unicode_escape,
    SubprocessProgressView,
    SUB_PROGRESS,
    )


class TestBencode(TestCase):


    def test_bittorrent_b_encode_unicode(self):
        self.assertEqual("l7:versione", bittorrent_b_encode_unicode(["version"]))
        self.assertEqual("l3:add3:\u1234e", bittorrent_b_encode_unicode(["add", "\u1234"]))

    def test_bittorrent_b_encode_prompt(self):
        self.assertEqual(b"4:spam", bittorrent_b_encode_prompt(utf_string='spam'))
        self.assertEqual(b"9:spam\neggs", bittorrent_b_encode_prompt('spam'+'\n'+'eggs'))
        # "Р\nС" is NOT "P\nC" it's b'\xd0\xa0\n\xd0\xa1'
        # CYRILLIC CAPITAL LETTER ER, \n and CYRILLIC CAPITAL LETTER ES
        self.assertEqual(b'5:\xd0\xa0\n\xd0\xa1', bittorrent_b_encode_prompt("Р\nС"))

    def test_bittorrent_b_decode_prompt(self):
        self.assertEqual('spam', bittorrent_b_decode_prompt(b"4:spam"))
        self.assertEqual('spam'+'\n'+'eggs', bittorrent_b_decode_prompt(b"9:spam\neggs"))
        # "Р\nС" is NOT "P\nC" it's b'\xd0\xa0\n\xd0\xa1'
        # CYRILLIC CAPITAL LETTER ER, \n and CYRILLIC CAPITAL LETTER ES
        self.assertEqual("Р\nС", bittorrent_b_decode_prompt(b'5:\xd0\xa0\n\xd0\xa1'))


    # def test_bittorrent_b_encode_unicode_escape_dict(self):
    #     self.assertEqual({'key': 'foo\\nbar', 'ukey': '\\u1234'},
    #         bittorrent_b_encode_unicode_escape({'key': 'foo\nbar', 'ukey': '\u1234'}))

    # def test_bittorrent_b_decode_unicode_escape_dict(self):
    #     self.assertEqual({'key': 'foo\nbar', 'ukey': '\u1234'},
    #         bittorrent_b_decode_unicode_escape({'key': 'foo\\nbar', 'ukey': '\\u1234'}))


class TestExceptionInstanceSerialisation(TestCase):
    """Check exceptions can serialised safely with needed details preserved"""

    def check_exception_instance(self, e):
        encoded = bittorrent_b_encode_exception_instance(e)
        name, attr_dict = bittorrent_b_decode_exception_instance(encoded)
        self.assertEqual(name, e.__class__.__name__)
        return attr_dict

    def test_simple_error(self):
        """A common error with just an args attribute"""
        self.check_exception_instance(ValueError("Simple"))
        # TODO: if transmitted assert args/message in return dict

    def test_non_ascii_bytes(self):
        """An error with a non-ascii bytestring attribute"""
        self.check_exception_instance(OSError(13, "Lupa ev\xc3\xa4tty"))
        # TODO: if transmitted assert errno/strerror/etc in return dict

    def test_unreprable_obj(self):
        """Ensure an object with a broken repr doesn't break the exception"""
        class Bad(object):
            def __repr__(self):
                return self.attribute_that_does_not_exist
        self.check_exception_instance(ValueError(Bad()))
        # TODO: if transmitted assert message equals the placeholder string

    def test_uncommittedchanges_display_url(self):
        """The display_url of UncommittedChanges errors should be serialised"""
        self.requireFeature(features.UnicodeFilenameFeature)
        path = "\u1234"
        class FakeTree(object):
            def __init__(self, url):
                self.user_url = url
        attrs = self.check_exception_instance(errors.UncommittedChanges(FakeTree(urlutils.local_path_to_url(path))))
        self.assertIsSameRealPath(path, urlutils.local_path_from_url(attrs["display_url"]))


class TestSubprocessProgressView(TestCase):
    """Check serialisation of progress updates"""

    def decode_progress(self, bencoded_data:bytes) -> list:
        """Decodes string of bencoded progress output to list of updates

        Duplicates logic decoding logic from `SubProcessWidget.readStdout` and
        `SubProcessWidget.setProgress` which would be good to factor out.

        bdecode requires bencoded bytes and bencoded_data should BE bytes
        but doesn't appear to be.
        """
        updates = []
        for line in bencoded_data.split("\n"):
            if line.startswith(SUB_PROGRESS):
                # bdecode needs bytes, but we need to snip off the leading SUB_PROGRESS first
                n, transport_activity, task_info = bencode.bdecode(line[len(SUB_PROGRESS):].encode('utf-8'))
                if n == 1000000 and not task_info:
                    task_message = "Finished!"
                else:
                    # task_info will be a list of byte-strings, so join and then decode
                    task_message = b" / ".join(task_info).decode("utf-8")
                # transport_activity will be bytes too...
                updates.append((n, transport_activity.decode('utf-8'), task_message))
        # Now we'll return a list of lines like: (0, '', 'Finding revisions /  0/2')
        return updates

    def make_stream_and_task(self):
        """Create a new output stream and ProgressTask for testing"""
        sio = StringIO()
        task = progress.ProgressTask(progress_view=SubprocessProgressView(sio))
        return sio, task

    @staticmethod
    def refresh(task):
        """Allow a new update without a time delay"""
        task.progress_view._last_repaint = 0

    def test_task_one_update(self):
        """Sending a single progress update should work"""
        sio, task = self.make_stream_and_task()
        task.update("Finding revisions", 0, 2)
        self.assertEqual([(0, "", "Finding revisions /  0/2")],
            self.decode_progress(sio.getvalue()))

    def test_task_multiple_updates(self):
        """Sending a single progress update should work"""
        sio, task = self.make_stream_and_task()
        task.update("Finding revisions", 0, 2)
        self.refresh(task)
        task.update("Finding revisions", 1, 2)
        self.refresh(task)
        task.update("Finding revisions", 2, 2)
        self.assertEqual([
                (0, "", "Finding revisions /  0/2"),
                (500000, "", "Finding revisions /  1/2"),
                (1000000, "", "Finding revisions /  2/2")],
            self.decode_progress(sio.getvalue()))

    def test_task_update_and_finished(self):
        """Sending a single progress update should work"""
        sio, task = self.make_stream_and_task()
        task.update("Finding revisions", 0, 2)
        self.refresh(task)
        try:
            task.finished()
        except AttributeError as e:
            self.knownFailure("No ui_factory so calls missing task_finished")
        self.assertEqual([(0, "", "Finding revisions /  0/2")],
            self.decode_progress(sio.getvalue()))

    def test_task_non_ascii_message(self):
        """A localised progress message should be transmitted cleanly"""
        sio, task = self.make_stream_and_task()
        # Would be nice to use an actual translation
        task.update("\u1234", 0, 2)
        self.assertEqual([(0, "", "\u1234 /  0/2")], self.decode_progress(sio.getvalue()))


