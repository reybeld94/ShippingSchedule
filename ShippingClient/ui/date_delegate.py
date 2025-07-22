from PyQt6.QtWidgets import QStyledItemDelegate, QDateEdit
from PyQt6.QtCore import Qt, QDate

class ClearableDateEdit(QDateEdit):
    """QDateEdit that allows clearing the value back to an empty string."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self._blank = False
        self.dateChanged.connect(self._mark_filled)

    def _mark_filled(self, *args):
        """Mark the widget as filled unless we are clearing it."""
        if getattr(self, "_ignore_next_date_change", False):
            self._ignore_next_date_change = False
            return
        if self.text().strip():
            self._blank = False

    def keyPressEvent(self, event):
        super().keyPressEvent(event)
        if event.key() in (Qt.Key.Key_Backspace, Qt.Key.Key_Delete):
            if self.text().strip() == "":
                # Ensure the editor stays empty and mark it as blank
                self.lineEdit().clear()
                self._blank = True
                self._ignore_next_date_change = True

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
            date = QDate.fromString(text, "MM/dd/yy")
            if not date.isValid():
                date = QDate.fromString(text, "MM/dd/yyyy")
            if date.isValid():
                editor.setDate(date)
            else:
                editor.lineEdit().clear()
                editor._blank = True
        else:
            editor.lineEdit().clear()
            editor._blank = True

    def setModelData(self, editor, model, index):
        if getattr(editor, "_blank", False) or editor.text().strip() == "":
            model.setData(index, "", Qt.ItemDataRole.EditRole)
        else:
            date_str = editor.date().toString("MM/dd/yy")
            model.setData(index, date_str, Qt.ItemDataRole.EditRole)
