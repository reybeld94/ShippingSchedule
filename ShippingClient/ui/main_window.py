# ui/main_window.py - Ventana principal con diseño profesional
import json
import requests
from datetime import datetime
import os
from .utils import show_popup_notification
from core.settings_manager import SettingsManager
from PyQt6.QtWidgets import (
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
)
from PyQt6.QtCore import Qt, QTimer, QThread, pyqtSignal
from PyQt6.QtGui import QFont, QColor, QPixmap, QPalette

# Imports locales
from .widgets import ModernButton, ModernLineEdit, ModernComboBox
from .settings_dialog import SettingsDialog
from core.websocket_client import WebSocketClient
from core.config import (
    get_server_url,
    WINDOW_WIDTH,
    WINDOW_HEIGHT,
    REQUEST_TIMEOUT,
    MODERN_FONT,
)

class ShipmentLoader(QThread):
    """Thread para cargar datos en background"""
    data_loaded = pyqtSignal(list)
    error_occurred = pyqtSignal(str)
    
    def __init__(self, token):
        super().__init__()
        self.token = token
    
    def run(self):
        try:
            headers = {"Authorization": f"Bearer {self.token}"}
            server_url = get_server_url()
            response = requests.get(f"{server_url}/shipments", headers=headers, timeout=REQUEST_TIMEOUT)
            
            if response.status_code == 200:
                shipments = response.json()
                self.data_loaded.emit(shipments)
            else:
                self.error_occurred.emit(f"HTTP {response.status_code}")
        except Exception as e:
            self.error_occurred.emit(str(e))

class ModernShippingMainWindow(QMainWindow):
    def __init__(self, token, user_info):
        super().__init__()
        self.token = token
        self.user_info = user_info
        self.shipments = []

        self.is_admin = self.user_info.get("role") == "admin"
        self.read_only = self.user_info.get("role") == "read"

        # Manage persistent UI settings
        self.settings_mgr = SettingsManager()

        # Cache para optimización
        self._active_shipments = []
        self._history_shipments = []
        self._last_filter_text = ""
        self._last_status_filter = "All Status"
        self._tables_populated = {"active": False, "history": False}
        
        print(f"Inicializando ventana principal para usuario: {user_info['username']}")
        
        self.setWindowTitle("Shipping Schedule Management System")
        self.setGeometry(100, 100, WINDOW_WIDTH, WINDOW_HEIGHT)
        self.showMaximized()
        try:
            self.setup_ui()
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
        logo_path = "assets/images/logo.png"
        if os.path.exists(logo_path):
            pixmap = QPixmap(logo_path)
            # Escalar el logo manteniendo aspecto
            scaled_pixmap = pixmap.scaled(50, 50, Qt.AspectRatioMode.KeepAspectRatio, Qt.TransformationMode.SmoothTransformation)
            logo_label.setPixmap(scaled_pixmap)
        else:
            # Fallback: usar texto
            logo_label.setText("LOGO")
            logo_label.setStyleSheet("""
                background-color: #374151;
                color: white;
                font-weight: bold;
                padding: 15px;
                border-radius: 4px;
                font-size: 12px;
            """)
            logo_label.setFixedSize(50, 50)
            logo_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        
        # Información de la aplicación
        title_layout = QVBoxLayout()
        title_layout.setSpacing(2)
        
        title_label = QLabel("Shipping Schedule")
        title_label.setFont(QFont(MODERN_FONT, 18, QFont.Weight.DemiBold))
        title_label.setStyleSheet("color: #1F2937; letter-spacing: -0.5px;")
        
        subtitle_label = QLabel("Dashboard")
        subtitle_label.setFont(QFont(MODERN_FONT, 11))
        subtitle_label.setStyleSheet("color: #6B7280;")
        
        title_layout.addWidget(title_label)
        title_layout.addWidget(subtitle_label)
        
        logo_title_layout.addWidget(logo_label)
        logo_title_layout.addLayout(title_layout)
        
        # Información del usuario (derecha)
        user_info_layout = QVBoxLayout()
        user_info_layout.setSpacing(3)
        
        user_name_label = QLabel(f"{self.user_info['username']}")
        user_name_label.setFont(QFont(MODERN_FONT, 12, QFont.Weight.Medium))
        user_name_label.setStyleSheet("color: #1F2937;")
        user_name_label.setAlignment(Qt.AlignmentFlag.AlignRight)
        
        role_map = {
            "admin": "System Administrator",
            "write": "Write Access",
            "read": "Read Only"
        }
        role_text = role_map.get(self.user_info.get("role"), "Read Only")
        user_role_label = QLabel(role_text)
        user_role_label.setFont(QFont(MODERN_FONT, 9))
        user_role_label.setStyleSheet("color: #6B7280;")
        user_role_label.setAlignment(Qt.AlignmentFlag.AlignRight)
        
        # Connection status
        connection_layout = QHBoxLayout()
        connection_layout.setSpacing(5)
        
        self.connection_indicator = QLabel("●")
        self.connection_indicator.setFont(QFont("Arial", 12))
        self.connection_indicator.setStyleSheet("color: #10B981;")
        
        connection_text = QLabel("Connected")
        connection_text.setFont(QFont(MODERN_FONT, 9))
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
        
        self.edit_btn = ModernButton("Edit", "secondary")
        self.edit_btn.clicked.connect(self.edit_shipment)
        self.edit_btn.setEnabled(False)
        
        self.delete_btn = ModernButton("Delete", "danger")
        self.delete_btn.clicked.connect(self.delete_shipment)
        self.delete_btn.setEnabled(False)

        if self.read_only:
            self.add_btn.setEnabled(False)
            self.edit_btn.setEnabled(False)
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
        search_label.setFont(QFont(MODERN_FONT, 10, QFont.Weight.Medium))
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
        
        # Filtro por status
        filter_layout = QHBoxLayout()
        filter_layout.setSpacing(8)
        
        filter_label = QLabel("Status:")
        filter_label.setFont(QFont(MODERN_FONT, 10, QFont.Weight.Medium))
        filter_label.setStyleSheet("color: #374151;")
        
        self.status_filter = ModernComboBox()
        self.status_filter.addItems([
            "All Status",
            "Final Release",
            "Partial Release", 
            "Rejected",
            "Production Updated"
        ])
        self.status_filter.currentTextChanged.connect(self.perform_filter)
        
        filter_layout.addWidget(filter_label)
        filter_layout.addWidget(self.status_filter)
        
        # Refresh button
        self.refresh_btn = ModernButton("Refresh", "secondary")
        self.refresh_btn.clicked.connect(self.load_shipments_async)
        
        # Agregar todo al toolbar
        toolbar_layout.addWidget(self.add_btn)
        toolbar_layout.addWidget(self.edit_btn)
        toolbar_layout.addWidget(self.delete_btn)
        toolbar_layout.addWidget(separator)
        toolbar_layout.addLayout(search_layout)
        toolbar_layout.addLayout(filter_layout)
        toolbar_layout.addStretch()
        if self.is_admin:
            self.user_btn = ModernButton("Users", "secondary")
            self.user_btn.clicked.connect(self.open_user_management)
            toolbar_layout.addWidget(self.user_btn)
        toolbar_layout.addWidget(self.refresh_btn)
        
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
        self.tab_widget.setStyleSheet("""
            QTabWidget::pane {
                border: none;
                background: #FFFFFF;
                border-top: 1px solid #E5E7EB;
            }
            QTabBar::tab {
                background: #F9FAFB;
                color: #6B7280;
                padding: 14px 28px;
                margin-right: 1px;
                border-top-left-radius: 6px;
                border-top-right-radius: 6px;
                font-weight: 500;
                font-size: 13px;
                min-width: 120px;
                border: 1px solid #E5E7EB;
                border-bottom: none;
            }
            QTabBar::tab:selected {
                background: #FFFFFF;
                color: #1F2937;
                border-bottom: 2px solid #3B82F6;
                font-weight: 600;
            }
            QTabBar::tab:hover:!selected {
                background: #F3F4F6;
                color: #374151;
            }
        """)
        
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
            "Status", "QC Release", "Crated", "Ship Plan", "Shipped",
            "Invoice Number", "Notes"
        ]
        
        table.setColumnCount(len(columns))
        table.setHorizontalHeaderLabels(columns)
        
        # Estilo profesional para la tabla
        table.setStyleSheet(f"""
            QTableWidget {{
                background: #FFFFFF;
                border: none;
                gridline-color: #F3F4F6;
                font-family: '{MODERN_FONT}';
                font-size: 12px;
                selection-background-color: #EFF6FF;
                selection-color: #1F2937;
            }}
            QTableWidget::item {{
                padding: 12px 8px;
                border-bottom: 1px solid #F3F4F6;
                border-right: 1px solid #F9FAFB;
            }}
            QTableWidget::item:selected {{
                background: #EFF6FF;
                color: #1F2937;
            }}
            QHeaderView::section {{
                background-color: #F9FAFB;
                color: #374151;
                padding: 12px 8px;
                border: none;
                border-bottom: 2px solid #E5E7EB;
                border-right: 1px solid #E5E7EB;
                font-weight: 600;
                font-size: 11px;
                text-transform: uppercase;
                letter-spacing: 0.5px;
            }}
            QHeaderView::section:first {{
                border-left: none;
            }}
            QHeaderView::section:last {{
                border-right: none;
            }}
            QTableWidget::item:hover {{
                background: #F9FAFB;
            }}
        """)
        
        # Configuración
        table.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)
        table.setAlternatingRowColors(True)
        table.verticalHeader().setVisible(False)
        table.setShowGrid(False)
        
        # Optimización de performance
        table.setVerticalScrollMode(QTableWidget.ScrollMode.ScrollPerPixel)
        table.setHorizontalScrollMode(QTableWidget.ScrollMode.ScrollPerPixel)
        
        # Configurar columnas como ajustables por el usuario
        header = table.horizontalHeader()
        for i in range(len(columns)):
            header.setSectionResizeMode(i, QHeaderView.ResizeMode.Interactive)

        # Restaurar anchos guardados si existen
        self.restore_column_widths(table, name)

        # Guardar anchos cada vez que se ajusta alguna columna
        header.sectionResized.connect(lambda *args, tbl=table, nm=name: self.save_table_column_widths(tbl, nm))

        # Eventos
        table.selectionModel().selectionChanged.connect(self.on_selection_changed)
        table.doubleClicked.connect(self.edit_shipment)

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
    
    def create_professional_status_bar(self):
        """Crear status bar profesional"""
        self.status_bar = QStatusBar()
        self.setStatusBar(self.status_bar)
        
        # Widgets del status bar
        self.record_count_label = QLabel("Loading records...")
        self.record_count_label.setStyleSheet("color: #6B7280; font-size: 11px; font-weight: 500;")
        
        self.last_update_label = QLabel("Last updated: Never")
        self.last_update_label.setStyleSheet("color: #6B7280; font-size: 11px;")
        
        self.connection_status_label = QLabel("Disconnected")
        self.connection_status_label.setStyleSheet("color: #EF4444; font-size: 11px; font-weight: 600;")
        
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
            self.connection_status_label.setStyleSheet("color: #10B981; font-size: 11px; font-weight: 600;")
        else:
            self.connection_indicator.setStyleSheet("color: #EF4444;")
            self.connection_indicator.setToolTip("Disconnected - Manual refresh required")
            self.connection_status_label.setText("Disconnected")
            self.connection_status_label.setStyleSheet("color: #EF4444; font-size: 11px; font-weight: 600;")
    
    def handle_websocket_message(self, message):
        """Manejar mensajes del WebSocket"""
        try:
            data = json.loads(message)
            msg_type = data.get("type")
            
            if msg_type in ["shipment_created", "shipment_updated", "shipment_deleted"]:
                self.load_shipments_async()
                
                # Notificación discreta
                action_by = data["data"].get("action_by", "User")
                job_number = data["data"].get("job_number", "")
                
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
    
    

    def show_toast(self, message):
        """Mostrar notificación visual flotante"""
        show_popup_notification(self, message)
    
    def on_tab_changed(self, index):
        """Manejar cambio de tab optimizado"""
        if index == 0:  # Active tab
            self.status_filter.setEnabled(True)
            self.add_btn.setEnabled(True)
            
            if not self._tables_populated["active"]:
                self.populate_active_table()
                self._tables_populated["active"] = True
        else:  # History tab
            self.status_filter.setEnabled(False)
            
            if not self._tables_populated["history"]:
                self.populate_history_table()
                self._tables_populated["history"] = True
        
        self.update_status()
        self.on_selection_changed()
    
    def on_selection_changed(self):
        """Manejar cambio de selección en tabla"""
        current_table = self.get_current_table()
        has_selection = len(current_table.selectionModel().selectedRows()) > 0
        if self.read_only:
            self.edit_btn.setEnabled(False)
            self.delete_btn.setEnabled(False)
        else:
            self.edit_btn.setEnabled(has_selection)
            self.delete_btn.setEnabled(has_selection)
    
    def get_current_table(self):
        """Obtener la tabla actualmente activa"""
        return self.active_table if self.tab_widget.currentIndex() == 0 else self.history_table
    
    def is_shipped(self, shipment):
        """Verificar si un shipment ya fue enviado"""
        shipped_date = shipment.get("shipped", "").strip()
        return bool(shipped_date and shipped_date.lower() not in ["", "n/a", "pending", "tbd"])
    
    def load_shipments_async(self):
        """Cargar shipments de forma asíncrona"""
        print("Iniciando carga asíncrona de shipments...")
        self.record_count_label.setText("Loading records...")
        
        self.shipment_loader = ShipmentLoader(self.token)
        self.shipment_loader.data_loaded.connect(self.on_shipments_loaded)
        self.shipment_loader.error_occurred.connect(self.on_shipments_error)
        self.shipment_loader.start()
    
    def on_shipments_loaded(self, shipments):
        """Callback cuando se cargan los shipments"""
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
        print(f"Error cargando shipments: {error_msg}")
        self.show_error(f"Failed to load shipments: {error_msg}")
        self.record_count_label.setText("Error loading records")
    
    def populate_active_table(self):
        """Poblar tabla activa"""
        filtered_shipments = self.apply_filters_to_shipments(self._active_shipments, is_active=True)
        self.populate_table_fast(self.active_table, filtered_shipments, is_active=True)
    
    def populate_history_table(self):
        """Poblar tabla de historial"""
        filtered_shipments = self.apply_filters_to_shipments(self._history_shipments, is_active=False)
        self.populate_table_fast(self.history_table, filtered_shipments, is_active=False)
    
    def populate_table_fast(self, table, shipments, is_active=True):
        """Poblar tabla de forma optimizada"""
        try:
            table.setUpdatesEnabled(False)
            
            row_count = len(shipments)
            table.setRowCount(row_count)
            
            for row, shipment in enumerate(shipments):
                self.populate_table_row(table, row, shipment, is_active)
            
            table.setUpdatesEnabled(True)
            print(f"Tabla poblada: {row_count} filas")
            
        except Exception as e:
            table.setUpdatesEnabled(True)
            print(f"Error poblando tabla: {e}")
            raise
    
    def populate_table_row(self, table, row, shipment, is_active):
        """Poblar una fila de la tabla con estilo profesional"""
        items = [
            shipment.get("job_number", ""),
            shipment.get("job_name", ""),
            self.truncate_text(shipment.get("description", ""), 45),
            shipment.get("status", ""),
            shipment.get("qc_release", ""),
            shipment.get("created", ""),
            shipment.get("ship_plan", ""),
            shipment.get("shipped", ""),
            shipment.get("invoice_number", ""),
            self.truncate_text(shipment.get("shipping_notes", ""), 35)
        ]
        
        for col, item_text in enumerate(items):
            item = QTableWidgetItem(str(item_text))
            
            # Aplicar estilos profesionales
            if col == 3:  # Columna status
                self.style_professional_status_item(item, shipment.get("status", ""))
            elif not is_active and col == 9 and item_text:  # Shipped en history
                item.setFont(QFont(MODERN_FONT, 11, QFont.Weight.Medium))
                item.setForeground(QColor("#059669"))
            
            # Alineación
            if col in [0, 8]:  # Job # e Invoice #
                item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
            
            table.setItem(row, col, item)
        
        table.setRowHeight(row, 45)
    
    def style_professional_status_item(self, item, status):
        """Aplicar estilo profesional a item de status"""
        item.setFont(QFont(MODERN_FONT, 10, QFont.Weight.Medium))
        
        status_map = {
            "final_release": ("Final Release", "#DCFCE7", "#166534"),
            "partial_release": ("Partial Release", "#FEF3C7", "#92400E"), 
            "rejected": ("Rejected", "#FEE2E2", "#991B1B"),
            "prod_updated": ("Updated", "#DBEAFE", "#1E40AF")
        }
        
        if status in status_map:
            text, bg_color, text_color = status_map[status]
            item.setText(text)
            item.setBackground(QColor(bg_color))
            item.setForeground(QColor(text_color))
        else:
            item.setText(status.replace("_", " ").title())
    
    def apply_filters_to_shipments(self, shipments, is_active=True):
        """Aplicar filtros"""
        filtered = shipments
        
        # Filtro de búsqueda
        search_text = self.search_edit.text().lower().strip()
        if search_text:
            filtered = [s for s in filtered if 
                       search_text in s.get("job_number", "").lower() or
                       search_text in s.get("job_name", "").lower() or
                       search_text in s.get("status", "").lower()]
        
        # Filtro de status (solo para active)
        if is_active:
            status_filter = self.status_filter.currentText()
            if status_filter != "All Status":
                # Mapear texto del combo a valor real
                status_map = {
                    "Final Release": "final_release",
                    "Partial Release": "partial_release",
                    "Rejected": "rejected",
                    "Production Updated": "prod_updated"
                }
                actual_status = status_map.get(status_filter, status_filter)
                filtered = [s for s in filtered if s.get("status") == actual_status]
        
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
            
            dialog = ModernShipmentDialog(token=self.token)
            if dialog.exec() == QDialog.DialogCode.Accepted:
                self.load_shipments_async()
        except Exception as e:
            print(f"Error abriendo diálogo de nuevo shipment: {e}")
            self.show_error(f"Error opening new shipment dialog: {str(e)}")
    
    def edit_shipment(self):
        """Editar shipment seleccionado"""
        if self.read_only:
            return
        try:
            current_table = self.get_current_table()
            selected_rows = current_table.selectionModel().selectedRows()
            if not selected_rows:
                return
            
            row = selected_rows[0].row()
            
            # Obtener datos según el tab actual
            if self.tab_widget.currentIndex() == 0:  # Active
                filtered_shipments = self.apply_filters_to_shipments(self._active_shipments, True)
            else:  # History
                filtered_shipments = self.apply_filters_to_shipments(self._history_shipments, False)
            
            if row >= len(filtered_shipments):
                return
                
            shipment_data = filtered_shipments[row]
            
            from .shipment_dialog import ModernShipmentDialog
            
            dialog = ModernShipmentDialog(shipment_data=shipment_data, token=self.token)
            if dialog.exec() == QDialog.DialogCode.Accepted:
                self.load_shipments_async()
        except Exception as e:
            print(f"Error editando shipment: {e}")
            self.show_error(f"Error editing shipment: {str(e)}")
    
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
            
            # Obtener datos según el tab actual
            if self.tab_widget.currentIndex() == 0:  # Active
                filtered_shipments = self.apply_filters_to_shipments(self._active_shipments, True)
            else:  # History
                filtered_shipments = self.apply_filters_to_shipments(self._history_shipments, False)
            
            if row >= len(filtered_shipments):
                return
                
            shipment = filtered_shipments[row]
            
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
                headers = {"Authorization": f"Bearer {self.token}"}
                server_url = get_server_url()
                response = requests.delete(
                    f"{server_url}/shipments/{shipment['id']}",
                    headers=headers,
                    timeout=REQUEST_TIMEOUT
                )
                
                if response.status_code == 200:
                    self.load_shipments_async()
                    self.show_toast(f"Shipment deleted: Job #{shipment['job_number']}")
                else:
                    self.show_error("Failed to delete shipment")
        
        except requests.exceptions.RequestException as e:
            self.show_error(f"Connection error: {str(e)}")
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
            if hasattr(self, "ws_client"):
                self.ws_client.stop()
            self.setup_websocket()
            self.load_shipments_async()
    
    def closeEvent(self, event):
        """Manejar cierre de ventana"""
        try:
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
