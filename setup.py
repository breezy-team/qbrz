#!/usr/bin/env python
# -*- coding: utf-8 -*-

from distutils.core import setup

try:
    from extras import cmdclass
except ImportError:
    cmdclass = {}

ext_modules = []

setup(name='qbzr',
      description='Qt4 frontend for Bazaar',
      keywords='plugin bzr qt qbzr',
      version='0.23.2',
      url='http://wiki.bazaar.canonical.com/QBzr',
      license='GPL',
      author='QBzr Developers',
      author_email='qbzr@googlegroups.com',
      package_dir={'bzrlib.plugins.qbzr': '.'},
      package_data={'bzrlib.plugins.qbzr': ['locale/*/LC_MESSAGES/qbzr.mo',
                                            '*.txt',
                                            ]},
      packages=['bzrlib.plugins.qbzr',
                'bzrlib.plugins.qbzr.lib',
                'bzrlib.plugins.qbzr.lib.extra',
                'bzrlib.plugins.qbzr.lib.tests',
                'bzrlib.plugins.qbzr.lib.widgets',
                ],
      ext_modules=ext_modules,
      cmdclass=cmdclass,
)
