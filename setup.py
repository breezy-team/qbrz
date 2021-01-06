#!/usr/bin/env python
# -*- coding: utf-8 -*-

import sys

if sys.version_info < (3,4,0):
    sys.stderr.write("You need python 3.4.0 or later to run this setup script\n")
    exit(1)

# from distutils.core import setup
from setuptools import setup

# RJL Patched out temporarily
try:
    from .extras import cmdclass
except (ImportError, SystemError):
    cmdclass = {}
except ValueError:
    try:
        from extras import cmdclass
    except ImportError:
        cmdclass = {}

# RJLRJL: patiencediff and dulwich also needed
# Dulwich is installed with breezy and you cannot use this without breezy anyway
#
# https://katastrophos.net/andre/blog/2009/03/16/setting-up-the-inno-setup-compiler-on-debian/
# ... is needed for inno setup

from extras import cmdclass

# Get the version number from version.txt
with open('version.txt', encoding='utf-8') as f:
    version_str = f.read().strip()

ext_modules = []

setup(name='qbrz',
      description='Qt5 frontend for Breezy',
      keywords='plugin brz qt qbrz',
      version=version_str,
      url='https://www.breezy-vcs.org/',
      license='GPL',
      author='QBrz Developers',
      author_email='qbrz@googlegroups.com',
      package_dir={'breezy.plugins.qbrz': '.'},
      package_data={'breezy.plugins.qbrz': ['locale/*/LC_MESSAGES/qbrz.mo',
                                            '*.txt',
                                            ]},
      packages=['breezy.plugins.qbrz',
                'breezy.plugins.qbrz.lib',
                'breezy.plugins.qbrz.lib.extra',
                'breezy.plugins.qbrz.lib.tests',
                'breezy.plugins.qbrz.lib.widgets',
                ],
      ext_modules=ext_modules,
      cmdclass=cmdclass,
      install_requires = ['patiencediff', 'breezy'],

)
