#include "_ext.h"
#include <QPainter>

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

QColor LogWidgetDelegate::color[2] = {
	QColor(255, 255, 170),
	QColor(255, 188, 188),
};
QColor LogWidgetDelegate::borderColor[2] = {
	QColor(255, 238, 0),
	QColor(255, 79, 79),
};

static QList<QPair<int, QString> > labels;

LogWidgetDelegate::LogWidgetDelegate(QObject *parent) : QItemDelegate(parent)
{
}


void
LogWidgetDelegate::paint(QPainter *painter, const QStyleOptionViewItem &option, const QModelIndex &index) const
{
	labels.clear();
	if (index.column() == 3) {
		for (int i = 0; i < 10; i++) {
			QVariant label = index.data(Qt::UserRole + 1 + i);
			if (!label.isNull())
				labels += qMakePair(0, label.toString());
			else
				break;
		}
		for (int i = 0; i < 10; i++) {
			QVariant label = index.data(Qt::UserRole + 100 + i);
			if (!label.isNull())
				labels += qMakePair(1, label.toString());
			else
				break;
		}
	}
	QItemDelegate::paint(painter, option, index);
}

void
LogWidgetDelegate::drawDisplay(QPainter *painter, const QStyleOptionViewItem &option, const QRect &rect, const QString &text) const
{
	if (!labels.size()) {
		QItemDelegate::drawDisplay(painter, option, rect, text);
		return;
	}

	painter->save();
	QFont tagFont = QFont(option.font);
	tagFont.setPointSizeF(tagFont.pointSizeF() * 9 / 10);

	int x = 0;
	QPair<int, QString> lbl;
	foreach(lbl, labels) {
		QRect tagRect = rect.adjusted(1, 1, -1, -1);
		tagRect.setWidth(QFontMetrics(tagFont).width(lbl.second) + 6);
		tagRect.moveLeft(tagRect.x() + x);
		painter->fillRect(tagRect.adjusted(1, 1, -1, -1), color[lbl.first]);
		painter->setPen(borderColor[lbl.first]);
		painter->drawRect(tagRect.adjusted(0, 0, -1, -1));
		painter->setFont(tagFont);
		painter->setPen(option.palette.text().color());
		painter->drawText(tagRect.left() + 3, tagRect.bottom() - option.fontMetrics.descent() + 1, lbl.second);
		x += tagRect.width() + 3;
	}

	painter->setFont(option.font);
	if (option.state & QStyle::State_Selected
        && option.state & QStyle::State_Active)
		painter->setPen(option.palette.highlightedText().color());
	else
		painter->setPen(option.palette.text().color());
	painter->drawText(rect.left() + x + 2, rect.bottom() - option.fontMetrics.descent(), text);
	painter->restore();
}
