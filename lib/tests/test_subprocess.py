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

from cStringIO import StringIO

from bzrlib import (
    bencode,
    errors,
    progress,
    urlutils,
    )
from bzrlib.tests import (
    TestCase,
    features,
    )
from bzrlib.plugins.qbzr.lib.subprocess import (
    bdecode_prompt,
    bencode_prompt,
    bencode_unicode,
    bencode_exception_instance,
    bdecode_exception_instance,
    encode_unicode_escape,
    decode_unicode_escape,
    SubprocessProgressView,
    SUB_PROGRESS,
    )
from bzrlib.plugins.qbzr.lib.tests import compatibility


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


class TestExceptionInstanceSerialisation(TestCase):
    """Check exceptions can serialised safely with needed details preserved"""

    def check_exception_instance(self, e):
        encoded = bencode_exception_instance(e)
        name, attr_dict = bdecode_exception_instance(encoded)
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
        self.requireFeature(compatibility.UnicodeFilenameFeature)
        path = u"\u1234"
        class FakeTree(object):
            def __init__(self, url):
                self.user_url = url
        attrs = self.check_exception_instance(errors.UncommittedChanges(
            FakeTree(urlutils.local_path_to_url(path))))
        self.assertIsSameRealPath(path,
            urlutils.local_path_from_url(attrs["display_url"]))


class TestSubprocessProgressView(TestCase):
    """Check serialisation of progress updates"""

    def decode_progress(self, bencoded_data):
        """Decodes string of bencoded progress output to list of updates

        Duplicates logic decoding logic from `SubProcessWidget.readStdout` and
        `SubProcessWidget.setProgress` which would be good to factor out.
        """
        updates = []
        for line in bencoded_data.split("\n"):
            if line.startswith(SUB_PROGRESS):
                n, transport_activity, task_info = bencode.bdecode(
                    line[len(SUB_PROGRESS):])
                if n == 1000000 and not task_info:
                    task_message = u"Finished!"
                else:
                    task_message = " / ".join(task_info).decode("utf-8")
                updates.append((n, transport_activity, task_message))
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
        task.update(u"Finding revisions", 0, 2)
        self.assertEqual([(0, "", u"Finding revisions /  0/2")],
            self.decode_progress(sio.getvalue()))

    def test_task_multiple_updates(self):
        """Sending a single progress update should work"""
        sio, task = self.make_stream_and_task()
        task.update(u"Finding revisions", 0, 2)
        self.refresh(task)
        task.update(u"Finding revisions", 1, 2)
        self.refresh(task)
        task.update(u"Finding revisions", 2, 2)
        self.assertEqual([
                (0, "", u"Finding revisions /  0/2"), 
                (500000, "", u"Finding revisions /  1/2"), 
                (1000000, "", u"Finding revisions /  2/2")],
            self.decode_progress(sio.getvalue()))

    def test_task_update_and_finished(self):
        """Sending a single progress update should work"""
        sio, task = self.make_stream_and_task()
        task.update(u"Finding revisions", 0, 2)
        self.refresh(task)
        try:
            task.finished()
        except AttributeError, e:
            self.knownFailure("No ui_factory so calls missing task_finished")
        self.assertEqual([(0, "", u"Finding revisions /  0/2")],
            self.decode_progress(sio.getvalue()))

    def test_task_non_ascii_message(self):
        """A localised progress message should be transmitted cleanly"""
        sio, task = self.make_stream_and_task()
        # Would be nice to use an actual translation
        task.update(u"\u1234", 0, 2)
        self.assertEqual([(0, "", u"\u1234 /  0/2")],
            self.decode_progress(sio.getvalue()))


