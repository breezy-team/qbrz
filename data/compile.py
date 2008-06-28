#!/usr/bin/env python

import os, sys

RESFILE = '../lib/resources.py'

os.system("pyrcc4 qbzr.qrc -o "+RESFILE)
if sys.platform == 'win32':
    f = open(RESFILE, 'rU')
    s = f.read()
    f.close()
    f = open(RESFILE, 'wb')
    f.write(s)
    f.close()
