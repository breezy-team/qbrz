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

class LogWidgetDelegate : QItemDelegate
{
%TypeHeaderCode
#include "_ext.h"
%End

public:
	LogWidgetDelegate(QObject *parent = 0);
	void paint(QPainter *painter, const QStyleOptionViewItem &option, const QModelIndex &index) const;

protected:
	void drawDisplay(QPainter *painter, const QStyleOptionViewItem &option, const QRect &rect, const QString &text) const;
};
