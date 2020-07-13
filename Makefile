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
	# cd ~/pythonstuff/bzr_test_dir/sopsteward; BRZ_PLUGINS_AT=qbrz@/home/rjl/pythonstuff/fix-python-etc brz qswitch
	# cd ~/pythonstuff/bzr_test_dir BRZ_PLUGINS_AT=qbrz@/home/rjl/pythonstuff/fix-python-etc brz qmain
	# cd ~/sopsteward; BRZ_PLUGINS_AT=qbrz@/home/rjl/pythonstuff/fix-python-etc brz qpush
	BRZ_PLUGINS_AT=qbrz@$(shell pwd) brz qcmd
	# BRZ_PLUGINS_AT=qbrz@$(shell pwd) brz qsend
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


# === qcmd ===

# brz: ERROR: TypeError: unorderable types: NoneType() < str()
# Traceback (most recent call last):
#   File "/home/rjl/pythonstuff/fix-python-etc/lib/commands.py", line 174, in run
#     ret_code = self._qbrz_run(*args, **kwargs)
#   File "/home/rjl/pythonstuff/fix-python-etc/lib/commands.py", line 1080, in _qbrz_run
#     execute=execute)
#   File "/home/rjl/pythonstuff/fix-python-etc/lib/run.py", line 67, in __init__
#     categories = sorted(self.all_cmds.keys())
# TypeError: unorderable types: NoneType() < str()


# === qdiff ===

# This *does* work when embedded in other windows
#
# brz: ERROR: AttributeError: 'function' object has no attribute 'enter_context'
# Traceback (most recent call last):
#   File "/home/rjl/pythonstuff/fix-python-etc/lib/trace.py", line 378, in reports_exception_decorate
#     return f(*args, **kargs)
#   File "/home/rjl/pythonstuff/fix-python-etc/lib/diffwindow.py", line 369, in initial_load
#     op.run()
#   File "/home/rjl/pythonstuff/fix-python-etc/lib/cleanup.py", line 138, in run
#     self.cleanups, self.func, self, *args, **kwargs)
#   File "/home/rjl/pythonstuff/fix-python-etc/lib/cleanup.py", line 171, in _do_with_cleanups
#     result = func(*args, **kwargs)
#   File "/home/rjl/pythonstuff/fix-python-etc/lib/diffwindow.py", line 373, in _initial_load
#     args = self.arg_provider.get_diff_window_args(self.processEvents, op.add_cleanup)
#   File "/home/rjl/pythonstuff/fix-python-etc/lib/commands.py", line 422, in get_diff_window_args
#     get_trees_and_branches_to_diff_locked(self.file_list, self.revision, self.old, self.new, add_cleanup)
#   File "/usr/local/lib/python3.5/dist-packages/breezy/diff.py", line 437, in get_trees_and_branches_to_diff_locked
#     lock_tree_or_branch(working_tree, branch)
#   File "/usr/local/lib/python3.5/dist-packages/breezy/diff.py", line 427, in lock_tree_or_branch
#     exit_stack.enter_context(wt.lock_read())
# AttributeError: 'function' object has no attribute 'enter_context'


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


# === qsubprocess ===

# brz: ERROR: AttributeError: 'bytes' object has no attribute 'read'
# Traceback (most recent call last):
#   File "/usr/local/lib/python3.5/dist-packages/breezy/commands.py", line 1022, in exception_to_return_code
#     return the_callable(*args, **kwargs)
#   File "/usr/local/lib/python3.5/dist-packages/breezy/commands.py", line 1208, in run_bzr
#     ret = run(*run_argv)
#   File "/usr/local/lib/python3.5/dist-packages/breezy/commands.py", line 762, in run_argv_aliases
#     return self.run(**all_cmd_args)
#   File "/usr/local/lib/python3.5/dist-packages/breezy/commands.py", line 787, in run
#     return class_run(*args, **kwargs)
#   File "/home/rjl/pythonstuff/fix-python-etc/lib/commands.py", line 803, in run
#     return run_subprocess_command(cmd, bencoded)
#   File "/home/rjl/pythonstuff/fix-python-etc/lib/subprocess.py", line 983, in run_subprocess_command
#     argv = [str(p, 'utf-8') for p in shlex.split(cmd_utf8)]
#   File "/usr/lib/python3.5/shlex.py", line 273, in split
#     return list(lex)
#   File "/usr/lib/python3.5/shlex.py", line 263, in __next__
#     token = self.get_token()
#   File "/usr/lib/python3.5/shlex.py", line 90, in get_token
#     raw = self.read_token()
#   File "/usr/lib/python3.5/shlex.py", line 118, in read_token
#     nextchar = self.instream.read(1)


# === qmain ===

# brz: ERROR: TypeError: 'TreeChange' object does not support indexing
# Traceback (most recent call last):
#   File "/home/rjl/pythonstuff/fix-python-etc/lib/statuscache.py", line 132, in getDirectoryStatus
#     entry = self._getCacheEntry(path)
#   File "/home/rjl/pythonstuff/fix-python-etc/lib/statuscache.py", line 73, in _getCacheEntry
#     entry = entry.children[part]
# KeyError: 'home'
# During handling of the above exception, another exception occurred:
# Traceback (most recent call last):
#   File "/home/rjl/pythonstuff/fix-python-etc/lib/commands.py", line 174, in run
#     ret_code = self._qbrz_run(*args, **kwargs)
#   File "/home/rjl/pythonstuff/fix-python-etc/lib/commands.py", line 778, in _qbrz_run
#     window.setDirectory(osutils.realpath(CUR_DIR))
#   File "/home/rjl/pythonstuff/fix-python-etc/lib/main.py", line 554, in setDirectory
#     status = self.cache.getDirectoryStatus(pathParts, str(fileInfo.fileName()))
#   File "/home/rjl/pythonstuff/fix-python-etc/lib/statuscache.py", line 134, in getDirectoryStatus
#     entry = self._cacheDirectoryStatus(path)
#   File "/home/rjl/pythonstuff/fix-python-etc/lib/statuscache.py", line 102, in _cacheDirectoryStatus
#     self._cacheStatus(osutils.splitpath(entry[0]), 'unchanged', root=root)
# TypeError: 'TreeChange' object does not support indexing

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
