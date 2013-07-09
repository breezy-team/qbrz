# -*- coding: utf-8 -*-
#
# QBzr - Qt frontend to Bazaar commands
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
    bugtracker,
    config,
    lazy_regex,
    )


# XXX use just (\d+) at the end of URL as simpler regexp?
_bug_id_re = lazy_regex.lazy_compile(r'(?:'
    r'bugs/'                    # Launchpad bugs URL
    r'|ticket/'                 # Trac bugs URL
    r'|show_bug\.cgi\?id='      # Bugzilla bugs URL
    r'|issues/(?:show/)?'       # Redmine bugs URL
    r'|DispForm.aspx\?ID='      # Microsoft SharePoint URL
    r'|default.asp\?'           # Fogbugz URL
    r'|issue'                   # Roundup issue tracker URL
    r'|view.php\?id='           # Mantis bug tracker URL
    r'|aid='                    # FusionForge bug tracker URL
    r'|task_id='                # Flyspray bug tracker URL (http://flyspray.org) - old style URLs(?)
    r'|task/'                   # Flyspray itself bugtracker (https://bugs.flyspray.org)
    r')(\d+)(?:\b|$)')


_jira_bug_id_re = lazy_regex.lazy_compile(r'(?:.*/browse/)([A-Z][A-Z0-9_]*-\d+)($)')


_unique_bugtrackers = ('lp', 'deb', 'gnome')
# bugtracker config settings
_bugtracker_re = lazy_regex.lazy_compile('(bugtracker|trac|bugzilla)_(.+)_url')


def get_bug_id(bug_url):
    match = _bug_id_re.search(bug_url)
    if match:
        return match.group(1)
    match = _jira_bug_id_re.search(bug_url)
    if match:
        return match.group(1)
    return None


class FakeBranchForBugs(object):
    """Fake branch required for bzrlib/bugtracker.py"""

    def __init__(self):
        self._config = config.GlobalConfig()

    def get_config(self):
        return self._config


def bug_urls_to_ids(bug_urls, branch=None):
    """Convert list of bug URLs to list of bug ids in form tag:id.

    @param bug_urls: list of bug URLs from revision property 'bugs'.
    @param branch: current branch object or None.
    """
    result = []
    urls_dict = {}
    for i in bug_urls:
        url = i.split(' ')[0]
        n = get_bug_id(url)
        if n:
            urls_dict[url] = n
    if not urls_dict:
        return result
    # collect bug tags
    bug_tags = {}
    bug_tags.update(get_unique_bug_tags())
    bug_tags.update(get_global_bug_tags())
    if branch is not None:
        bug_tags.update(get_branch_bug_tags(branch))
    else:
        branch = FakeBranchForBugs()
    # try to convert bug urls to tag:id values
    for k,n in urls_dict.iteritems():
        for tag in bug_tags:
            url = bugtracker.get_bug_url(tag, branch, n)
            if url == k:
                result.append(tag+':'+n)
                break
    return sorted(result)


def get_user_bug_trackers_tags(config_keys):
    """Return dict of abbreviated bugtrackers tags from user config.

    @param config_keys: options names from config which could be
        bugtracker settings.

    @return: dict with tags as keys and bugtracker_type as values,
        where bugtracker_type is prefix of tag entry in config_dict.
        Possible prefixes are: bugtracker, trac, bugzilla
    """
    result = {}
    for key in config_keys:
        m = _bugtracker_re.match(key)
        if m:
            result[m.group(2)] = m.group(1)
    return result

def get_unique_bug_tags():
    """Return dict of global unique bugtrackers, e.g. Launchpad."""
    return dict([(i, 'unique') for i in _unique_bugtrackers])

def get_global_bug_tags():
    """Return bug tags collected from global config bazaar.conf"""
    cfg = config.GlobalConfig()
    keys = cfg._get_parser().get('DEFAULT', {}).keys()
    return get_user_bug_trackers_tags(keys)

def get_branch_bug_tags(branch):
    """Return bug tags collected from branch configs
    (branch.conf and locations.conf).
    """
    result = {}
    cfg = branch.get_config()
    loc_cfg = cfg._get_location_config()
    keys = loc_cfg._get_parser().scalars
    result.update(get_user_bug_trackers_tags(keys))
    br_cfg = cfg._get_branch_data_config()
    keys = br_cfg._get_parser().scalars
    result.update(get_user_bug_trackers_tags(keys))
    return result
