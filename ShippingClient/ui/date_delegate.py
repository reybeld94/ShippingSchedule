from PyQt6.QtWidgets import (
    QStyledItemDelegate,
    QDateEdit,
    QWidget,
    QHBoxLayout,
    QToolButton,
)
from PyQt6.QtCore import Qt, QDate, pyqtSignal

from .style_tokens import (
    COLOR_BG_SUBTLE,
    COLOR_BORDER,
    COLOR_BORDER_STRONG,
    COLOR_TEXT_DISABLED,
    COLOR_TEXT_SECONDARY,
    CONTROL_HEIGHT,
    RADIUS_MD,
)


class ClearableDateEdit(QDateEdit):
    """QDateEdit that allows clearing the value back to an empty string."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self._blank = False
        # Start each editor on today's date so the calendar popup is sensible
        self.setDate(QDate.currentDate())
        self.dateChanged.connect(self._mark_filled)

    def _mark_filled(self, *args):
        """Mark the widget as filled unless we are clearing it."""
        if getattr(self, "_ignore_next_date_change", False):
            self._ignore_next_date_change = False
            return
        if self.text().strip():
            self._blank = False

    def keyPressEvent(self, event):
        """Allow the user to completely clear the date using Delete/Backspace."""
        if event.key() in (Qt.Key.Key_Backspace, Qt.Key.Key_Delete):
            # Clear the line edit and mark the widget as blank
            self.lineEdit().clear()
            self._blank = True
            # Reset the internal date to today so future selections start here
            self.setDate(QDate.currentDate())
            self._ignore_next_date_change = True
            event.accept()
            return
        super().keyPressEvent(event)

class DateDelegate(QStyledItemDelegate):
    """Delegate that shows a calendar popup when editing date cells."""
    def __init__(self, parent=None):
        super().__init__(parent)

    def createEditor(self, parent, option, index):
        editor = ClearableDateEdit(parent)
        editor.setCalendarPopup(True)
        editor.setDisplayFormat("MM/dd/yy")
        return editor

    def setEditorData(self, editor, index):
        text = index.data(Qt.ItemDataRole.EditRole)
        if text:
            date = QDate.fromString(text, "MM/dd/yyyy")
            if not date.isValid():
                date = QDate.fromString(text, "MM/dd/yy")
                if date.isValid() and date.year() < 2000:
                    # QDate assumes 1900s for two-digit years; shift to 2000s
                    date = date.addYears(100)
            if date.isValid():
                editor.setDate(date)
            else:
                # If parsing fails, default to today's date but keep the field blank
                editor.setDate(QDate.currentDate())
                editor.lineEdit().clear()
                editor._blank = True
        else:
            # Start with today's date selected so the popup opens there
            editor.setDate(QDate.currentDate())
            editor.lineEdit().clear()
            editor._blank = True

    def setModelData(self, editor, model, index):
        if getattr(editor, "_blank", False) or editor.text().strip() == "":
            model.setData(index, "", Qt.ItemDataRole.EditRole)
        else:
            date_str = editor.date().toString("MM/dd/yy")
            model.setData(index, date_str, Qt.ItemDataRole.EditRole)


class OptionalDateEdit(QWidget):
    """Composite date field with calendar popup and a Clear button.

    Exposes a ``text()`` / ``setText()`` API so it can be a drop-in replacement
    for ``ModernLineEdit`` in form dialogs. An empty string means "no date".
    Dates are returned in MM/dd/yy to match the existing backend contract.
    """

    textChanged = pyqtSignal(str)

    def __init__(self, placeholder: str = "MM/DD/YY", parent: QWidget | None = None):
        super().__init__(parent)
        layout = QHBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(4)

        self._date_edit = ClearableDateEdit()
        self._date_edit.setCalendarPopup(True)
        self._date_edit.setDisplayFormat("MM/dd/yy")
        self._date_edit.setMinimumHeight(CONTROL_HEIGHT)
        line = self._date_edit.lineEdit()
        if line is not None:
            line.setPlaceholderText(placeholder)
        # Start blank — leaving the line edit empty signals "no date set"
        self._date_edit.lineEdit().clear()
        self._date_edit._blank = True
        self._date_edit.dateChanged.connect(self._emit_text_changed)
        layout.addWidget(self._date_edit, 1)

        self._clear_btn = QToolButton(self)
        self._clear_btn.setText("×")  # multiplication sign as a slim X
        self._clear_btn.setToolTip("Clear date")
        self._clear_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self._clear_btn.setFixedSize(CONTROL_HEIGHT, CONTROL_HEIGHT)
        self._clear_btn.setStyleSheet(
            f"""
            QToolButton {{
                background-color: transparent;
                color: {COLOR_TEXT_SECONDARY};
                border: 1px solid {COLOR_BORDER};
                border-radius: {RADIUS_MD}px;
                font-size: 16px;
                font-weight: 600;
            }}
            QToolButton:hover {{
                background-color: {COLOR_BG_SUBTLE};
                border-color: {COLOR_BORDER_STRONG};
            }}
            QToolButton:disabled {{
                color: {COLOR_TEXT_DISABLED};
                border-color: {COLOR_BORDER};
            }}
            """
        )
        self._clear_btn.clicked.connect(self.clear)
        layout.addWidget(self._clear_btn)

        self.setFocusProxy(self._date_edit)

    # ------------------------------------------------------------------
    # API compatible with ModernLineEdit
    # ------------------------------------------------------------------
    def text(self) -> str:
        if getattr(self._date_edit, "_blank", False):
            return ""
        if self._date_edit.text().strip() == "":
            return ""
        return self._date_edit.date().toString("MM/dd/yy")

    def setText(self, value: str) -> None:
        text = (value or "").strip()
        if not text:
            self.clear()
            return

        # Accept MM/dd/yyyy first, then MM/dd/yy (server stores both shapes).
        date = QDate.fromString(text, "MM/dd/yyyy")
        if not date.isValid():
            date = QDate.fromString(text, "MM/dd/yy")
            if date.isValid() and date.year() < 2000:
                date = date.addYears(100)

        if date.isValid():
            # Block dateChanged briefly so we can update _blank atomically.
            self._date_edit.blockSignals(True)
            self._date_edit.setDate(date)
            self._date_edit._blank = False
            self._date_edit.blockSignals(False)
            self.textChanged.emit(self.text())
        else:
            self.clear()

    def clear(self) -> None:
        line = self._date_edit.lineEdit()
        if line is not None:
            line.clear()
        self._date_edit._blank = True
        # Reset internal date so the next popup opens on today rather than
        # the last selected value.
        self._date_edit.blockSignals(True)
        self._date_edit.setDate(QDate.currentDate())
        self._date_edit.blockSignals(False)
        self.textChanged.emit("")

    def setEnabled(self, enabled: bool) -> None:  # type: ignore[override]
        super().setEnabled(enabled)
        self._date_edit.setEnabled(enabled)
        self._clear_btn.setEnabled(enabled)

    # ------------------------------------------------------------------
    # Internals
    # ------------------------------------------------------------------
    def _emit_text_changed(self, *_args) -> None:
        self.textChanged.emit(self.text())
