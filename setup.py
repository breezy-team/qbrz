#!/usr/bin/env python
# -*- coding: utf-8 -*-

from distutils.core import setup

from extras.bdist_nsis import bdist_nsis
from extras.build_mo import build_mo
from extras.build_pot import build_pot
from extras.build_ui import build_ui
from extras.check_py24 import check_py24

cmdclass = {
    'bdist_nsis': bdist_nsis,
    'build_mo': build_mo,
    'build_pot': build_pot,
    'build_ui': build_ui,
    'check_py24': check_py24,
}

ext_modules = []

setup(name='qbzr',
      description='Qt4 frontend for Bazaar',
      keywords='plugin bzr qt qbzr',
      version='0.9.5',
      url='http://bazaar-vcs.org/QBzr',
      license='GPL',
      author='QBzr Developers',
      author_email='qbzr@googlegroups.com',
      package_dir={'bzrlib.plugins.qbzr': '.'},
      package_data={'bzrlib.plugins.qbzr': ['locale/*/LC_MESSAGES/qbzr.mo']},
      packages=['bzrlib.plugins.qbzr',
                'bzrlib.plugins.qbzr.lib',
                'bzrlib.plugins.qbzr.lib.extra',
                'bzrlib.plugins.qbzr.lib.tests',
                ],
      ext_modules=ext_modules,
      cmdclass=cmdclass,
)
