#!/usr/bin/env python
# -*- coding: utf-8 -*-

from distutils.core import setup

from extras.bdist_nsis import bdist_nsis
from extras.build_mo import build_mo
from extras.build_pot import build_pot


setup(name='qbzr',
      description='Qt4 frontend for Bazaar',
      keywords='plugin bzr qt qbzr',
      version='0.8.0.dev.0',
      url='http://bazaar-vcs.org/QBzr',
      license='GPL',
      author='Lukáš Lalinský',
      author_email='lalinsky@gmail.com',
      package_dir={'bzrlib.plugins.qbzr': '.'},
      package_data={'bzrlib.plugins.qbzr': ['locale/*/LC_MESSAGES/qbzr.mo']},
      packages=['bzrlib.plugins.qbzr'],
      cmdclass = {
            'bdist_nsis': bdist_nsis,
            'build_mo': build_mo,
            'build_pot': build_pot,
            },
      )
