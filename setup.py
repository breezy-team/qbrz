#!/usr/bin/env python
# -*- coding: utf-8 -*-

import os
from distutils.core import setup, Command, Extension

from extras.bdist_nsis import bdist_nsis
from extras.build_mo import build_mo
from extras.build_pot import build_pot
from extras.build_ui import build_ui

cmdclass = {
    'bdist_nsis': bdist_nsis,
    'build_mo': build_mo,
    'build_pot': build_pot,
    'build_ui': build_ui,
}

ext_modules = []

setup(name='qbzr',
      description='Qt4 frontend for Bazaar',
      keywords='plugin bzr qt qbzr',
      version='0.9.2',
      url='http://bazaar-vcs.org/QBzr',
      license='GPL',
      author='Lukáš Lalinský',
      author_email='lalinsky@gmail.com',
      package_dir={'bzrlib.plugins.qbzr': '.'},
      package_data={'bzrlib.plugins.qbzr': ['locale/*/LC_MESSAGES/qbzr.mo']},
      packages=['bzrlib.plugins.qbzr', 'bzrlib.plugins.qbzr.lib'],
      ext_modules=ext_modules,
      cmdclass=cmdclass,
)
