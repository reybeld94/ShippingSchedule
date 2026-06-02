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
    QTableWidget,
    QTableWidgetItem,
    QHeaderView,
    QAbstractItemView,
)
from PyQt6.QtGui import QFont
from PyQt6.QtCore import Qt

from .widgets import ModernButton, ModernComboBox, ModernLineEdit, PasswordLineEdit
from .user_dialog import UserManagementWidget
from core.settings_manager import SettingsManager
from core.config import MODERN_FONT
from core.api_client import RobustApiClient
from core.mie_trak_client import get_mie_trak_databases
from .utils import apply_scaled_font
from .style_tokens import (
    COLOR_BG_SUBTLE,
    COLOR_BORDER,
    COLOR_BORDER_STRONG,
    COLOR_PRIMARY,
    COLOR_PRIMARY_SUBTLE_BG,
    COLOR_PRIMARY_SUBTLE_BORDER,
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
        self.permission_users = []
        self.permission_checkboxes = {}
        self.permission_module_checkboxes = {}


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
            self.permissions_tab = QWidget()
            self._setup_permissions_tab()
            self.tabs.addTab(self.permissions_tab, "Permissions")

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
        if self.is_admin:
            self.apply_permissions_btn = ModernButton("Apply", "primary")
            self.apply_permissions_btn.setMinimumHeight(CONTROL_HEIGHT)
            self.apply_permissions_btn.setMinimumWidth(96)
            self.apply_permissions_btn.clicked.connect(self.apply_permissions)
            btn_layout.addWidget(self.apply_permissions_btn)
            self.tabs.currentChanged.connect(self._sync_permissions_apply_button_visibility)
            self._sync_permissions_apply_button_visibility()
        btn_layout.addWidget(save_btn)

        footer = QFrame()
        footer_layout = QVBoxLayout(footer)
        footer_layout.setContentsMargins(SPACE_8, SPACE_8, SPACE_8, 0)
        footer_layout.setSpacing(0)
        footer_layout.addLayout(btn_layout)

        layout.addWidget(content_wrapper, 1)
        layout.addWidget(footer)

    def _sync_permissions_apply_button_visibility(self):
        """Show Apply only when the Permissions tab is active."""
        if hasattr(self, "apply_permissions_btn"):
            self.apply_permissions_btn.setVisible(self.tabs.currentWidget() is getattr(self, "permissions_tab", None))

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
        self.fedex_enabled.setEnabled(self.is_admin)
        apply_scaled_font(self.fedex_enabled, offset=1, weight=QFont.Weight.Medium)
        self.fedex_api_key_edit = ModernLineEdit("FedEx API Key")
        self.fedex_api_key_edit.setEnabled(self.is_admin)
        self.fedex_secret_key_edit = PasswordLineEdit("FedEx Secret Key")
        self.fedex_secret_key_edit.setEnabled(self.is_admin)
        self.fedex_base_url_edit = ModernLineEdit("FedEx Base URL (optional)")
        self.fedex_base_url_edit.setPlaceholderText("https://apis.fedex.com or https://apis-sandbox.fedex.com")
        self.fedex_base_url_edit.setEnabled(self.is_admin)
        self.test_fedex_btn = ModernButton("Test Connection", "secondary")
        self.test_fedex_btn.setMinimumWidth(140)
        self.test_fedex_btn.clicked.connect(self.test_fedex_connection)
        self.test_fedex_btn.setEnabled(self.is_admin)

        self.mie_trak_server_edit = ModernLineEdit()
        self.mie_trak_server_edit.setText("GUNDMAIN")
        self.mie_trak_server_edit.setReadOnly(True)
        self.mie_trak_database_combo = ModernComboBox()
        self.mie_trak_database_combo.setEditable(True)
        self.mie_trak_refresh_btn = ModernButton("Load Databases", "secondary")
        self.mie_trak_refresh_btn.setMinimumWidth(140)
        self.mie_trak_refresh_btn.clicked.connect(self.load_mie_trak_databases)

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
        self._add_form_row(mie_trak_content, "Database", self.mie_trak_database_combo)
        mie_trak_actions_row = QHBoxLayout()
        mie_trak_actions_row.setContentsMargins(0, 0, 0, 0)
        mie_trak_actions_row.setSpacing(SPACE_8)
        mie_trak_actions_row.addStretch()
        mie_trak_actions_row.addWidget(self.mie_trak_refresh_btn)
        mie_trak_content.addLayout(mie_trak_actions_row)

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

    def _setup_permissions_tab(self):
        layout = QVBoxLayout(self.permissions_tab)
        layout.setContentsMargins(SPACE_16, SPACE_16, SPACE_16, SPACE_12)
        layout.setSpacing(SPACE_16)

        selector_row = QHBoxLayout()
        selector_label = QLabel("User")
        apply_scaled_font(selector_label, offset=1, weight=QFont.Weight.Medium)
        self.permissions_user_combo = ModernComboBox()
        self.permissions_user_combo.currentIndexChanged.connect(self._load_selected_user_permissions)
        selector_row.addWidget(selector_label)
        selector_row.addWidget(self.permissions_user_combo, 1)
        layout.addLayout(selector_row)

        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.Shape.NoFrame)
        content = QWidget()
        content_layout = QVBoxLayout(content)
        content_layout.setContentsMargins(0, 0, 0, 0)
        content_layout.setSpacing(SPACE_16)

        self._add_permission_section(
            content_layout,
            module_key="shipping_schedule",
            title="Schedule",
            rows=[
                ("job_number", "Job Number"),
                ("job_name", "Job Name"),
                ("status", "Job Status"),
                ("description", "Description"),
                ("qc_release", "QC Rel."),
                ("qc_notes", "QC Notes"),
                ("created", "Crated"),
                ("ship_plan", "Ship Plan"),
                ("shipped", "Shipped"),
                ("invoice_number", "Invoice"),
                ("tracking_number", "Tracking #"),
                ("address", "Address"),
                ("shipping_notes", "Shipping Notes"),
            ],
        )
        self._add_permission_section(
            content_layout,
            module_key="sills",
            title="Sills",
            rows=[
                ("material", "Material"),
                ("dimension", "Dimension"),
                ("location", "Location"),
                ("die_number", "Die #"),
                ("type", "Type"),
                ("speed", "Speed"),
                ("width", "Width"),
                ("sales_order", "Sales Order"),
                ("work_order", "Work Order"),
                ("assembly_number", "Assembly Number"),
                ("description", "Description"),
                ("qty", "Qty"),
                ("dimension_needed", "Dimension Needed"),
                ("notes", "Notes"),
                ("week_to_print", "Week to Print"),
                ("sills_delete", "Delete Sills"),
            ],
            extra_rows=[("sills_database", "Sills DB (all fields)")],
            view_subtabs=[("sills_dashboard", "Sills Dashboard")],
        )
        self._add_view_only_module_section(
            content_layout,
            module_key="bom_importer",
            title="BOM Importer",
        )
        content_layout.addStretch()
        scroll.setWidget(content)
        layout.addWidget(scroll, 1)

    def _add_permission_section(self, parent_layout, module_key: str, title: str, rows, extra_rows=None, view_subtabs=None):
        section, content_layout = self._create_connection_section(title)
        header = QHBoxLayout()
        header.setContentsMargins(0, 0, 0, 0)
        module_checkbox = QCheckBox("Visible")
        module_checkbox.setEnabled(self.is_admin)
        self.permission_module_checkboxes[module_key] = module_checkbox
        header.addWidget(QLabel("Module access"))
        header.addStretch()
        header.addWidget(module_checkbox)
        content_layout.addLayout(header)

        table = QTableWidget(0, 2)
        table.setHorizontalHeaderLabels(["Column", "Write"])
        table.horizontalHeader().setSectionResizeMode(0, QHeaderView.ResizeMode.Stretch)
        table.horizontalHeader().setSectionResizeMode(1, QHeaderView.ResizeMode.ResizeToContents)
        table.verticalHeader().setVisible(False)
        table.verticalHeader().setDefaultSectionSize(32)
        table.verticalHeader().setMinimumSectionSize(32)
        table.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        table.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        table.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
        table.setSelectionMode(QAbstractItemView.SelectionMode.NoSelection)
        table.setAlternatingRowColors(True)
        self.permission_checkboxes[module_key] = {}
        for key, label in rows:
            self._add_permission_row(table, module_key, key, label)
        self._size_permission_table_to_contents(table)
        content_layout.addWidget(table)

        if extra_rows or view_subtabs:
            extra_label = QLabel("Sub tabs")
            apply_scaled_font(extra_label, offset=1, weight=QFont.Weight.Medium)
            content_layout.addWidget(extra_label)
            for key, label in (extra_rows or []):
                row = QHBoxLayout()
                row.setContentsMargins(0, 0, 0, 0)
                checkbox = QCheckBox("Write")
                checkbox.setEnabled(self.is_admin)
                self.permission_checkboxes[key] = {key: checkbox}
                row.addWidget(QLabel(label))
                row.addStretch()
                row.addWidget(checkbox)
                content_layout.addLayout(row)
            for key, label in (view_subtabs or []):
                row = QHBoxLayout()
                row.setContentsMargins(0, 0, 0, 0)
                checkbox = QCheckBox("Visible")
                checkbox.setEnabled(self.is_admin)
                # Registered as a module checkbox so the generic apply/collect
                # logic handles its can_view flag (the module has no columns).
                self.permission_module_checkboxes[key] = checkbox
                row.addWidget(QLabel(label))
                row.addStretch()
                row.addWidget(checkbox)
                content_layout.addLayout(row)

        parent_layout.addWidget(section)

    def _add_view_only_module_section(self, parent_layout, module_key: str, title: str):
        """Add a permission section for a module that only has a Visible toggle (no columns)."""
        section, content_layout = self._create_connection_section(title)
        header = QHBoxLayout()
        header.setContentsMargins(0, 0, 0, 0)
        module_checkbox = QCheckBox("Visible")
        module_checkbox.setEnabled(self.is_admin)
        self.permission_module_checkboxes[module_key] = module_checkbox
        self.permission_checkboxes[module_key] = {}
        header.addWidget(QLabel("Module access"))
        header.addStretch()
        header.addWidget(module_checkbox)
        content_layout.addLayout(header)
        parent_layout.addWidget(section)

    def _size_permission_table_to_contents(self, table: QTableWidget):
        """Expand permission tables so column names are readable without nested scrolling."""
        table.resizeColumnsToContents()
        table.resizeRowsToContents()
        row_height = max(table.verticalHeader().defaultSectionSize(), 32)
        rows_height = sum(max(table.rowHeight(row), row_height) for row in range(table.rowCount()))
        table_height = table.horizontalHeader().height() + rows_height + (table.frameWidth() * 2) + SPACE_8
        table.setMinimumHeight(table_height)
        table.setMaximumHeight(table_height)

    def _add_permission_row(self, table, module_key: str, column_key: str, label: str):
        row = table.rowCount()
        table.insertRow(row)
        label_item = QTableWidgetItem(label)
        label_item.setFlags(label_item.flags() & ~Qt.ItemFlag.ItemIsEditable)
        table.setItem(row, 0, label_item)
        checkbox = QCheckBox()
        checkbox.setEnabled(self.is_admin)
        cell = QWidget()
        cell_layout = QHBoxLayout(cell)
        cell_layout.setContentsMargins(0, 0, 0, 0)
        cell_layout.addStretch()
        cell_layout.addWidget(checkbox)
        cell_layout.addStretch()
        table.setCellWidget(row, 1, cell)
        self.permission_checkboxes[module_key][column_key] = checkbox

    def _load_permission_users(self):
        if not self.is_admin or not hasattr(self, "permissions_user_combo"):
            return
        response = self.api_client.get("/users")
        if not response.is_success():
            QMessageBox.warning(self, "Permissions", response.get_error() or "Failed to load users")
            return
        self.permission_users = response.get_data() or []
        self.permissions_user_combo.blockSignals(True)
        self.permissions_user_combo.clear()
        for user in self.permission_users:
            self.permissions_user_combo.addItem(f"{user.get('username')} ({user.get('role')})", user.get("id"))
        self.permissions_user_combo.blockSignals(False)
        self._load_selected_user_permissions()

    def _load_selected_user_permissions(self):
        if not hasattr(self, "permissions_user_combo"):
            return
        user_id = self.permissions_user_combo.currentData()
        if not user_id:
            return
        response = self.api_client.get_user_permissions(int(user_id))
        if not response.is_success():
            QMessageBox.warning(self, "Permissions", response.get_error() or "Failed to load permissions")
            return
        self._apply_permissions_payload(response.get_data() or {})

    def _apply_permissions_payload(self, payload):
        modules = (payload or {}).get("modules", {})
        for module_key, checkbox in self.permission_module_checkboxes.items():
            checkbox.setChecked(bool(modules.get(module_key, {}).get("can_view", True)))
        for module_key, checkboxes in self.permission_checkboxes.items():
            if module_key == "sills_database":
                columns = modules.get("sills_database", {}).get("columns", {})
            else:
                columns = modules.get(module_key, {}).get("columns", {})
            for column_key, checkbox in checkboxes.items():
                checkbox.setChecked(bool(columns.get(column_key, False)))

    def _collect_permissions_payload(self):
        modules = {}
        for module_key, checkbox in self.permission_module_checkboxes.items():
            columns = {
                column_key: column_checkbox.isChecked()
                for column_key, column_checkbox in self.permission_checkboxes.get(module_key, {}).items()
            }
            modules[module_key] = {"can_view": checkbox.isChecked(), "columns": columns}
        sills_db_checkbox = self.permission_checkboxes.get("sills_database", {}).get("sills_database")
        modules["sills_database"] = {
            "can_view": self.permission_module_checkboxes.get("sills", QCheckBox()).isChecked(),
            "columns": {"sills_database": bool(sills_db_checkbox and sills_db_checkbox.isChecked())},
        }
        return {"modules": modules}

    def _save_permissions(self, show_success: bool = False) -> bool:
        if not self.is_admin or not hasattr(self, "permissions_user_combo"):
            return True
        user_id = self.permissions_user_combo.currentData()
        if not user_id:
            return True
        response = self.api_client.update_user_permissions(int(user_id), self._collect_permissions_payload())
        if not response.is_success():
            QMessageBox.warning(self, "Permissions", response.get_error() or "Failed to save permissions")
            return False
        self._apply_permissions_payload(response.get_data() or {})
        if show_success:
            QMessageBox.information(self, "Permissions", "Permissions applied successfully.")
        return True

    def apply_permissions(self):
        """Save the selected user's permissions without closing the settings dialog."""
        self._save_permissions(show_success=True)

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
                border-color: {COLOR_BORDER_STRONG};
            }}
            QCheckBox::indicator:checked {{
                border-color: {COLOR_PRIMARY};
                background-color: {COLOR_PRIMARY};
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
                background: {COLOR_BG_SUBTLE};
                color: {COLOR_TEXT_PRIMARY};
            }}
            QTabWidget#settingsTabs QTabBar::tab:selected {{
                background: {COLOR_PRIMARY_SUBTLE_BG};
                color: {COLOR_TEXT_PRIMARY};
                border: 1px solid {COLOR_PRIMARY_SUBTLE_BORDER};
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
        self.mie_trak_database_combo.clear()
        saved_database = self.settings_mgr.get_mie_trak_database()
        self.mie_trak_database_combo.addItem(saved_database)
        self.mie_trak_database_combo.setCurrentText(saved_database)
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
        self._load_permission_users()

    def load_mie_trak_databases(self):
        server = self.mie_trak_server_edit.text().strip() or "GUNDMAIN"
        current_database = self.mie_trak_database_combo.currentText().strip()
        try:
            databases = get_mie_trak_databases(server=server)
        except Exception as exc:
            QMessageBox.warning(
                self,
                "Mie Trak",
                f"Could not load databases from {server}: {exc}",
            )
            return

        self.mie_trak_database_combo.blockSignals(True)
        self.mie_trak_database_combo.clear()
        self.mie_trak_database_combo.addItems(databases)
        if current_database:
            self.mie_trak_database_combo.setCurrentText(current_database)
        self.mie_trak_database_combo.blockSignals(False)
        QMessageBox.information(self, "Mie Trak", f"{len(databases)} databases loaded.")

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

        selected_mie_trak_db = self.mie_trak_database_combo.currentText().strip()
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

            if not self._save_permissions():
                return

        app = QApplication.instance()
        if app is not None:
            font = app.font()
            font.setFamily(MODERN_FONT)
            font.setPointSize(new_size)
            app.setFont(font)
        self.accept()
