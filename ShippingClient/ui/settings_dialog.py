from PyQt6.QtWidgets import (
    QApplication,
    QDialog,
    QVBoxLayout,
    QHBoxLayout,
    QLabel,
    QMessageBox,
    QSpinBox,
    QWidget,
    QTabWidget,
    QCheckBox,
)
from PyQt6.QtGui import QFont

from .widgets import ModernButton, ModernLineEdit
from .user_dialog import UserManagementWidget
from core.settings_manager import SettingsManager
from core.config import MODERN_FONT
from core.api_client import RobustApiClient
from .utils import apply_scaled_font


class SettingsDialog(QDialog):
    """Settings dialog with tabs for general app options, connections and users."""

    def __init__(self, settings_mgr: SettingsManager, token: str = "", is_admin: bool = False):
        super().__init__()
        self.settings_mgr = settings_mgr
        self.token = token
        self.is_admin = is_admin
        self.api_client = RobustApiClient(
            base_url=self.settings_mgr.get_server_url(),
            token=self.token,
        )

        self.setWindowTitle("Settings")
        self.setModal(True)
        self.setMinimumSize(640, 460)
        self.setup_ui()
        self.load_values()

    def setup_ui(self):
        layout = QVBoxLayout(self)
        self.tabs = QTabWidget()

        self.general_tab = QWidget()
        self.connections_tab = QWidget()

        self._setup_general_tab()
        self._setup_connections_tab()

        self.tabs.addTab(self.general_tab, "General")
        self.tabs.addTab(self.connections_tab, "Connections")

        if self.is_admin:
            self.users_tab = QWidget()
            self._setup_users_tab()
            self.tabs.addTab(self.users_tab, "Users")

        btn_layout = QHBoxLayout()
        save_btn = ModernButton("Save", "primary")
        cancel_btn = ModernButton("Cancel", "secondary")
        save_btn.clicked.connect(self.save)
        cancel_btn.clicked.connect(self.reject)
        btn_layout.addStretch()
        btn_layout.addWidget(cancel_btn)
        btn_layout.addWidget(save_btn)

        layout.addWidget(self.tabs)
        layout.addLayout(btn_layout)

    def _setup_general_tab(self):
        layout = QVBoxLayout(self.general_tab)
        font_label = QLabel("Text size")
        apply_scaled_font(font_label, offset=1, weight=QFont.Weight.Medium)
        self.font_spin = QSpinBox()
        self.font_spin.setRange(8, 20)
        self.font_spin.setSingleStep(1)
        apply_scaled_font(self.font_spin)

        layout.addWidget(font_label)
        layout.addWidget(self.font_spin)
        layout.addStretch()

    def _setup_connections_tab(self):
        layout = QVBoxLayout(self.connections_tab)

        server_label = QLabel("Server URL")
        apply_scaled_font(server_label, offset=1, weight=QFont.Weight.Medium)
        self.server_edit = ModernLineEdit()

        ws_label = QLabel("WebSocket URL")
        apply_scaled_font(ws_label, offset=1, weight=QFont.Weight.Medium)
        self.ws_edit = ModernLineEdit()

        fedex_label = QLabel("FedEx")
        apply_scaled_font(fedex_label, offset=1, weight=QFont.Weight.Medium)
        self.fedex_enabled = QCheckBox("Enabled")
        apply_scaled_font(self.fedex_enabled)
        self.fedex_api_key_edit = ModernLineEdit("FedEx API Key")
        self.fedex_secret_key_edit = ModernLineEdit("FedEx Secret Key")
        self.fedex_secret_key_edit.setEchoMode(ModernLineEdit.EchoMode.Password)
        self.test_fedex_btn = ModernButton("Test Connection", "secondary")
        self.test_fedex_btn.clicked.connect(self.test_fedex_connection)
        self.test_fedex_btn.setEnabled(self.is_admin)

        layout.addWidget(server_label)
        layout.addWidget(self.server_edit)
        layout.addWidget(ws_label)
        layout.addWidget(self.ws_edit)
        layout.addSpacing(12)
        layout.addWidget(fedex_label)
        layout.addWidget(self.fedex_enabled)
        layout.addWidget(self.fedex_api_key_edit)
        layout.addWidget(self.fedex_secret_key_edit)
        layout.addWidget(self.test_fedex_btn)
        layout.addStretch()

    def _setup_users_tab(self):
        layout = QVBoxLayout(self.users_tab)
        self.user_management = UserManagementWidget(self.token, parent=self.users_tab)
        layout.addWidget(self.user_management)

    def load_values(self):
        self.server_edit.setText(self.settings_mgr.get_server_url())
        self.ws_edit.setText(self.settings_mgr.get_ws_url())
        self.font_spin.setValue(self.settings_mgr.get_font_size())
        response = self.api_client.get_connection_settings()
        if response.is_success():
            fedex = (response.get_data() or {}).get("fedex", {})
            self.fedex_enabled.setChecked(bool(fedex.get("enabled", False)))
            self.fedex_api_key_edit.setText(str(fedex.get("apiKey") or ""))
            if fedex.get("hasSecretKey"):
                self.fedex_secret_key_edit.setPlaceholderText("********")
        else:
            self.fedex_enabled.setChecked(False)

    def test_fedex_connection(self):
        if not self.is_admin:
            QMessageBox.warning(self, "Error", "Only admins can test FedEx credentials")
            return
        response = self.api_client.test_fedex_settings()
        if response.is_success():
            QMessageBox.information(self, "FedEx", "FedEx connection is valid.")
            return
        QMessageBox.warning(self, "FedEx", response.get_error() or "FedEx test failed")

    def save(self):
        server = self.server_edit.text().strip()
        ws = self.ws_edit.text().strip()
        if not server or not ws:
            QMessageBox.warning(self, "Error", "Both URLs are required")
            return

        self.settings_mgr.set_server_url(server)
        self.settings_mgr.set_ws_url(ws)
        new_size = self.font_spin.value()
        self.settings_mgr.set_font_size(new_size)

        enabled = self.fedex_enabled.isChecked()
        fedex_api_key = self.fedex_api_key_edit.text().strip()
        fedex_secret_key = self.fedex_secret_key_edit.text().strip()
        has_secret_placeholder = self.fedex_secret_key_edit.placeholderText() == "********"
        if not fedex_secret_key and has_secret_placeholder:
            fedex_secret_key = "********"

        if enabled and (not fedex_api_key or not fedex_secret_key):
            QMessageBox.warning(self, "Error", "FedEx API Key and Secret Key are required when enabled")
            return

        if self.is_admin:
            current = self.api_client.get_connection_settings()
            current_secret_present = False
            if current.is_success():
                current_secret_present = bool((current.get_data() or {}).get("fedex", {}).get("hasSecretKey"))
            if fedex_secret_key == "********" and current_secret_present:
                # Keep saved secret; resend masked token pattern is not supported by API.
                # We refetch by disabling secret updates when left masked.
                fedex_secret_key = ""

            response = self.api_client.update_fedex_settings(enabled, fedex_api_key, fedex_secret_key)
            if not response.is_success():
                QMessageBox.warning(self, "Error", response.get_error() or "Failed to save FedEx settings")
                return

        app = QApplication.instance()
        if app is not None:
            font = app.font()
            font.setFamily(MODERN_FONT)
            font.setPointSize(new_size)
            app.setFont(font)
        self.accept()
