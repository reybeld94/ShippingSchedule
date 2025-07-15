# ui/widgets.py - Widgets profesionales
from PyQt6.QtWidgets import (
    QPushButton,
    QLineEdit,
    QComboBox,
    QFrame,
    QLabel,
    QVBoxLayout,
)
from PyQt6.QtGui import QFont
from PyQt6.QtCore import Qt
from core.config import MODERN_FONT

class ModernButton(QPushButton):
    def __init__(self, text, button_type="primary"):
        super().__init__(text)
        self.button_type = button_type
        self.setMinimumHeight(40)
        self.setMinimumWidth(100)
        self.setFont(QFont(MODERN_FONT, 10, QFont.Weight.Medium))
        self.apply_professional_style()
    
    def apply_professional_style(self):
        """Aplicar estilos profesionales según el tipo de botón"""
        base_style = """
            QPushButton {
                border: none;
                border-radius: 6px;
                padding: 10px 20px;
                font-weight: 500;
                letter-spacing: 0.3px;
                text-align: center;
            }
            QPushButton:disabled {
                background-color: #F3F4F6;
                color: #9CA3AF;
                
            }
        """
        
        if self.button_type == "primary":
            style = base_style + """
                QPushButton {
                    background-color: #3B82F6;
                    color: white;
                }
                QPushButton:hover {
                    background-color: #2563EB;
                }
                QPushButton:pressed {
                    background-color: #1D4ED8;
                }
            """
        elif self.button_type == "secondary":
            style = base_style + """
                QPushButton {
                    background-color: #F3F4F6;
                    color: #374151;
                    border: 1px solid #D1D5DB;
                }
                QPushButton:hover {
                    background-color: #E5E7EB;
                    border-color: #9CA3AF;
                }
                QPushButton:pressed {
                    background-color: #D1D5DB;
                }
            """
        elif self.button_type == "success":
            style = base_style + """
                QPushButton {
                    background-color: #10B981;
                    color: white;
                }
                QPushButton:hover {
                    background-color: #059669;
                }
                QPushButton:pressed {
                    background-color: #047857;
                }
            """
        elif self.button_type == "danger":
            style = base_style + """
                QPushButton {
                    background-color: #EF4444;
                    color: white;
                }
                QPushButton:hover {
                    background-color: #DC2626;
                }
                QPushButton:pressed {
                    background-color: #B91C1C;
                }
            """
        elif self.button_type == "warning":
            style = base_style + """
                QPushButton {
                    background-color: #F59E0B;
                    color: white;
                }
                QPushButton:hover {
                    background-color: #D97706;
                }
                QPushButton:pressed {
                    background-color: #B45309;
                }
            """
        
        self.setStyleSheet(style)

class ModernLineEdit(QLineEdit):
    def __init__(self, placeholder=""):
        super().__init__()
        self.setPlaceholderText(placeholder)
        self.setMinimumHeight(40)
        self.setFont(QFont(MODERN_FONT, 10))
        self.apply_professional_style()
    
    def apply_professional_style(self):
        """Aplicar estilo profesional al input"""
        self.setStyleSheet("""
            QLineEdit {
                background: #FFFFFF;
                border: 1px solid #D1D5DB;
                border-radius: 6px;
                padding: 10px 14px;
                font-size: 13px;
                color: #1F2937;
                selection-background-color: #DBEAFE;
            }
            QLineEdit:focus {
                border-color: #3B82F6;
                background: #FFFFFF;
                outline: none;
                
            }
            QLineEdit:hover {
                border-color: #9CA3AF;
            }
            QLineEdit:disabled {
                background-color: #F9FAFB;
                color: #6B7280;
                border-color: #E5E7EB;
            }
        """)

class ModernComboBox(QComboBox):
    def __init__(self):
        super().__init__()
        self.setMinimumHeight(40)
        self.setFont(QFont(MODERN_FONT, 10))
        self.apply_professional_style()
    
    def apply_professional_style(self):
        """Aplicar estilo profesional al combobox"""
        self.setStyleSheet("""
            QComboBox {
                background: #FFFFFF;
                border: 1px solid #D1D5DB;
                border-radius: 6px;
                padding: 10px 14px;
                font-size: 13px;
                color: #1F2937;
                min-width: 140px;
                selection-background-color: #DBEAFE;
            }
            QComboBox:focus {
                border-color: #3B82F6;
                outline: none;
            }
            QComboBox:hover {
                border-color: #9CA3AF;
            }
            QComboBox::drop-down {
                border: none;
                width: 30px;
                background: transparent;
            }
            QComboBox::down-arrow {
                image: none;
                border-left: 5px solid transparent;
                border-right: 5px solid transparent;
                border-top: 6px solid #6B7280;
                margin-right: 8px;
            }
            QComboBox:on {
                border-color: #3B82F6;
            }
            QComboBox::down-arrow:on {
                border-top-color: #3B82F6;
            }
            QComboBox QAbstractItemView {
                border: 1px solid #D1D5DB;
                border-radius: 6px;
                background: #FFFFFF;
                selection-background-color: #EFF6FF;
                selection-color: #1F2937;
                padding: 4px;
                outline: none;
            }
            QComboBox QAbstractItemView::item {
                padding: 8px 12px;
                border-radius: 4px;
                margin: 1px;
            }
            QComboBox QAbstractItemView::item:selected {
                background-color: #EFF6FF;
                color: #1F2937;
            }
            QComboBox QAbstractItemView::item:hover {
                background-color: #F3F4F6;
            }
        """)

class ProfessionalCard(QFrame):
    """Widget de tarjeta profesional para agrupar contenido"""
    def __init__(self, title="", parent=None):
        super().__init__(parent)
        self.setFrameStyle(QFrame.Shape.NoFrame)
        self.apply_card_style()
        
        # Layout de la tarjeta
        self.card_layout = QVBoxLayout(self)
        self.card_layout.setContentsMargins(20, 16, 20, 20)
        self.card_layout.setSpacing(12)
        
        # Título si se proporciona
        if title:
            self.title_label = QLabel(title)
            self.title_label.setFont(QFont(MODERN_FONT, 14, QFont.Weight.DemiBold))
            self.title_label.setStyleSheet("color: #1F2937; margin-bottom: 8px;")
            self.card_layout.addWidget(self.title_label)
    
    def apply_card_style(self):
        """Aplicar estilo de tarjeta profesional"""
        self.setStyleSheet("""
            QFrame {
                background: #FFFFFF;
                border: 1px solid #E5E7EB;
                border-radius: 8px;
            }
        """)
    
    def add_widget(self, widget):
        """Agregar widget al contenido de la tarjeta"""
        self.card_layout.addWidget(widget)
    
    def add_layout(self, layout):
        """Agregar layout al contenido de la tarjeta"""
        self.card_layout.addLayout(layout)

class StatusBadge(QLabel):
    """Badge profesional para mostrar estados"""
    def __init__(self, text="", status_type="default"):
        super().__init__(text)
        self.status_type = status_type
        self.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.setFont(QFont(MODERN_FONT, 9, QFont.Weight.Medium))
        self.apply_badge_style()
    
    def apply_badge_style(self):
        """Aplicar estilo según el tipo de status"""
        base_style = """
            QLabel {
                padding: 4px 12px;
                border-radius: 12px;
                font-weight: 500;
                text-transform: uppercase;
                letter-spacing: 0.5px;
            }
        """
        
        if self.status_type == "success":
            style = base_style + """
                QLabel {
                    background-color: #DCFCE7;
                    color: #166534;
                }
            """
        elif self.status_type == "warning":
            style = base_style + """
                QLabel {
                    background-color: #FEF3C7;
                    color: #92400E;
                }
            """
        elif self.status_type == "error":
            style = base_style + """
                QLabel {
                    background-color: #FEE2E2;
                    color: #991B1B;
                }
            """
        elif self.status_type == "info":
            style = base_style + """
                QLabel {
                    background-color: #DBEAFE;
                    color: #1E40AF;
                }
            """
        else:  # default
            style = base_style + """
                QLabel {
                    background-color: #F3F4F6;
                    color: #374151;
                }
            """
        
        self.setStyleSheet(style)
    
    def update_status(self, text, status_type):
        """Actualizar el texto y tipo del badge"""
        self.setText(text)
        self.status_type = status_type
        self.apply_badge_style()

class ProfessionalSeparator(QFrame):
    """Separador profesional"""
    def __init__(self, orientation="horizontal"):
        super().__init__()
        if orientation == "horizontal":
            self.setFrameShape(QFrame.Shape.HLine)
            self.setFixedHeight(1)
        else:
            self.setFrameShape(QFrame.Shape.VLine)
            self.setFixedWidth(1)
        
        self.setStyleSheet("""
            QFrame {
                background-color: #E5E7EB;
                border: none;
            }
        """)

class ProfessionalSpinner(QLabel):
    """Indicador de carga profesional"""
    def __init__(self, size=20):
        super().__init__()
        self.size = size
        self.setFixedSize(size, size)
        self.setAlignment(Qt.AlignmentFlag.AlignCenter)
        
        # Crear animación simple con texto
        self.setText("●")
        self.setStyleSheet(f"""
            QLabel {{
                color: #3B82F6;
                font-size: {size-5}px;
                font-weight: bold;
            }}
        """)
    
    def start_animation(self):
        """Iniciar animación (simplificada)"""
        self.setText("⟳")
    
    def stop_animation(self):
        """Detener animación"""
        self.setText("●")
