# main.py - Servidor principal FastAPI
from fastapi import FastAPI, Depends, HTTPException, status, WebSocket, WebSocketDisconnect, Query
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy.orm import Session
from typing import List
from datetime import timedelta, datetime
import json
import asyncio
import logging
from sqlalchemy.exc import IntegrityError, SQLAlchemyError
from sqlalchemy.orm.exc import StaleDataError
import time

# Imports locales
from database import get_db, create_tables, create_admin_user
from models import User, Shipment, AuditLog
from auth import authenticate_user, create_access_token, get_current_user, get_current_admin_user, Token, UserLogin, UserCreate
from pydantic import BaseModel

# Crear app FastAPI
app = FastAPI(title="Shipping Schedule API", version="1.0.0")

# Configuración básica de logging para depuración
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

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
        if websocket in self.active_connections:
            self.active_connections.remove(websocket)

    async def broadcast(self, message: str):
        for connection in self.active_connections.copy():
            try:
                await connection.send_text(message)
            except:
                # Conexión cerrada, remover
                self.disconnect(connection)

manager = ConnectionManager()

# Schemas para API
class ShipmentCreate(BaseModel):
    job_number: str
    job_name: str
    week: str = ""
    description: str = ""
    status: str = "partial_release"
    qc_release: str = ""
    qc_notes: str = ""
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
    qc_notes: str = None
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
    qc_notes: str
    created: str
    ship_plan: str
    shipped: str
    invoice_number: str
    shipping_notes: str
    created_by: int
    
    class Config:
        from_attributes = True

# ==== Esquemas de Usuario ====

class UserUpdate(BaseModel):
    username: str | None = None
    email: str | None = None
    password: str | None = None
    role: str | None = None
    is_active: str | None = None

class UserResponse(BaseModel):
    id: int
    username: str
    email: str
    role: str
    is_active: str

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
            "email": user.email,
            "role": user.role
        }
    }

@app.post("/register")
async def register(
    user_data: UserCreate,
    db: Session = Depends(get_db),
    current_admin: User = Depends(get_current_admin_user)
):
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
        hashed_password=hashed_password,
        role=user_data.role
    )
    
    db.add(new_user)
    db.commit()
    db.refresh(new_user)

    return {"message": "User created successfully", "user_id": new_user.id}

@app.post("/users")
async def create_user(
    user_data: UserCreate,
    db: Session = Depends(get_db),
    current_admin: User = Depends(get_current_admin_user)
):
    existing_user = db.query(User).filter(User.username == user_data.username).first()
    if existing_user:
        raise HTTPException(status_code=400, detail="Username already registered")

    from auth import get_password_hash
    hashed_password = get_password_hash(user_data.password)
    new_user = User(
        username=user_data.username,
        email=user_data.email,
        hashed_password=hashed_password,
        role=user_data.role
    )
    db.add(new_user)
    db.commit()
    db.refresh(new_user)
    return {"message": "User created successfully", "user_id": new_user.id}

@app.get("/users", response_model=List[UserResponse])
async def list_users(
    db: Session = Depends(get_db),
    current_admin: User = Depends(get_current_admin_user),
):
    users = db.query(User).all()
    return users

@app.put("/users/{user_id}", response_model=UserResponse)
async def update_user(
    user_id: int,
    user_data: UserUpdate,
    db: Session = Depends(get_db),
    current_admin: User = Depends(get_current_admin_user),
):
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    if user_data.username is not None:
        user.username = user_data.username
    if user_data.email is not None:
        user.email = user_data.email
    if user_data.role is not None:
        user.role = user_data.role
    if user_data.is_active is not None:
        user.is_active = user_data.is_active
    if user_data.password:
        from auth import get_password_hash
        user.hashed_password = get_password_hash(user_data.password)
    db.commit()
    db.refresh(user)
    return user

@app.delete("/users/{user_id}")
async def delete_user(
    user_id: int,
    db: Session = Depends(get_db),
    current_admin: User = Depends(get_current_admin_user),
):
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    db.delete(user)
    db.commit()
    return {"message": "User deleted"}

# ============ ENDPOINTS DE SHIPMENTS ============

@app.get("/shipments", response_model=List[ShipmentResponse])
async def get_shipments(db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    shipments = db.query(Shipment).all()
    return shipments

from models import AuditLog  # asegúrate de importar AuditLog arriba

# Utilidad para generar un job_number único con sufijo incremental
def generate_unique_job_number(base_job_number: str, db: Session) -> str:
    """Devuelve un job number único agregando sufijos numéricos si es necesario."""
    # Obtener todos los job_numbers que comiencen con el job ingresado
    pattern = f"{base_job_number}%"
    existing_numbers = [r[0] for r in db.query(Shipment.job_number).filter(Shipment.job_number.like(pattern)).all()]

    # Si no existe exactamente, usar el número ingresado
    if base_job_number not in existing_numbers:
        return base_job_number

    suffixes = [0]
    for number in existing_numbers:
        if number.startswith(f"{base_job_number}."):
            suffix = number[len(base_job_number) + 1 :]
            if suffix.isdigit():
                suffixes.append(int(suffix))

    next_suffix = max(suffixes) + 1
    return f"{base_job_number}.{next_suffix}"

@app.post("/shipments", response_model=ShipmentResponse)
async def create_shipment(
    shipment: ShipmentCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    if current_user.role not in ["write", "admin"]:
        raise HTTPException(status_code=403, detail="Insufficient permissions")

    max_retries = 3
    for attempt in range(max_retries):
        try:
            with db.begin():  # Transacción explícita
                # Generar job_number único
                unique_job_number = generate_unique_job_number(shipment.job_number, db)

                # Crear shipment con validación
                shipment_data = shipment.dict()
                shipment_data["job_number"] = unique_job_number

                try:
                    new_shipment = Shipment(
                        **shipment_data,
                        created_by=current_user.id,
                        last_modified_by=current_user.id,
                        version=1
                    )
                except ValueError as e:
                    raise HTTPException(status_code=400, detail=str(e))

                db.add(new_shipment)
                db.flush()  # Para obtener el ID sin commit

                # Crear audit log en la misma transacción
                log = AuditLog(
                    user_id=current_user.id,
                    action="create",
                    table_name="shipments",
                    record_id=new_shipment.id,
                    changes=json.dumps(shipment_data)
                )
                db.add(log)

                # Commit automático al salir del with
                break  # Salir del retry loop si fue exitoso

        except IntegrityError as e:
            db.rollback()
            if "duplicate key" in str(e).lower() and attempt < max_retries - 1:
                time.sleep(0.1 * (attempt + 1))  # Backoff
                continue
            raise HTTPException(status_code=400, detail="Job number already exists")
        except SQLAlchemyError as e:
            db.rollback()
            logger.error(f"Database error creating shipment: {e}")
            raise HTTPException(status_code=500, detail="Database error")
        except Exception as e:
            db.rollback()
            logger.error(f"Unexpected error creating shipment: {e}")
            raise HTTPException(status_code=500, detail="Internal server error")

    # Refrescar para obtener datos completos
    db.refresh(new_shipment)

    # Notificar después del commit exitoso
    try:
        await manager.broadcast(json.dumps({
            "type": "shipment_created",
            "data": {
                "id": new_shipment.id,
                "job_number": new_shipment.job_number,
                "action_by": current_user.username
            }
        }))
    except Exception as e:
        logger.warning(f"Failed to broadcast creation: {e}")

    return new_shipment


@app.put("/shipments/{shipment_id}", response_model=ShipmentResponse)
async def update_shipment(
    shipment_id: int,
    shipment_update: ShipmentUpdate,
    current_version: int = Query(..., description="Current version for optimistic locking"),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    if current_user.role not in ["write", "admin"]:
        raise HTTPException(status_code=403, detail="Insufficient permissions")

    try:
        with db.begin():  # Transacción explícita
            # Verificar versión para control de concurrencia
            shipment = db.query(Shipment).filter(
                Shipment.id == shipment_id,
                Shipment.version == current_version
            ).first()

            if not shipment:
                existing = db.query(Shipment).filter(Shipment.id == shipment_id).first()
                if not existing:
                    raise HTTPException(status_code=404, detail="Shipment not found")
                else:
                    raise HTTPException(
                        status_code=409,
                        detail=f"Shipment was modified by another user. Current version: {existing.version}"
                    )

            # Aplicar cambios con validación
            update_data = shipment_update.dict(exclude_unset=True)
            changes_made = {}

            for field, value in update_data.items():
                if field == "job_number" and value:
                    value = generate_unique_job_number(value, db)

                old_value = getattr(shipment, field)
                if old_value != value:
                    changes_made[field] = {"old": old_value, "new": value}
                    try:
                        setattr(shipment, field, value)
                    except ValueError as e:
                        raise HTTPException(status_code=400, detail=str(e))

            if not changes_made:
                return shipment  # No hay cambios

            # Actualizar metadatos
            shipment.version += 1
            shipment.last_modified_by = current_user.id
            shipment.updated_at = datetime.utcnow()

            # Crear audit log en la misma transacción
            log = AuditLog(
                user_id=current_user.id,
                action="update",
                table_name="shipments",
                record_id=shipment.id,
                changes=json.dumps(changes_made)
            )
            db.add(log)

            # Commit automático al salir del with

    except HTTPException:
        raise  # Re-raise HTTP exceptions
    except SQLAlchemyError as e:
        db.rollback()
        logger.error(f"Database error updating shipment: {e}")
        raise HTTPException(status_code=500, detail="Database error")
    except Exception as e:
        db.rollback()
        logger.error(f"Unexpected error updating shipment: {e}")
        raise HTTPException(status_code=500, detail="Internal server error")

    # Refrescar datos
    db.refresh(shipment)

    # Notificar cambios
    try:
        await manager.broadcast(json.dumps({
            "type": "shipment_updated",
            "data": {
                "id": shipment.id,
                "job_number": shipment.job_number,
                "version": shipment.version,
                "changes": changes_made,
                "action_by": current_user.username
            }
        }))
    except Exception as e:
        logger.warning(f"Failed to broadcast update: {e}")

    return shipment


@app.delete("/shipments/{shipment_id}")
async def delete_shipment(
    shipment_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    if current_user.role not in ["write", "admin"]:
        raise HTTPException(status_code=403, detail="Insufficient permissions")
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
        "qc_notes": shipment.qc_notes,
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