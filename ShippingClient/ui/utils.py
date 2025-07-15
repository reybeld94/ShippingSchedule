# ui/utils.py
from PyQt6.QtWidgets import QLabel
from PyQt6.QtCore import QTimer, Qt, QPoint

def show_popup_notification(parent, message, duration=3000):
    popup = QLabel(parent)
    popup.setText(f"  ●  {message}")
    popup.setStyleSheet("""
        QLabel {
            background-color: #3B82F6;
            color: white;
            padding: 12px 22px;
            border-radius: 10px;
            font-size: 14px;
            font-family: 'Roboto';
        }
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
