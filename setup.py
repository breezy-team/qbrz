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

try:
    import sipdistutils
    from PyQt4 import pyqtconfig
    have_pyqt_dev = True
except ImportError:
    have_pyqt_dev = False

if have_pyqt_dev:

    class SipExtension(Extension):

        def __init__(self, pkgname, sources, *args, **kwargs):
            self.sip_include_dirs = kwargs.pop("sip_include_dirs", [])
            self.sip_flags = kwargs.pop("sip_flags", [])
            self.moc_sources = kwargs.pop("moc_sources", [])
            Extension.__init__(self, pkgname, sources, *args, **kwargs)

    class qbzr_build_ext(sipdistutils.build_ext):

        def swig_sources(self, sources, ext=None):
            if not isinstance(ext, SipExtension):
                return sipdistutils.build_ext.swig_sources(self, sources, ext)

            self.__ext = ext

            generated_sources = []
            for source in ext.moc_sources:
                output_path = os.path.join(self.build_temp, os.path.dirname(source))
                output = os.path.join(output_path, "moc_%s.cpp" % os.path.basename(source)[:-2])
                try:
                    os.makedirs(output_path)
                except:
                    pass
                self.spawn(["moc-qt4", source, "-o", output])
                generated_sources.append(output)

            return generated_sources + sipdistutils.build_ext.swig_sources(self, sources, ext)

        def _sip_compile(self, sip_bin, source, sbf):
            args = [sip_bin, "-c", self.build_temp, "-b", sbf]
            for name in self.__ext.sip_include_dirs:
                args.extend(["-I", name])
            args.extend(self.__ext.sip_flags)
            args.append(source)
            self.spawn(args)

    cmdclass['build_ext'] = qbzr_build_ext

    pyqt_cfg = pyqtconfig.Configuration()

    ext_modules.append(
        SipExtension("bzrlib.plugins.qbzr.lib._ext",
            ["lib/_ext.sip", "lib/_ext.cpp"],
            #moc_sources=["_ext.h"],
            include_dirs=[
                pyqt_cfg.qt_inc_dir,
                os.path.join(pyqt_cfg.qt_inc_dir, "QtCore"),
                os.path.join(pyqt_cfg.qt_inc_dir, "QtGui"),
                "."],
            libraries=["QtCore", "QtGui"],
            library_dirs=[pyqt_cfg.qt_lib_dir],
            sip_include_dirs=[pyqt_cfg.pyqt_sip_dir],
            sip_flags=pyqt_cfg.pyqt_sip_flags.split()))


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
      packages=['bzrlib.plugins.qbzr'],
      ext_modules=ext_modules,
      cmdclass=cmdclass,
)
