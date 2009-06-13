all:
	@echo Targets:
	@echo   test - run tests
	@echo   pot  - regenerate qbzr.pot translations template
	@echo   mo   - build binary translations

test:
	bzr selftest -s bp.qbzr

pot:
	python setup.py build_pot -N

mo:
	python setup.py build_mo -f

copy-libs:
	python setup.py bdist_nsis --copy-all --dry-run

tarball:
	bzr export --root=qbzr qbzr-$(RELEASE).tar.gz
	gpg -ab qbzr-$(RELEASE).tar.gz

py-inst: mo
	python setup.py bdist_wininst -d.
	gpg -ab qbzr-$(RELEASE).win32.exe

inno: mo copy-libs
	iscc installer/qbzr-setup.iss
	gpg -ab qbzr-setup-$(RELEASE).exe

release: tarball py-inst inno

clean:
	python setup.py clean -a
