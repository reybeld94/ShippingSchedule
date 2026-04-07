# ui/widgets.py - Widgets profesionales
from typing import Tuple

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
from .utils import apply_scaled_font
from .style_tokens import (
    COLOR_BORDER,
    COLOR_BORDER_STRONG,
    COLOR_PRIMARY,
    COLOR_PRIMARY_HOVER,
    COLOR_PRIMARY_PRESSED,
    COLOR_SUCCESS,
    COLOR_SUCCESS_HOVER,
    COLOR_SUCCESS_PRESSED,
    COLOR_SUCCESS_SOFT_BG,
    COLOR_SUCCESS_SOFT_BORDER,
    COLOR_SUCCESS_SOFT_TEXT,
    COLOR_SURFACE,
    COLOR_TEXT_PRIMARY,
    COLOR_TEXT_SECONDARY,
    CONTROL_HEIGHT,
    RADIUS_MD,
    SPACE_12,
    SPACE_16,
    SPACE_20,
    SPACE_8,
)

class ModernButton(QPushButton):
    def __init__(
        self,
        text,
        button_type="primary",
        *,
        min_height: int = CONTROL_HEIGHT,
        min_width: int = 80,
        padding: Tuple[int, int] | None = None,
        font_offset: int | None = None,
        font_weight: QFont.Weight | int | None = None,
    ):
        super().__init__(text)
        self.button_type = button_type
        self._min_height = max(0, min_height)
        self._min_width = max(0, min_width)
        if padding is None:
            padding = (SPACE_8, SPACE_16)
        self._padding_vertical = max(0, padding[0])
        self._padding_horizontal = max(0, padding[1])
        self.setMinimumHeight(self._min_height)
        self.setMinimumWidth(self._min_width)
        self._font_offset = 0 if font_offset is None else font_offset
        self._font_weight = (
            QFont.Weight.Medium if font_weight is None else font_weight
        )
        apply_scaled_font(self, offset=self._font_offset, weight=self._font_weight)
        self.apply_professional_style()

    def apply_professional_style(self):
        """Aplicar estilos profesionales según el tipo de botón"""
        base_style = f"""
            QPushButton {{
                border: 1px solid transparent;
                border-radius: {RADIUS_MD}px;
                padding: {self._padding_vertical}px {self._padding_horizontal}px;
                font-weight: 500;
                letter-spacing: 0.3px;
                text-align: center;
                min-height: {self._min_height}px;
                min-width: {self._min_width}px;
            }}
            QPushButton:disabled {{
                background-color: #F1F5F9;
                border-color: {COLOR_BORDER};
                color: #94A3B8;
            }}
        """

        if self.button_type == "primary":
            style = base_style + f"""
                QPushButton {{
                    background-color: {COLOR_PRIMARY};
                    color: #FFFFFF;
                }}
                QPushButton:hover {{
                    background-color: {COLOR_PRIMARY_HOVER};
                }}
                QPushButton:pressed {{
                    background-color: {COLOR_PRIMARY_PRESSED};
                }}
            """
        elif self.button_type in ("secondary", "outline"):
            style = base_style + f"""
                QPushButton {{
                    background-color: {COLOR_SURFACE};
                    color: {COLOR_TEXT_SECONDARY};
                    border-color: {COLOR_BORDER};
                }}
                QPushButton:hover {{
                    background-color: #F8FAFC;
                    border-color: {COLOR_BORDER_STRONG};
                }}
                QPushButton:pressed {{
                    background-color: #E2E8F0;
                    border-color: {COLOR_BORDER_STRONG};
                }}
            """
        elif self.button_type == "success":
            style = base_style + f"""
                QPushButton {{
                    background-color: {COLOR_SUCCESS};
                    color: #FFFFFF;
                }}
                QPushButton:hover {{
                    background-color: {COLOR_SUCCESS_HOVER};
                }}
                QPushButton:pressed {{
                    background-color: {COLOR_SUCCESS_PRESSED};
                }}
            """
        elif self.button_type == "danger":
            style = base_style + """
                QPushButton {
                    background-color: #DC2626;
                    color: #FFFFFF;
                }
                QPushButton:hover {
                    background-color: #B91C1C;
                }
                QPushButton:pressed {
                    background-color: #991B1B;
                }
            """
        elif self.button_type == "danger-outline":
            style = base_style + """
                QPushButton {
                    background-color: #FFFFFF;
                    color: #B91C1C;
                    border-color: #E5E7EB;
                }
                QPushButton:hover {
                    background-color: #FEF2F2;
                    border-color: #F1F5F9;
                }
                QPushButton:pressed {
                    background-color: #FDE8E8;
                    border-color: #F1F5F9;
                }
            """
        elif self.button_type == "warning":
            style = base_style + """
                QPushButton {
                    background-color: #F59E0B;
                    color: #FFFFFF;
                }
                QPushButton:hover {
                    background-color: #D97706;
                }
                QPushButton:pressed {
                    background-color: #B45309;
                }
            """
        else:
            style = base_style

        self.setStyleSheet(style)

    def changeEvent(self, event):  # type: ignore[override]
        from PyQt6.QtCore import QEvent

        if event.type() == QEvent.Type.FontChange:
            if getattr(self, "_handling_font_change", False):
                super().changeEvent(event)
                return
            self._handling_font_change = True
            try:
                apply_scaled_font(
                    self,
                    offset=getattr(self, "_font_offset", 0),
                    weight=getattr(self, "_font_weight", QFont.Weight.Medium),
                )
                self.apply_professional_style()
            finally:
                self._handling_font_change = False
        super().changeEvent(event)

class ModernLineEdit(QLineEdit):
    def __init__(self, placeholder=""):
        super().__init__()
        self.setPlaceholderText(placeholder)
        self.setMinimumHeight(CONTROL_HEIGHT)
        apply_scaled_font(self, offset=2)
        self.apply_professional_style()

    def apply_professional_style(self):
        """Aplicar estilo profesional al input"""
        font_size = max(10, self.font().pointSize() + 4)
        placeholder_font_size = font_size
        self.setStyleSheet(
            f"""
            QLineEdit {{
                background: {COLOR_SURFACE};
                border: 1px solid {COLOR_BORDER};
                border-radius: {RADIUS_MD}px;
                padding: {SPACE_8}px {SPACE_12}px;
                font-size: {font_size}px;
                color: {COLOR_TEXT_PRIMARY};
                selection-background-color: #DBEAFE;
            }}
            QLineEdit::placeholder {{
                color: #9CA3AF;
                font-size: {placeholder_font_size}px;
            }}
            QLineEdit:focus {{
                border-color: {COLOR_PRIMARY};
                background: {COLOR_SURFACE};
                outline: none;

            }}
            QLineEdit:hover {{
                border-color: {COLOR_BORDER_STRONG};
            }}
            QLineEdit:disabled {{
                background-color: #F9FAFB;
                color: #6B7280;
                border-color: #E5E7EB;
            }}
        """
        )

    def changeEvent(self, event):  # type: ignore[override]
        from PyQt6.QtCore import QEvent

        if event.type() == QEvent.Type.FontChange:
            if getattr(self, "_handling_font_change", False):
                super().changeEvent(event)
                return
            self._handling_font_change = True
            try:
                apply_scaled_font(self)
                self.apply_professional_style()
            finally:
                self._handling_font_change = False
        super().changeEvent(event)

class ModernComboBox(QComboBox):
    def __init__(self):
        super().__init__()
        self.setMinimumHeight(CONTROL_HEIGHT)
        apply_scaled_font(self)
        self.apply_professional_style()

    def apply_professional_style(self):
        """Aplicar estilo profesional al combobox"""
        font_size = max(8, self.font().pointSize() + 3)
        self.setStyleSheet(
            f"""
            QComboBox {{
                background: {COLOR_SURFACE};
                border: 1px solid {COLOR_BORDER};
                border-radius: {RADIUS_MD}px;
                padding: {SPACE_8}px {SPACE_12}px;
                font-size: {font_size}px;
                color: {COLOR_TEXT_PRIMARY};
                min-width: 140px;
                selection-background-color: #DBEAFE;
            }}
            QComboBox:focus {{
                border-color: {COLOR_PRIMARY};
                outline: none;
            }}
            QComboBox:hover {{
                border-color: {COLOR_BORDER_STRONG};
            }}
            QComboBox::drop-down {{
                border: none;
                width: 30px;
                background: transparent;
            }}
            QComboBox::down-arrow {{
                image: none;
                border-left: 5px solid transparent;
                border-right: 5px solid transparent;
                border-top: 6px solid #6B7280;
                margin-right: 8px;
            }}
            QComboBox:on {{
                border-color: #3B82F6;
            }}
            QComboBox::down-arrow:on {{
                border-top-color: #3B82F6;
            }}
            QComboBox QAbstractItemView {{
                border: 1px solid {COLOR_BORDER};
                border-radius: {RADIUS_MD}px;
                background: {COLOR_SURFACE};
                selection-background-color: #EFF6FF;
                selection-color: #1F2937;
                padding: 4px;
                outline: none;
            }}
            QComboBox QAbstractItemView::item {{
                padding: 8px 12px;
                border-radius: {SPACE_8}px;
                margin: 1px;
            }}
            QComboBox QAbstractItemView::item:selected {{
                background-color: #EFF6FF;
                color: #1F2937;
            }}
            QComboBox QAbstractItemView::item:hover {{
                background-color: #F3F4F6;
            }}
        """
        )

    def changeEvent(self, event):  # type: ignore[override]
        from PyQt6.QtCore import QEvent

        if event.type() == QEvent.Type.FontChange:
            if getattr(self, "_handling_font_change", False):
                super().changeEvent(event)
                return
            self._handling_font_change = True
            try:
                apply_scaled_font(self)
                self.apply_professional_style()
            finally:
                self._handling_font_change = False
        super().changeEvent(event)

class ProfessionalCard(QFrame):
    """Widget de tarjeta profesional para agrupar contenido"""
    def __init__(self, title="", parent=None):
        super().__init__(parent)
        self.setFrameStyle(QFrame.Shape.NoFrame)
        self.apply_card_style()
        
        # Layout de la tarjeta
        self.card_layout = QVBoxLayout(self)
        self.card_layout.setContentsMargins(SPACE_20, SPACE_16, SPACE_20, SPACE_20)
        self.card_layout.setSpacing(SPACE_12)
        
        # Título si se proporciona
        if title:
            self.title_label = QLabel(title)
            apply_scaled_font(self.title_label, offset=4, weight=QFont.Weight.DemiBold)
            self.title_label.setStyleSheet(f"color: {COLOR_TEXT_PRIMARY}; margin-bottom: {SPACE_8}px;")
            self.card_layout.addWidget(self.title_label)
    
    def apply_card_style(self):
        """Aplicar estilo de tarjeta profesional"""
        self.setStyleSheet(f"""
            QFrame {{
                background: {COLOR_SURFACE};
                border: 1px solid {COLOR_BORDER};
                border-radius: {RADIUS_MD}px;
            }}
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
        apply_scaled_font(self, offset=-1, weight=QFont.Weight.Medium)
        self.apply_badge_style()
    
    def apply_badge_style(self):
        """Aplicar estilo según el tipo de status"""
        base_style = """
            QLabel {
                padding: 4px 10px;
                border-radius: 10px;
                border: 1px solid transparent;
                font-weight: 500;
                text-transform: uppercase;
                letter-spacing: 0.5px;
            }
        """
        
        if self.status_type == "success":
            style = base_style + f"""
                QLabel {
                    background-color: {COLOR_SUCCESS_SOFT_BG};
                    border-color: {COLOR_SUCCESS_SOFT_BORDER};
                    color: {COLOR_SUCCESS_SOFT_TEXT};
                }
            """
        elif self.status_type == "warning":
            style = base_style + """
                QLabel {
                    background-color: #FFFBEB;
                    border-color: #FDE68A;
                    color: #92400E;
                }
            """
        elif self.status_type == "error":
            style = base_style + """
                QLabel {
                    background-color: #FEF2F2;
                    border-color: #FECACA;
                    color: #B91C1C;
                }
            """
        elif self.status_type == "info":
            style = base_style + """
                QLabel {
                    background-color: #EFF6FF;
                    border-color: #BFDBFE;
                    color: #1D4ED8;
                }
            """
        else:  # default
            style = base_style + """
                QLabel {
                    background-color: #F1F5F9;
                    border-color: #CBD5E1;
                    color: #475569;
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
        font_size = max(6, self.font().pointSize() - 2)
        self.setStyleSheet(
            f"""
            QLabel {{
                color: #3B82F6;
                font-size: {font_size}px;
                font-weight: bold;
            }}
        """
        )
    
    def start_animation(self):
        """Iniciar animación (simplificada)"""
        self.setText("⟳")
    
    def stop_animation(self):
        """Detener animación"""
        self.setText("●")
