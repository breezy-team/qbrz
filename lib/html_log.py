# Copyright (C) 2009 Canonical Ltd
#
# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation; either version 2 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program; if not, write to the Free Software
# Foundation, Inc., 59 Temple Place, Suite 330, Boston, MA  02111-1307  USA


from cgi import escape
import codecs
from cStringIO import StringIO

from bzrlib import log


def log_as_html(branch, rqst):
    """Get the log for a branch as HTML text."""
    sio = codecs.getwriter('utf-8')(StringIO())
    #sio.encoding = 'utf-8'
    try:
        lf = HtmlLogFormatter(sio)
        log.Logger(branch, rqst).show(lf)
        return sio.getvalue().decode('utf-8')
    finally:
        sio.close()


class HtmlLogFormatter(log.LineLogFormatter):

    def __init__(self, *args, **kwargs):
        super(HtmlLogFormatter, self).__init__(*args, **kwargs)
        self.show_markers = False

    def begin_log(self):
        self.to_file.write('<table>\n')
        headers = ['Rev', 'Message', 'Date', 'Author']
        if self.show_markers:
            headers.append('Markers')
        self.to_file.write(self._make_row(headers, header=True))

    def end_log(self):
        self.to_file.write("</table>\n")

    def log_revision(self, revision):
        rev = revision.rev
        cells = []
        if revision.revno:
            # Is it worth doing anything smart with depth here?
            revno_str = "%s" % revision.revno
        else:
            # don't show revno when it is None
            revno_str = ""
        cells.append(revno_str)
        cells.append(rev.get_summary())
        cells.append(self.date_string(rev))
        cells.append(self.author_string(rev))
        if self.show_markers:
            markers = []
            if len(rev.parent_ids) > 1:
                markers.append('[merge]')
            if revision.tags:
                markers.append('{%s} ' % (', '.join(revision.tags)))
            cells.append(" ".join(markers))
        self.to_file.write(self._make_row(cells))

    def author_string(self, rev):
        return self.short_author(rev)

    def _make_row(self, cells, header=False):
        if header:
            cells = ['<th align="left">%s</th>' % escape(cell)
                for cell in cells]
        else:
            cells = ["<td>%s&nbsp;</td>" % escape(cell)
                for cell in cells]
        return "<tr>%s</tr>\n" % ''.join(cells)
