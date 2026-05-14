# main.py - Servidor principal FastAPI
from fastapi import FastAPI, Depends, HTTPException, status, WebSocket, WebSocketDisconnect, Query
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy.orm import Session
from typing import List, Any
from datetime import timedelta, datetime, date
import json
import asyncio
import logging
import time
import importlib
from decimal import Decimal, InvalidOperation
from sqlalchemy import or_
from sqlalchemy.exc import IntegrityError, SQLAlchemyError
from sqlalchemy.orm.exc import StaleDataError

# Imports locales
from database import get_db, create_tables, create_admin_user, SessionLocal
from models import User, Shipment, AuditLog, ShippingLog, AppConnectionSettings, Sill, SillLog, SillDieDatabase, UserPermission
from auth import authenticate_user, create_access_token, get_current_user, get_current_admin_user, Token, UserLogin, UserCreate
from pydantic import BaseModel, Field
from fedex_service import FedExService



SHIPPING_PERMISSION_COLUMNS = [
    "job_number",
    "job_name",
    "status",
    "description",
    "qc_release",
    "qc_notes",
    "created",
    "ship_plan",
    "shipped",
    "invoice_number",
    "tracking_number",
    "address",
    "shipping_notes",
]
SILLS_PERMISSION_COLUMNS = [
    "material",
    "dimension",
    "location",
    "die_number",
    "type",
    "speed",
    "width",
    "sales_order",
    "work_order",
    "assembly_number",
    "description",
    "qty",
    "dimension_needed",
    "notes",
    "week_to_print",
]
SILLS_DIE_PERMISSION_KEY = "sills_database"
PERMISSION_MODULES = {
    "shipping_schedule": set(SHIPPING_PERMISSION_COLUMNS),
    "sills": set(SILLS_PERMISSION_COLUMNS),
    "sills_database": {SILLS_DIE_PERMISSION_KEY},
}
PERMISSION_COLUMN_ALIASES = {
    module: {column.replace("_", "").lower(): column for column in columns}
    for module, columns in PERMISSION_MODULES.items()
}


def _normalize_permission_column_key(module: str, column_key: str) -> str:
    """Return the canonical column key accepted by the permissions API."""
    cleaned_key = str(column_key or "").strip()
    if cleaned_key in PERMISSION_MODULES.get(module, set()):
        return cleaned_key
    alias_key = cleaned_key.replace(" ", "_").replace("-", "_").lower()
    if alias_key in PERMISSION_MODULES.get(module, set()):
        return alias_key
    compact_key = alias_key.replace("_", "")
    return PERMISSION_COLUMN_ALIASES.get(module, {}).get(compact_key, cleaned_key)

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
    address: str = ""

class ShipmentUpdate(BaseModel):
    job_number: str = None
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
    address: str = None

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
    address: str
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


class ModulePermissionUpdate(BaseModel):
    can_view: bool = True
    columns: dict[str, bool] = Field(default_factory=dict)


class UserPermissionsUpdate(BaseModel):
    modules: dict[str, ModulePermissionUpdate] = Field(default_factory=dict)


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


class SillCreate(BaseModel):
    material: str
    dimension: str = ""
    location: str = ""
    die_number: str = ""
    type: str = ""
    speed: str = ""
    width: str = ""
    sales_order: str = ""
    work_order: str = ""
    assembly_number: str = ""
    description: str = ""
    qty: str = ""
    dimension_needed: str = ""
    notes: str = ""
    week_to_print: str = ""


class SillUpdate(BaseModel):
    material: str | None = None
    dimension: str | None = None
    location: str | None = None
    die_number: str | None = None
    type: str | None = None
    speed: str | None = None
    width: str | None = None
    sales_order: str | None = None
    work_order: str | None = None
    assembly_number: str | None = None
    description: str | None = None
    qty: str | None = None
    dimension_needed: str | None = None
    notes: str | None = None
    week_to_print: str | None = None


class SillResponse(BaseModel):
    id: int
    material: str
    dimension: str
    location: str
    die_number: str
    type: str
    speed: str
    width: str
    sales_order: str
    work_order: str
    assembly_number: str
    issue_quantity: str = "0"
    issue_quantity_required: str = ""
    issue_status: str = "pending"
    issue_checked_at: datetime | None = None
    issue_completed_at: datetime | None = None
    description: str
    qty: str
    dimension_needed: str
    notes: str
    week_to_print: str
    created_by: int

    class Config:
        from_attributes = True


class SillLogResponse(BaseModel):
    id: int
    sill_id: int | None = None
    changed_by: int
    username: str
    action: str
    field_name: str
    old_value: str
    new_value: str
    changed_at: datetime

    class Config:
        from_attributes = True


class SillDieCreate(BaseModel):
    die_number: str
    type: str = ""
    speed: str = ""
    width: str = ""
    supplier: str = ""
    notes: str = ""
    vendor_drawing: str = ""


class SillDieUpdate(BaseModel):
    die_number: str | None = None
    type: str | None = None
    speed: str | None = None
    width: str | None = None
    supplier: str | None = None
    notes: str | None = None
    vendor_drawing: str | None = None


class SillDieResponse(BaseModel):
    id: int
    die_number: str
    type: str
    speed: str
    width: str
    supplier: str
    notes: str
    vendor_drawing: str

    class Config:
        from_attributes = True


def _safe_text(value) -> str:
    if value is None:
        return ""
    if isinstance(value, bool):
        return "true" if value else "false"
    return str(value)


def _normalize_for_compare(field_name: str, value):
    """Normaliza valores para evitar updates/logs por cambios equivalentes."""
    if isinstance(value, str):
        value = value.strip()
    if field_name in {"qc_release", "created", "ship_plan", "shipped"}:
        if value in (None, "", "—", "-", "N/A", "n/a", "null", "None"):
            return ""
    if field_name in {
        "description",
        "qc_notes",
        "shipping_notes",
        "invoice_number",
        "tracking_number",
        "status",
        "week",
    }:
        return "" if value is None else value
    return value


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


def _append_sills_logs(
    db: Session,
    *,
    sill_id: int | None,
    action: str,
    user_id: int,
    changes: dict[str, dict[str, str]],
):
    for field_name, diff in changes.items():
        db.add(
            SillLog(
                sill_id=sill_id,
                changed_by=user_id,
                action=action,
                field_name=field_name,
                old_value=_safe_text(diff.get("old")),
                new_value=_safe_text(diff.get("new")),
            )
        )


def _admin_permissions_payload() -> dict:
    return {
        "modules": {
            "shipping_schedule": {
                "can_view": True,
                "columns": {column: True for column in SHIPPING_PERMISSION_COLUMNS},
            },
            "sills": {
                "can_view": True,
                "columns": {column: True for column in SILLS_PERMISSION_COLUMNS},
            },
            "sills_database": {
                "can_view": True,
                "columns": {SILLS_DIE_PERMISSION_KEY: True},
            },
        }
    }


def _get_user_permissions_payload(db: Session, user: User) -> dict:
    if user.role == "admin":
        return _admin_permissions_payload()

    payload = {
        "modules": {
            "shipping_schedule": {
                "can_view": True,
                "columns": {column: user.role == "write" for column in SHIPPING_PERMISSION_COLUMNS},
            },
            "sills": {
                "can_view": True,
                "columns": {column: user.role == "write" for column in SILLS_PERMISSION_COLUMNS},
            },
            "sills_database": {
                "can_view": True,
                "columns": {SILLS_DIE_PERMISSION_KEY: user.role == "write"},
            },
        }
    }
    records = db.query(UserPermission).filter(UserPermission.user_id == user.id).all()
    for record in records:
        module_payload = payload["modules"].get(record.module)
        if module_payload is None:
            continue
        if not record.column_key:
            module_payload["can_view"] = bool(record.can_view)
        elif record.column_key in module_payload["columns"]:
            module_payload["columns"][record.column_key] = bool(record.can_write)
    return payload


def _upsert_permission(
    db: Session,
    *,
    target_user_id: int,
    module: str,
    column_key: str,
    can_view: bool,
    can_write: bool,
    updated_by: int,
):
    record = (
        db.query(UserPermission)
        .filter(
            UserPermission.user_id == target_user_id,
            UserPermission.module == module,
            UserPermission.column_key == column_key,
        )
        .first()
    )
    if record is None:
        record = UserPermission(user_id=target_user_id, module=module, column_key=column_key)
        db.add(record)
    record.can_view = can_view
    record.can_write = can_write
    record.updated_by = updated_by
    record.updated_at = datetime.utcnow()


def _can_view_module(db: Session, user: User, module: str) -> bool:
    if user.role == "admin":
        return True
    permissions = _get_user_permissions_payload(db, user)
    return bool(permissions.get("modules", {}).get(module, {}).get("can_view", True))


def _can_write_columns(db: Session, user: User, module: str, fields: list[str]) -> bool:
    if user.role == "admin":
        return True
    if user.role not in ["write", "admin"]:
        return False
    permissions = _get_user_permissions_payload(db, user)
    module_payload = permissions.get("modules", {}).get(module, {})
    if not module_payload.get("can_view", True):
        return False
    column_permissions = module_payload.get("columns", {})
    return all(bool(column_permissions.get(field, False)) for field in fields)


def _ensure_module_view(db: Session, user: User, module: str):
    if not _can_view_module(db, user, module):
        raise HTTPException(status_code=403, detail="Module access denied")


def _ensure_column_write(db: Session, user: User, module: str, fields: list[str]):
    if not _can_write_columns(db, user, module, fields):
        raise HTTPException(status_code=403, detail="Insufficient column permissions")

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


@app.get("/permissions/me")
async def get_my_permissions(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    return _get_user_permissions_payload(db, current_user)


@app.get("/users/{user_id}/permissions")
async def get_user_permissions(
    user_id: int,
    db: Session = Depends(get_db),
    current_admin: User = Depends(get_current_admin_user),
):
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    return _get_user_permissions_payload(db, user)


@app.put("/users/{user_id}/permissions")
async def update_user_permissions(
    user_id: int,
    permissions_update: UserPermissionsUpdate,
    db: Session = Depends(get_db),
    current_admin: User = Depends(get_current_admin_user),
):
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    for module, module_update in permissions_update.modules.items():
        if module not in PERMISSION_MODULES:
            raise HTTPException(status_code=400, detail=f"Unknown permission module: {module}")
        _upsert_permission(
            db,
            target_user_id=user_id,
            module=module,
            column_key="",
            can_view=bool(module_update.can_view),
            can_write=False,
            updated_by=current_admin.id,
        )
        valid_columns = PERMISSION_MODULES[module]
        for column_key, can_write in module_update.columns.items():
            normalized_column_key = _normalize_permission_column_key(module, column_key)
            if normalized_column_key not in valid_columns:
                raise HTTPException(status_code=400, detail=f"Unknown permission column: {module}.{column_key}")
            _upsert_permission(
                db,
                target_user_id=user_id,
                module=module,
                column_key=normalized_column_key,
                can_view=False,
                can_write=bool(can_write),
                updated_by=current_admin.id,
            )

    db.commit()
    return _get_user_permissions_payload(db, user)


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


def _is_masked_fedex_secret(secret_key: str | None) -> bool:
    return (secret_key or "").strip() == "********"


def _has_fedex_secret_for_save(secret_key: str | None, saved_secret_key: str | None) -> bool:
    incoming_secret = (secret_key or "").strip()
    if incoming_secret and not _is_masked_fedex_secret(incoming_secret):
        return True
    return bool((saved_secret_key or "").strip())


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

    if base_url and not (base_url.startswith("http://") or base_url.startswith("https://")):
        raise HTTPException(status_code=400, detail="FedEx Base URL must start with http:// or https://")

    settings = _get_or_create_fedex_settings(db)
    if enabled and (not api_key or not _has_fedex_secret_for_save(secret_key, settings.secret_key)):
        raise HTTPException(status_code=400, detail="FedEx API Key and Secret Key are required when enabled")

    settings.enabled = enabled
    settings.api_key = api_key
    settings.base_url = base_url
    if secret_key and not _is_masked_fedex_secret(secret_key):
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
    _ensure_module_view(db, current_user, "shipping_schedule")
    started_at = time.perf_counter()
    shipments = db.query(Shipment).all()
    elapsed_ms = (time.perf_counter() - started_at) * 1000
    shipped_count = sum(1 for shipment in shipments if str(getattr(shipment, "shipped", "") or "").strip())
    avg_notes_len = 0.0
    if shipments:
        avg_notes_len = sum(len(str(getattr(shipment, "shipping_notes", "") or "")) for shipment in shipments) / len(shipments)
    logger.info(
        "GET /shipments user=%s rows=%s shipped_rows=%s avg_shipping_notes_len=%.1f query_time_ms=%.1f",
        getattr(current_user, "username", "unknown"),
        len(shipments),
        shipped_count,
        avg_notes_len,
        elapsed_ms,
    )
    return shipments

@app.get("/shipments/{shipment_id}", response_model=ShipmentResponse)
async def get_shipment_by_id(
    shipment_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Obtener un shipment específico por ID"""
    _ensure_module_view(db, current_user, "shipping_schedule")
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
    _ensure_column_write(db, current_user, "shipping_schedule", SHIPPING_PERMISSION_COLUMNS)

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
    current_version: int | None = Query(
        None,
        description="Current version for optimistic locking (optional for legacy clients)",
    ),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Actualizar shipment con control de concurrencia optimista"""
    try:
        logger.info(f"Updating shipment {shipment_id}, version {current_version}")

        # Buscar shipment; usar lock optimista solo cuando el cliente envía versión
        if current_version is None:
            shipment = db.query(Shipment).filter(Shipment.id == shipment_id).first()
        else:
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
        _ensure_column_write(db, current_user, "shipping_schedule", list(update_data.keys()))
        changes_made = {}

        for field, new_value in update_data.items():
            if field == "job_number" and new_value:
                # Limpiar job number (permitir duplicados)
                new_value = clean_job_number(new_value)

            old_value = getattr(shipment, field, None)
            old_value_normalized = _normalize_for_compare(field, old_value)
            new_value_normalized = _normalize_for_compare(field, new_value)

            # Solo actualizar si el valor cambió
            if old_value_normalized != new_value_normalized:
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
    _ensure_column_write(db, current_user, "shipping_schedule", SHIPPING_PERMISSION_COLUMNS)
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

async def _handle_websocket_connection(websocket: WebSocket):
    await manager.connect(websocket)
    try:
        while True:
            # Mantener conexión viva
            await websocket.receive_text()
    except WebSocketDisconnect:
        manager.disconnect(websocket)


@app.websocket("/ws")
@app.websocket("/ws/")
async def websocket_endpoint(websocket: WebSocket):
    await _handle_websocket_connection(websocket)


@app.websocket("/")
async def websocket_root_compat_endpoint(websocket: WebSocket):
    logger.warning(
        "WebSocket client connected to root path; accepting for compatibility. "
        "Update clients to use /ws."
    )
    await _handle_websocket_connection(websocket)

# ============ STARTUP ============

@app.on_event("startup")
async def startup_event():
    print("🚀 Iniciando Shipping Schedule Server...")
    print("📦 Creando tablas de base de datos...")
    create_tables()
    print("👤 Configurando usuario admin...")
    create_admin_user()
    asyncio.create_task(_sills_issue_status_scheduler())
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



MIE_TRAK_SERVER = "GUNDMAIN"
MIE_TRAK_DATABASE = "GunderlinLive"
MIE_TRAK_USER = "mie"
MIE_TRAK_PASSWORD = "mie"
ISSUE_COMPLETE_STATUS = "complete"
ISSUE_PARTIAL_STATUS = "partial"
ISSUE_PENDING_STATUS = "pending"
ISSUE_CHECK_INTERVAL_SECONDS = 15 * 60


def _decimal_from_value(value: Any) -> Decimal:
    if value is None or value == "":
        return Decimal("0")
    try:
        return Decimal(str(value).strip())
    except (InvalidOperation, ValueError):
        return Decimal("0")


def _format_issue_quantity(value: Decimal) -> str:
    normalized = value.quantize(Decimal("0.001")).normalize()
    return format(normalized, "f")


def _fetch_mie_trak_issue_snapshot(assembly_number: str) -> dict[str, str]:
    """Return issue quantities for one Mie Trak WorkOrderAssemblyPK."""
    pymssql = importlib.import_module("pymssql")
    cleaned_assembly = str(assembly_number or "").strip()
    conn = None
    try:
        conn = pymssql.connect(
            server=MIE_TRAK_SERVER,
            user=MIE_TRAK_USER,
            password=MIE_TRAK_PASSWORD,
            database=MIE_TRAK_DATABASE,
        )
        cursor = conn.cursor(as_dict=True)
        cursor.execute(
            """
            SELECT
                woa.WorkOrderAssemblyPK AS assemblyNumber,
                woa.WorkOrderAssemblyBOMStatusFK AS bomStatusFk,
                COALESCE(woa.QuantityRequired, 0) AS quantityRequired,
                COALESCE(woa.QuantityIssued, 0) AS issuedQuantity
            FROM dbo.WorkOrderAssembly woa
            WHERE woa.WorkOrderAssemblyPK = %s;
            """,
            (cleaned_assembly,),
        )
        assembly_row = cursor.fetchone()
        if not assembly_row:
            return {
                "issue_quantity": "0",
                "issue_quantity_required": "",
                "issue_status": ISSUE_PENDING_STATUS,
            }

        required = _decimal_from_value(assembly_row.get("quantityRequired"))
        issued = _decimal_from_value(assembly_row.get("issuedQuantity"))

        if issued <= 0:
            status = ISSUE_PENDING_STATUS
        elif issued < required:
            status = ISSUE_PARTIAL_STATUS
        else:
            status = ISSUE_COMPLETE_STATUS

        return {
            "issue_quantity": _format_issue_quantity(issued),
            "issue_quantity_required": _format_issue_quantity(required) if required else "",
            "issue_status": status,
        }
    finally:
        if conn:
            try:
                conn.close()
            except Exception:
                pass


def _get_sills_due_for_issue_status(db: Session, *, only_due: bool = True) -> list[Sill]:
    """Return Sills that still need Mie Trak issue verification."""
    query = (
        db.query(Sill)
        .filter(Sill.assembly_number != "")
        .filter(Sill.issue_status != ISSUE_COMPLETE_STATUS)
    )
    if only_due:
        due_before = datetime.utcnow() - timedelta(seconds=ISSUE_CHECK_INTERVAL_SECONDS)
        query = query.filter(
            or_(Sill.issue_checked_at.is_(None), Sill.issue_checked_at < due_before)
        )
    return query.all()


def _apply_sill_issue_snapshot(sill: Sill, snapshot: dict[str, str], checked_at: datetime) -> bool:
    """Apply a Mie Trak issue snapshot to one Sill and return whether visible data changed."""
    changed = False
    old_status = _safe_text(getattr(sill, "issue_status", ""))
    for field_name in ("issue_quantity", "issue_quantity_required", "issue_status"):
        value = snapshot[field_name]
        if getattr(sill, field_name) != value:
            setattr(sill, field_name, value)
            changed = True

    sill.issue_checked_at = checked_at
    if snapshot["issue_status"] == ISSUE_COMPLETE_STATUS and old_status != ISSUE_COMPLETE_STATUS:
        sill.issue_completed_at = checked_at
        changed = True
    if changed:
        sill.updated_at = checked_at
    return changed


def _refresh_pending_sills_issue_status(db: Session, *, only_due: bool = True) -> int:
    """Refresh Sills that still need Mie Trak issue verification."""
    pending_sills = _get_sills_due_for_issue_status(db, only_due=only_due)
    updated_count = 0
    checked_count = 0
    for sill in pending_sills:
        try:
            snapshot = _fetch_mie_trak_issue_snapshot(sill.assembly_number)
            checked_at = datetime.utcnow()
            if _apply_sill_issue_snapshot(sill, snapshot, checked_at):
                updated_count += 1
            checked_count += 1
        except Exception as exc:
            logger.warning(
                "Failed to refresh Sill issue status for id=%s assembly=%s: %s",
                sill.id,
                sill.assembly_number,
                exc,
            )

    if checked_count:
        db.commit()
    logger.info(
        "Sills issue status refresh checked=%s updated=%s interval_seconds=%s",
        checked_count,
        updated_count,
        ISSUE_CHECK_INTERVAL_SECONDS,
    )
    return updated_count


def _refresh_pending_sills_issue_status_with_new_session(*, only_due: bool = True) -> int:
    """Refresh Sills issue status in a worker thread with its own DB session."""
    db = SessionLocal()
    try:
        return _refresh_pending_sills_issue_status(db, only_due=only_due)
    finally:
        db.close()


async def _sills_issue_status_scheduler():
    force_full_refresh = True
    while True:
        try:
            updated_count = await asyncio.to_thread(
                _refresh_pending_sills_issue_status_with_new_session,
                only_due=not force_full_refresh,
            )
            force_full_refresh = False
            if updated_count:
                await manager.broadcast(json.dumps({
                    "type": "sills_issue_status_updated",
                    "data": {"updated_count": updated_count},
                }))
        except Exception as exc:
            logger.warning(f"Failed to refresh Sills issue status: {exc}")
        await asyncio.sleep(ISSUE_CHECK_INTERVAL_SECONDS)


# ============ ENDPOINTS DE SILLS ============

@app.get("/sills", response_model=List[SillResponse])
async def get_sills(db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    _ensure_module_view(db, current_user, "sills")
    try:
        await asyncio.to_thread(_refresh_pending_sills_issue_status_with_new_session)
    except Exception as exc:
        logger.warning(f"Unable to refresh Sills issue status before listing: {exc}")
    return db.query(Sill).order_by(Sill.id.desc()).all()


@app.post("/sills", response_model=SillResponse)
async def create_sill(
    sill: SillCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    _ensure_column_write(db, current_user, "sills", SILLS_PERMISSION_COLUMNS)

    sill_data = {k: _safe_text(v).strip() for k, v in sill.dict().items()}
    new_sill = Sill(
        **sill_data,
        created_by=current_user.id,
        last_modified_by=current_user.id,
    )
    db.add(new_sill)
    db.flush()

    changes = {
        field_name: {"old": "", "new": value}
        for field_name, value in sill_data.items()
        if value != ""
    }
    _append_sills_logs(
        db,
        sill_id=new_sill.id,
        action="create",
        user_id=current_user.id,
        changes=changes,
    )

    db.commit()
    db.refresh(new_sill)
    return new_sill


@app.put("/sills/{sill_id}", response_model=SillResponse)
async def update_sill(
    sill_id: int,
    sill_update: SillUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    update_data = sill_update.dict(exclude_unset=True)
    _ensure_column_write(db, current_user, "sills", list(update_data.keys()))

    sill = db.query(Sill).filter(Sill.id == sill_id).first()
    if not sill:
        raise HTTPException(status_code=404, detail="Sill not found")

    changes_made = {}
    for field, raw_value in update_data.items():
        new_value = _safe_text(raw_value).strip()
        old_value = _safe_text(getattr(sill, field, ""))
        if old_value != new_value:
            setattr(sill, field, new_value)
            changes_made[field] = {"old": old_value, "new": new_value}
            if field == "assembly_number":
                sill.issue_quantity = "0"
                sill.issue_quantity_required = ""
                sill.issue_status = ISSUE_PENDING_STATUS
                sill.issue_checked_at = None
                sill.issue_completed_at = None

    if not changes_made:
        return sill

    sill.last_modified_by = current_user.id
    sill.updated_at = datetime.utcnow()
    _append_sills_logs(
        db,
        sill_id=sill.id,
        action="update",
        user_id=current_user.id,
        changes=changes_made,
    )
    db.commit()
    db.refresh(sill)
    return sill


@app.delete("/sills/{sill_id}")
async def delete_sill(
    sill_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    _ensure_column_write(db, current_user, "sills", SILLS_PERMISSION_COLUMNS)

    sill = db.query(Sill).filter(Sill.id == sill_id).first()
    if not sill:
        raise HTTPException(status_code=404, detail="Sill not found")

    backup_data = {
        "material": sill.material,
        "dimension": sill.dimension,
        "location": sill.location,
        "die_number": sill.die_number,
        "type": sill.type,
        "speed": sill.speed,
        "width": sill.width,
        "sales_order": sill.sales_order,
        "work_order": sill.work_order,
        "assembly_number": sill.assembly_number,
        "description": sill.description,
        "qty": sill.qty,
        "dimension_needed": sill.dimension_needed,
        "notes": sill.notes,
        "week_to_print": sill.week_to_print,
    }
    _append_sills_logs(
        db,
        sill_id=sill.id,
        action="delete",
        user_id=current_user.id,
        changes={key: {"old": _safe_text(value), "new": ""} for key, value in backup_data.items()},
    )
    db.delete(sill)
    db.commit()
    return {"message": "Sill deleted successfully"}


@app.get("/sills-logs", response_model=List[SillLogResponse])
async def get_sills_logs(
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
        db.query(SillLog)
        .filter(SillLog.changed_at >= start_dt)
        .filter(SillLog.changed_at < end_dt)
        .order_by(SillLog.changed_at.desc())
        .limit(limit)
        .all()
    )

    return [
        SillLogResponse(
            id=log.id,
            sill_id=log.sill_id,
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


def _validate_sill_die_payload(payload: dict) -> dict:
    normalized = {k: _safe_text(v).strip() for k, v in payload.items()}
    valid_types = {"Car", "Hatch", "Extension"}
    valid_speeds = {"0", "1", "2", "3"}

    if not normalized.get("die_number"):
        raise HTTPException(status_code=400, detail="Die number is required")
    if normalized.get("type") and normalized["type"] not in valid_types:
        raise HTTPException(status_code=400, detail="Type must be Car, Hatch, or Extension")
    if normalized.get("speed") and normalized["speed"] not in valid_speeds:
        raise HTTPException(status_code=400, detail="Speed must be one of: 0, 1, 2, 3")
    return normalized


@app.get("/sills/dies", response_model=List[SillDieResponse])
async def get_sill_dies(db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    _ensure_module_view(db, current_user, "sills_database")
    return db.query(SillDieDatabase).order_by(SillDieDatabase.die_number.asc()).all()


@app.post("/sills/dies", response_model=SillDieResponse)
async def create_sill_die(
    die_data: SillDieCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    _ensure_column_write(db, current_user, "sills_database", [SILLS_DIE_PERMISSION_KEY])

    payload = _validate_sill_die_payload(die_data.dict())
    new_die = SillDieDatabase(
        **payload,
        created_by=current_user.id,
        last_modified_by=current_user.id,
    )
    db.add(new_die)
    try:
        db.commit()
    except IntegrityError:
        db.rollback()
        raise HTTPException(status_code=409, detail="Die number already exists")
    db.refresh(new_die)
    return new_die


@app.put("/sills/dies/{die_id}", response_model=SillDieResponse)
async def update_sill_die(
    die_id: int,
    die_update: SillDieUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    _ensure_column_write(db, current_user, "sills_database", [SILLS_DIE_PERMISSION_KEY])

    die = db.query(SillDieDatabase).filter(SillDieDatabase.id == die_id).first()
    if not die:
        raise HTTPException(status_code=404, detail="Die not found")

    payload = {k: _safe_text(v).strip() for k, v in die_update.dict(exclude_unset=True).items()}
    if "type" in payload and payload["type"] and payload["type"] not in {"Car", "Hatch", "Extension"}:
        raise HTTPException(status_code=400, detail="Type must be Car, Hatch, or Extension")
    if "speed" in payload and payload["speed"] and payload["speed"] not in {"0", "1", "2", "3"}:
        raise HTTPException(status_code=400, detail="Speed must be one of: 0, 1, 2, 3")
    if "die_number" in payload and not payload["die_number"]:
        raise HTTPException(status_code=400, detail="Die number is required")

    for field, value in payload.items():
        setattr(die, field, value)

    die.last_modified_by = current_user.id
    die.updated_at = datetime.utcnow()
    try:
        db.commit()
    except IntegrityError:
        db.rollback()
        raise HTTPException(status_code=409, detail="Die number already exists")
    db.refresh(die)
    return die


@app.delete("/sills/dies/{die_id}")
async def delete_sill_die(
    die_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    _ensure_column_write(db, current_user, "sills_database", [SILLS_DIE_PERMISSION_KEY])

    die = db.query(SillDieDatabase).filter(SillDieDatabase.id == die_id).first()
    if not die:
        raise HTTPException(status_code=404, detail="Die not found")

    db.delete(die)
    db.commit()
    return {"message": "Die deleted successfully"}

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
