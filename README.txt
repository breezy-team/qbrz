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

qdiff
~~~~~

qlog
~~~~

qannotate
~~~~~~~~~

qbrowse
~~~~~~~

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
   https://launchpad.net/products/qbzr
