%Module bzrlib.plugins.qbzr._ext 0

%Import QtCore/QtCoremod.sip
%Import QtGui/QtGuimod.sip

class TreeFilterProxyModel : QSortFilterProxyModel
{
%TypeHeaderCode
#include "_ext.h"
%End

protected:
	virtual bool filterAcceptsRow(int sourceRow, const QModelIndex &sourceParent) const;
	void setFilterRegExp(const QString &pattern);
	void setFilterRole(int role);
};
