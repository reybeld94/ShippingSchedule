# models.py - Estructura de la base de datos
from sqlalchemy import Column, Integer, String, DateTime, Text, ForeignKey
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import relationship
from datetime import datetime

Base = declarative_base()

class User(Base):
    __tablename__ = "users"
    
    id = Column(Integer, primary_key=True, index=True)
    username = Column(String(50), unique=True, index=True, nullable=False)
    email = Column(String(100), unique=True, index=True, nullable=False)
    hashed_password = Column(String(255), nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)
    is_active = Column(String(10), default="active")
    
    # Relación con shipments
    created_shipments = relationship("Shipment", back_populates="created_by_user")

class Shipment(Base):
    __tablename__ = "shipments"
    
    id = Column(Integer, primary_key=True, index=True)
    job_number = Column(String(20), unique=True, index=True, nullable=False)
    shipping_list = Column(String(200), nullable=False)
    job_name = Column(String(200), nullable=False)
    week = Column(String(20))
    description = Column(Text)
    
    # Estados: final_release, partial_release, rejected, prod_updated
    status = Column(String(20), default="partial_release")
    
    # Fechas
    qc_release = Column(String(20))  # Formato: MM/DD/YY
    created = Column(String(20))     # Formato: MM/DD/YY
    ship_plan = Column(String(20))   # Formato: MM/DD/YY  
    shipped = Column(String(20))     # Formato: MM/DD/YY
    
    invoice_number = Column(String(50))
    shipping_notes = Column(Text)
    
    # Metadata
    created_by = Column(Integer, ForeignKey("users.id"))
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relaciones
    created_by_user = relationship("User", back_populates="created_shipments")

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
