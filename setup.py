#!/usr/bin/env python
# -*- coding: utf-8 -*-

from distutils.core import setup

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
# https://katastrophos.net/andre/blog/2009/03/16/setting-up-the-inno-setup-compiler-on-debian/
# ... is needed for inno setup

from extras import cmdclass


ext_modules = []

setup(name='qbrz',
      description='Qt4 frontend for Breezy',
      keywords='plugin brz qt qbrz',
      version='0.3.1',
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
)
