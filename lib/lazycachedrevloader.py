# -*- coding: utf-8 -*-
#
# QBzr - Qt frontend to Bazaar commands
# Copyright (C) 2006-2007 Gary van der Merwe <garyvdm@gmail.com> 
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

#import weakref
from time import clock

from PyQt4 import QtCore

from bzrlib.transport.local import LocalTransport
from bzrlib.repository import Repository
from bzrlib.remote import RemoteRepository
from bzrlib.plugins.qbzr.lib.uifactory import current_throbber

cached_revisions = {} #weakref.WeakValueDictionary()
"""Global cache of revisions."""

def load_revisions(revids, repo,
                   time_before_first_ui_update = 0.5,
                   local_batch_size = 30,
                   remote_batch_size = 5,
                   before_batch_load = None,
                   revisions_loaded = None,
                   pass_prev_loaded_rev = False):
    
    start_time = clock()
    showed_throbber = False
    revids = [revid for revid in revids if not revid == "root:"]
    return_revisions = {}
    throbber = current_throbber()
    
    try:
        for revid in [revid for revid in revids
                      if revid in cached_revisions]:
            return_revisions[revid] = cached_revisions[revid]
        if pass_prev_loaded_rev:
            if revisions_loaded is not None:
                revisions_loaded(return_revisions, False)
        
        revs_loaded = {}
        revids = [revid for revid in revids if revid not in cached_revisions]
        if revids:
            if isinstance(repo, Repository) or isinstance(repo, RemoteRepository):
                repo_revids=((repo, revids),)
            else:
                repo_revids = repo(revids)
            
            for repo, revids in repo_revids:
                repo_is_local = isinstance(repo.bzrdir.transport, LocalTransport)
                if repo_is_local:
                    batch_size = local_batch_size
                else:
                    batch_size = remote_batch_size
                
                if revids:
                    repo.lock_read()
                    try:
                        if not repo_is_local:
                            update_ui()
                        
                        for offset in range(0, len(revids), batch_size):
                            
                            running_time = clock() - start_time
                            
                            if time_before_first_ui_update < running_time:
                                if revisions_loaded is not None:
                                    revisions_loaded(revs_loaded, False)
                                    revs_loaded = {}
                                if not showed_throbber:
                                    if throbber:
                                        throbber.show()
                                        showed_throbber = True
                                update_ui()
                            
                            batch_revids = revids[offset:offset+batch_size]
                            
                            if before_batch_load is not None:
                                stop = before_batch_load(repo, batch_revids)
                                if stop:
                                    break
                            
                            for rev in repo.get_revisions(batch_revids):
                                cached_revisions[rev.revision_id] = rev
                                return_revisions[rev.revision_id] = rev
                                revs_loaded[rev.revision_id] = rev
                                rev.repository = repo
                    finally:
                        repo.unlock()
            
            if revisions_loaded is not None:
                revisions_loaded(revs_loaded, True)
    finally:
        if showed_throbber:
            throbber.hide()
    
    return return_revisions

def update_ui():
    QtCore.QCoreApplication.processEvents()

