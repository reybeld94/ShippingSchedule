# ui/shipment_dialog.py - Diálogo profesional para crear/editar shipments
import os
from PyQt6.QtWidgets import (
    QDialog,
    QVBoxLayout,
    QHBoxLayout,
    QGridLayout,
    QLabel,
    QFrame,
    QScrollArea,
    QWidget,
    QTextEdit,
    QMessageBox,
    QStyle,
)
from PyQt6.QtGui import QFont, QPixmap
from PyQt6.QtCore import Qt

from .widgets import ModernButton, ModernLineEdit, ModernComboBox, ProfessionalCard, StatusBadge
from core.api_client import RobustApiClient
from core.config import (
    DIALOG_WIDTH,
    DIALOG_HEIGHT,
    MODERN_FONT,
    LOGO_PATH,
)

class ModernShipmentDialog(QDialog):
    def __init__(self, shipment_data=None, api_client: RobustApiClient | None = None):
        super().__init__()
        self.api_client = api_client
        self.shipment_data = shipment_data
        
        # Configurar ventana
        title = "Create New Shipment" if not shipment_data else "Edit Shipment"
        self.setWindowTitle(title)
        self.setFixedSize(DIALOG_WIDTH, DIALOG_HEIGHT)
        self.setModal(True)
        
        print(f"Inicializando diálogo profesional: {title}")
        
        try:
            self.setup_professional_ui()
            
            if shipment_data:
                self.populate_form(shipment_data)
                
            print("Diálogo de shipment profesional inicializado exitosamente")
        except Exception as e:
            print(f"Error inicializando diálogo de shipment: {e}")
            import traceback
            traceback.print_exc()
    
    def setup_professional_ui(self):
        """Configurar interfaz profesional"""
        # Layout principal
        main_layout = QVBoxLayout()
        main_layout.setContentsMargins(20, 20, 20, 20)
        main_layout.setSpacing(20)
        
        # Header profesional
        self.create_professional_header(main_layout)
        
        # Contenido principal con splitter
        self.create_main_content(main_layout)
        
        # Footer con botones
        self.create_footer_buttons(main_layout)
        
        self.setLayout(main_layout)
        
        # Tema general profesional
        self.apply_professional_theme()
    
    def create_professional_header(self, layout):
        """Crear header profesional"""
        header_frame = QFrame()
        header_frame.setFixedHeight(70)
        header_frame.setStyleSheet("""
            QFrame {
                background-color: #FFFFFF;
                border: none;
            }
        """)
        
        header_layout = QHBoxLayout(header_frame)
        header_layout.setContentsMargins(20, 15, 20, 15)
        
        # Icono y título
        icon_title_layout = QHBoxLayout()
        icon_title_layout.setSpacing(15)
        
        # Icono (usando logo si está disponible)
        icon_label = QLabel()

        if os.path.exists(LOGO_PATH):
            pixmap = QPixmap(LOGO_PATH)
            scaled_pixmap = pixmap.scaled(40, 40, Qt.AspectRatioMode.KeepAspectRatio, Qt.TransformationMode.SmoothTransformation)
            icon_label.setPixmap(scaled_pixmap)
        else:
            icon_label.setText("📋")
            icon_label.setStyleSheet("font-size: 24px;")
        
        # Información del título
        title_layout = QVBoxLayout()
        title_layout.setSpacing(2)
        
        title_text = "Create New Shipment" if not self.shipment_data else "Edit Shipment"
        title_label = QLabel(title_text)
        title_label.setFont(QFont(MODERN_FONT, 18, QFont.Weight.DemiBold))
        title_label.setStyleSheet("color: #1F2937;")
        
        subtitle_text = "Enter shipment details below" if not self.shipment_data else f"Modifying Job #{self.shipment_data.get('job_number', '')}"
        subtitle_label = QLabel(subtitle_text)
        subtitle_label.setFont(QFont(MODERN_FONT, 11))
        subtitle_label.setStyleSheet("color: #6B7280;")
        
        title_layout.addWidget(title_label)
        title_layout.addWidget(subtitle_label)
        
        icon_title_layout.addWidget(icon_label)
        icon_title_layout.addLayout(title_layout)
        
        # Status badge si estamos editando
        if self.shipment_data:
            current_status = self.shipment_data.get("status", "")
            status_badge = StatusBadge(current_status.replace("_", " ").title(), self.get_status_type(current_status))
            
            header_layout.addLayout(icon_title_layout)
            header_layout.addStretch()
            header_layout.addWidget(status_badge)
        else:
            header_layout.addLayout(icon_title_layout)
            header_layout.addStretch()
        
        layout.addWidget(header_frame)
    
    def get_status_type(self, status):
        """Obtener tipo de status para el badge"""
        status_types = {
            "final_release": "success",
            "partial_release": "warning",
            "rejected": "error",
            "prod_updated": "info"
        }
        return status_types.get(status, "default")
    
    def create_main_content(self, layout):
        """Crear contenido principal con scroll"""
        # Scroll area para el formulario
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.Shape.NoFrame)
        scroll.setStyleSheet("""
            QScrollArea {
                background: transparent;
                border: none;
            }}
            QScrollBar:vertical {
                background: #F3F4F6;
                width: 8px;
                border-radius: 4px;
            }}
            QScrollBar::handle:vertical {
                background: #D1D5DB;
                border-radius: 4px;
                min-height: 20px;
            }}
            QScrollBar::handle:vertical:hover {
                background: #9CA3AF;
            }
        """)
        
        # Widget contenedor del formulario
        form_container = QWidget()
        form_layout = QVBoxLayout(form_container)
        form_layout.setContentsMargins(10, 10, 10, 10)
        form_layout.setSpacing(20)
        
        # Sección de información básica
        self.create_basic_info_section(form_layout)
        
        # Sección de fechas
        self.create_dates_section(form_layout)
        
        # Sección de detalles adicionales
        self.create_additional_details_section(form_layout)
        
        scroll.setWidget(form_container)
        layout.addWidget(scroll)
    
    def create_basic_info_section(self, layout):
        """Crear sección de información básica"""
        basic_card = ProfessionalCard("Basic Information")
        
        # Grid para campos básicos
        grid_layout = QGridLayout()
        grid_layout.setSpacing(15)
        grid_layout.setContentsMargins(0, 10, 0, 0)
        
        # Fila 1: Job Number y Job Name
        grid_layout.addWidget(self.create_field_label("Job Number", required=True), 0, 0)
        self.job_number_edit = ModernLineEdit("e.g., 38465")
        grid_layout.addWidget(self.job_number_edit, 0, 1)
        
        grid_layout.addWidget(self.create_field_label("Job Name", required=True), 0, 2)
        self.job_name_edit = ModernLineEdit("e.g., Macy's Project")
        grid_layout.addWidget(self.job_name_edit, 0, 3)
        
        # Fila 3: Status
        grid_layout.addWidget(self.create_field_label("Status"), 2, 0)
        self.status_combo = ModernComboBox()
        status_options = [
            "",
            "Partial Release",
            "Final Release",
            "Rejected",
        ]
        self.status_combo.addItems(status_options)
        grid_layout.addWidget(self.status_combo, 2, 1)

        # Fila 4: Description (span completo)
        grid_layout.addWidget(self.create_field_label("Description"), 3, 0)
        self.description_edit = self.create_professional_text_edit(80)
        grid_layout.addWidget(self.description_edit, 3, 1, 1, 3)

        # Fila 5: QC Notes debajo de Description
        grid_layout.addWidget(self.create_field_label("QC Notes"), 4, 0)
        self.qc_notes_edit = self.create_professional_text_edit(60)
        grid_layout.addWidget(self.qc_notes_edit, 4, 1, 1, 3)
        
        basic_card.add_layout(grid_layout)
        layout.addWidget(basic_card)
    
    def create_dates_section(self, layout):
        """Crear sección de fechas"""
        dates_card = ProfessionalCard("Important Dates")
        
        # Grid para fechas
        dates_grid = QGridLayout()
        dates_grid.setSpacing(15)
        dates_grid.setContentsMargins(0, 10, 0, 0)
        
        # Fila 1: QC Release y Crated
        dates_grid.addWidget(self.create_field_label("QC Release"), 0, 0)
        self.qc_release_edit = ModernLineEdit("MM/DD/YY")
        dates_grid.addWidget(self.qc_release_edit, 0, 1)

        dates_grid.addWidget(self.create_field_label("Crated"), 0, 2)
        self.created_edit = ModernLineEdit("MM/DD/YY")
        dates_grid.addWidget(self.created_edit, 0, 3)

        # Fila 2: Ship Plan y Shipped
        dates_grid.addWidget(self.create_field_label("Ship Plan"), 1, 0)
        self.ship_plan_edit = ModernLineEdit("MM/DD/YY")
        dates_grid.addWidget(self.ship_plan_edit, 1, 1)

        dates_grid.addWidget(self.create_field_label("Shipped"), 1, 2)
        self.shipped_edit = ModernLineEdit("MM/DD/YY")
        dates_grid.addWidget(self.shipped_edit, 1, 3)
        
        dates_card.add_layout(dates_grid)
        layout.addWidget(dates_card)
    
    def create_additional_details_section(self, layout):
        """Crear sección de detalles adicionales"""
        details_card = ProfessionalCard("Additional Details")
        
        details_layout = QGridLayout()
        details_layout.setSpacing(15)
        details_layout.setContentsMargins(0, 10, 0, 0)
        
        # Invoice Number
        details_layout.addWidget(self.create_field_label("Invoice Number"), 0, 0)
        self.invoice_edit = ModernLineEdit("Invoice number")
        details_layout.addWidget(self.invoice_edit, 0, 1, 1, 3)
        
        # Notes
        details_layout.addWidget(self.create_field_label("Notes"), 1, 0)
        self.notes_edit = self.create_professional_text_edit(60)
        details_layout.addWidget(self.notes_edit, 1, 1, 1, 3)
        
        details_card.add_layout(details_layout)
        layout.addWidget(details_card)
    
    def create_field_label(self, text, required=False):
        """Crear label profesional para campo"""
        label = QLabel(text + (" *" if required else ""))
        label.setFont(QFont(MODERN_FONT, 11, QFont.Weight.Medium))
        
        if required:
            label.setStyleSheet("""
                color: #1F2937;
                border: none;
                background: transparent;
            """)
        else:
            label.setStyleSheet("color: #374151;")
        
        return label
    
    def create_professional_text_edit(self, height):
        """Crear QTextEdit con estilo profesional"""
        text_edit = QTextEdit()
        text_edit.setMaximumHeight(height)
        text_edit.setStyleSheet(f"""
            QTextEdit {{
                background: #FFFFFF;
                border: 1px solid #D1D5DB;
                border-radius: 6px;
                padding: 10px;
                font-family: '{MODERN_FONT}';
                font-size: 13px;
                color: #1F2937;
                selection-background-color: #DBEAFE;
            }}
            QTextEdit:focus {{
                border-color: #3B82F6;
                outline: none;
            }}
            QTextEdit:hover {{
                border-color: #9CA3AF;
            }}
        """)
        return text_edit
    
    def create_footer_buttons(self, layout):
        """Crear botones del footer"""
        footer_frame = QFrame()
        footer_frame.setFixedHeight(70)
        footer_frame.setStyleSheet("""
            QFrame {
                background: #F9FAFB;
                border: none;
                border-top: 1px solid #E5E7EB;
            }
        """)
        
        footer_layout = QHBoxLayout(footer_frame)
        footer_layout.setContentsMargins(20, 15, 20, 15)
        footer_layout.setSpacing(12)
        
        # Botones
        self.cancel_btn = ModernButton("Cancel", "secondary")
        self.cancel_btn.setMinimumWidth(120)
        self.cancel_btn.setIcon(
            self.style().standardIcon(QStyle.StandardPixmap.SP_DialogCancelButton)
        )
        
        save_text = "Create Shipment" if not self.shipment_data else "Update Shipment"
        self.save_btn = ModernButton(save_text, "primary")
        self.save_btn.setMinimumWidth(150)
        self.save_btn.setIcon(
            self.style().standardIcon(QStyle.StandardPixmap.SP_DialogApplyButton)
        )
        
        # Conectar eventos
        self.cancel_btn.clicked.connect(self.reject)
        self.save_btn.clicked.connect(self.save_shipment)
        
        footer_layout.addStretch()
        footer_layout.addWidget(self.cancel_btn)
        footer_layout.addWidget(self.save_btn)
        
        layout.addWidget(footer_frame)
    
    def apply_professional_theme(self):
        """Aplicar tema profesional"""
        self.setStyleSheet(f"""
            QDialog {{
                background: #F3F4F6;
                font-family: '{MODERN_FONT}', sans-serif;
            }}
            QLabel {{
                color: #374151;
            }}
        """)
    
    def populate_form(self, data):
        """Poblar formulario con datos existentes"""
        try:
            # Convertir valores None a cadena vacía antes de asignar al widget
            def safe_str(value):
                return "" if value is None else str(value)

            self.job_number_edit.setText(safe_str(data.get("job_number")))
            self.job_number_edit.setEnabled(False)  # No editable en modo edición
            self.job_name_edit.setText(safe_str(data.get("job_name")))
            self.description_edit.setPlainText(safe_str(data.get("description")))
            
            # Mapear status del servidor al combo
            status = data.get("status") or ""
            status_map = {
                "": "",
                "partial_release": "Partial Release",
                "final_release": "Final Release",
                "rejected": "Rejected",
                "prod_updated": "Production Updated"
            }
            combo_text = status_map.get(status, "")
            if combo_text and self.status_combo.findText(combo_text) == -1:
                # Permitir mostrar estados heredados que ya no están disponibles para nuevos shipments
                self.status_combo.addItem(combo_text)
            index = self.status_combo.findText(combo_text)
            if index >= 0:
                self.status_combo.setCurrentIndex(index)
            else:
                self.status_combo.setCurrentIndex(0)
            
            self.qc_release_edit.setText(safe_str(data.get("qc_release")))
            self.qc_notes_edit.setPlainText(safe_str(data.get("qc_notes")))
            self.created_edit.setText(safe_str(data.get("created")))
            self.ship_plan_edit.setText(safe_str(data.get("ship_plan")))
            self.shipped_edit.setText(safe_str(data.get("shipped")))
            self.invoice_edit.setText(safe_str(data.get("invoice_number")))
            self.notes_edit.setPlainText(safe_str(data.get("shipping_notes")))
            
            print("Formulario poblado con datos existentes")
        except Exception as e:
            print(f"Error poblando formulario: {e}")
    
    def save_shipment(self):
        """Guardar shipment con validaciones"""
        try:
            # Guardar el texto original del botón por si se necesita restaurar
            original_text = self.save_btn.text()

            # Validaciones
            if not self.job_number_edit.text().strip():
                self.show_professional_error("Job Number is required")
                self.job_number_edit.setFocus()
                return
            if not self.job_name_edit.text().strip():
                self.show_professional_error("Job Name is required")
                self.job_name_edit.setFocus()
                return
            
            # Mapear status del combo al servidor
            combo_status = self.status_combo.currentText()
            status_map = {
                "": "",
                "Partial Release": "partial_release",
                "Final Release": "final_release",
                "Rejected": "rejected",
                "Production Updated": "prod_updated"
            }
            actual_status = status_map.get(combo_status, "")
            
            # Preparar datos
            data = {
                "job_number": self.job_number_edit.text().strip(),
                "job_name": self.job_name_edit.text().strip(),
                "description": self.description_edit.toPlainText().strip(),
                "status": actual_status,
                "qc_release": self.qc_release_edit.text().strip(),
                "qc_notes": self.qc_notes_edit.toPlainText().strip(),
                "created": self.created_edit.text().strip(),
                "ship_plan": self.ship_plan_edit.text().strip(),
                "shipped": self.shipped_edit.text().strip(),
                "invoice_number": self.invoice_edit.text().strip(),
                "shipping_notes": self.notes_edit.toPlainText().strip()
            }
            
            print(f"Guardando shipment: {data['job_number']}")

            # Cambiar estado del botón
            self.save_btn.setText("Saving...")
            self.save_btn.setEnabled(False)
            
            if self.shipment_data:  # Editar
                api_response = self.api_client.update_shipment(self.shipment_data['id'], data)
            else:  # Crear nuevo
                api_response = self.api_client.create_shipment(data)

            if api_response.is_success():
                print("Shipment guardado exitosamente")
                self.accept()
            else:
                self.show_professional_error(f"Failed to save shipment:\n{api_response.get_error()}")

        except Exception as e:
            print(f"Error guardando shipment: {e}")
            self.show_professional_error(f"Error saving shipment:\n{str(e)}")
        finally:
            self.save_btn.setText(original_text)
            self.save_btn.setEnabled(True)
    
    def show_professional_error(self, message):
        """Mostrar mensaje de error profesional"""
        msg = QMessageBox(self)
        msg.setIcon(QMessageBox.Icon.Warning)
        msg.setWindowTitle("Validation Error")
        msg.setText(message)
        
        # Estilo profesional
        msg.setStyleSheet(f"""
            QMessageBox {{
                background: #FFFFFF;
                font-family: '{MODERN_FONT}';
            }}
            QMessageBox QLabel {{
                color: #374151;
                font-size: 13px;
                padding: 10px;
            }}
            QMessageBox QPushButton {{
                background: #3B82F6;
                color: white;
                border: none;
                padding: 8px 24px;
                border-radius: 6px;
                font-weight: 500;
                font-size: 12px;
                min-width: 80px;
            }}
            QMessageBox QPushButton:hover {{
                background: #2563EB;
            }}
        """)
        
        msg.exec()
