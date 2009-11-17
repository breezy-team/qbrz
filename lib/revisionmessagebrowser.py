# -*- coding: utf-8 -*-
#
# QBzr - Qt frontend to Bazaar commands
# Copyright (C) 2009 Gary van der Merwe <garyvdm@gmail.com>
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

import os
import re
import sys
import itertools

from PyQt4 import QtCore, QtGui

from bzrlib.revision import Revision, CURRENT_REVISION
from bzrlib import (
    lazy_regex,
    osutils,
    urlutils,
    )

from bzrlib.plugins.qbzr.lib.i18n import gettext, N_, ngettext

from bzrlib.plugins.qbzr.lib.lazycachedrevloader import load_revisions
from bzrlib.plugins.qbzr.lib.util import (
    runs_in_loading_queue,
    format_timestamp,
    get_message,
    get_summary,
    )

from bzrlib.lazy_import import lazy_import
lazy_import(globals(), '''
from bzrlib import foreign
from bzrlib.plugins.qbzr.lib.uifactory import ui_current_widget
from bzrlib.plugins.qbzr.lib import logmodel
from bzrlib.plugins.qbzr.lib.logwidget import LogList
''')

def htmlencode(string):
    return "<br/>".join(
           string.replace("&", "&amp;")
                 .replace("<", "&lt;")
                 .replace(">", "&gt;")
                 .replace("\"", "&quot;")
                 .splitlines())

_email_re = lazy_regex.lazy_compile(r'([a-z0-9_\-.+]+@[a-z0-9_\-.+]+)', re.IGNORECASE)
_link1_re = lazy_regex.lazy_compile(r'([\s>])(https?)://([^\s<>{}()]+[^\s.,<>{}()])', re.IGNORECASE)
_link2_re = lazy_regex.lazy_compile(r'(\s)www\.([a-z0-9\-]+)\.([a-z0-9\-.\~]+)((?:/[^ <>{}()\n\r]*[^., <>{}()\n\r]?)?)', re.IGNORECASE)
_tag_re = lazy_regex.lazy_compile(r'[, ]')
_start_of_line_whitespace_re = lazy_regex.lazy_compile(r'(?m)^ +')

def htmlize(text):
    text = htmlencode(text)
    text = _start_of_line_whitespace_re.sub(lambda m: "&nbsp;" * len(m.group()), text)
    text = text.replace("\n", '<br />')
    text = _email_re.sub('<a href="mailto:\\1">\\1</a>', text)
    text = _link1_re.sub('\\1<a href="\\2://\\3">\\2://\\3</a>', text)
    text = _link2_re.sub('\\1<a href="http://www.\\2.\\3\\4">www.\\2.\\3\\4</a>', text)
    return text

class RevisionMessageBrowser(QtGui.QTextBrowser):
    """Widget to display revision metadata and messages."""
    
    _display_revids = []
    _all_loaded_revs = {}
    
    def set_display_revids(self, revids, repo):
        self._display_revids = revids
        self._all_loaded_revs = {}
        
        revids_to_load = set(revids)
        for revid in revids:
            revids_to_load.update(set(self.get_parents(revid)))
            revids_to_load.update(set(self.get_children(revid)))
        
        load_revisions(list(revids_to_load), repo, 
                       revisions_loaded=self.revisions_loaded,
                       pass_prev_loaded_rev=True)
    
    def revisions_loaded(self, revs_loaded, last_call):
        self._all_loaded_revs.update(revs_loaded)
        
        rev_html = []
        for revid in self._display_revids:
            props = []
            message = ""
            props.append((gettext("Revision:"),
                          "%s revid:%s" % (self.get_revno(revid), revid)))
            
            parents = self.get_parents(revid)
            children = self.get_children(revid)
            
            def short_text(summary, length):
                if len(summary) > length:
                    return summary[:length-1] + u"\u2026"
                else:
                    return summary
        
            def revision_list_html(revids):
                revs = []
                for revid in revids:
                    revno = self.get_revno(revid)
                    if revid in self._all_loaded_revs:
                        summary = get_summary(self._all_loaded_revs[revid])
                        revs.append(
                            '<a href="qlog-revid:%s" title="%s">%s: %s</a>' %
                            (revid, htmlencode(summary), revno, 
                             htmlencode((short_text(summary, 60)))))
                    else:
                        revs.append(
                            '<a href="qlog-revid:%s">revid: %s</a>' %
                            (revid, revid))
                return '<br>'.join(revs)
            
            if parents:
                props.append((gettext("Parents:"), 
                              revision_list_html(parents)))
            if children:
                props.append((gettext("Children:"), 
                              revision_list_html(children)))
            
            if not revid == CURRENT_REVISION:
                if revid in self._all_loaded_revs:
                    rev = self._all_loaded_revs[revid]
                    props.extend(self.loaded_revision_props(rev))
                    message = htmlize(get_message(rev))
                    
                    search_replace = self.get_search_replace(revid)
                    if search_replace:
                        for search, replace in search_replace:
                            message = re.sub(search, replace, message)
            else:
                message = gettext("Uncommited Working Tree Changes")

            text = []
            text.append('<table style="background:#EDEDED;">')
            for prop in props:
                # white-space: pre is needed because in some languaged, some 
                # prop labels have more than 1 word. white-space: nowrap
                # does not work for Japanese, but pre does.
                text.append(('<tr><td style="padding-left:2px; font-weight:bold; white-space: pre;" align="right">%s</td>'
                    '<td width="100%%">%s</td></tr>') % prop)
            text.append('</table>')
        
            text.append('<div style="margin:2px;margin-top:0.5em;">%s</div>' % message)
            rev_html.append("".join(text))
    
        self.setHtml("<br>".join(rev_html))
    
    def loaded_revision_props(self, rev):
        props = []
        if rev.timestamp is not None:
            props.append((gettext("Date:"), format_timestamp(rev.timestamp)))
        if rev.committer:
            props.append((gettext("Committer:"), htmlize(rev.committer)))
        
        authors = rev.properties.get('authors')
        if not authors:
            authors = rev.properties.get('author')
        if authors:
            props.append((gettext("Author:"), htmlize(authors)))
        
        foreign_attribs = None
        if isinstance(rev, foreign.ForeignRevision):
            foreign_attribs = \
                rev.mapping.vcs.show_foreign_revid(rev.foreign_revid)
        elif ":" in rev.revision_id:
            try:
                foreign_revid, mapping = \
                    foreign.foreign_vcs_registry.parse_revision_id(
                        rev.revision_id)
                
                foreign_attribs = \
                    mapping.vcs.show_foreign_revid(foreign_revid)
            except errors.InvalidRevisionId:
                pass
        
        if foreign_attribs:
            keys = foreign_attribs.keys()
            keys.sort()
            for key in keys:
                props.append((key + ":", foreign_attribs[key]))
        return props
    
    def get_parents(self, revid):
        # Normaly, we don't know how to do this.
        return []
    
    def get_children(self, revid):
        # Normaly, we don't know how to do this.
        return []
    
    def get_revno(self, revid):
        # Normaly, we don't know how to do this.
        return ""

    def get_search_replace(self, revid):
        # Normaly, we don't know how to do this.
        return None
    
    def setSource(self, uri):
        pass
    

class LogListRevisionMessageBrowser(RevisionMessageBrowser):
    """RevisionMessageBrowser customized to work with LogList"""
    

    
    def __init__(self, log_list, parent=None):
        super(type(self), self).__init__(parent)
        self.log_list = log_list
        assert(isinstance(self.log_list, LogList))

        self.connect(self.log_list.selectionModel(),
                     QtCore.SIGNAL("selectionChanged(QItemSelection, QItemSelection)"),
                     self.update_selection)
        self.connect(self,
                     QtCore.SIGNAL("anchorClicked(QUrl)"),
                     self.link_clicked)
        self.throbber = parent.throbber

    @runs_in_loading_queue
    @ui_current_widget
    def update_selection(self, selected, deselected):
        indexes = self.log_list.get_selection_indexes()
        if not indexes:
            self.setHtml("")
        else:
            revids = [str(index.data(logmodel.RevIdRole).toString())
                      for index in indexes]
            self.set_display_revids(
                revids, self.log_list.graph_provider.get_repo_revids)
    
    def link_clicked(self, url):
        scheme = unicode(url.scheme())
        if scheme == 'qlog-revid':
            revision_id = unicode(url.path())
            self.log_list.log_model.ensure_rev_visible(revision_id)
            index = self.log_list.log_model.indexFromRevId(revision_id)
            index = self.log_list.filter_proxy_model.mapFromSource(index)
            self.log_list.setCurrentIndex(index)
        else:
            open_browser(str(url.toEncoded()))

    def get_parents(self, revid):
        return self.log_list.graph_provider.graph_parents[revid]
    
    def get_children(self, revid):
        return self.log_list.graph_provider.graph_children[revid]
    
    def get_revno(self, revid):
        return self.log_list.graph_provider.revid_rev[revid].revno_str

