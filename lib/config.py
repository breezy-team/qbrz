# -*- coding: utf-8 -*-
#
# QBzr - Qt frontend to Bazaar commands
# Copyright (C) 2007 Lukáš Lalinský <lalinsky@gmail.com>
#
# This program is free software; you can redistribute it and/or
# modify it under the terms of the GNU General Public License
# as published by the Free Software Foundation; either version 2
# of the License, or (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program; if not, write to the Free Software
# Foundation, Inc., 51 Franklin Street, Fifth Floor, Boston, MA 02110-1301, USA.

import re
import os.path
from PyQt4 import QtCore, QtGui
from bzrlib.config import (
    ensure_config_dir_exists,
    extract_email_address,
    )
from bzrlib import cmdline, errors, trace

from bzrlib.plugins.qbzr.lib import ui_merge_config
from bzrlib.plugins.qbzr.lib.i18n import gettext, N_
from bzrlib.plugins.qbzr.lib.spellcheck import SpellChecker
from bzrlib.plugins.qbzr.lib.util import (
    BTN_OK,
    BTN_CANCEL,
    QBzrDialog,
    extract_name,
    get_qbzr_config,
    get_global_config,
    get_set_tab_width_chars,
    )

try:
    from bzrlib import mergetools
except ImportError:
    mergetools = None


_mail_clients = [
    ('default', N_('Default')),
    ('thunderbird', N_('Thunderbird')),
    ('evolution', N_('Evolution')),
    ('kmail', N_('KMail')),
    ('mutt', N_('Mutt')),
    ('xdg-email', N_('XDG e-mail client')),
    ('mapi', N_('MAPI e-mail client')),
    ('editor', N_('Editor')),
]

# XXX use special function from bugs.py instead
_bug_tracker_re = re.compile('bugtracker_(.+?)_url')

class QRadioCheckItemDelegate(QtGui.QItemDelegate):
    
    def drawCheck (self, painter, option, rect, state):
        style = self.parent().style()
        radioOption = QtGui.QStyleOptionButton()
        radioOption.rect = option.rect
        radioOption.state = option.state
        if state:
            radioOption.state = radioOption.state | QtGui.QStyle.State_On
        style.drawControl(QtGui.QStyle.CE_RadioButton,
                          radioOption,
                          painter)


class QBzrConfigWindow(QBzrDialog):

    def __init__(self, parent=None):
        QBzrDialog.__init__(self, [gettext("Configuration")], parent)
        self.restoreSize("config", (400, 300))

        self.tabwidget = QtGui.QTabWidget()

        generalWidget = QtGui.QWidget()
        generalVBox = QtGui.QVBoxLayout(generalWidget)
        generalGrid = QtGui.QGridLayout()

        self.nameEdit = QtGui.QLineEdit()
        label = QtGui.QLabel(gettext("&Name:"))
        label.setBuddy(self.nameEdit)
        generalGrid.addWidget(label, 0, 0)
        generalGrid.addWidget(self.nameEdit, 0, 1)

        self.emailEdit = QtGui.QLineEdit()
        label = QtGui.QLabel(gettext("E-&mail:"))
        label.setBuddy(self.emailEdit)
        generalGrid.addWidget(label, 1, 0)
        generalGrid.addWidget(self.emailEdit, 1, 1)

        self.editorEdit = QtGui.QLineEdit()
        btnEditorBrowse = QtGui.QPushButton(gettext('&Browse...'))
        self.connect(btnEditorBrowse,
            QtCore.SIGNAL("clicked()"),
            self.browseEditor)
        editorHBox = QtGui.QHBoxLayout()
        editorHBox.addWidget(self.editorEdit)
        editorHBox.addWidget(btnEditorBrowse)
        label = QtGui.QLabel(gettext("&Editor:"))
        label.setBuddy(self.editorEdit)
        generalGrid.addWidget(label, 2, 0)
        generalGrid.addLayout(editorHBox, 2, 1)

        self.emailClientCombo = QtGui.QComboBox()
        for name, label in _mail_clients:
            self.emailClientCombo.addItem(gettext(label), QtCore.QVariant(name))
        label = QtGui.QLabel(gettext("E-mail &client:"))
        label.setBuddy(self.emailClientCombo)
        generalGrid.addWidget(label, 3, 0)
        generalGrid.addWidget(self.emailClientCombo, 3, 1)

        self.tabWidthSpinner = QtGui.QSpinBox()
        self.tabWidthSpinner.setRange(1, 20)
        self.tabWidthSpinner.setToolTip(gettext("Tab width in characters\n"
            "option is used in qdiff, qannotate and qcat windows"))
        label = QtGui.QLabel(gettext("Tab &Width:"))
        label.setBuddy(self.tabWidthSpinner)
        generalGrid.addWidget(label, 4, 0)
        _hb = QtGui.QHBoxLayout()
        _hb.addWidget(self.tabWidthSpinner)
        _hb.addStretch(10)
        generalGrid.addLayout(_hb, 4, 1)
        generalVBox.addLayout(generalGrid)
        generalVBox.addStretch()

        self.aliasesList = QtGui.QTreeWidget()
        self.aliasesList.setRootIsDecorated(False)
        self.aliasesList.setHeaderLabels([gettext("Alias"), gettext("Command")])

        addAliasButton = QtGui.QPushButton(gettext("Add"))
        self.connect(addAliasButton, QtCore.SIGNAL("clicked()"),
                     self.addAlias)
        removeAliasButton = QtGui.QPushButton(gettext("Remove"))
        self.connect(removeAliasButton, QtCore.SIGNAL("clicked()"),
                     self.removeAlias)

        aliasesHBox = QtGui.QHBoxLayout()
        aliasesHBox.addWidget(addAliasButton)
        aliasesHBox.addWidget(removeAliasButton)
        aliasesHBox.addStretch()

        aliasesWidget = QtGui.QWidget()
        aliasesVBox = QtGui.QVBoxLayout(aliasesWidget)
        aliasesVBox.addWidget(self.aliasesList)
        aliasesVBox.addLayout(aliasesHBox)

        self.bugTrackersList = QtGui.QTreeWidget()
        self.bugTrackersList.setRootIsDecorated(False)
        self.bugTrackersList.setHeaderLabels([gettext("Abbreviation"), gettext("URL")])

        addBugTrackerButton = QtGui.QPushButton(gettext("Add"))
        self.connect(addBugTrackerButton, QtCore.SIGNAL("clicked()"),
                     self.addBugTracker)
        removeBugTrackerButton = QtGui.QPushButton(gettext("Remove"))
        self.connect(removeBugTrackerButton, QtCore.SIGNAL("clicked()"),
                     self.removeBugTracker)

        bugTrackersHBox = QtGui.QHBoxLayout()
        bugTrackersHBox.addWidget(addBugTrackerButton)
        bugTrackersHBox.addWidget(removeBugTrackerButton)
        bugTrackersHBox.addStretch()

        bugTrackersWidget = QtGui.QWidget()
        bugTrackersVBox = QtGui.QVBoxLayout(bugTrackersWidget)
        bugTrackersVBox.addWidget(self.bugTrackersList)
        bugTrackersVBox.addLayout(bugTrackersHBox)
        
        diffWidget = QtGui.QWidget()

        self.diffShowIntergroupColors = QtGui.QCheckBox(gettext("Show inter-group inserts and deletes in green and red"), diffWidget)
        
        label = QtGui.QLabel(gettext("External Diff Apps:"))
        self.extDiffList = QtGui.QTreeWidget(diffWidget)
        self.extDiffList.setRootIsDecorated(False)
        self.extDiffList.setHeaderLabels([gettext("Name"),
                                          gettext("Command")])
        self.extDiffList.setItemDelegateForColumn(0,
            QRadioCheckItemDelegate(self.extDiffList))
        self.connect(self.extDiffList, QtCore.SIGNAL("itemChanged (QTreeWidgetItem *,int)"),
                     self.extDiffListItemChanged)        

        addExtDiffButton = QtGui.QPushButton(gettext("Add"), diffWidget)
        self.connect(addExtDiffButton, QtCore.SIGNAL("clicked()"),
                     self.addExtDiff)
        removeExtDiffButton = QtGui.QPushButton(gettext("Remove"), diffWidget)
        self.connect(removeExtDiffButton, QtCore.SIGNAL("clicked()"),
                     self.removeExtDiff)

        extDiffButtonsLayout = QtGui.QHBoxLayout()
        extDiffButtonsLayout.addWidget(addExtDiffButton)
        extDiffButtonsLayout.addWidget(removeExtDiffButton)
        extDiffButtonsLayout.addStretch()

        diffLayout = QtGui.QVBoxLayout(diffWidget)
        diffLayout.addWidget(self.diffShowIntergroupColors)
        diffLayout.addWidget(label)
        diffLayout.addWidget(self.extDiffList)
        diffLayout.addLayout(extDiffButtonsLayout)
        
        if mergetools is not None:
            mergeWidget = QtGui.QWidget()
            self.merge_ui = ui_merge_config.Ui_MergeConfig()
            self.merge_ui.setupUi(mergeWidget)
            self.merge_ui.tools.sortByColumn(0, QtCore.Qt.AscendingOrder)
            self.merge_ui.remove.setEnabled(False)
            self.merge_ui.set_default.setEnabled(False)
            
            self.merge_tools_model = MergeToolsTableModel()
            self.merge_ui.tools.setModel(self.merge_tools_model)
            
            self.connect(self.merge_tools_model,
                         QtCore.SIGNAL("dataChanged(QModelIndex,QModelIndex)"),
                         self.merge_tools_data_changed)
    
            self.connect(self.merge_ui.tools.selectionModel(),
                         QtCore.SIGNAL("selectionChanged(QItemSelection,QItemSelection)"),
                         self.merge_tools_selectionChanged)
            
            self.connect(self.merge_ui.add,
                         QtCore.SIGNAL("clicked()"),
                         self.merge_tools_add_clicked)
            self.connect(self.merge_ui.remove,
                         QtCore.SIGNAL("clicked()"),
                         self.merge_tools_remove_clicked)
            self.connect(self.merge_ui.set_default,
                         QtCore.SIGNAL("clicked()"),
                         self.merge_tools_set_default_clicked)
        else:
            mergeWidget = QtGui.QLabel(gettext("Bazaar 2.4 or newer is required to configure mergetools."))
            mergeWidget.setAlignment(QtCore.Qt.AlignHCenter | QtCore.Qt.AlignVCenter)
        
        self.tabwidget.addTab(generalWidget, gettext("General"))
        self.tabwidget.addTab(aliasesWidget, gettext("Aliases"))
        self.tabwidget.addTab(bugTrackersWidget, gettext("Bug Trackers"))
        self.tabwidget.addTab(self.getGuiTabWidget(), gettext("&User Interface"))
        self.tabwidget.addTab(diffWidget, gettext("&Diff"))
        self.tabwidget.addTab(mergeWidget, gettext("&Merge"))

        buttonbox = self.create_button_box(BTN_OK, BTN_CANCEL)

        vbox = QtGui.QVBoxLayout(self)
        vbox.addWidget(self.tabwidget)
        vbox.addWidget(buttonbox)
        self.load()

    def getGuiTabWidget(self):
        """
        Returns the widget for the GUI tab.
        """
        tabwidget = QtGui.QWidget()
        grid = QtGui.QGridLayout()
        vbox = QtGui.QVBoxLayout(tabwidget)
        vbox.addLayout(grid)
        vbox.addStretch()

        self.spellcheck_language_combo = QtGui.QComboBox()
        languages = sorted(SpellChecker.list_languages())
        for name in languages:
            self.spellcheck_language_combo.addItem(gettext(name), QtCore.QVariant(name))
        if not languages:
            self.spellcheck_language_combo.setEnabled(False)
        label = QtGui.QLabel(gettext("Spell check &language:"))
        label.setBuddy(self.spellcheck_language_combo)
        label.setSizePolicy(QtGui.QSizePolicy.Maximum, QtGui.QSizePolicy.Minimum)
        grid.addWidget(label, 0, 0)
        grid.addWidget(self.spellcheck_language_combo, 0, 1)

        self.branchsourceBasedirEdit = QtGui.QLineEdit()
        self.branchsourceBasedirEdit.setToolTip(gettext("This directory will be automatically filled in your branch source input field"))
        btnBranchsourceBasedirBrowse = QtGui.QPushButton(gettext('Browse...'))
        self.connect(btnBranchsourceBasedirBrowse,
            QtCore.SIGNAL("clicked()"),
            self.browseBranchsourceBasedir)
        branchsourceBasedirHBox = QtGui.QHBoxLayout()
        branchsourceBasedirHBox.addWidget(self.branchsourceBasedirEdit)
        branchsourceBasedirHBox.addWidget(btnBranchsourceBasedirBrowse)
        label = QtGui.QLabel(gettext("Base directory\nfor &branch sources:"))
        label.setBuddy(self.branchsourceBasedirEdit)
        grid.addWidget(label, 1, 0)
        grid.addLayout(branchsourceBasedirHBox, 1, 1)
        
        self.checkoutBasedirEdit = QtGui.QLineEdit()
        self.checkoutBasedirEdit.setToolTip(gettext("This directory will be automatically filled in your checkout destination input field"))
        btnCheckoutBasedirBrowse = QtGui.QPushButton(gettext('Browse...'))
        self.connect(btnCheckoutBasedirBrowse,
            QtCore.SIGNAL("clicked()"),
            self.browseCheckoutBasedir)
        checkoutBasedirHBox = QtGui.QHBoxLayout()
        checkoutBasedirHBox.addWidget(self.checkoutBasedirEdit)
        checkoutBasedirHBox.addWidget(btnCheckoutBasedirBrowse)
        label = QtGui.QLabel(gettext("Base directory\nfor &checkouts:"))
        label.setBuddy(self.checkoutBasedirEdit)
        grid.addWidget(label, 2, 0)
        grid.addLayout(checkoutBasedirHBox, 2, 1)

        return tabwidget

    def load(self):
        """Load the configuration."""
        config = get_global_config()
        parser = config._get_parser()
        
        qconfig = get_qbzr_config()

        # Name & e-mail
        try:
            try:
                username = config.username()
                name = extract_name(username, strict=True)
                try:
                    email = extract_email_address(username)
                except errors.NoEmailInUsername:
                    email = ''
            except errors.NoWhoami:
                name, email = get_user_id_from_os()
        except Exception, e:
            trace.mutter("qconfig: load name/email error: %s", str(e))
            name, email = '', ''
        
        self.nameEdit.setText(name)
        self.emailEdit.setText(email)

        # Editor
        editor = config.get_user_option('editor')
        if editor:
            self.editorEdit.setText(editor)

        # E-mail client
        mailClient = config.get_user_option('mail_client')
        if mailClient:
            index = self.emailClientCombo.findData(
                QtCore.QVariant(mailClient))
            if index >= 0:
                self.emailClientCombo.setCurrentIndex(index)

        # Tab-width
        self.tabWidthSpinner.setValue(get_set_tab_width_chars())

        # Spellcheck language
        spellcheck_language = config.get_user_option('spellcheck_language') or 'en'
        if spellcheck_language:
            index = self.spellcheck_language_combo.findData(
                QtCore.QVariant(spellcheck_language))
            if index >= 0:
                self.spellcheck_language_combo.setCurrentIndex(index)

        # Branch source basedir
        branchsourceBasedir = qconfig.get_option('branchsource_basedir')
        if branchsourceBasedir:
            self.branchsourceBasedirEdit.setText(branchsourceBasedir)

        # Checkout basedir
        checkoutBasedir = qconfig.get_option('checkout_basedir')
        if checkoutBasedir:
            self.checkoutBasedirEdit.setText(checkoutBasedir)

        # Aliases
        aliases = parser.get('ALIASES', {})
        for alias, command in aliases.items():
            item = QtGui.QTreeWidgetItem(self.aliasesList)
            item.setFlags(QtCore.Qt.ItemIsSelectable |
                          QtCore.Qt.ItemIsEditable |
                          QtCore.Qt.ItemIsEnabled)
            item.setText(0, alias)
            item.setText(1, command)

        # Bug trackers
        # XXX use special function from bugs.py
        for name, value in parser.get('DEFAULT', {}).items():
            m = _bug_tracker_re.match(name)
            if not m:
                continue
            abbreviation = m.group(1)
            item = QtGui.QTreeWidgetItem(self.bugTrackersList)
            item.setFlags(QtCore.Qt.ItemIsSelectable |
                          QtCore.Qt.ItemIsEditable |
                          QtCore.Qt.ItemIsEnabled)
            item.setText(0, abbreviation)
            item.setText(1, value)
        
        # Diff
        self.diffShowIntergroupColors.setChecked(qconfig.get_option("diff_show_intergroup_colors") in ("True", "1"))
        defaultDiff = qconfig.get_option("default_diff")
        if defaultDiff is None:
            defaultDiff = ""

        self.extDiffListIgnore = True
        def create_ext_diff_item(name, command):
            item = QtGui.QTreeWidgetItem(self.extDiffList)
            item.setFlags(QtCore.Qt.ItemIsSelectable |
                          QtCore.Qt.ItemIsEditable |
                          QtCore.Qt.ItemIsEnabled |
                          QtCore.Qt.ItemIsUserCheckable)
            if command == defaultDiff:
                item.setCheckState(0, QtCore.Qt.Checked)
            else:
                item.setCheckState(0, QtCore.Qt.Unchecked)
            
            item.setText(0, name)
            item.setText(1, command)
            return item
            
        builtin = create_ext_diff_item(gettext("Builtin Diff"),"")
        builtin.setFlags(QtCore.Qt.ItemIsSelectable |
                      QtCore.Qt.ItemIsEnabled |
                      QtCore.Qt.ItemIsUserCheckable)        
        
        extDiffs = qconfig.get_section('EXTDIFF')
        for name, command in extDiffs.items():
            create_ext_diff_item(name, command)
        self.extDiffListIgnore = False

        # Merge
        if mergetools is not None:
            user_merge_tools = config.get_merge_tools()
            default_merge_tool = config.get_user_option('bzr.default_mergetool')
            if len(user_merge_tools) == 0:
                self.import_external_merge(user_merge_tools, config, qconfig)
            self.merge_tools_model.set_merge_tools(user_merge_tools,
                mergetools.known_merge_tools, default_merge_tool)
            self.merge_tools_model.sort(0, QtCore.Qt.AscendingOrder)
    
    def import_external_merge(self, user_merge_tools, config, qconfig):
        # don't ask to import if we already asked before
        if qconfig.get_option_as_bool('imported_external_merge'):
            return
        external_merge = config.get_user_option('external_merge')
        if external_merge is None or external_merge.strip() == '':
            return
        name, new_cmdline = self.convert_external_merge(external_merge)
        answer = QtGui.QMessageBox.question(
            self,
            gettext('Import old external merge tool'),
            gettext('Would you like to import your previously configured '
                    'external merge tool:\n\n  %(old_cmdline)s\n\nas:\n\n'
                    '  %(new_cmdline)s' %
                    {'old_cmdline':external_merge, 'new_cmdline':new_cmdline}),
            QtGui.QMessageBox.Yes | QtGui.QMessageBox.No,
            QtGui.QMessageBox.Yes
        )
        if answer == QtGui.QMessageBox.Yes:
            if name in mergetools.known_merge_tools:
                name = name + '-NEW'
            user_merge_tools[name] = new_cmdline
        # set a flag to indicate that we've already asked about this
        qconfig.set_option('imported_external_merge', True)
    
    def convert_external_merge(self, external_merge):
        args = cmdline.split(external_merge)
        # %b %t %o -o %r
        external_merge = external_merge.replace('%b', '{base}')
        external_merge = external_merge.replace('%t', '{this}')
        external_merge = external_merge.replace('%T', '{this_temp}')
        external_merge = external_merge.replace('%o', '{other}')
        external_merge = external_merge.replace('%r', '{result}')
        return os.path.basename(args[0]), external_merge

    def save(self):
        """Save the configuration."""
        config = get_global_config()
        parser = config._get_parser()

        qconfig = get_qbzr_config()

        def set_or_delete_option(parser, name, value):
            if value:
                if 'DEFAULT' not in parser:
                    parser['DEFAULT'] = {}
                parser['DEFAULT'][name] = value
            else:
                try:
                    del parser['DEFAULT'][name]
                except KeyError:
                    pass

        # Name & e-mail
        _name = unicode(self.nameEdit.text()).strip()
        _email = unicode(self.emailEdit.text()).strip()
        username = u''
        if _name:
            username = _name
        if _email:
            username = (username + ' <%s>' % _email).strip()
        set_or_delete_option(parser, 'email', username)

        # Editor
        editor = unicode(self.editorEdit.text())
        set_or_delete_option(parser, 'editor', editor)

        # E-mail client
        index = self.emailClientCombo.currentIndex()
        mail_client = unicode(self.emailClientCombo.itemData(index).toString())
        set_or_delete_option(parser, 'mail_client', mail_client)

        tabWidth = self.tabWidthSpinner.value()
        set_or_delete_option(parser, 'tab_width', tabWidth)

        # Spellcheck language
        index = self.spellcheck_language_combo.currentIndex()
        spellcheck_language = unicode(self.spellcheck_language_combo.itemData(index).toString())
        set_or_delete_option(parser, 'spellcheck_language', spellcheck_language)

        # Branch source basedir
        branchsource_basedir = unicode(self.branchsourceBasedirEdit.text())
        qconfig.set_option('branchsource_basedir', branchsource_basedir)

        # Checkout basedir
        checkout_basedir = unicode(self.checkoutBasedirEdit.text())
        qconfig.set_option('checkout_basedir', checkout_basedir)

        # Aliases
        parser['ALIASES'] = {}
        for index in range(self.aliasesList.topLevelItemCount()):
            item = self.aliasesList.topLevelItem(index)
            alias = unicode(item.text(0))
            command = unicode(item.text(1))
            if alias and command:
                parser['ALIASES'][alias] = command

        # Bug trackers
        for name, value in parser.get('DEFAULT', {}).items():
            m = _bug_tracker_re.match(name)
            if m:
                abbrev = m.group(1)
                del parser['DEFAULT']['bugtracker_%s_url' % abbrev]
        for index in range(self.bugTrackersList.topLevelItemCount()):
            item = self.bugTrackersList.topLevelItem(index)
            abbrev = unicode(item.text(0))
            url = unicode(item.text(1))
            # FIXME add URL validation (must contain {id})
            if abbrev and url:
                parser['DEFAULT']['bugtracker_%s_url' % abbrev] = url

        # Diff
        qconfig.set_option('diff_show_intergroup_colors',
                           self.diffShowIntergroupColors.isChecked())
        
        defaultDiff = None
        ext_diffs = {}
        for index in range(1, self.extDiffList.topLevelItemCount()):
            item = self.extDiffList.topLevelItem(index)
            name = unicode(item.text(0))
            command = unicode(item.text(1))
            if item.checkState(0) == QtCore.Qt.Checked:
                defaultDiff = command
            if name and command:
                ext_diffs[name] = command
        qconfig.set_section('EXTDIFF', ext_diffs)
        qconfig.set_option('default_diff',
                           defaultDiff)
        
        
        if hasattr(config, 'file_name'):
            file_name = config.file_name
        else:
            file_name = config._get_filename()
        ensure_config_dir_exists(os.path.dirname(file_name))
        f = open(file_name, 'wb')
        parser.write(f)
        f.close()
        
        qconfig.save()

        # Merge
        if mergetools is not None:
            for name in self.merge_tools_model.get_removed_merge_tools():
                option = 'bzr.mergetool.%s' % name
                if config.get_user_option(option, expand=False) is not None:
                    config.remove_user_option(option)
            user_merge_tools = self.merge_tools_model.get_user_merge_tools()
            for name, cmdline in user_merge_tools.iteritems():
                orig_cmdline = config.find_merge_tool(name)
                if orig_cmdline is None or orig_cmdline != cmdline:
                    config.set_user_option('bzr.mergetool.%s' % name, cmdline)
            default_mt = self.merge_tools_model.get_default()
            if default_mt is not None:
                config.set_user_option('bzr.default_mergetool', default_mt)

    def do_accept(self):
        """Save changes and close the window."""
        if not self.validate():
            return
        self.save()
        self.close()

    def do_reject(self):
        """Close the window."""
        self.close()

    def validate(self):
        """Check the inputs and return False if there is something wrong
        and save should be prohibited."""
        # check whoami
        _name = unicode(self.nameEdit.text()).strip()
        _email = unicode(self.emailEdit.text()).strip()
        if (_name, _email) == ('', ''):
            if QtGui.QMessageBox.warning(self, "Configuration",
                "Name and E-mail settings should not be empty",
                gettext("&Ignore and proceed"),
                gettext("&Change the values")) != 0:
                # change the values
                self.tabwidget.setCurrentIndex(0)
                self.nameEdit.setFocus()
                return False
        return True

    def addAlias(self):
        item = QtGui.QTreeWidgetItem(self.aliasesList)
        item.setFlags(QtCore.Qt.ItemIsSelectable |
                      QtCore.Qt.ItemIsEditable |
                      QtCore.Qt.ItemIsEnabled)
        self.aliasesList.setCurrentItem(item)
        self.aliasesList.editItem(item, 0)

    def removeAlias(self):
        for item in self.aliasesList.selectedItems():
            index = self.aliasesList.indexOfTopLevelItem(item)
            if index >= 0:
                self.aliasesList.takeTopLevelItem(index)

    def addBugTracker(self):
        item = QtGui.QTreeWidgetItem(self.bugTrackersList)
        item.setFlags(QtCore.Qt.ItemIsSelectable |
                      QtCore.Qt.ItemIsEditable |
                      QtCore.Qt.ItemIsEnabled)
        self.bugTrackersList.setCurrentItem(item)
        self.bugTrackersList.editItem(item, 0)

    def removeBugTracker(self):
        for item in self.bugTrackersList.selectedItems():
            index = self.bugTrackersList.indexOfTopLevelItem(item)
            if index >= 0:
                self.bugTrackersList.takeTopLevelItem(index)

    def addExtDiff(self):
        item = QtGui.QTreeWidgetItem(self.extDiffList)
        item.setFlags(QtCore.Qt.ItemIsSelectable |
                      QtCore.Qt.ItemIsEditable |
                      QtCore.Qt.ItemIsEnabled |
                      QtCore.Qt.ItemIsUserCheckable)
        item.setCheckState(0, QtCore.Qt.Unchecked)
        self.extDiffList.setCurrentItem(item)
        self.extDiffList.editItem(item, 0)

    def removeExtDiff(self):
        for item in self.extDiffList.selectedItems():
            index = self.extDiffList.indexOfTopLevelItem(item)
            if index >= 1: # You can't remove the builtin diff
                self.extDiffList.takeTopLevelItem(index)
    
    def extDiffListItemChanged(self, changed_item, col):
        if col == 0 and not self.extDiffListIgnore:
            checked_count = 0
            for index in range(self.extDiffList.topLevelItemCount()):
                item = self.extDiffList.topLevelItem(index)
                if item.checkState(0) == QtCore.Qt.Checked:
                    checked_count += 1
            
            if checked_count == 0:
                self.extDiffListIgnore = True
                changed_item.setCheckState(0, QtCore.Qt.Checked)
                self.extDiffListIgnore = False
            elif checked_count > 1:
                self.extDiffListIgnore = True
                for index in range(self.extDiffList.topLevelItemCount()):
                    item = self.extDiffList.topLevelItem(index)
                    if item.checkState(0) == QtCore.Qt.Checked:
                        item.setCheckState(0, QtCore.Qt.Unchecked)
                changed_item.setCheckState(0, QtCore.Qt.Checked)
                self.extDiffListIgnore = False
    
    def get_selected_merge_tool(self):
        sel_model = self.merge_ui.tools.selectionModel()
        if len(sel_model.selectedRows()) == 0:
            return None
        row = sel_model.selectedRows()[0].row()
        return self.merge_tools_model.get_merge_tool_name(row)
        
    def update_buttons(self):
        selected = self.get_selected_merge_tool()
        self.merge_ui.remove.setEnabled(selected is not None and
            self.merge_tools_model.is_user_merge_tool(selected))
        self.merge_ui.set_default.setEnabled(selected is not None and
            self.merge_tools_model.get_default() != selected)
        
    def merge_tools_data_changed(self, top_left, bottom_right):
        self.update_buttons()
        
    def merge_tools_selectionChanged(self, selected, deselected):
        self.update_buttons()

    def merge_tools_add_clicked(self):
        index = self.merge_tools_model.new_merge_tool()
        sel_model = self.merge_ui.tools.selectionModel()
        sel_model.select(index, QtGui.QItemSelectionModel.ClearAndSelect)
        self.merge_ui.tools.edit(index)
        
    def merge_tools_remove_clicked(self):
        sel_model = self.merge_ui.tools.selectionModel()
        assert len(sel_model.selectedRows()) > 0
        for index in sel_model.selectedRows():
            self.merge_tools_model.remove_merge_tool(index.row())
    
    def merge_tools_set_default_clicked(self):
        sel_model = self.merge_ui.tools.selectionModel()
        self.merge_tools_model.set_default(self.get_selected_merge_tool())
        
    def browseEditor(self):
        filename = QtGui.QFileDialog.getOpenFileName(self,
            gettext('Select editor executable'),
            '/')
        if filename:
            self.editorEdit.setText(filename)
            
    def browseCheckoutBasedir(self):
        filename = QtGui.QFileDialog.getExistingDirectory(self,
            gettext('Select base directory for checkouts'),
            '/')
        if filename:
            self.checkoutBasedirEdit.setText(filename)
            
    def browseBranchsourceBasedir(self):
        filename = QtGui.QFileDialog.getExistingDirectory(self,
            gettext('Select default directory for branch sources'),
            '/')
        if filename:
            self.branchsourceBasedirEdit.setText(filename)


def get_user_id_from_os():
    """Calculate automatic user identification.

    Returns (realname, email).

    Only used when none is set in the environment or the id file.

    This previously used the FQDN as the default domain, but that can
    be very slow on machines where DNS is broken.  So now we simply
    use the hostname.
    """
    
    # This use to live in bzrlib.config._auto_user_id, but got removed, so
    # we have a copy.
    
    import sys
    if sys.platform == 'win32':
        from bzrlib import win32utils
        name = win32utils.get_user_name_unicode()
        if name is None:
            raise errors.BzrError("Cannot autodetect user name.\n"
                                  "Please, set your name with command like:\n"
                                  'bzr whoami "Your Name <name@domain.com>"')
        host = win32utils.get_host_name_unicode()
        if host is None:
            host = socket.gethostname()
        return name, (name + '@' + host)

    try:
        import pwd
        uid = os.getuid()
        try:
            w = pwd.getpwuid(uid)
        except KeyError:
            raise errors.BzrCommandError('Unable to determine your name.  '
                'Please use "bzr whoami" to set it.')

        # we try utf-8 first, because on many variants (like Linux),
        # /etc/passwd "should" be in utf-8, and because it's unlikely to give
        # false positives.  (many users will have their user encoding set to
        # latin-1, which cannot raise UnicodeError.)
        try:
            gecos = w.pw_gecos.decode('utf-8')
            encoding = 'utf-8'
        except UnicodeError:
            try:
                encoding = osutils.get_user_encoding()
                gecos = w.pw_gecos.decode(encoding)
            except UnicodeError:
                raise errors.BzrCommandError('Unable to determine your name.  '
                   'Use "bzr whoami" to set it.')
        try:
            username = w.pw_name.decode(encoding)
        except UnicodeError:
            raise errors.BzrCommandError('Unable to determine your name.  '
                'Use "bzr whoami" to set it.')

        comma = gecos.find(',')
        if comma == -1:
            realname = gecos
        else:
            realname = gecos[:comma]
        if not realname:
            realname = username

    except ImportError:
        import getpass
        try:
            user_encoding = osutils.get_user_encoding()
            realname = username = getpass.getuser().decode(user_encoding)
        except UnicodeDecodeError:
            raise errors.BzrError("Can't decode username as %s." % \
                    user_encoding)

    import socket
    return realname, (username + '@' + socket.gethostname())


class MergeToolsTableModel(QtCore.QAbstractTableModel):
    COL_NAME = 0
    COL_COMMANDLINE = 1
    COL_COUNT = 2
    
    def __init__(self):
        super(MergeToolsTableModel, self).__init__()
        self._order = []
        self._user = {}
        self._known = {}
        self._default = None
        self._removed = []
        
    def get_user_merge_tools(self):
        return self._user
    
    def set_merge_tools(self, user, known, default):
        self.beginResetModel()
        self._user = user
        self._known = known
        self._order = user.keys() + known.keys()
        self._default = default
        self.endResetModel()

    def get_default(self):
        return self._default
        
    def set_default(self, new_default):
        old_row = None
        if self._default is not None:
            old_row = self._order.index(self._default)
        new_row = None
        if new_default is not None:
            new_row = self._order.index(new_default)
            self._default = new_default
        else:
            self._default = None
        if old_row is not None:
            self.emit(QtCore.SIGNAL("dataChanged(QModelIndex,QModelIndex)"),
                      self.index(old_row, self.COL_NAME),
                      self.index(old_row, self.COL_NAME))
        if new_row is not None:
            self.emit(QtCore.SIGNAL("dataChanged(QModelIndex,QModelIndex)"),
                      self.index(new_row, self.COL_NAME),
                      self.index(new_row, self.COL_NAME))
    
    def get_removed_merge_tools(self):
        return self._removed
    
    def get_merge_tool_name(self, row):
        return self._order[row]
        
    def get_merge_tool_command_line(self, row):
        name = self._order[row]
        return self._user.get(name, self._known.get(name, None))
        
    def is_user_merge_tool(self, name):
        return name in self._user
        
    def new_merge_tool(self):
        index = self.createIndex(len(self._order), 0)
        self.beginInsertRows(QtCore.QModelIndex(), index.row(), index.row())
        self._order.append('')
        self._user[''] = ''
        self.endInsertRows()
        return index
        
    def remove_merge_tool(self, row):
        name = self._order[row]
        if name not in self._user:
            return
        self.beginRemoveRows(QtCore.QModelIndex(), row, row)
        self._removed.append(name)
        if name == self._default:
            self._default = None
        del self._order[row]
        del self._user[name]
        self.endRemoveRows()
        
    def rowCount(self, parent):
        return len(self._order)
        
    def columnCount(self, parent):
        return self.COL_COUNT
    
    def data(self, index, role):
        name = self._order[index.row()]
        cmdline = self.get_merge_tool_command_line(index.row())
        if role == QtCore.Qt.DisplayRole:
            if index.column() == self.COL_NAME:
                return QtCore.QVariant(name)
            elif index.column() == self.COL_COMMANDLINE:
                return QtCore.QVariant(cmdline)
        elif role == QtCore.Qt.EditRole:
            if index.column() == self.COL_NAME:
                return QtCore.QVariant(name)
            elif index.column() == self.COL_COMMANDLINE:
                return QtCore.QVariant(cmdline)
        elif role == QtCore.Qt.CheckStateRole:
            if index.column() == self.COL_NAME:
                return self._default == name and QtCore.Qt.Checked or QtCore.Qt.Unchecked
        elif role == QtCore.Qt.BackgroundRole:
            if name in self._known:
                palette = QtGui.QApplication.palette()
                return palette.alternateBase()
        return QtCore.QVariant()
        
    def setData(self, index, value, role):
        name = self._order[index.row()]
        if role == QtCore.Qt.EditRole:
            if index.column() == self.COL_NAME:
                # To properly update the config, renaming a merge tool must be
                # handled as a remove and add.
                cmdline = self.get_merge_tool_command_line(index.row())
                if name != '':
                    self._removed.append(name)
                del self._order[index.row()]
                del self._user[name]
                new_name = unicode(value.toString())
                self._order.insert(index.row(), new_name)
                self._user[new_name] = cmdline
                if self._default == name:
                    self._default = new_name
                self.emit(QtCore.SIGNAL("dataChanged(QModelIndex,QModelIndex)"),
                          index, index)
                self.sort(self.COL_NAME, QtCore.Qt.AscendingOrder)
                return True
            elif index.column() == self.COL_COMMANDLINE:
                self._user[name] = unicode(value.toString())
                self.emit(QtCore.SIGNAL("dataChanged(QModelIndex,QModelIndex)"),
                          index, index)
                return True
        elif role == QtCore.Qt.CheckStateRole:
            if index.column() == self.COL_NAME:
                if value.toInt() == (QtCore.Qt.Checked, True):
                    self.set_default(name)
                elif (value.toInt() == (QtCore.Qt.Unchecked, True) and
                      self._default == name):
                    self.set_default(None)
        return False
        
    def flags(self, index):
        f = super(MergeToolsTableModel, self).flags(index)
        name = self._order[index.row()]
        if name not in self._known:
            f = f | QtCore.Qt.ItemIsEditable
        if index.column() == self.COL_NAME:
            f = f | QtCore.Qt.ItemIsUserCheckable
        return f
    
    def headerData(self, section, orientation, role):
        if orientation == QtCore.Qt.Horizontal:
            if section == self.COL_NAME:
                if role == QtCore.Qt.DisplayRole:
                    return QtCore.QVariant(gettext("Name"))
            elif section == self.COL_COMMANDLINE:
                if role == QtCore.Qt.DisplayRole:
                    return QtCore.QVariant(gettext("Command Line"))
        return QtCore.QVariant()

    def sort(self, column, sortOrder):
        self.emit(QtCore.SIGNAL("layoutAboutToBeChanged()"))
        index_map = self._order[:] # copy
        def tool_cmp(a, b):
            if column == self.COL_NAME:
                return cmp(a, b)
            elif column == self.COL_COMMANDLINE:
                return cmp(self.get_merge_tool_command_line(a),
                           self.get_merge_tool_command_line(b))
            return 0
        self._order.sort(cmp=tool_cmp,
                         reverse=sortOrder==QtCore.Qt.DescendingOrder)
        for i in range(0, len(index_map)):
            index_map[i] = self._order.index(index_map[i])
        from_list = []
        to_list = []
        for col in range(0, self.columnCount(None)):
            from_list.extend([self.index(i, col) for i in index_map])
            to_list.extend([self.index(i, col)
                            for i in range(0, len(index_map))])
        self.changePersistentIndexList(from_list, to_list)
        self.emit(QtCore.SIGNAL("layoutChanged()"))
