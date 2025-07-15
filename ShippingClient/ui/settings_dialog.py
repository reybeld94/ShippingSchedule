from PyQt6.QtWidgets import QDialog, QVBoxLayout, QHBoxLayout, QLabel, QMessageBox
from PyQt6.QtCore import Qt
from .widgets import ModernButton, ModernLineEdit
from core.settings_manager import SettingsManager
from core.config import MODERN_FONT


class SettingsDialog(QDialog):
    """Simple dialog to configure server connection URLs."""

    def __init__(self, settings_mgr: SettingsManager):
        super().__init__()
        self.settings_mgr = settings_mgr
        self.setWindowTitle("Connection Settings")
        self.setModal(True)
        self.setMinimumSize(400, 200)
        self.setup_ui()
        self.load_values()

    def setup_ui(self):
        layout = QVBoxLayout(self)
        form_layout = QVBoxLayout()

        server_label = QLabel("Server URL")
        self.server_edit = ModernLineEdit()

        ws_label = QLabel("WebSocket URL")
        self.ws_edit = ModernLineEdit()

        form_layout.addWidget(server_label)
        form_layout.addWidget(self.server_edit)
        form_layout.addWidget(ws_label)
        form_layout.addWidget(self.ws_edit)

        btn_layout = QHBoxLayout()
        save_btn = ModernButton("Save", "primary")
        cancel_btn = ModernButton("Cancel", "secondary")
        save_btn.clicked.connect(self.save)
        cancel_btn.clicked.connect(self.reject)
        btn_layout.addStretch()
        btn_layout.addWidget(cancel_btn)
        btn_layout.addWidget(save_btn)

        layout.addLayout(form_layout)
        layout.addLayout(btn_layout)

    def load_values(self):
        self.server_edit.setText(self.settings_mgr.get_server_url())
        self.ws_edit.setText(self.settings_mgr.get_ws_url())

    def save(self):
        server = self.server_edit.text().strip()
        ws = self.ws_edit.text().strip()
        if not server or not ws:
            QMessageBox.warning(self, "Error", "Both URLs are required")
            return
        self.settings_mgr.set_server_url(server)
        self.settings_mgr.set_ws_url(ws)
        self.accept()
