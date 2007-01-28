QBzr - Qt-based front end for Bazaar
====================================

Requirements
------------

 * PyQt4 <http://www.riverbankcomputing.co.uk/pyqt/>
 * Pygments <http://pygments.pocoo.org/>, optional. Only needed for
   syntax highlighting in qannotate.

Provided Commands
-----------------

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
-------------

qlog_replace
~~~~~~~~~~~~

Multiline value containing regular expressions to replace text in commit
messages (useful to make clickable links to bug reports, ...). Can be used
for example by adding::

 qlog_replace='''#(\d+)
 <a href="https://launchpad.net/qbzr/+bug/\1">#\1</a>'''

to `project/.bzr/branch/branch.conf`.

qdiff_window_size
~~~~~~~~~~~~~~~~~

Default window size in format WIDTHxHEIGHT (e.g. 780x580)

More Info
---------

 * Homepage <http://oxygene.sk/lukas/projects/qbzr>
 * Bug Tracker <https://launchpad.net/products/qbzr>
