from PyQt6.QtWidgets import QStyledItemDelegate, QComboBox
from PyQt6.QtCore import Qt

class StatusDelegate(QStyledItemDelegate):
    """Delegate with a dropdown editor for the status column."""

    DISPLAY_MAP = {
        "partial_release": "Partial Release",
        "final_release": "Final Release",
        "rejected": "Rejected",
    }
    CODE_MAP = {v: k for k, v in DISPLAY_MAP.items()}

    def createEditor(self, parent, option, index):
        editor = QComboBox(parent)
        editor.addItems(["Partial Release", "Final Release", "Rejected"])
        editor.setEditable(False)
        return editor

    def setEditorData(self, editor, index):
        # value stored in model is the internal code
        value = index.data(Qt.ItemDataRole.EditRole)
        display = self.DISPLAY_MAP.get(str(value).lower(), str(value))
        idx = editor.findText(display)
        if idx >= 0:
            editor.setCurrentIndex(idx)
        else:
            editor.setCurrentText(display)

    def setModelData(self, editor, model, index):
        display = editor.currentText()
        code = self.CODE_MAP.get(display, display.lower().replace(" ", "_"))
        # store internal code and display text separately
        model.setData(index, code, Qt.ItemDataRole.EditRole)
        model.setData(index, display, Qt.ItemDataRole.DisplayRole)
