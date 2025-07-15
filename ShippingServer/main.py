# main.py - Servidor principal FastAPI
from fastapi import FastAPI, Depends, HTTPException, status, WebSocket, WebSocketDisconnect, Query
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy.orm import Session
from typing import List
from datetime import timedelta
import json
import asyncio

# Imports locales
from database import get_db, create_tables, create_admin_user
from models import User, Shipment, AuditLog
from auth import authenticate_user, create_access_token, get_current_user, Token, UserLogin, UserCreate
from pydantic import BaseModel

# Crear app FastAPI
app = FastAPI(title="Shipping Schedule API", version="1.0.0")

# CORS para permitir conexiones desde clientes
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # En producción, especificar IPs exactas
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Manager para WebSocket connections
class ConnectionManager:
    def __init__(self):
        self.active_connections: List[WebSocket] = []

    async def connect(self, websocket: WebSocket):
        await websocket.accept()
        self.active_connections.append(websocket)

    def disconnect(self, websocket: WebSocket):
        self.active_connections.remove(websocket)

    async def broadcast(self, message: str):
        for connection in self.active_connections:
            try:
                await connection.send_text(message)
            except:
                # Conexión cerrada, remover
                self.active_connections.remove(connection)

manager = ConnectionManager()

# Schemas para API
class ShipmentCreate(BaseModel):
    job_number: str
    job_name: str
    week: str = ""
    description: str = ""
    status: str = "partial_release"
    qc_release: str = ""
    created: str = ""
    ship_plan: str = ""
    shipped: str = ""
    invoice_number: str = ""
    shipping_notes: str = ""

class ShipmentUpdate(BaseModel):
    job_name: str = None
    week: str = None
    description: str = None
    status: str = None
    qc_release: str = None
    created: str = None
    ship_plan: str = None
    shipped: str = None
    invoice_number: str = None
    shipping_notes: str = None

class ShipmentResponse(BaseModel):
    id: int
    job_number: str
    job_name: str
    week: str
    description: str
    status: str
    qc_release: str
    created: str
    ship_plan: str
    shipped: str
    invoice_number: str
    shipping_notes: str
    created_by: int
    
    class Config:
        from_attributes = True

# ============ ENDPOINTS DE AUTENTICACIÓN ============

@app.post("/login", response_model=Token)
async def login(user_data: UserLogin, db: Session = Depends(get_db)):
    user = authenticate_user(db, user_data.username, user_data.password)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect username or password"
        )
    
    access_token_expires = timedelta(minutes=8 * 60)  # 8 horas
    access_token = create_access_token(
        data={"sub": user.username}, expires_delta=access_token_expires
    )
    
    return {
        "access_token": access_token,
        "token_type": "bearer",
        "user_info": {
            "id": user.id,
            "username": user.username,
            "email": user.email
        }
    }

@app.post("/register")
async def register(user_data: UserCreate, db: Session = Depends(get_db)):
    # Verificar si usuario ya existe
    existing_user = db.query(User).filter(User.username == user_data.username).first()
    if existing_user:
        raise HTTPException(status_code=400, detail="Username already registered")
    
    # Crear nuevo usuario
    from auth import get_password_hash
    hashed_password = get_password_hash(user_data.password)
    new_user = User(
        username=user_data.username,
        email=user_data.email,
        hashed_password=hashed_password
    )
    
    db.add(new_user)
    db.commit()
    db.refresh(new_user)
    
    return {"message": "User created successfully", "user_id": new_user.id}

# ============ ENDPOINTS DE SHIPMENTS ============

@app.get("/shipments", response_model=List[ShipmentResponse])
async def get_shipments(db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    shipments = db.query(Shipment).all()
    return shipments

from models import AuditLog  # asegúrate de importar AuditLog arriba

@app.post("/shipments", response_model=ShipmentResponse)
async def create_shipment(
    shipment: ShipmentCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    # Verificar que job_number sea único
    existing = db.query(Shipment).filter(Shipment.job_number == shipment.job_number).first()
    if existing:
        raise HTTPException(status_code=400, detail="Job number already exists")
    
    new_shipment = Shipment(
        **shipment.dict(),
        created_by=current_user.id
    )
    
    db.add(new_shipment)
    db.commit()
    db.refresh(new_shipment)

    # 🔐 Guardar log de creación
    log = AuditLog(
        user_id=current_user.id,
        action="create",
        table_name="shipments",
        record_id=new_shipment.id,
        changes=json.dumps(shipment.dict())
    )
    db.add(log)
    db.commit()
    
    # 🔔 Notificar a todos los clientes conectados
    await manager.broadcast(json.dumps({
        "type": "shipment_created",
        "data": {
            "id": new_shipment.id,
            "job_number": new_shipment.job_number,
            "action_by": current_user.username
        }
    }))
    
    return new_shipment


@app.put("/shipments/{shipment_id}", response_model=ShipmentResponse)
async def update_shipment(
    shipment_id: int,
    shipment_update: ShipmentUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    shipment = db.query(Shipment).filter(Shipment.id == shipment_id).first()
    if not shipment:
        raise HTTPException(status_code=404, detail="Shipment not found")
    
    # Actualizar solo campos que no son None
    update_data = shipment_update.dict(exclude_unset=True)
    for field, value in update_data.items():
        setattr(shipment, field, value)
    
    db.commit()
    db.refresh(shipment)
    
    # 🔐 Registrar log de actualización
    log = AuditLog(
        user_id=current_user.id,
        action="update",
        table_name="shipments",
        record_id=shipment.id,
        changes=json.dumps(update_data)
    )
    db.add(log)
    db.commit()
    
    # 🔔 Notificar cambios
    await manager.broadcast(json.dumps({
        "type": "shipment_updated",
        "data": {
            "id": shipment.id,
            "job_number": shipment.job_number,
            "changes": update_data,
            "action_by": current_user.username
        }
    }))
    
    return shipment


@app.delete("/shipments/{shipment_id}")
async def delete_shipment(
    shipment_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    shipment = db.query(Shipment).filter(Shipment.id == shipment_id).first()
    if not shipment:
        raise HTTPException(status_code=404, detail="Shipment not found")
    
    # Backup de los datos antes de borrar
    backup_data = {
        "job_number": shipment.job_number,
        "job_name": shipment.job_name,
        "week": shipment.week,
        "description": shipment.description,
        "status": shipment.status,
        "qc_release": shipment.qc_release,
        "created": shipment.created,
        "ship_plan": shipment.ship_plan,
        "shipped": shipment.shipped,
        "invoice_number": shipment.invoice_number,
        "shipping_notes": shipment.shipping_notes
    }
    
    job_number = shipment.job_number
    db.delete(shipment)
    db.commit()

    # 🔐 Registrar log de eliminación
    log = AuditLog(
        user_id=current_user.id,
        action="delete",
        table_name="shipments",
        record_id=shipment_id,
        changes=json.dumps(backup_data)
    )
    db.add(log)
    db.commit()
    
    # 🔔 Notificar eliminación
    await manager.broadcast(json.dumps({
        "type": "shipment_deleted",
        "data": {
            "id": shipment_id,
            "job_number": job_number,
            "action_by": current_user.username
        }
    }))
    
    return {"message": "Shipment deleted successfully"}


# ============ WEBSOCKET ============

@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    await manager.connect(websocket)
    try:
        while True:
            # Mantener conexión viva
            await websocket.receive_text()
    except WebSocketDisconnect:
        manager.disconnect(websocket)

# ============ STARTUP ============

@app.on_event("startup")
async def startup_event():
    print("🚀 Iniciando Shipping Schedule Server...")
    print("📦 Creando tablas de base de datos...")
    create_tables()
    print("👤 Configurando usuario admin...")
    create_admin_user()
    print("✅ Servidor listo en http://localhost:8000")
    print("📡 WebSocket disponible en ws://localhost:8000/ws")

@app.get("/")
async def root():
    return {
        "message": "Shipping Schedule API",
        "version": "1.0.0",
        "docs": "/docs",
        "websocket": "/ws"
    }

@app.get("/audit-logs")
async def get_audit_logs(limit: int = Query(100), db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    logs = db.query(AuditLog).order_by(AuditLog.timestamp.desc()).limit(limit).all()
    return [
        {
            "user": log.user.username if log.user else "Unknown",
            "action": log.action,
            "table_name": log.table_name,
            "record_id": log.record_id,
            "changes": log.changes,
            "timestamp": log.timestamp.isoformat()
        }
        for log in logs
    ]    

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)