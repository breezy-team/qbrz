# -*- coding: utf-8 -*-
#
# QBzr - Qt frontend to Bazaar commands
# Copyright (C) 2010 Alexander Belchenko <bialix@ukr.net>
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

"""Regenerate English en.po file from POT file."""

import os


def regenerate_en(prj_name, po_dir, pot_file, spawn):
    if prj_name and prj_name != 'messages':
        en_po = '%s-en.po' % prj_name
    else:
        en_po = 'en.po'
    en_po_path = os.path.join(po_dir, en_po)
    spawn(['msginit',
        '--no-translator',
        '-l', 'en',
        '-i', os.path.join(po_dir, pot_file),
        '-o', en_po_path,
        ])
    # normalize line-endings in en.po file (to LF)
    f = open(en_po_path, 'rU')
    s = f.read()
    f.close()
    f = open(en_po_path, 'wb')
    f.write(s)
    f.close()
