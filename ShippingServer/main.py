# main.py - Servidor principal FastAPI
from fastapi import FastAPI, Depends, HTTPException, status, WebSocket, WebSocketDisconnect, Query
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy.orm import Session
from typing import List
from datetime import timedelta, datetime, date
import json
import asyncio
import logging
from sqlalchemy.exc import IntegrityError, SQLAlchemyError
from sqlalchemy.orm.exc import StaleDataError

# Imports locales
from database import get_db, create_tables, create_admin_user
from models import User, Shipment, AuditLog, ShippingLog, AppConnectionSettings
from auth import authenticate_user, create_access_token, get_current_user, get_current_admin_user, Token, UserLogin, UserCreate
from pydantic import BaseModel
from fedex_service import FedExService

# Crear app FastAPI
app = FastAPI(title="Shipping Schedule API", version="1.0.0")

# Configuración básica de logging para depuración
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)
fedex_service = FedExService()

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
    status: str = ""
    qc_release: str = ""
    qc_notes: str = ""
    created: str = ""
    ship_plan: str = ""
    shipped: str = ""
    invoice_number: str = ""
    shipping_notes: str = ""
    tracking_number: str = ""
    address: bool = False

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
    tracking_number: str = None
    address: bool = None

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
    tracking_number: str
    address: bool
    created_by: int
    version: int
    last_modified_by: int | None = None

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


class FedExConnectionSettingsUpdate(BaseModel):
    enabled: bool = False
    apiKey: str = ""
    secretKey: str = ""
    baseUrl: str = ""


class FedExTrackRequest(BaseModel):
    trackingNumber: str


class ShippingLogResponse(BaseModel):
    id: int
    shipment_id: int | None = None
    job_number: str = ""
    changed_by: int
    username: str
    action: str
    field_name: str
    old_value: str
    new_value: str
    changed_at: datetime

    class Config:
        from_attributes = True


def _safe_text(value) -> str:
    if value is None:
        return ""
    if isinstance(value, bool):
        return "true" if value else "false"
    return str(value)


def _append_shipping_logs(
    db: Session,
    *,
    shipment_id: int | None,
    action: str,
    user_id: int,
    changes: dict[str, dict[str, str]],
):
    for field_name, diff in changes.items():
        db.add(
            ShippingLog(
                shipment_id=shipment_id,
                changed_by=user_id,
                action=action,
                field_name=field_name,
                old_value=_safe_text(diff.get("old")),
                new_value=_safe_text(diff.get("new")),
            )
        )

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


def _get_or_create_fedex_settings(db: Session) -> AppConnectionSettings:
    settings = (
        db.query(AppConnectionSettings)
        .filter(AppConnectionSettings.provider == "fedex")
        .first()
    )
    if not settings:
        settings = AppConnectionSettings(provider="fedex", enabled=False, api_key="", secret_key="")
        db.add(settings)
        db.commit()
        db.refresh(settings)
    return settings


def _normalize_fedex_base_url(base_url: str | None) -> str:
    value = (base_url or "").strip()
    if not value:
        return ""
    return value.rstrip("/")


@app.get("/settings/connections")
async def get_connection_settings(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    fedex = _get_or_create_fedex_settings(db)
    return {
        "fedex": {
            "enabled": bool(fedex.enabled),
            "apiKey": fedex.api_key or "",
            "hasSecretKey": bool(fedex.secret_key),
            "secretKeyMasked": "********" if fedex.secret_key else "",
            "baseUrl": _normalize_fedex_base_url(fedex.base_url),
        }
    }


@app.put("/settings/connections/fedex")
async def update_fedex_connection_settings(
    payload: FedExConnectionSettingsUpdate,
    db: Session = Depends(get_db),
    current_admin: User = Depends(get_current_admin_user),
):
    api_key = (payload.apiKey or "").strip()
    secret_key = (payload.secretKey or "").strip()
    base_url = _normalize_fedex_base_url(payload.baseUrl)
    enabled = bool(payload.enabled)

    if enabled and (not api_key or not secret_key):
        raise HTTPException(status_code=400, detail="FedEx API Key and Secret Key are required when enabled")
    if base_url and not (base_url.startswith("http://") or base_url.startswith("https://")):
        raise HTTPException(status_code=400, detail="FedEx Base URL must start with http:// or https://")

    settings = _get_or_create_fedex_settings(db)
    settings.enabled = enabled
    settings.api_key = api_key
    settings.base_url = base_url
    if secret_key:
        settings.secret_key = secret_key
    db.commit()
    db.refresh(settings)

    return {
        "message": "FedEx connection settings saved",
        "fedex": {
            "enabled": bool(settings.enabled),
            "apiKey": settings.api_key or "",
            "hasSecretKey": bool(settings.secret_key),
            "secretKeyMasked": "********" if settings.secret_key else "",
            "baseUrl": _normalize_fedex_base_url(settings.base_url),
        },
    }


@app.post("/settings/connections/fedex/test")
async def test_fedex_connection_settings(
    db: Session = Depends(get_db),
    current_admin: User = Depends(get_current_admin_user),
):
    settings = _get_or_create_fedex_settings(db)
    if not settings.api_key or not settings.secret_key:
        raise HTTPException(status_code=400, detail="FedEx credentials are not configured")

    fedex_service.get_fedex_access_token(
        settings.api_key,
        settings.secret_key,
        base_url=_normalize_fedex_base_url(settings.base_url) or None,
    )
    return {"message": "FedEx connection is valid"}


@app.get("/tracking/fedex/{tracking_number}")
async def get_fedex_tracking(
    tracking_number: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    normalized = (tracking_number or "").strip()
    if not normalized:
        raise HTTPException(status_code=400, detail="Tracking number is required")
    if len(normalized) > 100:
        raise HTTPException(status_code=400, detail="Tracking number is too long")

    settings = _get_or_create_fedex_settings(db)
    if not settings.enabled:
        raise HTTPException(status_code=400, detail="FedEx integration is disabled")
    if not settings.api_key or not settings.secret_key:
        raise HTTPException(status_code=400, detail="FedEx credentials are not configured")

    return fedex_service.track_fedex_number(
        normalized,
        settings.api_key,
        settings.secret_key,
        base_url=_normalize_fedex_base_url(settings.base_url) or None,
    )

# ============ ENDPOINTS DE SHIPMENTS ============

@app.get("/shipments", response_model=List[ShipmentResponse])
async def get_shipments(db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    shipments = db.query(Shipment).all()
    return shipments

@app.get("/shipments/{shipment_id}", response_model=ShipmentResponse)
async def get_shipment_by_id(
    shipment_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Obtener un shipment específico por ID"""
    shipment = db.query(Shipment).filter(Shipment.id == shipment_id).first()
    if not shipment:
        raise HTTPException(status_code=404, detail="Shipment not found")
    return shipment

# Utilidad para limpiar un job_number sin generar sufijos únicos
def clean_job_number(job_number: str) -> str:
    """Limpiar job number sin generar únicos"""
    return str(job_number).strip()


@app.post("/shipments", response_model=ShipmentResponse)
async def create_shipment(
    shipment: ShipmentCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Crear nuevo shipment con validación robusta y manejo de duplicados"""
    if current_user.role not in ["write", "admin"]:
        raise HTTPException(status_code=403, detail="Insufficient permissions")

    # Retry para manejar conflictos de concurrencia
    max_retries = 3
    last_error = None

    for attempt in range(max_retries):
        try:
            logger.info(f"Creating shipment attempt {attempt + 1}: {shipment.job_number}")

            # Limpiar job_number (permitir duplicados)
            clean_job_number_value = clean_job_number(shipment.job_number)

            # Preparar datos con validación
            shipment_data = shipment.dict()
            shipment_data["job_number"] = clean_job_number_value

            # Crear shipment - las validaciones se ejecutan automáticamente
            try:
                new_shipment = Shipment(
                    **shipment_data,
                    created_by=current_user.id,
                    last_modified_by=current_user.id,
                    version=1  # Versión inicial
                )
                db.add(new_shipment)
                db.flush()  # Flush para obtener ID y detectar errores antes del commit

                # Crear audit log
                audit_changes = {k: v for k, v in shipment_data.items() if v}
                log = AuditLog(
                    user_id=current_user.id,
                    action="create",
                    table_name="shipments",
                    record_id=new_shipment.id,
                    changes=json.dumps(audit_changes)
                )
                db.add(log)

                shipping_changes = {
                    field_name: {"old": "", "new": _safe_text(value)}
                    for field_name, value in shipment_data.items()
                    if value not in (None, "")
                }
                _append_shipping_logs(
                    db,
                    shipment_id=new_shipment.id,
                    action="create",
                    user_id=current_user.id,
                    changes=shipping_changes,
                )
            except ValueError as e:
                db.rollback()
                logger.warning(f"Validation error creating shipment: {e}")
                raise HTTPException(status_code=400, detail=str(e))

            db.commit()
            db.refresh(new_shipment)

            # Notificar via WebSocket (fuera de la transacción)
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
                logger.warning(f"Failed to broadcast shipment creation: {e}")

            return new_shipment

        except IntegrityError as e:
            # Error de integridad (duplicados, constraints)
            db.rollback()
            error_msg = str(e).lower()

            if "duplicate key" in error_msg or "unique constraint" in error_msg:
                if attempt < max_retries - 1:
                    # Esperar un poco antes de reintentar
                    await asyncio.sleep(0.1 * (attempt + 1))
                    logger.warning(f"Duplicate key on attempt {attempt + 1}, retrying...")
                    continue
                else:
                    logger.error(f"Duplicate key after {max_retries} attempts: {shipment.job_number}")
                    raise HTTPException(
                        status_code=400,
                        detail=f"Job number conflict after multiple attempts. Please try with a different number."
                    )
            else:
                logger.error(f"Integrity error creating shipment: {e}")
                raise HTTPException(status_code=400, detail="Data integrity error")

        except SQLAlchemyError as e:
            # Error general de base de datos
            db.rollback()
            last_error = e
            logger.error(f"Database error on attempt {attempt + 1}: {e}")

            if attempt < max_retries - 1:
                await asyncio.sleep(0.2 * (attempt + 1))
                continue
            else:
                break

        except Exception as e:
            # Error inesperado
            db.rollback()
            logger.error(f"Unexpected error creating shipment: {e}")
            raise HTTPException(status_code=500, detail="Internal server error")

    # Si salimos del loop sin return, hubo un error persistente
    logger.error(f"Failed to create shipment after {max_retries} attempts. Last error: {last_error}")
    raise HTTPException(status_code=500, detail="Unable to create shipment due to persistent database issues")


@app.put("/shipments/{shipment_id}", response_model=ShipmentResponse)
async def update_shipment(
    shipment_id: int,
    shipment_update: ShipmentUpdate,
    current_version: int = Query(..., description="Current version for optimistic locking"),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Actualizar shipment con control de concurrencia optimista"""
    if current_user.role not in ["write", "admin"]:
        raise HTTPException(status_code=403, detail="Insufficient permissions")

    try:
        logger.info(f"Updating shipment {shipment_id}, version {current_version}")

        # Buscar con version lock
        shipment = db.query(Shipment).filter(
            Shipment.id == shipment_id,
            Shipment.version == current_version
        ).first()

        if not shipment:
            # Verificar si existe pero con versión diferente
            existing = db.query(Shipment).filter(Shipment.id == shipment_id).first()
            if not existing:
                raise HTTPException(status_code=404, detail="Shipment not found")
            else:
                logger.warning(f"Version conflict: expected {current_version}, found {existing.version}")
                raise HTTPException(
                    status_code=409,
                    detail=f"Shipment was modified by another user. Current version is {existing.version}, please refresh and try again."
                )

        # Aplicar cambios con validación
        update_data = shipment_update.dict(exclude_unset=True)
        changes_made = {}

        for field, new_value in update_data.items():
            if field == "job_number" and new_value:
                # Limpiar job number (permitir duplicados)
                new_value = clean_job_number(new_value)

            old_value = getattr(shipment, field, None)

            # Solo actualizar si el valor cambió
            if old_value != new_value:
                changes_made[field] = {
                    "old": old_value,
                    "new": new_value
                }

                try:
                    # Aplicar cambio - validadores se ejecutan automáticamente
                    setattr(shipment, field, new_value)
                except ValueError as e:
                    db.rollback()
                    raise HTTPException(status_code=400, detail=f"Validation error in {field}: {str(e)}")

        # Si no hay cambios, no hacer nada
        if not changes_made:
            logger.info(f"No changes detected for shipment {shipment_id}")
            db.rollback()
            return shipment

        # Actualizar metadatos de versión
        shipment.version += 1
        shipment.last_modified_by = current_user.id
        shipment.updated_at = datetime.utcnow()

        # Crear audit log
        log = AuditLog(
            user_id=current_user.id,
            action="update",
            table_name="shipments",
            record_id=shipment.id,
            changes=json.dumps(changes_made)
        )
        db.add(log)
        _append_shipping_logs(
            db,
            shipment_id=shipment.id,
            action="update",
            user_id=current_user.id,
            changes=changes_made,
        )

        logger.info(f"Successfully updated shipment {shipment_id} to version {shipment.version}")
        db.commit()

    except IntegrityError as e:
        db.rollback()
        logger.error(f"Integrity error updating shipment {shipment_id}: {e}")
        if "duplicate key" in str(e).lower():
            raise HTTPException(status_code=400, detail="Job number already exists")
        else:
            raise HTTPException(status_code=400, detail="Data integrity error")

    except SQLAlchemyError as e:
        db.rollback()
        logger.error(f"Database error updating shipment {shipment_id}: {e}")
        raise HTTPException(status_code=500, detail="Database error")

    except HTTPException:
        db.rollback()
        raise  # Re-raise HTTP exceptions

    except Exception as e:
        db.rollback()
        logger.error(f"Unexpected error updating shipment {shipment_id}: {e}")
        raise HTTPException(status_code=500, detail="Internal server error")

    # Refresh datos después del commit
    db.refresh(shipment)

    # Notificar cambios
    try:
        await manager.broadcast(json.dumps({
            "type": "shipment_updated",
            "data": {
                "id": shipment.id,
                "job_number": shipment.job_number,
                "version": shipment.version,
                "changes": list(changes_made.keys()),
                "action_by": current_user.username
            }
        }))
    except Exception as e:
        logger.warning(f"Failed to broadcast shipment update: {e}")

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
        "shipping_notes": shipment.shipping_notes,
        "tracking_number": shipment.tracking_number,
        "address": shipment.address,
    }
    
    job_number = shipment.job_number
    shipping_changes = {
        field_name: {"old": _safe_text(value), "new": ""}
        for field_name, value in backup_data.items()
    }
    _append_shipping_logs(
        db,
        shipment_id=shipment.id,
        action="delete",
        user_id=current_user.id,
        changes=shipping_changes,
    )
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
@app.websocket("/ws/")
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


@app.get("/shipping-logs", response_model=List[ShippingLogResponse])
async def get_shipping_logs(
    start_date: date | None = Query(None, description="Start date in YYYY-MM-DD format"),
    end_date: date | None = Query(None, description="End date in YYYY-MM-DD format"),
    limit: int = Query(1000, ge=1, le=5000),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    today = datetime.utcnow().date()
    effective_end_date = end_date or today
    effective_start_date = start_date or (effective_end_date - timedelta(days=30))

    if effective_start_date > effective_end_date:
        raise HTTPException(status_code=400, detail="start_date must be before or equal to end_date")

    start_dt = datetime.combine(effective_start_date, datetime.min.time())
    end_dt = datetime.combine(effective_end_date + timedelta(days=1), datetime.min.time())

    logs = (
        db.query(ShippingLog)
        .filter(ShippingLog.changed_at >= start_dt)
        .filter(ShippingLog.changed_at < end_dt)
        .order_by(ShippingLog.changed_at.desc())
        .limit(limit)
        .all()
    )

    shipment_ids = {log.shipment_id for log in logs if log.shipment_id is not None}
    shipments_by_id = {}
    if shipment_ids:
        shipments = db.query(Shipment.id, Shipment.job_number).filter(Shipment.id.in_(shipment_ids)).all()
        shipments_by_id = {shipment.id: shipment.job_number for shipment in shipments}

    return [
        ShippingLogResponse(
            id=log.id,
            shipment_id=log.shipment_id,
            job_number=shipments_by_id.get(log.shipment_id, ""),
            changed_by=log.changed_by,
            username=log.user.username if log.user else "Unknown",
            action=log.action,
            field_name=log.field_name,
            old_value=log.old_value or "",
            new_value=log.new_value or "",
            changed_at=log.changed_at,
        )
        for log in logs
    ]

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
