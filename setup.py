#!/usr/bin/env python
# -*- coding: utf-8 -*-

from distutils.core import setup

setup(name='qbzr',
      description='Qt4 frontend for Bazaar',
      keywords='plugin bzr qt qbzr',
      version='0.5.0',
      url='http://lukas.oxygene.sk/wiki/QBzr',
      license='GPL',
      author='Lukáš Lalinský',
      author_email='lalinsky@gmail.com',
      package_dir={'bzrlib.plugins.qbzr':'.'},
      packages=['bzrlib.plugins.qbzr']
      )
