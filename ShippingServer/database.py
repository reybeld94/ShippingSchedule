# database.py - Configuración de PostgreSQL
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from models import Base
import os

# Configuración de PostgreSQL
DATABASE_URL = "postgresql://postgres:Gundcab@localhost:5432/shipping_db"

# Crear engine
engine = create_engine(DATABASE_URL)

# Crear sesión
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

# Crear todas las tablas
def create_tables():
    Base.metadata.create_all(bind=engine)

# Dependency para obtener sesión de BD
def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

# Función para crear usuario admin inicial
def create_admin_user():
    from passlib.context import CryptContext
    from models import User
    
    pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")
    
    db = SessionLocal()
    try:
        # Verificar si ya existe un admin
        admin = db.query(User).filter(User.username == "admin").first()
        if not admin:
            hashed_password = pwd_context.hash("admin123")  # Cambiar en producción
            admin_user = User(
                username="admin",
                email="admin@shipping.com",
                hashed_password=hashed_password,
                role="admin"
            )
            db.add(admin_user)
            db.commit()
            print("✅ Usuario admin creado - user: admin, pass: admin123")
        else:
            print("✅ Usuario admin ya existe")
    finally:
        db.close()

if __name__ == "__main__":
    print("Creando tablas...")
    create_tables()
    print("✅ Tablas creadas")
    
    print("Creando usuario admin...")
    create_admin_user()
    print("✅ Setup completado")
