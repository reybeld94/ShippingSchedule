from PyQt6.QtWidgets import (
    QApplication,
    QDialog,
    QVBoxLayout,
    QHBoxLayout,
    QFormLayout,
    QLabel,
    QMessageBox,
    QSpinBox,
    QWidget,
    QTabWidget,
    QCheckBox,
    QFrame,
    QScrollArea,
)
from PyQt6.QtGui import QFont
from PyQt6.QtCore import Qt

from .widgets import ModernButton, ModernLineEdit
from .user_dialog import UserManagementWidget
from core.settings_manager import SettingsManager
from core.config import MODERN_FONT
from core.api_client import RobustApiClient
from .utils import apply_scaled_font
from .style_tokens import (
    COLOR_BG_SUBTLE,
    COLOR_BORDER,
    COLOR_PRIMARY,
    COLOR_SURFACE,
    COLOR_TEXT_PRIMARY,
    COLOR_TEXT_SECONDARY,
    CONTROL_HEIGHT,
    RADIUS_LG,
    RADIUS_MD,
    SPACE_12,
    SPACE_16,
    SPACE_20,
    SPACE_8,
)


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
        layout.setContentsMargins(SPACE_20, SPACE_20, SPACE_20, SPACE_16)
        layout.setSpacing(SPACE_12)
        self._apply_dialog_style()

        header = QFrame()
        header_layout = QVBoxLayout(header)
        header_layout.setContentsMargins(SPACE_8, 0, SPACE_8, SPACE_8)
        header_layout.setSpacing(4)
        title = QLabel("Settings")
        apply_scaled_font(title, offset=5, weight=QFont.Weight.DemiBold)
        title.setObjectName("settingsDialogTitle")
        header_layout.addWidget(title)
        layout.addWidget(header)

        self.tabs = QTabWidget()
        self.tabs.setDocumentMode(True)
        self.tabs.setObjectName("settingsTabs")

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

        content_wrapper = QFrame()
        content_wrapper.setObjectName("contentWrapper")
        content_layout = QVBoxLayout(content_wrapper)
        content_layout.setContentsMargins(SPACE_12, SPACE_12, SPACE_12, SPACE_12)
        content_layout.setSpacing(0)
        content_layout.addWidget(self.tabs)

        btn_layout = QHBoxLayout()
        btn_layout.setContentsMargins(0, 0, 0, 0)
        btn_layout.setSpacing(SPACE_12)
        save_btn = ModernButton("Save", "primary")
        cancel_btn = ModernButton("Cancel", "secondary")
        save_btn.setMinimumHeight(CONTROL_HEIGHT)
        cancel_btn.setMinimumHeight(CONTROL_HEIGHT)
        save_btn.setMinimumWidth(108)
        cancel_btn.setMinimumWidth(108)
        save_btn.clicked.connect(self.save)
        cancel_btn.clicked.connect(self.reject)
        btn_layout.addStretch()
        btn_layout.addWidget(cancel_btn)
        btn_layout.addWidget(save_btn)

        footer = QFrame()
        footer_layout = QVBoxLayout(footer)
        footer_layout.setContentsMargins(SPACE_8, SPACE_8, SPACE_8, 0)
        footer_layout.setSpacing(0)
        footer_layout.addLayout(btn_layout)

        layout.addWidget(content_wrapper, 1)
        layout.addWidget(footer)

    def _setup_general_tab(self):
        layout = QVBoxLayout(self.general_tab)
        layout.setContentsMargins(SPACE_16, SPACE_16, SPACE_16, SPACE_12)
        layout.setSpacing(SPACE_16)

        text_section = QFrame()
        text_section.setObjectName("generalSection")
        text_section_layout = QVBoxLayout(text_section)
        text_section_layout.setContentsMargins(SPACE_16, SPACE_12, SPACE_16, SPACE_16)
        text_section_layout.setSpacing(SPACE_12)

        section_title = QLabel("Appearance")
        section_title.setObjectName("generalSectionTitle")
        apply_scaled_font(section_title, offset=2, weight=QFont.Weight.DemiBold)

        text_section_layout.addWidget(section_title)

        font_label = QLabel("Text size")
        font_label.setObjectName("generalFieldLabel")
        apply_scaled_font(font_label, offset=1, weight=QFont.Weight.Medium)
        self.font_spin = QSpinBox()
        self.font_spin.setRange(8, 20)
        self.font_spin.setSingleStep(1)
        self.font_spin.setMinimumHeight(CONTROL_HEIGHT)
        self.font_spin.setMaximumWidth(180)
        apply_scaled_font(self.font_spin)

        font_row = QFormLayout()
        font_row.setContentsMargins(0, 0, 0, 0)
        font_row.setHorizontalSpacing(SPACE_12)
        font_row.setVerticalSpacing(SPACE_8)
        font_row.setFieldGrowthPolicy(QFormLayout.FieldGrowthPolicy.AllNonFixedFieldsGrow)
        font_row.setLabelAlignment(Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter)
        font_row.addRow(font_label, self.font_spin)

        text_section_layout.addLayout(font_row)
        layout.addWidget(text_section)
        layout.addStretch()

    def _setup_connections_tab(self):
        tab_layout = QVBoxLayout(self.connections_tab)
        tab_layout.setContentsMargins(0, 0, 0, 0)
        tab_layout.setSpacing(0)

        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.Shape.NoFrame)

        content = QWidget()
        layout = QVBoxLayout(content)
        layout.setContentsMargins(SPACE_16, SPACE_16, SPACE_16, SPACE_12)
        layout.setSpacing(SPACE_16)

        self.server_edit = ModernLineEdit()
        self.ws_edit = ModernLineEdit()

        self.fedex_enabled = QCheckBox("Enabled")
        apply_scaled_font(self.fedex_enabled, offset=1, weight=QFont.Weight.Medium)
        self.fedex_api_key_edit = ModernLineEdit("FedEx API Key")
        self.fedex_secret_key_edit = ModernLineEdit("FedEx Secret Key")
        self.fedex_secret_key_edit.setEchoMode(ModernLineEdit.EchoMode.Password)
        self.fedex_base_url_edit = ModernLineEdit("FedEx Base URL (optional)")
        self.fedex_base_url_edit.setPlaceholderText("https://apis.fedex.com or https://apis-sandbox.fedex.com")
        self.test_fedex_btn = ModernButton("Test Connection", "secondary")
        self.test_fedex_btn.setMinimumWidth(140)
        self.test_fedex_btn.clicked.connect(self.test_fedex_connection)
        self.test_fedex_btn.setEnabled(self.is_admin)

        self.mie_trak_server_edit = ModernLineEdit()
        self.mie_trak_server_edit.setText("GUNDMAIN")
        self.mie_trak_server_edit.setReadOnly(True)
        self.mie_trak_database_edit = ModernLineEdit("Database name")

        server_section, server_content = self._create_connection_section("Server")
        self._add_form_row(server_content, "Server URL", self.server_edit)

        ws_section, ws_content = self._create_connection_section("WebSocket")
        self._add_form_row(ws_content, "WebSocket URL", self.ws_edit)

        fedex_section, fedex_content = self._create_connection_section("FedEx")
        fedex_header_row = QHBoxLayout()
        fedex_header_row.setContentsMargins(0, 0, 0, 0)
        fedex_header_row.addStretch()
        fedex_header_row.addWidget(self.fedex_enabled)
        fedex_content.addLayout(fedex_header_row)

        self._add_form_row(fedex_content, "API Key", self.fedex_api_key_edit)
        self._add_form_row(fedex_content, "Secret Key", self.fedex_secret_key_edit)
        self._add_form_row(fedex_content, "Base URL", self.fedex_base_url_edit)

        test_row = QHBoxLayout()
        test_row.setContentsMargins(0, 0, 0, 0)
        test_row.setSpacing(SPACE_8)
        test_row.addStretch()
        test_row.addWidget(self.test_fedex_btn)
        fedex_content.addLayout(test_row)

        layout.addWidget(server_section)
        layout.addWidget(ws_section)
        mie_trak_section, mie_trak_content = self._create_connection_section("Mie Trak")
        self._add_form_row(mie_trak_content, "Server Name", self.mie_trak_server_edit)
        self._add_form_row(mie_trak_content, "Database", self.mie_trak_database_edit)

        layout.addWidget(mie_trak_section)
        layout.addWidget(fedex_section)
        layout.addStretch()

        scroll.setWidget(content)
        tab_layout.addWidget(scroll)

    def _create_connection_section(self, title: str) -> tuple[QFrame, QVBoxLayout]:
        section = QFrame()
        section.setObjectName("connectionSection")

        section_layout = QVBoxLayout(section)
        section_layout.setContentsMargins(SPACE_16, SPACE_12, SPACE_16, SPACE_16)
        section_layout.setSpacing(SPACE_12)

        title_label = QLabel(title)
        title_label.setObjectName("connectionSectionTitle")
        apply_scaled_font(title_label, offset=2, weight=QFont.Weight.DemiBold)

        section_layout.addWidget(title_label)

        content_layout = QVBoxLayout()
        content_layout.setContentsMargins(0, 0, 0, 0)
        content_layout.setSpacing(SPACE_12)
        section_layout.addLayout(content_layout)

        return section, content_layout

    def _add_form_row(self, parent_layout: QVBoxLayout, label_text: str, field: QWidget):
        row = self._create_form_layout()
        self._add_form_field(row, label_text, field)
        parent_layout.addLayout(row)

    def _create_form_layout(self) -> QFormLayout:
        layout = QFormLayout()
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setHorizontalSpacing(SPACE_12)
        layout.setVerticalSpacing(SPACE_8)
        layout.setFieldGrowthPolicy(QFormLayout.FieldGrowthPolicy.AllNonFixedFieldsGrow)
        layout.setRowWrapPolicy(QFormLayout.RowWrapPolicy.DontWrapRows)
        layout.setLabelAlignment(Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter)
        return layout

    def _add_form_field(self, form_layout: QFormLayout, label_text: str, field: QWidget):
        label = QLabel(label_text)
        label.setObjectName("connectionFieldLabel")
        apply_scaled_font(label, offset=1, weight=QFont.Weight.Medium)
        field.setMinimumHeight(CONTROL_HEIGHT)
        form_layout.addRow(label, field)

    def _setup_users_tab(self):
        layout = QVBoxLayout(self.users_tab)
        self.user_management = UserManagementWidget(self.token, parent=self.users_tab)
        layout.addWidget(self.user_management)

    def _apply_dialog_style(self):
        self.setStyleSheet(
            f"""
            QDialog {{
                background-color: {COLOR_SURFACE};
                border: 1px solid {COLOR_BORDER};
                border-radius: {RADIUS_LG}px;
                font-family: "{MODERN_FONT}";
            }}
            QLabel#settingsDialogTitle {{
                color: {COLOR_TEXT_PRIMARY};
            }}
            QFrame#sectionDivider {{
                background-color: {COLOR_BORDER};
                max-height: 1px;
            }}
            QFrame#contentWrapper {{
                background-color: {COLOR_BG_SUBTLE};
                border: 1px solid {COLOR_BORDER};
                border-radius: {RADIUS_LG}px;
            }}
            QFrame#connectionSection {{
                background-color: {COLOR_SURFACE};
                border: 1px solid {COLOR_BORDER};
                border-radius: {RADIUS_MD}px;
            }}
            QFrame#generalSection {{
                background-color: {COLOR_SURFACE};
                border: 1px solid {COLOR_BORDER};
                border-radius: {RADIUS_MD}px;
            }}
            QLabel#connectionSectionTitle {{
                color: {COLOR_TEXT_PRIMARY};
            }}
            QLabel#connectionSectionSubtitle {{
                color: {COLOR_TEXT_SECONDARY};
            }}
            QLabel#generalSectionTitle {{
                color: {COLOR_TEXT_PRIMARY};
            }}
            QLabel#generalSectionSubtitle {{
                color: {COLOR_TEXT_SECONDARY};
            }}
            QFrame#connectionSectionDivider {{
                background-color: {COLOR_BORDER};
                max-height: 1px;
            }}
            QFrame#generalSectionDivider {{
                background-color: {COLOR_BORDER};
                max-height: 1px;
            }}
            QLabel#connectionFieldLabel {{
                color: {COLOR_TEXT_SECONDARY};
                min-width: 118px;
            }}
            QLabel#generalFieldLabel {{
                color: {COLOR_TEXT_SECONDARY};
                min-width: 118px;
            }}
            QCheckBox {{
                spacing: 8px;
                color: {COLOR_TEXT_SECONDARY};
            }}
            QCheckBox::indicator {{
                width: 16px;
                height: 16px;
                border-radius: 4px;
                border: 1px solid {COLOR_BORDER};
                background: {COLOR_SURFACE};
            }}
            QCheckBox::indicator:hover {{
                border-color: #94A3B8;
            }}
            QCheckBox::indicator:checked {{
                border-color: {COLOR_PRIMARY};
                background-color: #DBEAFE;
            }}
            QTabWidget#settingsTabs::pane {{
                border: none;
                background: transparent;
                margin-top: {SPACE_8}px;
            }}
            QTabWidget#settingsTabs::tab-bar {{
                left: 0px;
            }}
            QTabWidget#settingsTabs QTabBar::tab {{
                background: transparent;
                color: {COLOR_TEXT_SECONDARY};
                border: 1px solid transparent;
                border-bottom: 2px solid transparent;
                border-top-left-radius: {RADIUS_MD - 2}px;
                border-top-right-radius: {RADIUS_MD - 2}px;
                padding: {SPACE_8 + 2}px {SPACE_16}px;
                margin-right: {SPACE_8}px;
                margin-bottom: 2px;
                font-weight: 500;
            }}
            QTabWidget#settingsTabs QTabBar::tab:hover:!selected {{
                background: #F8FAFC;
                color: #334155;
            }}
            QTabWidget#settingsTabs QTabBar::tab:selected {{
                background: #EFF6FF;
                color: {COLOR_TEXT_PRIMARY};
                border: 1px solid #BFDBFE;
                border-bottom: 2px solid {COLOR_PRIMARY};
                font-weight: 600;
            }}
            """
        )

    def load_values(self):
        self.server_edit.setText(self.settings_mgr.get_server_url())
        self.ws_edit.setText(self.settings_mgr.get_ws_url())
        self.font_spin.setValue(self.settings_mgr.get_font_size())
        self.mie_trak_server_edit.setText(self.settings_mgr.get_mie_trak_server())
        self.mie_trak_database_edit.setText(self.settings_mgr.get_mie_trak_database())
        response = self.api_client.get_connection_settings()
        if response.is_success():
            fedex = (response.get_data() or {}).get("fedex", {})
            self.fedex_enabled.setChecked(bool(fedex.get("enabled", False)))
            self.fedex_api_key_edit.setText(str(fedex.get("apiKey") or ""))
            self.fedex_base_url_edit.setText(str(fedex.get("baseUrl") or ""))
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

        selected_mie_trak_db = self.mie_trak_database_edit.text().strip()
        if not selected_mie_trak_db:
            QMessageBox.warning(self, "Error", "Mie Trak database is required")
            return

        self.settings_mgr.set_server_url(server)
        self.settings_mgr.set_ws_url(ws)
        new_size = self.font_spin.value()
        self.settings_mgr.set_font_size(new_size)
        self.settings_mgr.set_mie_trak_server(self.mie_trak_server_edit.text().strip() or "GUNDMAIN")
        self.settings_mgr.set_mie_trak_database(selected_mie_trak_db)

        enabled = self.fedex_enabled.isChecked()
        fedex_api_key = self.fedex_api_key_edit.text().strip()
        fedex_secret_key = self.fedex_secret_key_edit.text().strip()
        fedex_base_url = self.fedex_base_url_edit.text().strip()
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

            response = self.api_client.update_fedex_settings(enabled, fedex_api_key, fedex_secret_key, fedex_base_url)
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
