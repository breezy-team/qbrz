all:
	@echo Targets:
	@echo   test   - run tests
	@echo   pot    - regenerate qbzr.pot translations template
	@echo   mo     - build binary translations
	@echo   clean  - remove build products
	@echo   tags   - collect tags with ctags utility
	@echo   docs   - build htmls for texts in docs/ directory
	@echo   epydoc - build API docs with epydoc
	@echo   ui     - compile UI files
	@echo
	@echo To build release run:
	@echo    make release RELEASE=X.Y.Z

.PHONY: test pot mo clean tags docs ui

# Ignore internationalization for now
check: test
	BRZ_PLUGINS_AT=qbrz@$(shell pwd) brz selftest -s bp.qbrz -x TestI18n

# Stop on first error, ignore internationalization for now
checkone: test
	BRZ_PLUGINS_AT=qbrz@$(shell pwd) brz selftest -v --one -s bp.qbrz -x TestI18n -x TestTreeFilterProxyModel

# Test specific item
checkspecific: test
	BRZ_PLUGINS_AT=qbrz@$(shell pwd) brz selftest --one --strict  -s bp.qbrz TestTreeWidget

qtest:
	# cd ~/pythonstuff/bzr_test_dir/sopsteward; BRZ_PLUGINS_AT=qbrz@/home/rjl/pythonstuff/fix-python-etc brz qdiff
	# cd ~/pythonstuff/bzr_test_dir; BRZ_PLUGINS_AT=qbrz@/home/rjl/pythonstuff/fix-python-etc brz qbranch
	# cd ~/sopsteward; BRZ_PLUGINS_AT=qbrz@/home/rjl/pythonstuff/fix-python-etc brz qpush
	BRZ_PLUGINS_AT=qbrz@$(shell pwd) brz qsubprocess qdiff
	# BRZ_PLUGINS_AT=qbrz@$(shell pwd) brz qlog
	cd ~/pythonstuff/fix-python-etc

# Fully working: (note, qchecout-ala-explorer is qgetn
# qlog
# qadd
# qannotate, qblame
# qcommit
# qbrowse
# qcat, qviewer
# qversion
# qplugins
# qinit
# qbranch
# qbind
# qunbind
# qignore
# qinfo
# qupdate
# quncommit
# qpull
# qshelve
# qunshelve
# qtag
# qgetn
# qrevert
# qpush
# qsend
# qmerge
# qconflicts
# qresolve
# qswitch
# qcmd
# qsubprocess
# qdiff



# === qconfig ===

# brz: ERROR: ImportError: cannot import name 'ensure_config_dir_exists'
# Traceback (most recent call last):
#   File "/home/rjl/pythonstuff/fix-python-etc/lib/commands.py", line 174, in run
#     ret_code = self._qbrz_run(*args, **kwargs)
#   File "/home/rjl/pythonstuff/fix-python-etc/lib/commands.py", line 515, in _qbrz_run
#     window = QBzrConfigWindow()
#   File "/usr/local/lib/python3.5/dist-packages/breezy/lazy_import.py", line 154, in __call__
#     obj = object.__getattribute__(self, '_resolve')()
#   File "/usr/local/lib/python3.5/dist-packages/breezy/lazy_import.py", line 122, in _resolve
#     obj = factory(self, scope, name)
#   File "/usr/local/lib/python3.5/dist-packages/breezy/lazy_import.py", line 241, in _import
#     module = _builtin_import(name, scope, scope, [member], level=0)
#   File "/home/rjl/pythonstuff/fix-python-etc/lib/config.py", line 23, in <module>
#     from breezy.config import (
# ImportError: cannot import name 'ensure_config_dir_exists'


# === qmain ===

# qmain fails in bzr


# === qverify-signatures ===

# qverify-signatures fails in bzr


# === qhelp ===

# qhelp doesn't work for me even in bzr


# === Items in Plug-ins ===

# NOT working
# qinit-workspace, qnew also unknown - they appear to be from the 'explorer' plugin


test:
	brz selftest -s bp.qbrz

pot:
	python3 setup.py build_pot -N -d.

mo:
	python3 setup.py build_mo -f --verbose

tarball:
	brz export --root=qbrz qbrz-$(RELEASE).tar.gz
	gpg2 -ab qbrz-$(RELEASE).tar.gz

# RJL needs to come back in
# inno: mo
# 	./iscc installer/qbrz-setup.iss
# 	gpg -ab qbrz-setup-$(RELEASE).exe

# release: tarball inno
release: tarball

clean:
	python3 setup.py clean -a

tags:
	ctags *.py lib/*.py lib/extra/*.py lib/tests/*.py

epydoc:
	epydoc.py -o api -v lib

docs:
	$(MAKE) -C docs

ui:
	python3 setup.py build_ui
