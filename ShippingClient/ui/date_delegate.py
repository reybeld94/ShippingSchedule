from PyQt6.QtWidgets import QStyledItemDelegate, QDateEdit
from PyQt6.QtCore import Qt, QDate

class DateDelegate(QStyledItemDelegate):
    """Delegate that shows a calendar popup when editing date cells."""
    def __init__(self, parent=None):
        super().__init__(parent)

    def createEditor(self, parent, option, index):
        editor = QDateEdit(parent)
        editor.setCalendarPopup(True)
        editor.setDisplayFormat("MM/dd/yy")
        return editor

    def setEditorData(self, editor, index):
        text = index.data(Qt.ItemDataRole.EditRole)
        date = QDate.fromString(text, "MM/dd/yy")
        if not date.isValid():
            date = QDate.fromString(text, "MM/dd/yyyy")
        if not date.isValid():
            date = QDate.currentDate()
        editor.setDate(date)

    def setModelData(self, editor, model, index):
        date_str = editor.date().toString("MM/dd/yy")
        model.setData(index, date_str, Qt.ItemDataRole.EditRole)
