======================================
 QBzr - Qt-based front end for Bazaar
======================================

QBzr is a cross platform, Qt-based front-end for Bazaar, providing GUI
applications for many core bzr commands. In addition, it provides several
special dialogs and helper commands. Equivalents for core bzr commands have
the same names as CLI commands but with a prefix of "q".

Requirements
============

 * Python 2.4-2.7
              
 * Bazaar VCS itself (see below version compatibility information)

 * PyQt 4.4 with Qt 4.4 or later
   http://www.riverbankcomputing.co.uk/pyqt/
   http://www.trolltech.com/products/qt

 * Pygments v.1.0 or higher (optional, needed for syntax highlighting)
   http://pygments.pocoo.org/

 * PyEnchant (optional, needed for spellchecking in qcommit)
   http://pyenchant.sourceforge.net/


Compatibility between qbzr and bzr versions
===========================================

 * QBzr 0.23 is targeted to bzr 2.6 and compatible with bzr 2.5.
   It may not work with older versions of bzr.

 * QBzr 0.22 is targeted to bzr 2.5 and compatible with bzr 2.4
   It may not work with older versions of bzr.

 * QBzr 0.21 is targeted to bzr 2.4 and compatible with bzr 2.3.
   It may not work with older versions of bzr.

 * QBzr 0.20 is targeted to bzr 2.3 and compatible with bzr 2.2.
   It may not work with older versions of bzr.

 * QBzr 0.19 required bzr 2.2 and compatible with bzr 2.1.
   It may not work with older versions of bzr.

 * QBzr 0.18.x required bzr 2.1.x.
   Some commands/dialogs are working with bzr 1.17, 1.18.x, 2.0.x.
   It may work with bzr 2.2 or later, but this is not guaranteed.

 * QBzr 0.14.x compatible with bzr 1.17, 1.18.x, 2.0.x. 


Other bzr plugins that improve QBzr
===================================

 * bzr-search (Makes searching in log faster)
   https://launchpad.net/bzr-search

 * bzr-difftools (Improves the usability of launching external diffs)
   https://launchpad.net/bzr-difftools

 * bzr-extmerge (Required to lauch external merge applications to resolve
   conficts.)
   https://launchpad.net/bzr-extmerge


Provided Commands
=================

Basic q-commands:

 * qadd - GUI for adding files or directories.
 * qannotate - Show the origin of each line in a file.
 * qbind - Convert the current branch into a checkout of the supplied branch.
 * qbranch - Create a new copy of a branch.
 * qcat - View the contents of a file as of a given revision.
 * qcommit - GUI for committing revisions.
 * qconflicts - Show conflicts.
 * qdiff - Show differences in working tree in a GUI window.
 * qexport - Export current or past revision to a destination directory or archive.
 * qignore - Ignore files or patterns.
 * qinfo - Shows information about the current location.
 * qinit - Initializes a new branch or shared repository.
 * qlog - Show log of a repository, branch, file, or directory in a Qt window.
 * qmerge - Perform a three-way merge.
 * qplugins - Display information about installed plugins.
 * qpull - Turn this branch into a mirror of another branch.
 * qpush - Update a mirror of this branch.
 * qrevert - Revert changes files.
 * qsend - Mail or create a merge-directive for submitting changes.
 * qswitch - Set the branch of a checkout and update.
 * qtag - Edit tags.
 * qunbind - Convert the current checkout into a regular branch.
 * quncommit - Move the tip of a branch to an earlier revision.
 * qupdate - Update working tree with latest changes in the branch.
 * qverify-signatures - Show digital signatures information
 * qversion - Show version/system information.

Hybrid dialogs:

 * qgetnew - Creates a new working tree (either a checkout or full branch).
 * qgetupdates - Fetches external changes into the working tree.

Additional commands:

 * qbrowse - Show inventory or working tree.
 * qconfig - Configure Bazaar and QBzr.
 * qrun - Run arbitrary bzr command.
 * qviewer - Simple file viewer.

Miscellaneous:

 * bug-url - print full URL to a specific bug, or open it in your browser.


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

You can use either Launchpad trnaslations interface (it's preferable way) 
see https://translations.launchpad.net/qbzr,
or you can translate it offline, see instructions below.

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

 * Mailing list/Discussion forum:
   http://groups.google.com/group/qbzr

 * Bug Tracker, Source Code, Translations, Questions:
   https://launchpad.net/qbzr
