#!/usr/bin/env python
# -*- coding: utf-8 -*-

from distutils.core import setup

try:
    from extras import cmdclass
except ImportError:
    cmdclass = {}

ext_modules = []

setup(name='qbrz',
      description='Qt4 frontend for Bazaar',
      keywords='plugin bzr qt qbrz',
      version='0.23.2',
      url='http://wiki.bazaar.canonical.com/QBzr',
      license='GPL',
      author='QBzr Developers',
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
