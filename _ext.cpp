#include "_ext.h"

void
TreeFilterProxyModel::setFilterRegExp(const QString &pattern)
{
	filterCache.clear();
	QSortFilterProxyModel::setFilterRegExp(pattern);
}

void
TreeFilterProxyModel::setFilterRole(int role)
{
	filterCache.clear();
	QSortFilterProxyModel::setFilterRole(role);
}

bool
TreeFilterProxyModel::filterAcceptsRow(int sourceRow, const QModelIndex &sourceParent) const
{
	QRegExp regex = filterRegExp();
	QAbstractItemModel *model = sourceModel();

	if (regex.isEmpty())
		return true;

	QModelIndex index = model->index(sourceRow, 0, sourceParent);
	if (!index.isValid())
		return true;

	QString filterId = model->data(index, Qt::UserRole + 200).toString();
	int accepts = filterCache.value(filterId, -1);
	if (accepts != -1)
		return accepts == 1;

	QString key = model->data(index, filterRole()).toString();
	if (key.contains(regex)) {
		((TreeFilterProxyModel *)this)->filterCache.insert(filterId, 1);
		return true;
	}

	if (model->hasChildren(index)) {
		int childRow = 0;
		while (true) {
			QModelIndex child = index.child(childRow, index.column());
			if (!child.isValid())
				break;
			if (filterAcceptsRow(childRow, index)) {
				((TreeFilterProxyModel *)this)->filterCache.insert(filterId, 1);
				return true;
			}
			childRow += 1;
		}
	}

	((TreeFilterProxyModel *)this)->filterCache.insert(filterId, 0);
	return false;
}
