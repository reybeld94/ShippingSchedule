from PyQt6.QtWidgets import QStyledItemDelegate, QDateEdit
from PyQt6.QtCore import Qt, QDate

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
