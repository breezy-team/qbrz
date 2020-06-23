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
	BRZ_PLUGINS_AT=qbrz@$(shell pwd) brz selftest --one --strict  -s bp.qbrz test_guidebar

qlogtest:
	BRZ_PLUGINS_AT=qbrz@$(shell pwd) brz qlog

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
