# ui/utils.py
from PyQt6.QtWidgets import QLabel
from PyQt6.QtCore import QTimer, Qt, QPoint
from core.config import MODERN_FONT

def show_popup_notification(parent, message, duration=3000, color="#3B82F6"):
    popup = QLabel(parent)
    popup.setText(f"  ●  {message}")
    popup.setStyleSheet(f"""
        QLabel {{
            background-color: {color};
            color: white;
            padding: 12px 22px;
            border-radius: 10px;
            font-size: 14px;
            font-family: '{MODERN_FONT}';
        }}
    """)
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
