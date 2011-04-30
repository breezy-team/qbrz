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

test:
	bzr selftest -s bp.qbzr

pot:
	python setup.py build_pot -N -d.

mo:
	python setup.py build_mo -f

tarball:
	bzr export --root=qbzr qbzr-$(RELEASE).tar.gz
	gpg -ab qbzr-$(RELEASE).tar.gz

inno: mo
	iscc installer/qbzr-setup.iss
	gpg -ab qbzr-setup-$(RELEASE).exe

release: tarball inno

clean:
	python setup.py clean -a

tags:
	ctags *.py lib/*.py lib/extra/*.py lib/tests/*.py

epydoc:
	epydoc.py -o api -v lib

docs:
	$(MAKE) -C docs

ui:
	python setup.py build_ui
