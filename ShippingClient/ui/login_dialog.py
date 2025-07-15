# ui/login_dialog.py - Diálogo de autenticación profesional
import requests
import os
from PyQt6.QtWidgets import QDialog, QVBoxLayout, QHBoxLayout, QLabel, QFrame, QMessageBox, QLineEdit
from PyQt6.QtCore import Qt
from PyQt6.QtGui import QFont, QPixmap

from .widgets import ModernButton, ModernLineEdit, ProfessionalCard
from core.config import SERVER_URL, LOGIN_WIDTH, LOGIN_HEIGHT, REQUEST_TIMEOUT

class ModernLoginDialog(QDialog):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Shipping Schedule Management System")
        self.setMinimumSize(600, 600)
        self.setModal(True)
        
        # Configurar ventana sin frame personalizado
        #self.setWindowFlags(Qt.WindowType.FramelessWindowHint | Qt.WindowType.Dialog)
        
        self.setup_professional_ui()
        self.token = None
        self.user_info = None
    
    def setup_professional_ui(self):
        """Configurar interfaz profesional"""
        # Layout principal con gradiente de fondo
        main_layout = QVBoxLayout()
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.setSpacing(0)
        
        # Contenedor con fondo gradiente
        background_frame = QFrame()
        background_frame.setStyleSheet("""
            QFrame {
                background: qlineargradient(
                    x1: 0, y1: 0, x2: 1, y2: 1,
                    stop: 0 #F8FAFC,
                    stop: 1 #E2E8F0
                );
            }
        """)
        
        background_layout = QVBoxLayout(background_frame)
        background_layout.setContentsMargins(40, 60, 40, 60)
        background_layout.setAlignment(Qt.AlignmentFlag.AlignCenter)
        
        # Tarjeta principal de login
        login_card = QFrame()
        login_card.setFixedWidth(420)
        login_card.setStyleSheet("""
            QFrame {
                background: #FFFFFF;
                border-radius: 12px;
            }
        """)
        
        card_layout = QVBoxLayout(login_card)
        card_layout.setContentsMargins(40, 40, 40, 40)
        card_layout.setSpacing(20)
        
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
    
    def create_login_header(self, layout):
        """Crear header del login con logo"""
        header_layout = QVBoxLayout()
        header_layout.setSpacing(10)
        header_layout.setAlignment(Qt.AlignmentFlag.AlignCenter)
    
        # Logo (eliminar duplicación)
        logo_container = QHBoxLayout()
        logo_container.setAlignment(Qt.AlignmentFlag.AlignCenter)
    
        logo_label = QLabel()
        logo_label.setText("🚢")
        logo_label.setStyleSheet("font-size: 32px; color: #3B82F6; border: none; background: transparent;")
        logo_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        logo_container.addWidget(logo_label)
    
        # Título principal
        title_label = QLabel("Shipping Schedule")
        title_label.setFont(QFont("Roboto", 16, QFont.Weight.DemiBold))
        title_label.setStyleSheet("color: #1F2937; border: none; background: transparent;")
        title_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
    
        # Subtítulo
        subtitle_label = QLabel("Management System")
        subtitle_label.setFont(QFont("Roboto", 11))
        subtitle_label.setStyleSheet("color: #6B7280; border: none; background: transparent;")
        subtitle_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
    
        # Texto de instrucción
        instruction_label = QLabel("Please sign in to continue")
        instruction_label.setFont(QFont("Roboto", 9))
        instruction_label.setStyleSheet("color: #9CA3AF; border: none; background: transparent;")
        instruction_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
    
        header_layout.addLayout(logo_container)
        header_layout.addWidget(title_label)
        header_layout.addWidget(subtitle_label)
        header_layout.addWidget(instruction_label)
    
        layout.addLayout(header_layout)
    
    def create_login_form(self, layout):
        """Crear formulario de login"""
        form_layout = QVBoxLayout()
        form_layout.setSpacing(20)
        
        # Campo usuario
        username_layout = QVBoxLayout()
        username_layout.setSpacing(6)
        
        username_label = QLabel("Username")
        username_label.setFont(QFont("Roboto", 11, QFont.Weight.Medium))
        username_label.setStyleSheet("color: #374151;")
        
        self.username_edit = ModernLineEdit("Enter your username")
        self.username_edit.setText("admin")  # Valor por defecto para desarrollo
        
        username_layout.addWidget(username_label)
        username_layout.addWidget(self.username_edit)
        
        # Campo contraseña
        password_layout = QVBoxLayout()
        password_layout.setSpacing(6)
        
        password_label = QLabel("Password")
        password_label.setFont(QFont("Roboto", 11, QFont.Weight.Medium))
        password_label.setStyleSheet("color: #374151;")
        
        self.password_edit = ModernLineEdit("Enter your password")
        self.password_edit.setEchoMode(QLineEdit.EchoMode.Password)
        self.password_edit.setText("admin123")  # Valor por defecto para desarrollo
        
        password_layout.addWidget(password_label)
        password_layout.addWidget(self.password_edit)
        
        form_layout.addLayout(username_layout)
        form_layout.addLayout(password_layout)
        
        layout.addLayout(form_layout)
    
    def create_login_buttons(self, layout):
        """Crear botones del login"""
        button_layout = QVBoxLayout()
        button_layout.setSpacing(12)
        
        # Botón principal de login
        self.login_btn = ModernButton("Sign In", "primary")
        self.login_btn.setMinimumHeight(44)
        self.login_btn.clicked.connect(self.login)
        self.password_edit.returnPressed.connect(self.login)
        
        # Botón secundario de cancelar
        self.cancel_btn = ModernButton("Cancel", "secondary")
        self.cancel_btn.setMinimumHeight(44)
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
        separator.setStyleSheet("background-color: #E5E7EB; border: none; height: 1px;")
        separator.setFixedHeight(1)
        
        # Texto informativo
        info_label = QLabel("Secure access to shipment management")
        info_label.setFont(QFont("Roboto", 9))
        info_label.setStyleSheet("color: #9CA3AF; text-align: center;")
        info_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        
        # Status de conexión
        connection_layout = QHBoxLayout()
        connection_layout.setAlignment(Qt.AlignmentFlag.AlignCenter)
        connection_layout.setSpacing(6)
        
        connection_indicator = QLabel("●")
        connection_indicator.setFont(QFont("Arial", 10))
        connection_indicator.setStyleSheet("color: #10B981;")
        
        connection_text = QLabel("Server connection active")
        connection_text.setFont(QFont("Roboto", 9))
        connection_text.setStyleSheet("color: #6B7280;")
        
        connection_layout.addWidget(connection_indicator)
        connection_layout.addWidget(connection_text)
        
        footer_layout.addWidget(separator)
        footer_layout.addWidget(info_label)
        footer_layout.addLayout(connection_layout)
        
        layout.addLayout(footer_layout)
    
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
            response = requests.post(f"{SERVER_URL}/login", json={
                "username": username,
                "password": password
            }, timeout=REQUEST_TIMEOUT)
            
            if response.status_code == 200:
                data = response.json()
                self.token = data["access_token"]
                self.user_info = data["user_info"]
                print(f"Login successful for user: {username}")
                self.accept()
            else:
                error_data = response.json() if response.headers.get('content-type') == 'application/json' else {}
                error_message = error_data.get("detail", "Invalid credentials. Please check your username and password.")
                self.show_professional_error(error_message)
                
        except requests.exceptions.ConnectionError:
            self.show_professional_error("Unable to connect to server.\nPlease check your network connection.")
        except requests.exceptions.Timeout:
            self.show_professional_error("Connection timeout.\nPlease try again.")
        except requests.exceptions.RequestException as e:
            self.show_professional_error(f"Network error:\n{str(e)}")
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
        msg.setStyleSheet("""
            QMessageBox {
                background: #FFFFFF;
                font-family: 'Roboto';
            }
            QMessageBox QLabel {
                color: #374151;
                font-size: 13px;
                padding: 10px;
            }
            QMessageBox QPushButton {
                background: #3B82F6;
                color: white;
                border: none;
                padding: 8px 24px;
                border-radius: 6px;
                font-weight: 500;
                font-size: 12px;
                min-width: 80px;
            }
            QMessageBox QPushButton:hover {
                background: #2563EB;
            }
            QMessageBox QPushButton:pressed {
                background: #1D4ED8;
            }
        """)
        
        msg.exec()
    
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
