#ifndef _METADATA_H__
#define _METADATA_H__

#include <QHash>
#include <QSortFilterProxyModel>

class TreeFilterProxyModel : public QSortFilterProxyModel
{
protected:
	bool filterAcceptsRow(int sourceRow, const QModelIndex &sourceParent) const;
	void setFilterRegExp(const QString &pattern);
	void setFilterRole(int role);

private:
	QHash<QString, int> filterCache;
};

#endif
