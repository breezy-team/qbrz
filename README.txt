======================================
 QBzr - Qt-based front end for Bazaar
======================================

Requirements
============

 * PyQt 4.1 with Qt 4.2
   http://www.riverbankcomputing.co.uk/pyqt/
   http://www.trolltech.com/products/qt

 * Pygments (optional, only needed for syntax highlighting in qannotate)
   http://pygments.pocoo.org/


Provided Commands
=================

qcommit
~~~~~~~
GUI interface to enter log message and select changes to commit.

qdiff
~~~~~
Side-by-side and unidiff view of changes.

qlog
~~~~
Show log messages in GUI window.

qannotate
~~~~~~~~~
GUI interface for file annotation.

qbrowse
~~~~~~~
Browse your branch a-la Trac Browse Source.


Interface localization
======================

QBzr uses gettext library for i18n support. 
Available translations resides in po/ subdirectory of the tree.
QBzr expects to load binary mo-files from locale/ subdirectory
of the tree.

To generate translation POT-template file you need to run command:
	python setup.py build_pot

All existing PO-files will be updated as well.

To compile translations to binary mo-files you need to run command:
	python setup.py build_mo

NOTE: windows installer ships with latest compiled translation inside.

Help translate
~~~~~~~~~~~~~~

You can help to translate QBzr interface to other languages.
You can use any suitable editor with UTF-8 support and edit
corresponding po-file. Or you can use web-interface at Launchpad:
	https://translations.launchpad.net/qbzr/


Configuration
=============

The configuration is in .bazaar/qbzr.conf.

qlog_replace
~~~~~~~~~~~~

Multiline value containing regular expressions to replace text in commit
messages (useful to make clickable links to bug reports, ...). Can be used
for example by adding:

qlog_replace='''#(\d+)
<a href="https://launchpad.net/qbzr/+bug/\1">#\1</a>'''

to project/.bzr/branch/branch.conf.


More Info
=========

 * Bug Tracker, Source Code
   https://launchpad.net/qbzr
