# ui/utils.py
from PyQt6.QtWidgets import QApplication, QLabel, QWidget
from PyQt6.QtGui import QFont
from PyQt6.QtCore import QTimer, Qt, QPoint

from core.config import MODERN_FONT


def _resolve_base_font_size(default: int = 10) -> int:
    """Return the current application font size or a sensible default."""
    app = QApplication.instance()
    if app is not None:
        size = app.font().pointSize()
        if size > 0:
            return size
    return default


def get_base_font_size() -> int:
    """Public helper to access the current base font size."""
    return _resolve_base_font_size()


def apply_scaled_font(widget: QWidget, offset: int = 0, weight: QFont.Weight | None = None) -> None:
    """Apply the preferred font family with a size relative to the global preference."""
    base_size = _resolve_base_font_size()
    font = widget.font()
    font.setFamily(MODERN_FONT)
    font.setPointSize(max(6, base_size + offset))
    if weight is not None:
        font.setWeight(weight)
        widget.setProperty("_font_weight", int(weight))
    widget.setFont(font)
    widget.setProperty("_font_offset", offset)


def refresh_scaled_fonts(root: QWidget) -> None:
    """Re-apply stored offsets for widgets created with apply_scaled_font."""
    widgets = [root]
    widgets.extend(root.findChildren(QWidget))

    base_size = _resolve_base_font_size()
    for widget in widgets:
        offset = widget.property("_font_offset")
        if offset is None:
            continue
        try:
            offset_int = int(offset)
        except (TypeError, ValueError):
            offset_int = 0

        font = widget.font()
        font.setFamily(MODERN_FONT)
        font.setPointSize(max(6, base_size + offset_int))

        weight_value = widget.property("_font_weight")
        if weight_value is not None:
            try:
                font.setWeight(QFont.Weight(int(weight_value)))
            except (TypeError, ValueError):
                pass

        widget.setFont(font)


def show_popup_notification(parent, message, duration=3000, color="#3B82F6"):
    popup = QLabel(parent)
    popup.setText(f"  ●  {message}")
    font_size = max(8, _resolve_base_font_size() + 4)
    popup.setStyleSheet(
        f"""
        QLabel {{
            background-color: {color};
            color: white;
            padding: 12px 22px;
            border-radius: 10px;
            font-size: {font_size}px;
            font-family: '{MODERN_FONT}';
        }}
    """
    )
    popup.setWindowFlags(Qt.WindowType.FramelessWindowHint | Qt.WindowType.ToolTip)
    popup.setAttribute(Qt.WidgetAttribute.WA_TransparentForMouseEvents)
    popup.adjustSize()

    def position_and_show():
        parent_pos = parent.mapToGlobal(QPoint(0, 0))
        x = parent_pos.x() + parent.width() - popup.width() - 30
        y = parent_pos.y() + parent.height() - popup.height() - 30
        popup.move(x, y)
        popup.show()
        QTimer.singleShot(duration, popup.deleteLater)

    QTimer.singleShot(0, position_and_show)
