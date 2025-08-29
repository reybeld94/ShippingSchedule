# models.py - Estructura de la base de datos
from sqlalchemy import Column, Integer, String, DateTime, Text, ForeignKey
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import relationship, validates
from datetime import datetime

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
    created_shipments = relationship("Shipment", back_populates="created_by_user")

class Shipment(Base):
    __tablename__ = "shipments"
    
    id = Column(Integer, primary_key=True, index=True)
    job_number = Column(String(20), unique=True, index=True, nullable=False)
    job_name = Column(String(200), nullable=False)
    week = Column(String(20))
    description = Column(Text)
    
    # Estados: final_release, partial_release, rejected, prod_updated
    status = Column(String(20), default="partial_release")
    
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
    created_by_user = relationship("User", back_populates="created_shipments")

    @validates('job_number')
    def validate_job_number(self, key, value):
        if not value or not str(value).strip():
            raise ValueError("Job number is required")

        # Limpiar y validar formato
        cleaned = str(value).strip()
        base_number = cleaned.split('.')[0]  # Remover sufijos

        if not base_number.isdigit():
            raise ValueError("Job number must be numeric")

        if len(base_number) > 20:
            raise ValueError("Job number too long")

        return cleaned

    @validates('job_name')
    def validate_job_name(self, key, value):
        if not value or not str(value).strip():
            raise ValueError("Job name is required")

        cleaned = str(value).strip()
        if len(cleaned) > 200:
            raise ValueError("Job name too long")

        return cleaned

    @validates('qc_release', 'created', 'ship_plan', 'shipped')
    def validate_date_fields(self, key, value):
        if not value:
            return ""

        date_str = str(value).strip()
        if not date_str or date_str.upper() in ['N/A', 'NA', 'NULL', 'NONE']:
            return ""

        # Validar formato de fecha
        for fmt in ('%m/%d/%y', '%m/%d/%Y'):
            try:
                datetime.strptime(date_str, fmt)
                return date_str
            except ValueError:
                continue

        raise ValueError(f"Invalid date format for {key}: {date_str}. Use MM/DD/YY or MM/DD/YYYY")

    @validates('status')
    def validate_status(self, key, value):
        valid_statuses = ['final_release', 'partial_release', 'rejected', 'prod_updated']
        if value not in valid_statuses:
            raise ValueError(f"Invalid status: {value}. Must be one of {valid_statuses}")
        return value

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
