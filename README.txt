======================================
 QBzr - Qt-based front end for Bazaar
======================================

Requirements
============

 * Python 2.4 or 2.5

 * Bazaar VCS itself

 * PyQt 4.1 with Qt 4.2
   http://www.riverbankcomputing.co.uk/pyqt/
   http://www.trolltech.com/products/qt

 * Pygments (optional, needed for syntax highlighting in qcat)
   http://pygments.pocoo.org/

 * PyEnchant (optional, needed for spellchecking in qcommit)
   http://pyenchant.sourceforge.net/


Provided Commands
=================

* qannotate - GUI interface for file annotation
* qbrowse - Browse your branch a-la Trac Browse Source
* qcat - View the contents of a file as of a given revision
* qcommit - GUI interface to enter log message and select changes to commit
* qconfig - Bazaar configuration
* qdiff - Side-by-side and unidiff view of changes.
* qlog - Show log messages in GUI window.
* qpull - GUI interface for pull command
* qpush - GUI interface for push command


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

First at all you need to download from 
http://bazaar.launchpad.net/~qbzr-dev/qbzr/trunk/files
either `po/qbzr-XX.po` (where XX is your language and country code) 
or `po/qbzr.pot` if there is no po-file for your language yet.

Then you need to translate it either using any suitable text editor 
with UTF-8 support or with tools like Poedit (http://www.poedit.net/)  
or KBabel (http://kbabel.kde.org/).

When you're finish please file a bug report at
https://launchpad.net/qbzr/+filebug and attach the translated file.

To learn more about gettext and po-files see:
	http://www.gnu.org/software/gettext/

Language and country codes listed in gettext manual:
	http://www.gnu.org/software/gettext/manual/gettext.html#Language-Codes
        http://www.gnu.org/software/gettext/manual/gettext.html#Country-Codes


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


diff_show_intergroup_colors
~~~~~~~~~~~~~~~~~~~~~~~~~~~
Boolean value to allow painting interline changes in different colors
depend on the kind of change. Use values 'True' or '1' to enable option.


More Info
=========

 * Bug Tracker, Source Code
   https://launchpad.net/qbzr
