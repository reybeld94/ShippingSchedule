# ui/widgets.py - Widgets profesionales
from typing import Tuple

from PyQt6.QtWidgets import (
    QPushButton,
    QLineEdit,
    QComboBox,
    QFrame,
    QHBoxLayout,
    QLabel,
    QToolButton,
    QVBoxLayout,
    QWidget,
)
from PyQt6.QtGui import QFont
from PyQt6.QtCore import pyqtSignal, Qt
from core.config import MODERN_FONT
from .utils import apply_scaled_font
from .style_tokens import (
    COLOR_BG_SUBTLE,
    COLOR_BORDER,
    COLOR_BORDER_STRONG,
    COLOR_DANGER,
    COLOR_DANGER_HOVER,
    COLOR_DANGER_PRESSED,
    COLOR_DANGER_SOFT_BG,
    COLOR_DANGER_SOFT_BORDER,
    COLOR_DANGER_SOFT_TEXT,
    COLOR_INFO_SOFT_BG,
    COLOR_INFO_SOFT_BORDER,
    COLOR_INFO_SOFT_TEXT,
    COLOR_NEUTRAL_SOFT_BG,
    COLOR_NEUTRAL_SOFT_BORDER,
    COLOR_NEUTRAL_SOFT_TEXT,
    COLOR_PRIMARY,
    COLOR_PRIMARY_HOVER,
    COLOR_PRIMARY_PRESSED,
    COLOR_PRIMARY_SUBTLE_BG,
    COLOR_SELECTION_BG,
    COLOR_SELECTION_TEXT,
    COLOR_SUCCESS,
    COLOR_SUCCESS_HOVER,
    COLOR_SUCCESS_PRESSED,
    COLOR_SUCCESS_SOFT_BG,
    COLOR_SUCCESS_SOFT_BORDER,
    COLOR_SUCCESS_SOFT_TEXT,
    COLOR_SURFACE,
    COLOR_TEXT_DISABLED,
    COLOR_TEXT_ON_ACCENT,
    COLOR_TEXT_PRIMARY,
    COLOR_TEXT_SECONDARY,
    COLOR_WARNING,
    COLOR_WARNING_HOVER,
    COLOR_WARNING_PRESSED,
    COLOR_WARNING_SOFT_BG,
    COLOR_WARNING_SOFT_BORDER,
    COLOR_WARNING_SOFT_TEXT,
    CONTROL_HEIGHT,
    RADIUS_MD,
    RADIUS_SM,
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
        """Apply Fluent-flavored styling per button type."""
        base_style = f"""
            QPushButton {{
                border: 1px solid transparent;
                border-radius: {RADIUS_MD}px;
                padding: {self._padding_vertical}px {self._padding_horizontal}px;
                font-weight: 600;
                text-align: center;
                min-height: {self._min_height}px;
                min-width: {self._min_width}px;
            }}
            QPushButton:disabled {{
                background-color: {COLOR_BG_SUBTLE};
                border-color: {COLOR_BORDER};
                color: {COLOR_TEXT_DISABLED};
            }}
            QPushButton:focus {{
                outline: none;
            }}
        """

        if self.button_type == "primary":
            style = base_style + f"""
                QPushButton {{
                    background-color: {COLOR_PRIMARY};
                    color: {COLOR_TEXT_ON_ACCENT};
                    border-color: {COLOR_PRIMARY};
                }}
                QPushButton:hover {{
                    background-color: {COLOR_PRIMARY_HOVER};
                    border-color: {COLOR_PRIMARY_HOVER};
                }}
                QPushButton:pressed {{
                    background-color: {COLOR_PRIMARY_PRESSED};
                    border-color: {COLOR_PRIMARY_PRESSED};
                }}
            """
        elif self.button_type in ("secondary", "outline"):
            style = base_style + f"""
                QPushButton {{
                    background-color: {COLOR_SURFACE};
                    color: {COLOR_TEXT_PRIMARY};
                    border-color: {COLOR_BORDER_STRONG};
                }}
                QPushButton:hover {{
                    background-color: {COLOR_BG_SUBTLE};
                    border-color: {COLOR_BORDER_STRONG};
                }}
                QPushButton:pressed {{
                    background-color: {COLOR_BG_SUBTLE};
                    border-color: {COLOR_TEXT_SECONDARY};
                }}
            """
        elif self.button_type == "subtle":
            # Fluent subtle button: transparent, only shows on hover
            style = base_style + f"""
                QPushButton {{
                    background-color: transparent;
                    color: {COLOR_TEXT_PRIMARY};
                    border-color: transparent;
                }}
                QPushButton:hover {{
                    background-color: {COLOR_BG_SUBTLE};
                }}
                QPushButton:pressed {{
                    background-color: {COLOR_BORDER};
                }}
            """
        elif self.button_type == "success":
            style = base_style + f"""
                QPushButton {{
                    background-color: {COLOR_SUCCESS};
                    color: {COLOR_TEXT_ON_ACCENT};
                    border-color: {COLOR_SUCCESS};
                }}
                QPushButton:hover {{
                    background-color: {COLOR_SUCCESS_HOVER};
                    border-color: {COLOR_SUCCESS_HOVER};
                }}
                QPushButton:pressed {{
                    background-color: {COLOR_SUCCESS_PRESSED};
                    border-color: {COLOR_SUCCESS_PRESSED};
                }}
            """
        elif self.button_type == "danger":
            style = base_style + f"""
                QPushButton {{
                    background-color: {COLOR_DANGER};
                    color: {COLOR_TEXT_ON_ACCENT};
                    border-color: {COLOR_DANGER};
                }}
                QPushButton:hover {{
                    background-color: {COLOR_DANGER_HOVER};
                    border-color: {COLOR_DANGER_HOVER};
                }}
                QPushButton:pressed {{
                    background-color: {COLOR_DANGER_PRESSED};
                    border-color: {COLOR_DANGER_PRESSED};
                }}
            """
        elif self.button_type == "danger-outline":
            style = base_style + f"""
                QPushButton {{
                    background-color: {COLOR_SURFACE};
                    color: {COLOR_DANGER_SOFT_TEXT};
                    border-color: {COLOR_BORDER_STRONG};
                }}
                QPushButton:hover {{
                    background-color: {COLOR_DANGER_SOFT_BG};
                    border-color: {COLOR_DANGER_SOFT_BORDER};
                    color: {COLOR_DANGER_HOVER};
                }}
                QPushButton:pressed {{
                    background-color: {COLOR_DANGER_SOFT_BG};
                    border-color: {COLOR_DANGER};
                    color: {COLOR_DANGER_PRESSED};
                }}
            """
        elif self.button_type == "warning":
            style = base_style + f"""
                QPushButton {{
                    background-color: {COLOR_WARNING};
                    color: {COLOR_TEXT_ON_ACCENT};
                    border-color: {COLOR_WARNING};
                }}
                QPushButton:hover {{
                    background-color: {COLOR_WARNING_HOVER};
                    border-color: {COLOR_WARNING_HOVER};
                }}
                QPushButton:pressed {{
                    background-color: {COLOR_WARNING_PRESSED};
                    border-color: {COLOR_WARNING_PRESSED};
                }}
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
        apply_scaled_font(self, offset=3)
        self.apply_professional_style()

    def apply_professional_style(self):
        """Fluent-styled text input."""
        font_size = max(13, self.font().pointSize() + 2)
        self.setStyleSheet(
            f"""
            QLineEdit {{
                background: {COLOR_SURFACE};
                border: 1px solid {COLOR_BORDER_STRONG};
                border-radius: {RADIUS_MD}px;
                padding: {SPACE_8 - 2}px {SPACE_12}px;
                font-size: {font_size}px;
                color: {COLOR_TEXT_PRIMARY};
                selection-background-color: {COLOR_SELECTION_BG};
                selection-color: {COLOR_SELECTION_TEXT};
            }}
            QLineEdit:hover {{
                border-color: {COLOR_TEXT_SECONDARY};
            }}
            QLineEdit:focus {{
                border-color: {COLOR_PRIMARY};
                background: {COLOR_SURFACE};
                outline: none;
            }}
            QLineEdit:disabled {{
                background-color: {COLOR_BG_SUBTLE};
                color: {COLOR_TEXT_DISABLED};
                border-color: {COLOR_BORDER};
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

class PasswordLineEdit(QWidget):
    """ModernLineEdit in password echo mode with a show/hide toggle button."""

    returnPressed = pyqtSignal()

    def __init__(self, placeholder: str = "Password", parent=None):
        super().__init__(parent)
        self._visible = False

        layout = QHBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(4)

        self._edit = ModernLineEdit(placeholder)
        self._edit.setEchoMode(QLineEdit.EchoMode.Password)
        self._edit.returnPressed.connect(self.returnPressed)

        self._toggle_btn = QToolButton()
        self._toggle_btn.setText("Show")
        self._toggle_btn.setFixedWidth(48)
        self._toggle_btn.setMinimumHeight(CONTROL_HEIGHT)
        self._toggle_btn.clicked.connect(self._toggle_visibility)
        apply_scaled_font(self._toggle_btn, offset=-1)

        layout.addWidget(self._edit)
        layout.addWidget(self._toggle_btn)

    def _toggle_visibility(self) -> None:
        self._visible = not self._visible
        mode = QLineEdit.EchoMode.Normal if self._visible else QLineEdit.EchoMode.Password
        self._edit.setEchoMode(mode)
        self._toggle_btn.setText("Hide" if self._visible else "Show")

    def text(self) -> str:
        return self._edit.text()

    def setText(self, value: str) -> None:
        self._edit.setText(value)

    def clear(self) -> None:
        self._edit.clear()

    def setPlaceholderText(self, text: str) -> None:
        self._edit.setPlaceholderText(text)

    def placeholderText(self) -> str:
        return self._edit.placeholderText()

    def setEnabled(self, enabled: bool) -> None:
        super().setEnabled(enabled)
        self._edit.setEnabled(enabled)
        self._toggle_btn.setEnabled(enabled)


class ModernComboBox(QComboBox):
    def __init__(self):
        super().__init__()
        self.setMinimumHeight(CONTROL_HEIGHT)
        apply_scaled_font(self)
        self.apply_professional_style()

    def apply_professional_style(self):
        """Fluent-styled combobox."""
        font_size = max(12, self.font().pointSize() + 2)
        self.setStyleSheet(
            f"""
            QComboBox {{
                background: {COLOR_SURFACE};
                border: 1px solid {COLOR_BORDER_STRONG};
                border-radius: {RADIUS_MD}px;
                padding: {SPACE_8 - 2}px {SPACE_12}px;
                font-size: {font_size}px;
                color: {COLOR_TEXT_PRIMARY};
                min-width: 140px;
                selection-background-color: {COLOR_SELECTION_BG};
                selection-color: {COLOR_SELECTION_TEXT};
            }}
            QComboBox:hover {{
                border-color: {COLOR_TEXT_SECONDARY};
            }}
            QComboBox:focus, QComboBox:on {{
                border-color: {COLOR_PRIMARY};
                outline: none;
            }}
            QComboBox:disabled {{
                background-color: {COLOR_BG_SUBTLE};
                color: {COLOR_TEXT_DISABLED};
                border-color: {COLOR_BORDER};
            }}
            QComboBox::drop-down {{
                border: none;
                width: 24px;
                background: transparent;
            }}
            QComboBox::down-arrow {{
                image: none;
                border-left: 4px solid transparent;
                border-right: 4px solid transparent;
                border-top: 5px solid {COLOR_TEXT_SECONDARY};
                margin-right: 8px;
            }}
            QComboBox::down-arrow:on {{
                border-top-color: {COLOR_PRIMARY};
            }}
            QComboBox QAbstractItemView {{
                border: 1px solid {COLOR_BORDER_STRONG};
                border-radius: {RADIUS_MD}px;
                background: {COLOR_SURFACE};
                selection-background-color: {COLOR_PRIMARY_SUBTLE_BG};
                selection-color: {COLOR_TEXT_PRIMARY};
                padding: 4px;
                outline: none;
            }}
            QComboBox QAbstractItemView::item {{
                padding: 7px 10px;
                border-radius: {RADIUS_SM}px;
                margin: 1px 2px;
            }}
            QComboBox QAbstractItemView::item:selected {{
                background-color: {COLOR_PRIMARY_SUBTLE_BG};
                color: {COLOR_TEXT_PRIMARY};
            }}
            QComboBox QAbstractItemView::item:hover {{
                background-color: {COLOR_BG_SUBTLE};
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
        """Fluent card surface."""
        self.setStyleSheet(f"""
            QFrame {{
                background: {COLOR_SURFACE};
                border: 1px solid {COLOR_BORDER};
                border-radius: 8px;
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
        """Fluent-styled status pill."""
        palettes = {
            "success": (COLOR_SUCCESS_SOFT_BG, COLOR_SUCCESS_SOFT_BORDER, COLOR_SUCCESS_SOFT_TEXT),
            "warning": (COLOR_WARNING_SOFT_BG, COLOR_WARNING_SOFT_BORDER, COLOR_WARNING_SOFT_TEXT),
            "error":   (COLOR_DANGER_SOFT_BG, COLOR_DANGER_SOFT_BORDER, COLOR_DANGER_SOFT_TEXT),
            "info":    (COLOR_INFO_SOFT_BG, COLOR_INFO_SOFT_BORDER, COLOR_INFO_SOFT_TEXT),
            "default": (COLOR_NEUTRAL_SOFT_BG, COLOR_NEUTRAL_SOFT_BORDER, COLOR_NEUTRAL_SOFT_TEXT),
        }
        bg, border, fg = palettes.get(self.status_type, palettes["default"])
        self.setStyleSheet(
            f"""
            QLabel {{
                background-color: {bg};
                border: 1px solid {border};
                color: {fg};
                padding: 3px 10px;
                border-radius: 10px;
                font-weight: 600;
            }}
            """
        )
    
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
        
        self.setStyleSheet(f"""
            QFrame {{
                background-color: {COLOR_BORDER};
                border: none;
            }}
        """)

class ProfessionalSpinner(QLabel):
    """Indicador de carga profesional"""
    def __init__(self, size=20):
        super().__init__()
        self.size = size
        self.setFixedSize(size, size)
        self.setAlignment(Qt.AlignmentFlag.AlignCenter)
        
        self.setText("●")
        font_size = max(6, self.font().pointSize() - 2)
        self.setStyleSheet(
            f"""
            QLabel {{
                color: {COLOR_PRIMARY};
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
