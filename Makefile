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
	@echo   inno   - compile exe (pass RELEASE=X.Y.Z)
	@echo
	@echo To build release run:
	@echo    make release RELEASE=X.Y.Z

.PHONY: test pot mo clean tags docs ui

# Making pot files is disabled for now - no translators!
# pot:
# 	python3 setup.py build_pot -N -d.

mo:
	python3 setup.py build_mo -f --verbose

tarball:
	brz export --root=qbrz qbrz-$(RELEASE).tar.gz
	gpg2 -ab qbrz-$(RELEASE).tar.gz

# RJL needs to come back in
# inno: mo
# 	./iscc installer/qbrz-setup.iss
# 	gpg -ab qbrz-setup-$(RELEASE).exe
inno:
	./iscc installer/qbrz-setup.iss
	gpg2 -ab qbrz-setup-$(RELEASE).exe

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


# === Tests beyond this point ===

check: test
	BRZ_PLUGINS_AT=qbrz@$(shell pwd) brz selftest -s bp.qbrz -x TestTreeFilterProxyModel

# Stop on first error, ignore TestTreeFilterProxyModel for now

checkone: test
	BRZ_PLUGINS_AT=qbrz@$(shell pwd) brz selftest -v --one -s bp.qbrz -x  TestTreeFilterProxyModel

# Test specific item - e.g. for internationalisation, use:
#
#  BRZ_PLUGINS_AT=qbrz@$(shell pwd) brz selftest --one --strict -s bp.qbrz TestI18n
checkspecific: test
	BRZ_PLUGINS_AT=qbrz@$(shell pwd) brz selftest --one --strict -s bp.qbrz TestBencode

# Rather than running the test_ suite, this lets you run the actual plugin - note
# that the tests can often pass but the code fails in actual use.
qtest:
# You can test on qbrz itself like this (qlog in this example):
#
	 BRZ_PLUGINS_AT=qbrz@$(shell pwd) brz qignore
#
# If you have a test directory you wish to use, you can cd to it, run the code, cd back from it.
# In this example, we have a test dir of ``~/pythonstuff/bzr_test_dir/sopsteward`` - we have
# to ``cd`` to it (note the semi-colon) THEN execute the plugin code we want:
#
#  cd ~/pythonstuff/bzr_test_dir/sopsteward; BRZ_PLUGINS_AT=qbrz@/home/rjl/pythonstuff/fix-python-etc brz qdiff

test:
	brz selftest -s bp.qbrz


# Fully working: (note, qcheckout-ala-explorer is qgetn).
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
# qconfig


# === qmain ===

# qmain fails in bzr


# === qverify-signatures ===

# qverify-signatures fails in bzr


# === qhelp ===

# qhelp doesn't work for me even in bzr


# === Items in Plug-ins ===

# NOT working
# qinit-workspace, qnew also unknown - they appear to be from the 'explorer' plugin


