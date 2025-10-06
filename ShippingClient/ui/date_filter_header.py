from __future__ import annotations

from PyQt6.QtCore import QPoint, QPointF, QRect, Qt, pyqtSignal
from PyQt6.QtGui import QColor, QPainter, QPen
from PyQt6.QtWidgets import QHeaderView


class DateFilterHeader(QHeaderView):
    """Header view that shows a filter indicator for date columns."""

    filter_requested = pyqtSignal(int, QPoint)

    def __init__(self, parent=None, filter_columns=None):
        super().__init__(Qt.Orientation.Horizontal, parent)
        self._filter_columns = set(filter_columns or [])
        self._active_filters = set()
        self._indicator_width = 16
        self.setSectionsClickable(True)

    def set_filter_active(self, section: int, active: bool) -> None:
        if active:
            self._active_filters.add(section)
        else:
            self._active_filters.discard(section)
        self.updateSection(section)

    def filter_columns(self):
        return self._filter_columns

    def set_filter_columns(self, columns):
        self._filter_columns = set(columns)
        self.update()

    def mousePressEvent(self, event):
        logical = self.logicalIndexAt(event.pos())
        if logical in self._filter_columns and event.button() == Qt.MouseButton.RightButton:
            self.filter_requested.emit(logical, self.mapToGlobal(event.pos()))
            event.accept()
            return
        super().mousePressEvent(event)

    def paintSection(self, painter: QPainter, rect: QRect, logicalIndex: int) -> None:
        super().paintSection(painter, rect, logicalIndex)
        if logicalIndex not in self._filter_columns:
            return

        painter.save()
        painter.setRenderHint(QPainter.RenderHint.Antialiasing, True)

        color = QColor("#1F2937" if logicalIndex in self._active_filters else "#6B7280")
        painter.setBrush(color)
        painter.setPen(QPen(Qt.PenStyle.NoPen))

        indicator_width = min(self._indicator_width, rect.width())
        indicator_height = max(4, rect.height() // 4)

        right_margin = 6
        left = rect.right() - indicator_width - right_margin
        top = rect.center().y() - indicator_height / 2

        points = [
            QPointF(left, top),
            QPointF(left + indicator_width, top),
            QPointF(left + indicator_width / 2, top + indicator_height),
        ]

        painter.drawPolygon(points)
        painter.restore()

    def _section_rect(self, logical: int) -> QRect:
        left = self.sectionPosition(logical)
        width = self.sectionSize(logical)
        return QRect(left, 0, width, self.height())
