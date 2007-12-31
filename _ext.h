#ifndef _METADATA_H__
#define _METADATA_H__

#include <QHash>
#include <QSortFilterProxyModel>
#include <QItemDelegate>

class TreeFilterProxyModel : public QSortFilterProxyModel
{
protected:
	bool filterAcceptsRow(int sourceRow, const QModelIndex &sourceParent) const;
	void setFilterRegExp(const QString &pattern);
	void setFilterRole(int role);

private:
	QHash<QString, int> filterCache;
};

class LogWidgetDelegate : public QItemDelegate
{
public:
	LogWidgetDelegate(QObject *parent = 0);
	void paint(QPainter *painter, const QStyleOptionViewItem &option, const QModelIndex &index) const;

protected:
	void drawDisplay(QPainter *painter, const QStyleOptionViewItem &option, const QRect &rect, const QString &text) const;

private:
    static QColor color[2];
    static QColor borderColor[2];
};

#endif
