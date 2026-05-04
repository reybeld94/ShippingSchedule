# ui/login_dialog.py - Diálogo de autenticación profesional
import os
from PyQt6.QtWidgets import (
    QDialog,
    QVBoxLayout,
    QHBoxLayout,
    QLabel,
    QFrame,
    QMessageBox,
    QLineEdit,
    QStyle,
    QCheckBox,
)
from PyQt6.QtCore import Qt, QSize
from PyQt6.QtGui import QFont, QIcon

from .widgets import ModernButton, ModernLineEdit
from .settings_dialog import SettingsDialog
from core.settings_manager import SettingsManager
from core.api_client import RobustApiClient
from core.config import (
    get_server_url,
    LOGIN_WIDTH,
    LOGIN_HEIGHT,
    MODERN_FONT,
    ICON_PATH,
)
from .utils import apply_scaled_font, get_base_font_size, refresh_scaled_fonts
from .style_tokens import (
    COLOR_BG_APP,
    COLOR_BG_SUBTLE,
    COLOR_BORDER,
    COLOR_PRIMARY,
    COLOR_SUCCESS,
    COLOR_SUCCESS_SOFT_TEXT,
    COLOR_TEXT_PRIMARY,
    COLOR_TEXT_SECONDARY,
    COLOR_SURFACE,
    CONTROL_HEIGHT_LARGE,
    RADIUS_MD,
    SPACE_12,
    SPACE_16,
    SPACE_20,
    SPACE_24,
)

class ModernLoginDialog(QDialog):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Shipping Schedule")
        if os.path.exists(ICON_PATH):
            self.setWindowIcon(QIcon(ICON_PATH))
        self.setMinimumSize(600, 600)
        self.setModal(True)

        # Persistent settings manager
        self.settings_mgr = SettingsManager()
        
        # Configurar ventana sin frame personalizado
        #self.setWindowFlags(Qt.WindowType.FramelessWindowHint | Qt.WindowType.Dialog)
        
        self.setup_professional_ui()
        self.token = None
        self.user_info = None

        # Check connection asynchronously so UI isn't blocked
        self.check_server_connection_once()
    
    def setup_professional_ui(self):
        """Configurar interfaz profesional"""
        # Layout principal con gradiente de fondo
        main_layout = QVBoxLayout()
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.setSpacing(0)
        
        # Contenedor con fondo gradiente
        background_frame = QFrame()
        background_frame.setObjectName("loginBackground")
        background_frame.setStyleSheet("""
            QFrame#loginBackground {
                background: qlineargradient(
                    x1: 0, y1: 0, x2: 1, y2: 1,
                    stop: 0 #F5F7FA,
                    stop: 1 #E8EDF3
                );
            }
        """)
        
        background_layout = QVBoxLayout(background_frame)
        background_layout.setContentsMargins(40, 60, 40, 60)
        background_layout.setAlignment(Qt.AlignmentFlag.AlignCenter)
        
        # Tarjeta principal de login
        login_card = QFrame()
        login_card.setObjectName("loginCard")
        login_card.setFixedWidth(420)
        login_card.setStyleSheet(f"""
            QFrame#loginCard {{
                background: #FFFFFF;
                border: 1px solid #E5EAF0;
                border-radius: {RADIUS_MD}px;
            }}
        """)
        
        card_layout = QVBoxLayout(login_card)
        card_layout.setContentsMargins(SPACE_24, SPACE_24, SPACE_24, SPACE_24)
        card_layout.setSpacing(SPACE_20)
        
        # Header con logo y título
        self.create_login_header(card_layout)
        
        # Formulario de login
        self.create_login_form(card_layout)
        
        # Botones
        self.create_login_buttons(card_layout)
        
        # Footer informativo
        self.create_login_footer(card_layout)
        
        background_layout.addWidget(login_card)
        main_layout.addWidget(background_frame)

        self.setLayout(main_layout)
        # Prefill fields with last used credentials if available
        self.load_last_credentials()
    
    def create_login_header(self, layout):
        """Crear header del login con logo"""
        header_layout = QVBoxLayout()
        header_layout.setSpacing(10)
        header_layout.setAlignment(Qt.AlignmentFlag.AlignCenter)
    
        # Título principal
        title_label = QLabel("Shipping Schedule")
        apply_scaled_font(title_label, offset=6, weight=QFont.Weight.DemiBold)
        title_label.setStyleSheet(f"color: {COLOR_TEXT_PRIMARY}; border: none; background: transparent;")
        title_label.setAlignment(Qt.AlignmentFlag.AlignCenter)


        # Texto de instrucción
        instruction_label = QLabel("Please sign in to continue")
        apply_scaled_font(instruction_label, offset=-1)
        instruction_label.setStyleSheet(f"color: {COLOR_TEXT_SECONDARY}; border: none; background: transparent;")
        instruction_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
    
        header_layout.addWidget(title_label)
        header_layout.addWidget(instruction_label)
    
        layout.addLayout(header_layout)
    
    def create_login_form(self, layout):
        """Crear formulario de login"""
        form_layout = QVBoxLayout()
        form_layout.setSpacing(SPACE_20)
        
        # Campo usuario
        username_layout = QVBoxLayout()
        username_layout.setSpacing(6)
        
        username_label = QLabel("Username")
        apply_scaled_font(username_label, offset=1, weight=QFont.Weight.Medium)
        username_label.setStyleSheet(
            f"color: {COLOR_TEXT_PRIMARY}; background: transparent; border: none;"
        )

        self.username_edit = ModernLineEdit("Enter your username")
        
        username_layout.addWidget(username_label)
        username_layout.addWidget(self.username_edit)
        
        # Campo contraseña
        password_layout = QVBoxLayout()
        password_layout.setSpacing(6)
        
        password_label = QLabel("Password")
        apply_scaled_font(password_label, offset=1, weight=QFont.Weight.Medium)
        password_label.setStyleSheet(
            f"color: {COLOR_TEXT_PRIMARY}; background: transparent; border: none;"
        )

        self.password_edit = ModernLineEdit("Enter your password")
        self.password_edit.setEchoMode(QLineEdit.EchoMode.Password)

        password_layout.addWidget(password_label)
        password_layout.addWidget(self.password_edit)

        # Remember username checkbox
        self.remember_checkbox = QCheckBox("Remember username")
        apply_scaled_font(self.remember_checkbox)
        self.remember_checkbox.setChecked(False)

        form_layout.addLayout(username_layout)
        form_layout.addLayout(password_layout)
        form_layout.addWidget(self.remember_checkbox)

        layout.addLayout(form_layout)
    
    def create_login_buttons(self, layout):
        """Crear botones del login"""
        button_layout = QVBoxLayout()
        button_layout.setSpacing(12)
        
        # Botón principal de login
        self.login_btn = ModernButton("Sign In", "primary")
        self.login_btn.setMinimumHeight(CONTROL_HEIGHT_LARGE)
        self.login_btn.clicked.connect(self.login)
        self.password_edit.returnPressed.connect(self.login)
        
        # Botón secundario de cancelar
        self.cancel_btn = ModernButton("Cancel", "secondary")
        self.cancel_btn.setMinimumHeight(CONTROL_HEIGHT_LARGE)
        self.cancel_btn.clicked.connect(self.reject)
        
        button_layout.addWidget(self.login_btn)
        button_layout.addWidget(self.cancel_btn)
        
        layout.addLayout(button_layout)
    
    def create_login_footer(self, layout):
        """Crear footer informativo"""
        footer_layout = QVBoxLayout()
        footer_layout.setSpacing(8)
        footer_layout.setAlignment(Qt.AlignmentFlag.AlignCenter)
        
        # Separador visual
        separator = QFrame()
        separator.setFrameShape(QFrame.Shape.HLine)
        separator.setStyleSheet(f"background-color: {COLOR_BORDER}; border: none; height: 1px;")
        separator.setFixedHeight(1)
        
        # Status de conexión
        connection_layout = QHBoxLayout()
        connection_layout.setAlignment(Qt.AlignmentFlag.AlignCenter)
        connection_layout.setSpacing(6)
        
        self.connection_indicator = QLabel("●")
        apply_scaled_font(self.connection_indicator)
        self.connection_indicator.setStyleSheet(
            f"color: {COLOR_SUCCESS}; background: transparent; border: none;"
        )

        self.connection_text = QLabel("Server connection active")
        apply_scaled_font(self.connection_text, offset=-1)
        self.connection_text.setStyleSheet(
            f"color: {COLOR_TEXT_SECONDARY}; background: transparent; border: none;"
        )

        # Botón para abrir la configuración de servidor
        self.settings_btn = ModernButton(
            "",
            "secondary",
            min_height=20,
            min_width=20,
            padding=(0, 0),
        )
        self.settings_btn.setIcon(
            self.style().standardIcon(QStyle.StandardPixmap.SP_FileDialogDetailedView)
        )
        self.settings_btn.setIconSize(QSize(14, 14))
        self.settings_btn.setFixedSize(20, 20)
        self.settings_btn.setStyleSheet(
            f"""
            QPushButton {{
                background: transparent;
                border: none;
                border-radius: 10px;
                padding: 0px;
            }}
            QPushButton:hover {{
                background: {COLOR_BG_SUBTLE};
                border: 1px solid {COLOR_BORDER};
            }}
            QPushButton:pressed {{
                background: #E2E8F0;
            }}
            """
        )
        self.settings_btn.clicked.connect(self.open_settings_dialog)

        connection_layout.addWidget(self.connection_indicator)
        connection_layout.addWidget(self.connection_text)
        connection_layout.addWidget(self.settings_btn)

        footer_layout.addWidget(separator)
        footer_layout.addLayout(connection_layout)

        layout.addLayout(footer_layout)

    def load_last_credentials(self):
        """Fill username field with last used credentials if requested."""
        if self.settings_mgr.should_remember_credentials():
            self.username_edit.setText(self.settings_mgr.get_last_username())
            self.remember_checkbox.setChecked(True)

    def check_server_connection_once(self):
        """Check server connectivity in a background thread so UI is not blocked."""
        from PyQt6.QtCore import QThread, pyqtSignal as _pyqtSignal

        # Avoid spawning multiple concurrent checks
        existing = getattr(self, '_connection_checker', None)
        if existing is not None and existing.isRunning():
            existing.quit()
            existing.wait(500)

        checker = self
        class _ConnectionChecker(QThread):
            result_ready = _pyqtSignal(bool)
            def __init__(self, url, parent_checker, timeout=2):
                super().__init__()
                self._url = url
                self._timeout = timeout
                self.result_ready.connect(parent_checker._on_connection_checked)
            def run(self):
                try:
                    response = RobustApiClient(self._url, timeout=self._timeout, max_retries=1).get("/")
                    self.result_ready.emit(response.is_success())
                except Exception:
                    self.result_ready.emit(False)

        self._update_connection_ui("Checking...", "#F59E0B", "#F59E0B")
        self._connection_checker = _ConnectionChecker(get_server_url(), self)
        self._connection_checker.start()

    def _on_connection_checked(self, success):
        if success:
            self._update_connection_ui("Connected", COLOR_SUCCESS_SOFT_TEXT, "#10B981")
        else:
            self._update_connection_ui("Disconnected", "#EF4444", "#EF4444")

    def _update_connection_ui(self, text, text_color, indicator_color=None):
        self.connection_text.setText(text)
        self.connection_text.setStyleSheet(f"color: {text_color}; background: transparent; border: none;")
        if indicator_color:
            self.connection_indicator.setStyleSheet(f"color: {indicator_color}; background: transparent; border: none;")
    
    def login(self):
        """Realizar proceso de login"""
        username = self.username_edit.text().strip()
        password = self.password_edit.text().strip()
        
        if not username or not password:
            self.show_professional_error("Please enter both username and password")
            return
        
        # Cambiar estado del botón durante el proceso
        self.login_btn.setText("Signing in...")
        self.login_btn.setEnabled(False)
        self.username_edit.setEnabled(False)
        self.password_edit.setEnabled(False)
        
        try:
            temp_client = RobustApiClient(get_server_url(), max_retries=2)
            api_response = temp_client.login(username, password)

            if api_response.is_success():
                data = api_response.get_data()
                self.token = data["access_token"]
                self.user_info = data["user_info"]
                print(f"Login successful for user: {username}")
                self.settings_mgr.save_credentials(username, self.remember_checkbox.isChecked())
                self.accept()
            else:
                self.show_professional_error(api_response.get_error())

        except Exception as e:
            self.show_professional_error(f"Login error:\n{str(e)}")
        finally:
            # Restaurar estado del botón
            self.login_btn.setText("Sign In")
            self.login_btn.setEnabled(True)
            self.username_edit.setEnabled(True)
            self.password_edit.setEnabled(True)
    
    def show_professional_error(self, message):
        """Mostrar mensaje de error con estilo profesional"""
        msg = QMessageBox(self)
        msg.setIcon(QMessageBox.Icon.Warning)
        msg.setWindowTitle("Authentication Error")
        msg.setText(message)
        
        # Estilo profesional para el mensaje de error
        base = get_base_font_size()
        label_size = max(8, base + 3)
        button_size = max(8, base + 2)
        msg.setStyleSheet(
            f"""
            QMessageBox {{
                background: #FFFFFF;
                font-family: '{MODERN_FONT}';
            }}
            QMessageBox QLabel {{
                color: #374151;
                font-size: {label_size}px;
                padding: 10px;
            }}
            QMessageBox QPushButton {{
                background: #3B82F6;
                color: white;
                border: none;
                padding: 8px 24px;
                border-radius: 6px;
                font-weight: 500;
                font-size: {button_size}px;
                min-width: 80px;
            }}
            QMessageBox QPushButton:hover {{
                background: #2563EB;
            }}
            QMessageBox QPushButton:pressed {{
                background: #1D4ED8;
            }}
        """
        )
        
        msg.exec()

    def open_settings_dialog(self):
        """Open settings dialog for server configuration and re-check connection after."""
        dlg = SettingsDialog(self.settings_mgr)
        if dlg.exec() == QDialog.DialogCode.Accepted:
            refresh_scaled_fonts(self)
            self.check_server_connection_once()

    def keyPressEvent(self, event):
        """Manejar eventos de teclado"""
        # Permitir ESC para cerrar
        if event.key() == Qt.Key.Key_Escape:
            self.reject()
        # Enter en cualquier campo activa el login
        elif event.key() in (Qt.Key.Key_Return, Qt.Key.Key_Enter):
            self.login()
        else:
            super().keyPressEvent(event)
    
    def closeEvent(self, event):
        """Manejar evento de cierre"""
        self.reject()
