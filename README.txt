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

qlog_replace
~~~~~~~~~~~~

Multiline value containing regular expressions to replace text in commit
messages (useful to make clickable links to bug reports, ...). Can be used
for example by adding:

qlog_replace='''#(\d+)
<a href="https://launchpad.net/qbzr/+bug/\1">#\1</a>'''

to project/.bzr/branch/branch.conf.

qdiff_window_size
~~~~~~~~~~~~~~~~~

Default window size in format WIDTHxHEIGHT (e.g. 780x580)

More Info
=========

 * Homepage
   http://oxygene.sk/lukas/projects/qbzr

 * Bug Tracker
   https://launchpad.net/products/qbzr
