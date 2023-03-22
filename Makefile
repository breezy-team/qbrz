

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
	@echo   inno   - compile exe  - pass RELEASE=X.Y.Z
	@echo
	@echo To build release run:
	@echo    make release
	@echo the version will be picked up from version.txt
	@echo MAKE SURE YOU COMMIT FIRST - brz export USES THE COMMITTED FILES

# We'll read the RELEASE number from version.txt

.PHONY: test pot mo clean tags docs ui

# Making pot files is disabled for now - no translators!
# pot:
# 	python3 setup.py build_pot -N -d.
RELEASE:=$(shell cat version.txt)

.check-env-vars:
	$(info Building QBzr version ${RELEASE})

mo:
	python3 setup.py build_mo -f --verbose

tarball: .check-env-vars
	brz export --root=qbrz qbrz-$(RELEASE).tar.gz
	rm -f qbrz-$(RELEASE).tar.gz.asc
	# gpg2 -ab qbrz-$(RELEASE).tar.gz

# RJL needs to come back in
# inno: mo
# 	./iscc installer/qbrz-setup.iss
# 	gpg -ab qbrz-setup-$(RELEASE).exe
inno: .check-env-vars
	./iscc installer/qbrz-setup.iss /DVersion=$(RELEASE)
	rm -f qbrz-setup-$(RELEASE).exe.asc
	gpg2 -ab qbrz-setup-$(RELEASE).exe

# release: tarball inno
release: tarball inno

clean:
	python3 ./setup.py clean -a

tags:
	ctags *.py lib/*.py lib/extra/*.py lib/tests/*.py

epydoc:
	epydoc.py -o api -v lib

docs:
	$(MAKE) -C docs

ui:
	python3 setup.py build_ui


# === Tests beyond this point ===
# When you run ``brz selftest``, Breezy will scan all its plugins to see if they contain a function named test_suite().
# For each plugin that does, it calls the function and adds any resulting tests to the master test suite.
# To run just the tests for plugin xxx, the command is: ``brz selftest -s bp.xxx`` so we use bp.qbrz in our case.

check:
	BRZ_PLUGINS_AT=qbrz@$(shell pwd) brz selftest --starting-with=bp.qbrz --exclude=TestTreeFilterProxyModel --exclude=TestTreeWidget

# Stop on first error, ignore TestTreeFilterProxyModel for now

checkone:
	BRZ_PLUGINS_AT=qbrz@$(shell pwd) brz selftest -v --one --starting-with=bp.qbrz --exclude=TestTreeFilterProxyModel --exclude=TestTreeWidget

# Test specific item - e.g. for internationalisation, use:
#
#  BRZ_PLUGINS_AT=qbrz@$(shell pwd) brz selftest --one --strict -s bp.qbrz TestI18n
checkspecific:
	BRZ_PLUGINS_AT=qbrz@$(shell pwd) brz selftest -v  --one --strict --starting-with=bp.qbrz TestTreeWidget


# Rather than running the test_ suite, this lets you run the actual plugin - note
# that the tests can often pass but the code fails in actual use.
qtest:
# You can test on qbrz itself like this (qlog in the below example):
#
# BRZ_PLUGINS_AT=qbrz@$(shell pwd) brz qlog
#
# If you have a test directory you wish to use, you can pass it to the relevant command.
# In this example, we have a test dir of ``~/pythonstuff/bzr_test_dir/sopsteward`` and we
# are developing in ~/pythonstuff/qbrz - thus we call brz with qadd and the sopsteward directory
# Note we have to use ${HOME} for BZR_PLUGINS_AT...
#
	BRZ_PLUGINS_AT=qbrz@${HOME}/pythonstuff/qbrz brz qdiff 
	#BRZ_PLUGINS_AT=qbrz@${HOME}/pythonstuff/qbrz brz qplugins

test:
	brz selftest -s bp.qbrz

# Fully working: (note, qcheckout-ala-explorer is qgetn).
# qlog
# qadd <- fails to display new files
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


# === Literate documentation, etc ===

# This uses pycco to generate the literal documentation.
# To rebuild all of it, with an index.html file, use:
#
#  make literate_index
#
# To just update (although new files won't be added to index.html), use:
#
#  make literate_docs
#
# otherwise, you can just make the base, lib, or whatever using (for example):
#
#  make widget_docs
#
# Output goes into docs/literate/... mirroring the source-code locations (e.g.
# lib/widgets/... go into docs/literate/lib/widgets
#
# pycco isn't brilliant, but it tries its best

# We build or rebuild the documentation with pycco - shorthand for the command here in PYCCO_ALL variable
# This one builds the index.html file
PYCCO_ALL := pycco --generate_index --paths -s --directory

# This one does NOT build the index file - otherwise, if you pass a single file
# it will be the ONLY one in the index. Do'h!
PYCCO_ONE := pycco --paths -s --directory

# We want to look at all the .py files in the Code directory (where we start)
# in case any have changed. The makefile is in /Code so we just use './'
# the shell for 'this directory that we are in' - so the following means
# 'all the files ending in "py" in this directory'
PYMAINSOURCES=$(wildcard ./*.py)
# The lib sources
PYLIBSOURCES=$(wildcard ./lib/*.py)
# extras and tests
PYEXTRASOURCES=$(wildcard ./lib/extra/*.py)
PYEXTRASSOURCES=$(wildcard ./extras/*.py)
PYTESTSSOURCES=$(wildcard ./lib/tests/*.py)
PYWIDGETSOURCES=$(wildcard ./lib/widgets/*.py)

# So now add them all together
PYSOURCES=$(PYMAINSOURCES) $(PYLIBSOURCES) $(PYEXTRASOURCES) $(PYEXTRASSOURCES) $(PYTESTSSOURCES) $(PYWIDGETSOURCES)

# This is how we extract an html file-name for each changed python file-name
# It basically reads: for each .py file in the source directory (PYSOURCES),
# there should be a matching .html file in Code_Documentation.
# The % means the stem, for example world.py has a stem of 'world' so we
# make world.html from world.py
DOCUMENTS_NEEDED_BASE=$(PYSOURCES:%.py=docs/literate/%.html)

# For subdirectories, we'll get the subdirectory as a prefix
# for example, svrsub/svrconfig
DOCUMENTS_NEEDED_LIB=$(PYLIBSOURCES:%.py=docs/literate/%.html)
DOCUMENTS_NEEDED_EXTRA=$(PYEXTRASOURCES:%.py=docs/literate/%.html)
DOCUMENTS_NEEDED_EXTRAS=$(PYEXTRASSOURCES:%.py=docs/literate/%.html)
DOCUMENTS_NEEDED_TEST=$(PYTESTSSOURCES:%.py=docs/literate/%.html)
DOCUMENTS_NEEDED_WIDGETS=$(PYWIDGETSOURCES:%.py=docs/literate/%.html)

.PHONY: literate_docs
# No such file as all so mark it as a phony
.PHONY: base_docs
.PHONY: lib_docs
.PHONY: extra_docs
.PHONY: extras_docs
.PHONY: test_docs
.PHONY: widget_docs

base_docs: $(DOCUMENTS_NEEDED_BASE)
lib_docs: $(DOCUMENTS_NEEDED_LIB)
extra_docs: $(DOCUMENTS_NEEDED_EXTRA)
extras_docs: $(DOCUMENTS_NEEDED_EXTRAS)
test_docs: $(DOCUMENTS_NEEDED_TEST)
widget_docs: $(DOCUMENTS_NEEDED_WIDGETS)

literate_docs: base_docs lib_docs extra_docs extras_docs test_docs widget_docs

# The html file in docs/literate (and its cousins) depends upon the py file of the same name
# If the html file is missing or older than the python one, run the pycco command
# for the file (in $<)



docs/literate/%.html: %.py
	$(PYCCO_ONE) ./docs/literate $<


docs/literate/extras/%.html: %.py
	$(PYCCO_ONE) ./docs/literate $<

docs/literate/lib/%.html: %.py
	$(PYCCO_ONE) ./docs/literate $<


docs/literate/lib/data/%.html: %.py
	$(PYCCO_ONE) ./docs/literate $<

docs/literate/lib/extra/%.html: %.py
	$(PYCCO_ONE) ./docs/literate $<

docs/literate/lib/test/%.html: %.py
	$(PYCCO_ONE) ./docs/literate $<

docs/literate/lib/widgets/%.html: %.py
	$(PYCCO_ONE) ./docs/literate $<

# Call 'make index' to make the full documentation
.PHONY: literate_index
literate_index:
	make literate_clean
	$(PYCCO_ALL) ./docs/literate $(PYSOURCES)

.PHONY: literate_clean
literate_clean:
	rm -rf docs/literate/
