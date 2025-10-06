# ui/main_window.py - Ventana principal con diseño profesional
import json
from datetime import datetime, date
import os
import textwrap
from html import escape
from .utils import show_popup_notification, apply_scaled_font, refresh_scaled_fonts, get_base_font_size
from core.settings_manager import SettingsManager
from core.api_client import RobustApiClient
from core.mie_trak_client import get_mie_trak_address
from PyQt6.QtWidgets import (
    QApplication,
    QMainWindow,
    QWidget,
    QVBoxLayout,
    QHBoxLayout,
    QTableWidget,
    QTableWidgetItem,
    QLabel,
    QMessageBox,
    QHeaderView,
    QFrame,
    QStatusBar,
    QDialog,
    QTabWidget,
    QStyle,
    QFileDialog,
    QMenu,
    QProgressDialog,
)
from PyQt6.QtCore import (
    Qt,
    QTimer,
    QThread,
    pyqtSignal,
    QStandardPaths,
    QUrl,
    QPoint,
)
from PyQt6.QtGui import QFont, QColor, QPixmap, QPalette, QIcon, QDesktopServices, QBrush

# Imports locales
from .widgets import ModernButton, ModernLineEdit
from .date_delegate import DateDelegate
from .date_filter_dialog import DateFilterPopup
from .date_filter_header import DateFilterHeader
from .settings_dialog import SettingsDialog
from core.websocket_client import WebSocketClient
from core.config import (
    get_server_url,
    WINDOW_WIDTH,
    WINDOW_HEIGHT,
    MODERN_FONT,
    LOGO_PATH,
    ICON_PATH,
)

class ShipmentLoader(QThread):
    """Thread para cargar datos en background"""
    data_loaded = pyqtSignal(list)
    error_occurred = pyqtSignal(str)

    def __init__(self, api_client):
        super().__init__()
        self.api_client = api_client

    def run(self):
        try:
            api_response = self.api_client.get_shipments()
            if api_response.is_success():
                shipments = api_response.get_data()
                self.data_loaded.emit(shipments)
            else:
                self.error_occurred.emit(api_response.get_error())
        except Exception as e:
            self.error_occurred.emit(f"Unexpected error: {str(e)}")


class ShipPlanItem(QTableWidgetItem):
    """Item de tabla que ordena fechas colocando los vacíos al final."""

    def __lt__(self, other):  # type: ignore[override]
        def parse(text: str):
            text = text.strip()
            if not text or text == "-":
                return None
            for fmt in ("%m/%d/%y", "%m/%d/%Y"):
                try:
                    return datetime.strptime(text, fmt)
                except ValueError:
                    continue
            return None

        self_date = parse(self.text())
        other_date = parse(other.text())

        if self_date and other_date:
            return self_date < other_date
        if self_date and not other_date:
            return True
        if not self_date and other_date:
            return False
        return QTableWidgetItem.__lt__(self, other)

class ModernShippingMainWindow(QMainWindow):
    def __init__(self, token, user_info):
        super().__init__()
        self.token = token
        self.user_info = user_info
        self.shipments = []

        self.api_client = RobustApiClient(
            base_url=get_server_url(),
            token=self.token,
            max_retries=3,
            timeout=10,
        )

        self.is_admin = self.user_info.get("role") == "admin"
        self.read_only = self.user_info.get("role") == "read"

        # Manage persistent UI settings
        self.settings_mgr = SettingsManager()
        # Loaded shipment color mappings for persistence
        self.shipment_colors = {
            "active": self.settings_mgr.load_shipment_colors("active"),
            "history": self.settings_mgr.load_shipment_colors("history"),
        }

        # Cache para optimización
        self._active_shipments = []
        self._history_shipments = []
        self._last_filter_text = ""
        self._tables_populated = {"active": False, "history": False}
        self.date_filters = {
            "active": self.settings_mgr.load_date_filters("active"),
            "history": self.settings_mgr.load_date_filters("history"),
        }
        self._base_header_labels: dict[str, list[str]] = {}
        self.date_filter_headers = {}

        # Mapa de columna a campo de API para ediciones inline
        self.column_field_map = {
            1: "job_name",
            2: "description",
            3: "qc_release",
            4: "qc_notes",
            5: "created",
            6: "ship_plan",
            7: "shipped",
            8: "invoice_number",
            9: "shipping_notes",
        }

        # Mapeo de índice de columna a nombre de campo para colores
        self.column_to_field_name = {
            0: "job_number",
            1: "job_name",
            2: "description",
            3: "qc_release",
            4: "qc_notes",
            5: "created",
            6: "ship_plan",
            7: "shipped",
            8: "invoice_number",
            9: "shipping_notes",
        }

        # Flag para evitar disparar eventos al poblar tablas
        self.updating_table = False
        
        print(f"Inicializando ventana principal para usuario: {user_info['username']}")
        
        self.setWindowTitle("Shipping Schedule")
        if os.path.exists(ICON_PATH):
            self.setWindowIcon(QIcon(ICON_PATH))
        self.setGeometry(100, 100, WINDOW_WIDTH, WINDOW_HEIGHT)
        self.showMaximized()
        try:
            self.setup_ui()
            self.apply_global_font_preferences()
            self.setup_websocket()

            # Cargar datos en background
            self.load_shipments_async()
            
            # Timer para actualizar status
            self.status_timer = QTimer()
            self.status_timer.timeout.connect(self.update_status)
            self.status_timer.start(10000)  # Cada 10 segundos
            
            print("Ventana principal inicializada exitosamente")
        except Exception as e:
            print(f"Error inicializando ventana principal: {e}")
            import traceback
            traceback.print_exc()
    
    def setup_ui(self):
        """Configurar interfaz de usuario profesional"""
        try:
            # Widget central
            central_widget = QWidget()
            self.setCentralWidget(central_widget)
            
            # Layout principal
            main_layout = QVBoxLayout(central_widget)
            main_layout.setContentsMargins(15, 15, 15, 15)
            main_layout.setSpacing(12)
            
            # Header profesional
            self.create_professional_header(main_layout)
            
            # Toolbar
            self.create_professional_toolbar(main_layout)
            
            # Sistema de tabs
            self.create_professional_tabs(main_layout)
            
            # Status bar
            self.create_professional_status_bar()
            
            # Aplicar tema profesional
            self.apply_professional_theme()
            
            print("UI profesional configurada exitosamente")
        except Exception as e:
            print(f"Error configurando UI: {e}")
            raise

    def apply_global_font_preferences(self):
        """Apply the persisted font size across the interface."""
        app = QApplication.instance()
        if app is not None:
            base_size = self.settings_mgr.get_font_size()
            font = app.font()
            font.setFamily(MODERN_FONT)
            font.setPointSize(base_size)
            app.setFont(font)

        refresh_scaled_fonts(self)

        for table in getattr(self, "active_table", None), getattr(self, "history_table", None):
            if table is not None:
                self._apply_table_style(table)
                self._refresh_table_item_fonts(table)
    
    def create_professional_header(self, layout):
        """Crear header profesional con logo"""
        header_frame = QFrame()
        header_frame.setFixedHeight(85)
        header_frame.setStyleSheet("""
            QFrame {
                background-color: #FFFFFF;
                border: none;
                
            }
        """)
        
        header_layout = QHBoxLayout(header_frame)
        header_layout.setContentsMargins(25, 15, 25, 15)
        
        # Logo y título
        logo_title_layout = QHBoxLayout()
        logo_title_layout.setSpacing(15)
        
        # Intentar cargar el logo
        logo_label = QLabel()
        if os.path.exists(LOGO_PATH):
            pixmap = QPixmap(LOGO_PATH)
            # Escalar el logo manteniendo aspecto
            scaled_pixmap = pixmap.scaled(50, 50, Qt.AspectRatioMode.KeepAspectRatio, Qt.TransformationMode.SmoothTransformation)
            logo_label.setPixmap(scaled_pixmap)
        else:
            # Fallback: usar texto
            logo_label.setText("LOGO")
            fallback_size = max(8, get_base_font_size() + 2)
            logo_label.setStyleSheet(
                f"""
                background-color: #374151;
                color: white;
                font-weight: bold;
                padding: 15px;
                border-radius: 4px;
                font-size: {fallback_size}px;
            """
            )
            logo_label.setFixedSize(50, 50)
            logo_label.setAlignment(Qt.AlignmentFlag.AlignCenter)

        # Información de la aplicación
        title_layout = QVBoxLayout()
        title_layout.setSpacing(2)

        title_label = QLabel("Shipping Schedule")
        apply_scaled_font(title_label, offset=8, weight=QFont.Weight.DemiBold)
        title_label.setStyleSheet("color: #1F2937; letter-spacing: -0.5px;")

        subtitle_label = QLabel("Dashboard")
        apply_scaled_font(subtitle_label, offset=1)
        subtitle_label.setStyleSheet("color: #6B7280;")
        
        title_layout.addWidget(title_label)
        title_layout.addWidget(subtitle_label)
        
        logo_title_layout.addWidget(logo_label)
        logo_title_layout.addLayout(title_layout)
        
        # Información del usuario (derecha)
        user_info_layout = QVBoxLayout()
        user_info_layout.setSpacing(3)
        
        user_name_label = QLabel(f"{self.user_info['username']}")
        apply_scaled_font(user_name_label, offset=2, weight=QFont.Weight.Medium)
        user_name_label.setStyleSheet("color: #1F2937;")
        user_name_label.setAlignment(Qt.AlignmentFlag.AlignRight)
        
        role_map = {
            "admin": "System Administrator",
            "write": "Write Access",
            "read": "Read Only"
        }
        role_text = role_map.get(self.user_info.get("role"), "Read Only")
        user_role_label = QLabel(role_text)
        apply_scaled_font(user_role_label, offset=-1)
        user_role_label.setStyleSheet("color: #6B7280;")
        user_role_label.setAlignment(Qt.AlignmentFlag.AlignRight)
        
        # Connection status
        connection_layout = QHBoxLayout()
        connection_layout.setSpacing(5)
        
        self.connection_indicator = QLabel("●")
        apply_scaled_font(self.connection_indicator, offset=2)
        self.connection_indicator.setStyleSheet("color: #10B981;")

        connection_text = QLabel("Connected")
        apply_scaled_font(connection_text, offset=-1)
        connection_text.setStyleSheet("color: #6B7280;")

        # Settings button
        self.settings_btn = ModernButton("", "secondary")
        self.settings_btn.setIcon(
            self.style().standardIcon(QStyle.StandardPixmap.SP_FileDialogDetailedView)
        )
        self.settings_btn.setFixedSize(30, 30)
        self.settings_btn.clicked.connect(self.open_settings_dialog)

        connection_layout.addStretch()
        connection_layout.addWidget(self.connection_indicator)
        connection_layout.addWidget(connection_text)
        connection_layout.addWidget(self.settings_btn)
        
        user_info_layout.addWidget(user_name_label)
        user_info_layout.addWidget(user_role_label)
        user_info_layout.addLayout(connection_layout)
        
        header_layout.addLayout(logo_title_layout)
        header_layout.addStretch()
        header_layout.addLayout(user_info_layout)
        
        layout.addWidget(header_frame)
    
    def create_professional_toolbar(self, layout):
        """Crear toolbar profesional"""
        toolbar_frame = QFrame()
        toolbar_frame.setFixedHeight(65)
        toolbar_frame.setStyleSheet("""
            QFrame {
                background: #FFFFFF;
                border: 1px solid #E5E7EB;
                border-radius: 6px;
            }
        """)
        
        toolbar_layout = QHBoxLayout(toolbar_frame)
        toolbar_layout.setContentsMargins(20, 12, 20, 12)
        toolbar_layout.setSpacing(12)
        
        # Botones principales
        self.add_btn = ModernButton("New Shipment", "primary")
        self.add_btn.clicked.connect(self.add_shipment)
        
        
        self.delete_btn = ModernButton("Delete", "danger")
        self.delete_btn.clicked.connect(self.delete_shipment)
        self.delete_btn.setEnabled(False)

        if self.read_only:
            self.add_btn.setEnabled(False)
            self.delete_btn.setEnabled(False)
        
        # Separador
        separator = QFrame()
        separator.setFrameShape(QFrame.Shape.VLine)
        separator.setStyleSheet("color: #E5E7EB;")
        separator.setFixedHeight(25)
        
        # Búsqueda
        search_layout = QHBoxLayout()
        search_layout.setSpacing(8)
        
        search_label = QLabel("Search:")
        apply_scaled_font(search_label, weight=QFont.Weight.Medium)
        search_label.setStyleSheet("color: #374151;")
        
        self.search_edit = ModernLineEdit("Search shipments...")
        self.search_edit.setMinimumWidth(280)
        
        # Timer para debounce en búsqueda
        self.search_timer = QTimer()
        self.search_timer.setSingleShot(True)
        self.search_timer.timeout.connect(self.perform_filter)
        self.search_edit.textChanged.connect(lambda: self.search_timer.start(500))
        
        search_layout.addWidget(search_label)
        search_layout.addWidget(self.search_edit)
        
        # Refresh button
        self.refresh_btn = ModernButton("Refresh", "secondary")
        self.refresh_btn.clicked.connect(self.load_shipments_async)

        # Print button to export table contents
        self.print_btn = ModernButton("Print", "secondary")
        self.print_btn.clicked.connect(self.print_table_to_pdf)
        
        # Agregar todo al toolbar
        toolbar_layout.addWidget(self.add_btn)
        toolbar_layout.addWidget(self.delete_btn)
        toolbar_layout.addWidget(separator)
        toolbar_layout.addLayout(search_layout)
        toolbar_layout.addStretch()
        if self.is_admin:
            self.user_btn = ModernButton("Users", "secondary")
            self.user_btn.clicked.connect(self.open_user_management)
            toolbar_layout.addWidget(self.user_btn)
        toolbar_layout.addWidget(self.refresh_btn)
        toolbar_layout.addWidget(self.print_btn)

        layout.addWidget(toolbar_frame)
    
    def create_professional_tabs(self, layout):
        """Crear sistema de tabs profesional"""
        tabs_container = QFrame()
        tabs_container.setStyleSheet("""
            QFrame {
                background: #FFFFFF;
                border: 1px solid #E5E7EB;
                border-radius: 6px;
            }
        """)
        
        tabs_layout = QVBoxLayout(tabs_container)
        tabs_layout.setContentsMargins(1, 1, 1, 1)
        
        # Widget de tabs
        self.tab_widget = QTabWidget()
        tab_font_size = max(8, get_base_font_size() + 3)
        self.tab_widget.setStyleSheet(
            textwrap.dedent(
                f"""
                QTabWidget::pane {{
                    border: none;
                    background: #FFFFFF;
                    border-top: 1px solid #E5E7EB;
                }}
                QTabBar::tab {{
                    background: #F9FAFB;
                    color: #6B7280;
                    padding: 14px 28px;
                    margin-right: 1px;
                    border-top-left-radius: 6px;
                    border-top-right-radius: 6px;
                    font-weight: 500;
                    font-size: {tab_font_size}px;
                    min-width: 120px;
                    border: 1px solid #E5E7EB;
                    border-bottom: none;
                }}
                QTabBar::tab:selected {{
                    background: #FFFFFF;
                    color: #1F2937;
                    border-bottom: 2px solid #3B82F6;
                    font-weight: 600;
                }}
                QTabBar::tab:hover:!selected {{
                    background: #F3F4F6;
                    color: #374151;
                }}
            """
            )
        )
        
        # Tab 1: Active Shipments
        self.active_widget = QWidget()
        active_layout = QVBoxLayout(self.active_widget)
        active_layout.setContentsMargins(8, 8, 8, 8)
        
        self.active_table = QTableWidget()
        self.setup_professional_table(self.active_table, "active")
        active_layout.addWidget(self.active_table)
        
        self.tab_widget.addTab(self.active_widget, "Active Shipments")
        
        # Tab 2: History
        self.history_widget = QWidget()
        history_layout = QVBoxLayout(self.history_widget)
        history_layout.setContentsMargins(8, 8, 8, 8)
        
        self.history_table = QTableWidget()
        self.setup_professional_table(self.history_table, "history")
        history_layout.addWidget(self.history_table)
        
        self.tab_widget.addTab(self.history_widget, "Shipment History")
        
        # Conectar cambio de tab
        self.tab_widget.currentChanged.connect(self.on_tab_changed)
        
        tabs_layout.addWidget(self.tab_widget)
        layout.addWidget(tabs_container)
    
    def setup_professional_table(self, table, name):
        """Configurar tabla con estilo profesional y restaurar ancho de columnas"""
        columns = [
            "Job Number", "Job Name", "Description",
            "QC Release", "QC Notes", "Crated", "Ship Plan", "Shipped",
            "Invoice Number", "Notes"
        ]
        
        table.setColumnCount(len(columns))
        table.setHorizontalHeaderLabels(columns)
        self._base_header_labels[name] = list(columns)

        date_columns = self.get_date_filter_columns(name)
        header = DateFilterHeader(table, date_columns)
        table.setHorizontalHeader(header)
        header.filter_requested.connect(
            lambda column, pos, tbl=table, nm=name: self.open_date_filter_popup(tbl, nm, column, pos)
        )
        self.date_filter_headers[name] = header
        
        # Estilo profesional para la tabla
        self._apply_table_style(table)
        
        # Configuración
        table.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)
        table.setAlternatingRowColors(False)
        table.verticalHeader().setVisible(False)
        table.setShowGrid(True)
        table.setWordWrap(True)
        # Ajustar altura automáticamente para permitir que el texto se envuelva
        # en múltiples líneas cuando sea necesario
        table.verticalHeader().setSectionResizeMode(QHeaderView.ResizeMode.ResizeToContents)
        
        # Optimización de performance
        table.setVerticalScrollMode(QTableWidget.ScrollMode.ScrollPerPixel)
        table.setHorizontalScrollMode(QTableWidget.ScrollMode.ScrollPerPixel)
        
        # Configurar columnas como ajustables por el usuario
        header = table.horizontalHeader()
        for i in range(len(columns)):
            header.setSectionResizeMode(i, QHeaderView.ResizeMode.Interactive)

        # Delegates para campos de fecha
        date_delegate = DateDelegate(table)
        for col in (3, 5, 6, 7):
            table.setItemDelegateForColumn(col, date_delegate)

        # Restaurar anchos guardados si existen
        self.restore_column_widths(table, name)

        # Guardar anchos cada vez que se ajusta alguna columna
        header.sectionResized.connect(lambda *args, tbl=table, nm=name: self.save_table_column_widths(tbl, nm))

        # Eventos
        table.selectionModel().selectionChanged.connect(self.on_selection_changed)
        table.itemChanged.connect(self.on_item_changed)
        table.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
        table.customContextMenuRequested.connect(
            lambda pos, tbl=table, nm=name: self.show_cell_menu(tbl, nm, pos)
        )

        # Habilitar ordenamiento por columnas
        table.setSortingEnabled(True)
        header.setSortIndicatorShown(True)

        # Restaurar estado visual de filtros si ya existen
        existing_filters = self.date_filters.get(name, {})
        for column, data in existing_filters.items():
            header.set_filter_active(column, True)
            self.update_header_filter_state(table, name, column, True, data)

    def _apply_table_style(self, table):
        """Apply the dynamic table styling based on the global font size."""
        table_font_size = max(8, get_base_font_size() + 2)
        header_font_size = max(8, get_base_font_size() + 3)
        table.setStyleSheet(
            f"""
    QTableWidget {{
        font-family: '{MODERN_FONT}';
        font-size: {table_font_size}px;
        background: #FFFFFF;
        gridline-color: #E5E7EB;
        border: 1px solid #E5E7EB;
    }}
    QHeaderView::section {{
        background-color: #E5E5E5;
        color: #000000;
        padding: 12px 8px;
        border: none;
        border-bottom: 2px solid #E5E7EB;
        border-right: 1px solid #E5E7EB;
        font-weight: 600;
        font-size: {header_font_size}px;
        text-transform: uppercase;
    }}
        """
        )

    def _refresh_table_item_fonts(self, table):
        """Update table item fonts according to the active preference."""
        base_size = get_base_font_size()
        for row in range(table.rowCount()):
            for col in range(table.columnCount()):
                item = table.item(row, col)
                if item is None:
                    continue
                offset = item.data(Qt.ItemDataRole.UserRole + 5)
                try:
                    offset_value = int(offset)
                except (TypeError, ValueError):
                    offset_value = 0

                font = item.font()
                font.setFamily(MODERN_FONT)
                font.setPointSize(max(6, base_size + offset_value))
                item.setFont(font)

    def save_table_column_widths(self, table, name):
        """Guardar anchos actuales de la tabla."""
        widths = [table.columnWidth(i) for i in range(table.columnCount())]
        self.settings_mgr.save_column_widths(name, widths)

    def restore_column_widths(self, table, name):
        """Aplicar anchos previamente guardados si existen."""
        widths = self.settings_mgr.load_column_widths(name, table.columnCount())
        for i, width in enumerate(widths):
            if width is not None:
                table.setColumnWidth(i, width)

    def update_header_filter_state(self, table, name, column, active, filter_data=None):
        """Update the visual indicator of a column header when a filter is applied."""

        base_labels = self._base_header_labels.get(name)
        if not base_labels or column >= len(base_labels):
            return

        header_item = table.horizontalHeaderItem(column)
        if header_item is None:
            return

        base_text = base_labels[column]
        header_item.setText(f"{base_text} 🔽" if active else base_text)
        header_item.setForeground(QBrush(QColor("#1D4ED8" if active else "#000000")))

        if active:
            tooltip = self._build_column_filter_tooltip(filter_data)
            header_item.setToolTip(tooltip)
        else:
            header_item.setToolTip("")

    def _build_column_filter_tooltip(self, filter_data):
        if not filter_data:
            return "Filter applied"

        dates = filter_data.get("dates") if isinstance(filter_data, dict) else None
        if not dates:
            date_summary = "No specific dates selected"
        else:
            sorted_dates = sorted(dates)
            preview = [dt.strftime("%b %d, %Y") for dt in sorted_dates[:5]]
            if len(sorted_dates) > 5:
                preview.append(f"(+{len(sorted_dates) - 5} more)")
            date_summary = ", ".join(preview)

        include_blank = True
        if isinstance(filter_data, dict):
            include_blank = bool(filter_data.get("include_blank", True))

        blank_text = "Including blanks" if include_blank else "Excluding blanks"
        return f"Dates: {date_summary}\n{blank_text}"

    def get_date_filter_columns(self, name):
        """Return the indices of columns that support the date filter."""
        return [3, 5, 6, 7]

    def open_date_filter_popup(self, table, name, column, global_pos):
        """Open an inline hierarchical date filter for the specified column."""
        date_values, has_blank = self.collect_column_dates(table, column)
        if not date_values and not has_blank:
            return

        current_filter = self.date_filters.get(name, {}).get(column)
        selected_dates = None
        include_blank = True
        if current_filter:
            selected_dates = current_filter.get("dates")
            include_blank = current_filter.get("include_blank", True)

        table_filters = self.date_filters.setdefault(name, {})

        popup = DateFilterPopup(
            self,
            available_dates=date_values,
            has_blank=has_blank,
            selected_dates=selected_dates,
            include_blank=include_blank,
        )

        popup_size = popup.sizeHint()
        result = popup.exec_at(QPoint(global_pos.x() - popup_size.width(), global_pos.y()))

        if result is None:
            return

        selected, include_blank_selection = result

        header = self.date_filter_headers.get(name)
        if selected is None and include_blank_selection:
            if column in table_filters:
                table_filters.pop(column, None)
            if header:
                header.set_filter_active(column, False)
            self.update_header_filter_state(table, name, column, False)
        else:
            if selected is None:
                # All dates selected but blanks filtered out
                selected = set(date_values)
            table_filters[column] = {
                "dates": set(selected),
                "include_blank": include_blank_selection,
            }
            if header:
                header.set_filter_active(column, True)
            self.update_header_filter_state(table, name, column, True, table_filters[column])

        self.persist_date_filters(name)
        self.apply_date_filters_to_table(table, name)

    def persist_date_filters(self, name):
        """Persist current date filter configuration for a table."""

        filters = self.date_filters.get(name, {})
        self.settings_mgr.save_date_filters(name, filters)

    def collect_column_dates(self, table, column):
        """Gather unique date values from a table column."""
        dates = set()
        has_blank = False
        for row in range(table.rowCount()):
            item = table.item(row, column)
            value = item.text().strip() if item and item.text() else ""
            parsed = self.parse_table_date_value(value)
            if parsed:
                dates.add(parsed)
            else:
                if value:
                    # Non-empty but unparsable values treated as blanks for filtering
                    has_blank = True
                else:
                    has_blank = True
        return sorted(dates), has_blank

    def parse_table_date_value(self, value):
        """Parse a date value from table text."""
        if isinstance(value, datetime):
            return value.date()
        if isinstance(value, date):
            return value

        text = str(value).strip()
        if not text or text in {"-", "--", "None", "null"}:
            return None

        for fmt in ("%m/%d/%Y", "%m/%d/%y", "%Y-%m-%d"):
            try:
                return datetime.strptime(text, fmt).date()
            except ValueError:
                continue
        return None

    def apply_date_filters_to_table(self, table, name):
        """Apply the configured date filters to the given table."""
        active_filters = self.date_filters.get(name, {})
        if not active_filters:
            for row in range(table.rowCount()):
                table.setRowHidden(row, False)
            return

        for row in range(table.rowCount()):
            visible = True
            for column, filter_data in active_filters.items():
                if not self.row_matches_date_filter(table, row, column, filter_data):
                    visible = False
                    break
            table.setRowHidden(row, not visible)

    def row_matches_date_filter(self, table, row, column, filter_data):
        item = table.item(row, column)
        text = item.text().strip() if item and item.text() else ""
        parsed = self.parse_table_date_value(text)

        if parsed is None:
            return filter_data.get("include_blank", True)

        allowed_dates = filter_data.get("dates")
        if not allowed_dates:
            return False
        return parsed in allowed_dates

    def get_shipment_id_from_row(self, table, row):
        """Obtener shipment_id de una fila de la tabla."""
        job_item = table.item(row, 0)
        if job_item:
            shipment = job_item.data(Qt.ItemDataRole.UserRole)
            if shipment:
                return shipment.get('id')
        return None

    def show_cell_menu(self, table, name, pos):
        item = table.itemAt(pos)
        if not item:
            return
        menu = QMenu(table)
        update_action = menu.addAction("Update")
        clear_action = menu.addAction("Clear Mark")
        address_action = menu.addAction("Show Mie Trak Address")
        row = item.row()

        status_actions = {}
        if not self.read_only:
            job_item = table.item(row, 0)
            shipment = job_item.data(Qt.ItemDataRole.UserRole) if job_item else None
            current_status = shipment.get("status") if shipment else ""
            status_menu = menu.addMenu("Status")
            status_map = {
                "partial_release": "Partial Release",
                "final_release": "Final Release",
                "rejected": "Rejected",
            }
            for code, text in status_map.items():
                act = status_menu.addAction(text)
                act.setCheckable(True)
                if code == current_status:
                    act.setChecked(True)
                status_actions[act] = code

        action = menu.exec(table.viewport().mapToGlobal(pos))
        if action == update_action:
            shipment_id = self.get_shipment_id_from_row(table, item.row())
            field_name = self.column_to_field_name.get(item.column())
            if shipment_id and field_name:
                item.setBackground(QColor("#1E90FF"))
                self.shipment_colors[name][(shipment_id, field_name)] = "#1E90FF"
                self.save_shipment_colors(name)
        elif action == clear_action:
            shipment_id = self.get_shipment_id_from_row(table, item.row())
            field_name = self.column_to_field_name.get(item.column())
            if shipment_id and field_name:
                item.setBackground(QColor("transparent"))
                self.shipment_colors[name].pop((shipment_id, field_name), None)
                self.save_shipment_colors(name)
        elif action == address_action:
            job_item = table.item(row, 0)
            job_number = job_item.text() if job_item else ""
            if job_number:
                self.show_mie_trak_address(job_number)
        elif action in status_actions:
            self.change_status(table, row, status_actions[action])

    def change_status(self, table, row, new_status):
        """Change shipment status with flexible version control"""
        if self.read_only:
            return

        job_item = table.item(row, 0)
        shipment = job_item.data(Qt.ItemDataRole.UserRole) if job_item else None
        if not shipment or shipment.get("status") == new_status:
            return

        def update_ui_after_success(updated_data):
            """Helper to update UI consistently"""
            shipment["status"] = new_status
            shipment['version'] = updated_data.get('version', shipment.get('version', 1) + 1)
            shipment['last_modified_by'] = self.user_info.get('id')
            job_item.setData(Qt.ItemDataRole.UserRole, shipment)
            
            # Update visual status
            if new_status == "partial_release":
                job_item.setBackground(QColor("#FDE68A"))  # Amarillo más intenso - mismo que inicial
            elif new_status == "final_release":
                job_item.setBackground(QColor("#BBF7D0"))   # Verde más intenso - mismo que inicial
            elif new_status == "rejected":
                job_item.setBackground(QColor("#FED7AA"))   # Soft Orange más intenso - mismo que inicial
            else:
                job_item.setBackground(QColor("transparent"))
            
            self.show_toast("Status updated successfully", color="#16A34A")

        try:
            # Intentar con la versión actual conocida
            current_version = int(shipment.get('version', 1) or 1)
            
            api_response = self.api_client.update_shipment_with_version(
                shipment['id'],
                {"status": new_status},
                current_version
            )

            if api_response.is_success():
                updated_shipment = api_response.get_data()
                update_ui_after_success(updated_shipment)
                return

            elif api_response.status_code == 409:
                # Conflicto de versión - obtener la versión más reciente automáticamente
                print(f"Version conflict detected for shipment {shipment['id']}, attempting to resolve...")
                
                latest_resp = self.api_client.get_shipment_by_id(shipment['id'])
                if latest_resp.is_success():
                    latest_shipment = latest_resp.get_data()
                    latest_version = int(latest_shipment.get('version', current_version))
                    
                    # Actualizar datos locales con la información más reciente
                    for key, value in latest_shipment.items():
                        if key in shipment:
                            shipment[key] = value
                    
                    # Intentar nuevamente con la versión correcta
                    retry_response = self.api_client.update_shipment_with_version(
                        shipment['id'], 
                        {"status": new_status}, 
                        latest_version
                    )
                    
                    if retry_response.is_success():
                        updated_shipment = retry_response.get_data()
                        update_ui_after_success(updated_shipment)
                        print(f"Successfully resolved version conflict for shipment {shipment['id']}")
                        return
                    else:
                        print(f"Retry failed: {retry_response.get_error()}")
                        self.show_error(f"Failed to update status after resolving conflict: {retry_response.get_error()}")
                else:
                    print(f"Could not fetch latest version: {latest_resp.get_error()}")
                    self.show_error("Could not resolve version conflict. Please refresh and try again.")
            else:
                self.show_error(f"Failed to update status: {api_response.get_error()}")

        except Exception as e:
            print(f"Exception in change_status: {str(e)}")
            self.show_error(f"Failed to update status: {str(e)}")

    def show_mie_trak_address(self, job_number: str):
        """Fetch and display Mie Trak address for a job directly from DB"""
        try:
            address = get_mie_trak_address(job_number)
            QMessageBox.information(
                self, "Mie Trak Address", address or "No address found"
            )
        except Exception as e:
            self.show_error(str(e))

    def save_shipment_colors(self, name):
        """Guardar colores de shipments."""
        self.settings_mgr.save_shipment_colors(name, self.shipment_colors[name])

    def save_cell_colors(self, name):
        """DEPRECATED: Use save_shipment_colors instead."""
        pass

    def apply_saved_cell_colors(self, table, name):
        """Aplicar colores guardados basados en shipment_id y field_name."""
        for row in range(table.rowCount()):
            shipment_id = self.get_shipment_id_from_row(table, row)
            if not shipment_id:
                continue

            for col in range(table.columnCount()):
                field_name = self.column_to_field_name.get(col)
                if not field_name:
                    continue

                color = self.shipment_colors.get(name, {}).get((shipment_id, field_name))
                if color:
                    item = table.item(row, col)
                    if item:
                        item.setBackground(QColor(color))
    
    def create_professional_status_bar(self):
        """Crear status bar profesional"""
        self.status_bar = QStatusBar()
        self.setStatusBar(self.status_bar)
        
        # Widgets del status bar
        self.record_count_label = QLabel("Loading records...")
        apply_scaled_font(self.record_count_label, offset=1, weight=QFont.Weight.Medium)
        self.record_count_label.setStyleSheet("color: #6B7280; font-weight: 500;")

        self.last_update_label = QLabel("Last updated: Never")
        apply_scaled_font(self.last_update_label, offset=1)
        self.last_update_label.setStyleSheet("color: #6B7280;")

        self.connection_status_label = QLabel("Disconnected")
        apply_scaled_font(self.connection_status_label, offset=1, weight=QFont.Weight.DemiBold)
        self.connection_status_label.setStyleSheet("color: #EF4444; font-weight: 600;")
        
        self.status_bar.addWidget(self.record_count_label)
        self.status_bar.addPermanentWidget(self.last_update_label)
        self.status_bar.addPermanentWidget(self.connection_status_label)
        
        self.status_bar.setStyleSheet("""
            QStatusBar {
                background: #F9FAFB;
                border-top: 1px solid #E5E7EB;
                padding: 6px 15px;
            }
        """)
    
    def apply_professional_theme(self):
        """Aplicar tema profesional"""
        self.setStyleSheet(f"""
            QMainWindow {{
                background: #F3F4F6;
            }}
            QWidget {{
                font-family: '{MODERN_FONT}', 'Inter', 'Roboto', 'Helvetica Neue', sans-serif;
            }}
        """)

    # Resto de métodos permanecen igual pero con ajustes menores para status
    def setup_websocket(self):
        """Configurar cliente WebSocket"""
        try:
            self.ws_client = WebSocketClient()
            self.ws_client.message_received.connect(self.handle_websocket_message)
            self.ws_client.connection_status.connect(self.update_connection_status)
            self.ws_client.start()
            print("WebSocket client iniciado")
        except Exception as e:
            print(f"Error configurando WebSocket: {e}")
    
    def update_connection_status(self, connected):
        """Actualizar status de conexión profesional"""
        if connected:
            self.connection_indicator.setStyleSheet("color: #10B981;")
            self.connection_indicator.setToolTip("Connected - Real-time updates enabled")
            self.connection_status_label.setText("Connected")
            self.connection_status_label.setStyleSheet("color: #10B981; font-weight: 600;")
        else:
            self.connection_indicator.setStyleSheet("color: #EF4444;")
            self.connection_indicator.setToolTip("Disconnected - Manual refresh required")
            self.connection_status_label.setText("Disconnected")
            self.connection_status_label.setStyleSheet("color: #EF4444; font-weight: 600;")
    
    def handle_websocket_message(self, message):
        """Manejar mensajes del WebSocket"""
        try:
            data = json.loads(message)
            msg_type = data.get("type")
            
            if msg_type in ["shipment_created", "shipment_updated", "shipment_deleted"]:
                action_by = data["data"].get("action_by", "User")
                job_number = data["data"].get("job_number", "")

                # Solo recargar para actualizaciones realizadas por otros usuarios
                if msg_type != "shipment_updated" or action_by != self.user_info.get("username"):
                    self.load_shipments_async()

                # Notificación discreta solo si la acción la realizó otro usuario
                if action_by != self.user_info.get("username"):
                    if msg_type == "shipment_created":
                        self.show_toast(f"New shipment created: Job #{job_number}")
                    elif msg_type == "shipment_updated":
                        self.show_toast(f"Shipment updated: Job #{job_number}")
                    elif msg_type == "shipment_deleted":
                        self.show_toast(f"Shipment deleted: Job #{job_number}")
                    
        except json.JSONDecodeError:
            pass
        except Exception as e:
            print(f"Error procesando mensaje WebSocket: {e}")
    
    

    def show_toast(self, message, color="#3B82F6"):
        """Mostrar notificación visual flotante"""
        show_popup_notification(self, message, color=color)
    
    def on_tab_changed(self, index):
        """Manejar cambio de tab optimizado"""
        print(f"Cambio de tab: {index}")
        if index == 0:  # Active tab
            if not self._tables_populated["active"]:
                self.populate_active_table()
                self._tables_populated["active"] = True
            if not self.read_only:
                self.add_btn.setEnabled(True)
        else:  # History tab
            print("Abriendo tab de historial")
            if not self._tables_populated["history"]:
                self.populate_history_table()
                self._tables_populated["history"] = True
            if not self.read_only:
                self.add_btn.setEnabled(False)

        self.update_status()
        self.on_selection_changed()
    
    def on_selection_changed(self):
        """Manejar cambio de selección en tabla"""
        current_table = self.get_current_table()
        has_selection = len(current_table.selectionModel().selectedRows()) > 0
        if self.read_only:
            self.delete_btn.setEnabled(False)
        else:
            self.delete_btn.setEnabled(has_selection)
    
    def get_current_table(self):
        """Obtener la tabla actualmente activa"""
        return self.active_table if self.tab_widget.currentIndex() == 0 else self.history_table
    
    def is_shipped(self, shipment):
        """Verificar si un shipment ya fue enviado"""
        shipped_date = shipment.get("shipped")
        if not shipped_date:
            return False
        shipped_date = str(shipped_date).strip()
        return bool(shipped_date and shipped_date.lower() not in ["", "n/a", "pending", "tbd"])

    def _show_loading_indicator(self):
        """Mostrar indicador de progreso y desactivar controles"""
        self._hide_loading_indicator()
        self.progress_dialog = QProgressDialog("Loading shipments...", None, 0, 0, self)
        self.progress_dialog.setWindowTitle("Loading")
        self.progress_dialog.setWindowModality(Qt.WindowModality.ApplicationModal)
        self.progress_dialog.setCancelButton(None)
        self.progress_dialog.show()

        widgets = [
            self.active_table,
            self.history_table,
            self.add_btn,
            self.delete_btn,
            self.refresh_btn,
            self.print_btn,
        ]
        if hasattr(self, "user_btn"):
            widgets.append(self.user_btn)

        self._disabled_widgets = {w: w.isEnabled() for w in widgets}
        for w in self._disabled_widgets:
            w.setEnabled(False)

    def _hide_loading_indicator(self):
        """Ocultar indicador de progreso y restaurar controles"""
        if hasattr(self, "progress_dialog") and self.progress_dialog:
            self.progress_dialog.close()
            self.progress_dialog = None
        if hasattr(self, "_disabled_widgets"):
            for w, state in self._disabled_widgets.items():
                w.setEnabled(state)
            del self._disabled_widgets

    def load_shipments_async(self):
        """Cargar shipments de forma asíncrona"""
        print("Iniciando carga asíncrona de shipments...")
        self.record_count_label.setText("Loading records...")
        self._show_loading_indicator()
        # Detener hilo previo si todavía se está ejecutando
        if hasattr(self, "shipment_loader") and self.shipment_loader.isRunning():
            self.shipment_loader.quit()
            self.shipment_loader.wait()

        self.shipment_loader = ShipmentLoader(self.api_client)
        self.shipment_loader.data_loaded.connect(self.on_shipments_loaded)
        self.shipment_loader.error_occurred.connect(self.on_shipments_error)
        self.shipment_loader.start()

    def on_shipments_loaded(self, shipments):
        """Callback cuando se cargan los shipments"""
        self._hide_loading_indicator()
        print(f"Shipments cargados: {len(shipments)}")
        self.shipments = shipments
        
        # Separar datos para cache
        self._active_shipments = [s for s in shipments if not self.is_shipped(s)]
        self._history_shipments = [s for s in shipments if self.is_shipped(s)]
        
        # Marcar tablas como no pobladas
        self._tables_populated = {"active": False, "history": False}
        
        # Poblar tabla actual
        current_tab = self.tab_widget.currentIndex()
        if current_tab == 0:
            self.populate_active_table()
            self._tables_populated["active"] = True
        else:
            self.populate_history_table()
            self._tables_populated["history"] = True
        
        self.update_status()

    def on_shipments_error(self, error_msg):
        """Callback cuando hay error cargando shipments"""
        self._hide_loading_indicator()
        print(f"Error cargando shipments: {error_msg}")
        self.show_error(f"Failed to load shipments: {error_msg}")
        self.record_count_label.setText("Error loading records")
    
    def populate_active_table(self):
        """Poblar tabla activa"""
        filtered_shipments = self.apply_filters_to_shipments(self._active_shipments, is_active=True)
        self.populate_table_fast(self.active_table, filtered_shipments, is_active=True)
    
    def populate_history_table(self):
        """Poblar tabla de historial"""
        print(f"Populando historial: {len(self._history_shipments)} shipments totales")
        filtered_shipments = self.apply_filters_to_shipments(self._history_shipments, is_active=False)
        print(f"Populando historial tras filtros: {len(filtered_shipments)} shipments")
        self.populate_table_fast(self.history_table, filtered_shipments, is_active=False)
    
    def populate_table_fast(self, table, shipments, is_active=True):
        """Poblar tabla de forma optimizada"""
        try:
            self.updating_table = True
            table.setUpdatesEnabled(False)

            # Mantener columna y orden de sort actuales
            header = table.horizontalHeader()
            sort_col = header.sortIndicatorSection() if table.isSortingEnabled() else -1
            sort_order = header.sortIndicatorOrder() if table.isSortingEnabled() else Qt.SortOrder.AscendingOrder

            table.setSortingEnabled(False)

            row_count = len(shipments)
            table.setRowCount(row_count)

            for row, shipment in enumerate(shipments):
                self.populate_table_row(table, row, shipment, is_active)

            table.setSortingEnabled(True)
            if sort_col >= 0:
                table.sortItems(sort_col, sort_order)

            self.apply_saved_cell_colors(table, "active" if is_active else "history")
            self.apply_date_filters_to_table(table, "active" if is_active else "history")

            # El ajuste de filas a su contenido puede ser costoso para miles de
            # registros. Dejamos un tamaño fijo establecido en la configuración
            table.setUpdatesEnabled(True)
            self.updating_table = False
            print(
                f"Tabla {'activa' if is_active else 'historial'} poblada: {row_count} filas"
            )
            
        except Exception as e:
            table.setUpdatesEnabled(True)
            self.updating_table = False
            print(f"Error poblando tabla: {e}")
            raise
    
    def populate_table_row(self, table, row, shipment, is_active):
        """Poblar una fila de la tabla con estilo profesional"""
        items = [
            shipment.get("job_number", ""),
            shipment.get("job_name", ""),
            shipment.get("description", ""),
            shipment.get("qc_release", ""),
            shipment.get("qc_notes", ""),
            shipment.get("created", ""),
            shipment.get("ship_plan", ""),
            shipment.get("shipped", ""),
            shipment.get("invoice_number", ""),
            shipment.get("shipping_notes", "")
        ]
        
        job_item = None
        for col, item_text in enumerate(items):
            if col == 6:  # Ship Plan
                display_text = str(item_text).strip() if str(item_text).strip() else "-"
                item = ShipPlanItem(display_text)
            else:
                item = QTableWidgetItem(str(item_text))
                if not is_active and col == 7 and item_text:  # Shipped en history
                    shipped_font = QFont(MODERN_FONT, max(6, get_base_font_size() + 1), QFont.Weight.Medium)
                    item.setFont(shipped_font)
                    item.setForeground(QColor("#059669"))
                    item.setData(Qt.ItemDataRole.UserRole + 5, 1)

            # Alineación
            if col in [0, 8]:  # Job # e Invoice #
                item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
            if col == 0:
                job_item = item
                # store full shipment data for easy retrieval even after sorting
                item.setData(Qt.ItemDataRole.UserRole, shipment)
                # Asegurar que version esté disponible (valor por defecto si no existe)
                if 'version' not in shipment:
                    shipment['version'] = 1
                # job number no editable
                item.setFlags(item.flags() & ~Qt.ItemFlag.ItemIsEditable)
            # store original flags to avoid calling item.flags() during edits
            # Qt6's ItemFlag cannot be converted directly to int; use the .value
            item.setData(
                Qt.ItemDataRole.UserRole + 1,
                item.flags().value,
            )
            if item.data(Qt.ItemDataRole.UserRole + 5) is None:
                item.setData(Qt.ItemDataRole.UserRole + 5, 0)

            table.setItem(row, col, item)

        # Color de la celda de Job Number según el status
        if job_item is not None:
            raw_status = shipment.get("status", "")
            status = str(raw_status).strip().lower().replace(" ", "_")
            if status == "partial_release":
                job_item.setBackground(QColor("#FDE68A"))  # Amarillo más intenso
            elif status == "final_release":
                job_item.setBackground(QColor("#BBF7D0"))   # Verde más intenso
            elif status == "rejected":
                job_item.setBackground(QColor("#FED7AA"))   # Soft Orange más intenso

        # La altura de las filas se ajusta al finalizar el poblado completo

    def apply_filters_to_shipments(self, shipments, is_active=True):
        """Aplicar filtros"""
        filtered = shipments
        
        # Filtro de búsqueda
        search_text = self.search_edit.text().lower().strip()
        if search_text:
            def safe_lower(value):
                return str(value or "").lower()

            filtered = [
                s
                for s in filtered
                if search_text in safe_lower(s.get("job_number"))
                or search_text in safe_lower(s.get("job_name"))
                or search_text in safe_lower(s.get("status"))
            ]
        
        return filtered
    
    def perform_filter(self):
        """Ejecutar filtrado optimizado"""
        current_tab = self.tab_widget.currentIndex()
        
        if current_tab == 0:  # Active
            self.populate_active_table()
        else:  # History
            self.populate_history_table()
        
        self.update_status()
    
    def update_status(self):
        """Actualizar información del status bar"""
        total_count = len(self.shipments)
        active_count = len(self._active_shipments)
        history_count = len(self._history_shipments)
        
        current_tab = self.tab_widget.currentIndex()
        if current_tab == 0:  # Active tab
            filtered_count = len(self.apply_filters_to_shipments(self._active_shipments, True))
            if filtered_count != active_count:
                self.record_count_label.setText(f"Showing {filtered_count} of {active_count} active shipments")
            else:
                self.record_count_label.setText(f"Active: {active_count} | History: {history_count}")
        else:  # History tab
            filtered_count = len(self.apply_filters_to_shipments(self._history_shipments, False))
            if filtered_count != history_count:
                self.record_count_label.setText(f"Showing {filtered_count} of {history_count} historical shipments")
            else:
                self.record_count_label.setText(f"History: {history_count} | Active: {active_count}")
        
        current_time = datetime.now().strftime("%H:%M:%S")
        self.last_update_label.setText(f"Last updated: {current_time}")
    
    def truncate_text(self, text, max_length):
        """Truncar texto con puntos suspensivos"""
        if len(text) > max_length:
            return text[:max_length-3] + "..."
        return text
    
    def add_shipment(self):
        """Agregar nuevo shipment"""
        if self.read_only:
            return
        try:
            from .shipment_dialog import ModernShipmentDialog

            dialog = ModernShipmentDialog(api_client=self.api_client)
            if dialog.exec() == QDialog.DialogCode.Accepted:
                self.load_shipments_async()
                self.show_toast("Shipment saved successfully", color="#16A34A")
        except Exception as e:
            print(f"Error abriendo diálogo de nuevo shipment: {e}")
            self.show_error(f"Error opening new shipment dialog: {str(e)}")
    
    def edit_shipment(self):
        """Permitir edición directa de la celda seleccionada"""
        if self.read_only:
            return
        current_table = self.get_current_table()
        item = current_table.currentItem()
        if item:
            current_table.editItem(item)

    def on_item_changed(self, item):
        """Save cell changes with flexible version control"""
        if self.updating_table or self.read_only:
            return

        table = item.tableWidget()
        row = item.row()
        col = item.column()
        field = self.column_field_map.get(col)

        if field is None:
            return

        job_item = table.item(row, 0)
        shipment = job_item.data(Qt.ItemDataRole.UserRole) if job_item else None
        if not shipment:
            return

        old_value = shipment.get(field, "") or ""
        new_value = item.data(Qt.ItemDataRole.EditRole)

        if new_value == (old_value or ""):  # No real changes
            return

        def update_local_data(updated_data):
            """Helper to update local data consistently"""
            shipment[field] = new_value
            shipment['version'] = updated_data.get('version', shipment.get('version', 1) + 1)
            shipment['last_modified_by'] = self.user_info.get('id')
            job_item.setData(Qt.ItemDataRole.UserRole, shipment)
            for dataset in (self.shipments, self._active_shipments, self._history_shipments):
                for s in dataset:
                    if s["id"] == shipment["id"]:
                        s[field] = new_value
                        s["version"] = shipment["version"]
                        break
            self.show_toast("Changes saved successfully", color="#16A34A")
            table_name = "active" if table is self.active_table else "history"
            self.apply_date_filters_to_table(table, table_name)

        try:
            # Intentar con versión actual
            current_version = int(shipment.get('version', 1) or 1)

            api_response = self.api_client.update_shipment_with_version(
                shipment['id'],
                {field: new_value},
                current_version
            )

            if api_response.is_success():
                updated_shipment = api_response.get_data()
                update_local_data(updated_shipment)
                return

            elif api_response.status_code == 409:
                # Conflicto de versión - resolver automáticamente
                print(f"Version conflict on field '{field}' for shipment {shipment['id']}, resolving...")
                
                latest_resp = self.api_client.get_shipment_by_id(shipment['id'])
                if latest_resp.is_success():
                    latest_shipment = latest_resp.get_data()
                    latest_version = int(latest_shipment.get('version', current_version))
                    
                    # Verificar si el campo que estamos editando también fue modificado por otro usuario
                    latest_field_value = latest_shipment.get(field, "")
                    if latest_field_value != old_value:
                        # El campo fue modificado por otro usuario - mostrar conflicto y valor actual
                        from PyQt6.QtWidgets import QMessageBox
                        msg = QMessageBox(self)
                        msg.setIcon(QMessageBox.Icon.Question)
                        msg.setWindowTitle("Field Conflict Detected")
                        msg.setText(f"Another user modified the '{field}' field.")
                        msg.setInformativeText(f"Your value: '{new_value}'\nCurrent value: '{latest_field_value}'\n\nDo you want to overwrite with your value?")
                        msg.setStandardButtons(QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No)
                        msg.setDefaultButton(QMessageBox.StandardButton.No)
                        
                        if msg.exec() != QMessageBox.StandardButton.Yes:
                            # Usuario decidió no sobrescribir - revertir cambio local
                            item.setText(str(latest_field_value))
                            for key, value in latest_shipment.items():
                                if key in shipment:
                                    shipment[key] = value
                            job_item.setData(Qt.ItemDataRole.UserRole, shipment)
                            self.show_toast("Change cancelled - field updated with current value", color="#F59E0B")
                            return

                    # Actualizar datos locales con información más reciente (excepto el campo que estamos editando)
                    for key, value in latest_shipment.items():
                        if key in shipment and key != field:
                            shipment[key] = value
                    
                    # Intentar nuevamente con la versión correcta
                    retry_response = self.api_client.update_shipment_with_version(
                        shipment['id'], 
                        {field: new_value}, 
                        latest_version
                    )
                    
                    if retry_response.is_success():
                        updated_shipment = retry_response.get_data()
                        update_local_data(updated_shipment)
                        print(f"Successfully resolved field conflict for '{field}' in shipment {shipment['id']}")
                        return
                    else:
                        # Revertir cambio
                        item.setText(str(old_value))
                        self.show_error(f"Failed to save after resolving conflict: {retry_response.get_error()}")
                else:
                    # Revertir cambio
                    item.setText(str(old_value))
                    self.show_error("Could not resolve version conflict. Please refresh and try again.")
            else:
                # Revertir cambio
                item.setText(str(old_value))
                self.show_error(f"Failed to save changes: {api_response.get_error()}")

        except Exception as e:
            # Revertir cambio
            item.setText(str(old_value))
            print(f"Exception in on_item_changed: {str(e)}")
            self.show_error(f"Failed to save changes: {str(e)}")
    
    def delete_shipment(self):
        """Eliminar shipment seleccionado"""
        if self.read_only:
            return
        try:
            current_table = self.get_current_table()
            selected_rows = current_table.selectionModel().selectedRows()
            if not selected_rows:
                return
            
            row = selected_rows[0].row()
            shipment_item = current_table.item(row, 0)
            if not shipment_item:
                return
            shipment = shipment_item.data(Qt.ItemDataRole.UserRole)
            if not shipment:
                return
            
            # Confirmación profesional
            msg = QMessageBox(self)
            msg.setIcon(QMessageBox.Icon.Question)
            msg.setWindowTitle("Confirm Deletion")
            msg.setText("Are you sure you want to delete this shipment?")
            msg.setInformativeText(f"Job #{shipment['job_number']} - {shipment['job_name']}")
            msg.setStandardButtons(QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No)
            msg.setDefaultButton(QMessageBox.StandardButton.No)
            
            # Estilo profesional para el mensaje
            msg.setStyleSheet(f"""
                QMessageBox {{
                    background: #FFFFFF;
                    font-family: '{MODERN_FONT}';
                }}
                QMessageBox QPushButton {{
                    background: #3B82F6;
                    color: white;
                    border: none;
                    padding: 8px 20px;
                    border-radius: 4px;
                    font-weight: 500;
                    min-width: 80px;

                }}
                QMessageBox QPushButton:hover {{
                    background: #2563EB;
                }}
                QMessageBox QPushButton[text="No"] {{
                    background: #6B7280;
                }}
                QMessageBox QPushButton[text="No"]:hover {{
                    background: #4B5563;
                }}
            """)
            
            if msg.exec() == QMessageBox.StandardButton.Yes:
                api_response = self.api_client.delete_shipment(shipment['id'])

                if api_response.is_success():
                    self.load_shipments_async()
                    self.show_toast(f"Shipment deleted: Job #{shipment['job_number']}")
                else:
                    self.show_error(f"Failed to delete shipment: {api_response.get_error()}")

        except Exception as e:
            print(f"Error eliminando shipment: {e}")
            self.show_error(f"Error deleting shipment: {str(e)}")
    
    def show_error(self, message):
        """Mostrar mensaje de error profesional"""
        msg = QMessageBox(self)
        msg.setIcon(QMessageBox.Icon.Critical)
        msg.setWindowTitle("Error")
        msg.setText(message)
        msg.setStyleSheet(f"""
            QMessageBox {{
                background: #FFFFFF;
                font-family: '{MODERN_FONT}';
            }}
            QMessageBox QPushButton {{
                background: #EF4444;
                color: white;
                border: none;
                padding: 8px 20px;
                border-radius: 4px;
                font-weight: 500;
                min-width: 80px;
            }}
            QMessageBox QPushButton:hover {{
                background: #DC2626;
            }}
        """)
        msg.exec()

    def open_user_management(self):
        """Abrir diálogo de gestión de usuarios"""
        from .user_dialog import UserManagementDialog
        dialog = UserManagementDialog(token=self.token)
        dialog.exec()

    def open_settings_dialog(self):
        """Open settings dialog to configure server URLs"""
        dlg = SettingsDialog(self.settings_mgr)
        if dlg.exec() == QDialog.DialogCode.Accepted:
            self.apply_global_font_preferences()
            if hasattr(self, "ws_client"):
                self.ws_client.stop()
            self.setup_websocket()
            self.load_shipments_async()

    def print_table_to_pdf(self):
        """Export current table view to a professional PDF that fits on one page"""
        # Verificar dependencias antes de continuar
        missing_deps = []

        try:
            import reportlab
        except ImportError:
            missing_deps.append("reportlab")

        try:
            from reportlab.lib.pagesizes import LEGAL
        except ImportError:
            missing_deps.append("reportlab (lib.pagesizes)")

        try:
            from reportlab.platypus import SimpleDocTemplate
        except ImportError:
            missing_deps.append("reportlab (platypus)")

        if missing_deps:
            error_msg = f"Missing dependencies: {', '.join(missing_deps)}\n\n"
            error_msg += "Please install with:\n"
            error_msg += "pip install reportlab pillow\n\n"
            error_msg += "Make sure you're in the correct virtual environment."

            self.show_error(error_msg)
            return

        try:
            from reportlab.lib.pagesizes import LEGAL
            from reportlab.platypus import (
                SimpleDocTemplate,
                Table,
                TableStyle,
                Paragraph,
                Spacer,
            )
            from reportlab.lib import colors
            from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
            from reportlab.lib.units import inch

            # Ruta por defecto en carpeta de Documentos
            docs_dir = QStandardPaths.writableLocation(
                QStandardPaths.StandardLocation.DocumentsLocation
            )
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")

            # Determinar nombre según tab actual
            tab_name = "Active" if self.tab_widget.currentIndex() == 0 else "History"
            file_path = os.path.join(
                docs_dir, f"Shipping_Schedule_{tab_name}_{timestamp}.pdf"
            )

            # Usar formato vertical con papel Legal (8.5" x 14")
            page_width, page_height = LEGAL

            # Márgenes mínimos para maximizar espacio disponible
            margin = 20
            doc = SimpleDocTemplate(
                file_path,
                pagesize=LEGAL,
                leftMargin=margin,
                rightMargin=margin,
                topMargin=margin,
                bottomMargin=margin,
            )

            # Obtener tabla actual y datos
            current_table = self.get_current_table()
            rows = current_table.rowCount()

            if rows == 0:
                self.show_error("No data to export")
                return

            # Solo las columnas necesarias
            headers = [
                "Job Number",
                "Job Name",
                "Description",
                "QC Release",
                "Crated",
                "Ship Plan",
            ]

            # Mapeo de columnas: posición en el PDF -> columna en la tabla original
            # La tabla principal tiene las columnas en el siguiente orden:
            # 0: Job Number, 1: Job Name, 2: Description, 3: QC Release,
            # 4: QC Notes, 5: Crated, 6: Ship Plan, 7: Shipped, 8: Invoice Number, 9: Notes
            # Para el PDF solo exportamos seis columnas específicas y es importante
            # que los índices coincidan exactamente con el orden de la tabla para
            # evitar desalineaciones.  El mapeo anterior usaba los índices
            # [0, 1, 2, 4, 6, 7], lo que provocaba que la columna "QC Release"
            # mostrara los datos de "QC Notes" y que las columnas siguientes se
            # desplazaran.  Ajustamos el mapeo para que cada encabezado apunte a la
            # columna correcta.
            column_map = [0, 1, 2, 3, 5, 6]

            # Preparar datos con solo las columnas seleccionadas
            raw_data = [headers]
            for row in range(rows):
                row_data = []
                for col_index in column_map:
                    item = current_table.item(row, col_index)
                    text = item.text() if item else ""
                    row_data.append(text)
                raw_data.append(row_data)

            print(
                f"📊 Exportando {len(raw_data)-1} filas con {len(headers)} columnas seleccionadas"
            )

            # Calcular espacio disponible
            styles = getSampleStyleSheet()

            # Título compacto
            title_style = ParagraphStyle(
                "CustomTitle",
                parent=styles["Title"],
                fontSize=14,
                spaceBefore=0,
                spaceAfter=6,
                alignment=1,  # Center
            )

            title = Paragraph(f"Shipping Schedule - {tab_name}", title_style)
            title_height = 25  # Estimado para el título compacto

            # Espacio disponible para la tabla
            available_width = doc.width
            available_height = doc.height - title_height - 10  # 10 para spacing

            print(
                f"📐 Espacio disponible: {available_width} x {available_height}"
            )

            # === ALGORITMO DE AJUSTE AUTOMÁTICO ===

            # Anchos relativos optimizados para las 6 columnas en formato vertical
            relative_widths = [0.12, 0.25, 0.30, 0.12, 0.11, 0.10]

            # Calcular anchos absolutos
            col_widths = [available_width * w for w in relative_widths]

            # Función para crear tabla con parámetros dados
            def create_table_with_params(font_size, padding, row_height_factor=1.0):
                # Estilo de celda adaptativo
                cell_style = ParagraphStyle(
                    "CellStyle",
                    parent=styles["BodyText"],
                    fontSize=font_size,
                    leading=font_size * 1.1,
                    wordWrap="CJK",
                    alignment=0,  # Left align
                    spaceBefore=0,
                    spaceAfter=0,
                )

                # Convertir datos a Paragraphs con el estilo apropiado
                processed_data = []
                for r, row in enumerate(raw_data):
                    processed_row = []
                    for c, cell_text in enumerate(row):
                        # Truncar texto muy largo para optimizar
                        if len(str(cell_text)) > 100:
                            cell_text = str(cell_text)[:97] + "..."

                        para = Paragraph(str(cell_text), cell_style)
                        processed_row.append(para)
                    processed_data.append(processed_row)

                # Crear tabla
                table = Table(
                    processed_data,
                    colWidths=col_widths,
                    repeatRows=1,  # Repetir header si se extiende a múltiples páginas
                )

                # Aplicar estilo
                table_style = TableStyle(
                    [
                        # Bordes y grid
                        ("GRID", (0, 0), (-1, -1), 0.5, colors.grey),

                        # Header styling
                        ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#2563EB")),
                        ("TEXTCOLOR", (0, 0), (-1, 0), colors.whitesmoke),
                        ("FONTSIZE", (0, 0), (-1, 0), font_size),
                        ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),

                        # Datos
                        ("FONTSIZE", (0, 1), (-1, -1), font_size),
                        ("FONTNAME", (0, 1), (-1, -1), "Helvetica"),

                        # Alineación optimizada para las 6 columnas
                        ("ALIGN", (3, 0), (5, -1), "CENTER"),
                        ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),

                        # Padding
                        ("TOPPADDING", (0, 0), (-1, -1), padding),
                        ("BOTTOMPADDING", (0, 0), (-1, -1), padding),
                        ("LEFTPADDING", (0, 0), (-1, -1), padding * 0.7),
                        ("RIGHTPADDING", (0, 0), (-1, -1), padding * 0.7),

                        # Filas alternas para mejor legibilidad
                        (
                            "ROWBACKGROUNDS",
                            (0, 1),
                            (-1, -1),
                            [colors.white, colors.HexColor("#F8F9FA")],
                        ),
                    ]
                )

                table.setStyle(table_style)
                return table

            # === BÚSQUEDA BINARIA PARA EL TAMAÑO ÓPTIMO ===

            min_font = 4
            max_font = 12
            optimal_font = min_font
            optimal_padding = 1

            print("🔍 Buscando tamaño óptimo...")

            # Búsqueda binaria del tamaño de fuente óptimo
            while max_font - min_font > 0.5:
                test_font = (min_font + max_font) / 2
                test_padding = max(1, test_font * 0.3)

                test_table = create_table_with_params(test_font, test_padding)

                # Medir la tabla
                table_width, table_height = test_table.wrap(
                    available_width, available_height
                )

                print(
                    f"   Probando font={test_font:.1f}, padding={test_padding:.1f} -> {table_width:.0f}x{table_height:.0f}"
                )

                # Verificar si cabe
                if table_width <= available_width and table_height <= available_height:
                    optimal_font = test_font
                    optimal_padding = test_padding
                    min_font = test_font  # Puede ser más grande
                else:
                    max_font = test_font  # Debe ser más pequeño

            print(
                f"✅ Tamaño óptimo encontrado: font={optimal_font:.1f}, padding={optimal_padding:.1f}"
            )

            # Crear tabla final con parámetros óptimos
            final_table = create_table_with_params(optimal_font, optimal_padding)

            # Verificar medidas finales
            final_width, final_height = final_table.wrap(
                available_width, available_height
            )
            print(
                f"📏 Medidas finales: {final_width:.0f}x{final_height:.0f} (disponible: {available_width:.0f}x{available_height:.0f})"
            )

            # Construir documento
            elements = [title, final_table]

            # Texto de pie de página con la fecha actual en formato M/D/AAAA
            today = datetime.now()
            footer_text = f"Printed: {today.month}/{today.day}/{today.year}"

            def add_footer(canvas, document):
                """Agregar fecha de impresión en la esquina inferior derecha"""
                canvas.saveState()
                canvas.setFont("Helvetica", 8)
                text_width = canvas.stringWidth(footer_text, "Helvetica", 8)
                x = document.pagesize[0] - document.rightMargin - text_width
                y = document.bottomMargin * 0.5
                canvas.drawString(x, y, footer_text)
                canvas.restoreState()

            # Generar PDF con pie de página
            doc.build(elements, onFirstPage=add_footer, onLaterPages=add_footer)

            print(f"✅ PDF generado exitosamente: {file_path}")
            self.show_toast(
                f"PDF saved: {os.path.basename(file_path)}", color="#16A34A"
            )

            # Abrir PDF automáticamente
            QDesktopServices.openUrl(QUrl.fromLocalFile(file_path))

        except ImportError as e:
            error_msg = f"Import error: {str(e)}\n\n"
            error_msg += "Please ensure ReportLab is installed:\n"
            error_msg += "pip install reportlab pillow\n\n"
            error_msg += "And that you're running from the correct virtual environment."
            self.show_error(error_msg)
        except Exception as e:
            print(f"❌ Error al generar PDF: {e}")
            import traceback

            traceback.print_exc()
            self.show_error(f"Error generating PDF:\n{str(e)}")
    
    def closeEvent(self, event):
        """Manejar cierre de ventana"""
        try:
            # Guardar colores de shipments
            self.save_shipment_colors("active")
            self.save_shipment_colors("history")

            # Guardar anchos de columnas antes de cerrar
            self.save_table_column_widths(self.active_table, "active")
            self.save_table_column_widths(self.history_table, "history")

            if hasattr(self, 'ws_client'):
                self.ws_client.stop()
            if hasattr(self, 'shipment_loader') and self.shipment_loader.isRunning():
                self.shipment_loader.quit()
                self.shipment_loader.wait()
            print("Ventana principal cerrada")
            event.accept()
        except Exception as e:
            print(f"Error cerrando ventana: {e}")
            event.accept()
