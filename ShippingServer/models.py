# models.py - Estructura de la base de datos
from sqlalchemy import Column, Integer, String, DateTime, Text, ForeignKey, Index
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import relationship, validates
from datetime import datetime
import re

Base = declarative_base()

class User(Base):
    __tablename__ = "users"
    
    id = Column(Integer, primary_key=True, index=True)
    username = Column(String(50), unique=True, index=True, nullable=False)
    email = Column(String(100), unique=True, index=True, nullable=False)
    hashed_password = Column(String(255), nullable=False)
    role = Column(String(20), default="read")
    created_at = Column(DateTime, default=datetime.utcnow)
    is_active = Column(String(10), default="active")
    
    # Relación con shipments
    created_shipments = relationship(
        "Shipment",
        back_populates="created_by_user",
        foreign_keys="Shipment.created_by",
    )

class Shipment(Base):
    __tablename__ = "shipments"

    # Índices optimizados para integridad y performance
    __table_args__ = (
        # Índice para performance (sin restricción única)
        Index('ix_shipment_job_number', 'job_number'),
        
        # Índices para control de concurrencia
        Index('ix_shipment_id_version', 'id', 'version'),
        Index('ix_shipment_version', 'version'),
        
        # Índices para consultas frecuentes
        Index('ix_shipment_status_updated', 'status', 'updated_at'),
        Index('ix_shipment_created_by', 'created_by'),
        Index('ix_shipment_last_modified', 'last_modified_by'),
    )
    
    id = Column(Integer, primary_key=True, index=True)
    job_number = Column(String(20), index=True, nullable=False)
    job_name = Column(String(200), nullable=False)
    week = Column(String(20))
    description = Column(Text)
    
    # Estados: final_release, partial_release, rejected, prod_updated
    status = Column(String(20), default="")
    
    # Fechas
    qc_release = Column(String(20))  # Formato: MM/DD/YY
    qc_notes = Column(Text)
    created = Column(String(20))     # Formato: MM/DD/YY
    ship_plan = Column(String(20))   # Formato: MM/DD/YY  
    shipped = Column(String(20))     # Formato: MM/DD/YY
    
    invoice_number = Column(String(50))
    shipping_notes = Column(Text)
    
    # Metadata
    created_by = Column(Integer, ForeignKey("users.id"))
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Control de concurrencia
    version = Column(Integer, default=1, nullable=False)
    last_modified_by = Column(Integer, ForeignKey("users.id"))
    last_modified_user = relationship("User", foreign_keys=[last_modified_by])
    
    # Relaciones
    created_by_user = relationship(
        "User",
        back_populates="created_shipments",
        foreign_keys=[created_by],
    )

    # ============ VALIDADORES DE DATOS ============

    @validates('job_number')
    def validate_job_number(self, key, value):
        """Validar formato de job number"""
        if not value or not str(value).strip():
            raise ValueError("Job number is required")
        
        cleaned = str(value).strip()
        base_number = cleaned.split('.')[0]  # Remover sufijos
        
        if not base_number.isdigit():
            raise ValueError("Job number must be numeric (with optional decimal suffix)")
        
        if len(base_number) > 15:
            raise ValueError("Job number too long (max 15 digits)")
        
        if len(base_number) == 0:
            raise ValueError("Job number cannot be empty")
        
        return cleaned

    @validates('job_name')
    def validate_job_name(self, key, value):
        """Validar job name"""
        if not value or not str(value).strip():
            raise ValueError("Job name is required")
        
        cleaned = str(value).strip()
        
        if len(cleaned) > 200:
            raise ValueError("Job name too long (max 200 characters)")
        
        if len(cleaned) < 2:
            raise ValueError("Job name too short (min 2 characters)")
        
        return cleaned

    @validates('qc_release', 'created', 'ship_plan', 'shipped')
    def validate_date_fields(self, key, value):
        """Validar campos de fecha"""
        if not value:
            return ""
        
        date_str = str(value).strip()
        
        # Valores que se consideran vacíos
        empty_values = ['', 'n/a', 'na', 'null', 'none', 'pending', 'tbd']
        if date_str.lower() in empty_values:
            return ""
        
        # Validar formato de fecha
        valid_formats = ['%m/%d/%y', '%m/%d/%Y', '%m-%d-%y', '%m-%d-%Y']
        
        for fmt in valid_formats:
            try:
                # Intentar parsear la fecha
                parsed_date = datetime.strptime(date_str, fmt)
                
                # Validar que la fecha sea razonable
                current_year = datetime.now().year
                if parsed_date.year < 1990 or parsed_date.year > current_year + 10:
                    raise ValueError(f"Invalid year in {key}: {parsed_date.year}")
                
                # Devolver en formato consistente MM/DD/YY
                return parsed_date.strftime('%m/%d/%y')
                
            except ValueError:
                continue
        
        raise ValueError(f"Invalid date format for {key}: '{date_str}'. Use MM/DD/YY, MM/DD/YYYY, MM-DD-YY, or MM-DD-YYYY")

    @validates('status')
    def validate_status(self, key, value):
        """Validar status"""
        if value is None:
            return ""

        cleaned = str(value).strip()
        if not cleaned:
            return ""

        valid_statuses = ['final_release', 'partial_release', 'rejected', 'prod_updated']

        if cleaned not in valid_statuses:
            raise ValueError(f"Invalid status: '{value}'. Must be one of: {', '.join(valid_statuses)}")

        return cleaned

    @validates('description', 'qc_notes', 'shipping_notes')
    def validate_text_fields(self, key, value):
        """Validar campos de texto largos"""
        if not value:
            return ""
        
        cleaned = str(value).strip()
        
        # Validar longitud según el campo
        max_lengths = {
            'description': 1000,
            'qc_notes': 1000,
            'shipping_notes': 1000
        }
        
        max_length = max_lengths.get(key, 500)
        
        if len(cleaned) > max_length:
            raise ValueError(f"{key.replace('_', ' ').title()} too long (max {max_length} characters)")
        
        return cleaned

    @validates('invoice_number')
    def validate_invoice_number(self, key, value):
        """Validar número de invoice"""
        if not value:
            return ""
        
        cleaned = str(value).strip()
        
        if len(cleaned) > 50:
            raise ValueError("Invoice number too long (max 50 characters)")
        
        # Validar caracteres (permitir alfanuméricos, guiones y puntos)
        if not re.match(r'^[a-zA-Z0-9\-\.]*$', cleaned):
            raise ValueError("Invoice number contains invalid characters (only letters, numbers, hyphens, and dots allowed)")
        
        return cleaned

    def __repr__(self):
        return f"<Shipment(id={self.id}, job_number='{self.job_number}', status='{self.status}', version={self.version})>"

class AuditLog(Base):
    __tablename__ = "audit_logs"
    
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"))
    action = Column(String(20))  # create, update, delete
    table_name = Column(String(50))
    record_id = Column(Integer)
    changes = Column(Text)  # JSON string with changes
    timestamp = Column(DateTime, default=datetime.utcnow)
    
    # Relación
    user = relationship("User")
