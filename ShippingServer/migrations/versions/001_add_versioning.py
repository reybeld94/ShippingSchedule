"""Add versioning and integrity fields

Revision ID: 001
Revises: 
Create Date: 2024-12-20 10:00:00.000000

"""
from alembic import op

# revision identifiers
revision = '001'
down_revision = None
branch_labels = None
depends_on = None

def upgrade() -> None:
    # Mantener la migración idempotente para instalaciones parcialmente migradas
    op.execute("ALTER TABLE shipments ADD COLUMN IF NOT EXISTS version INTEGER NOT NULL DEFAULT 1")
    op.execute("ALTER TABLE shipments ADD COLUMN IF NOT EXISTS last_modified_by INTEGER")

    # Crear FK solo si no existe
    op.execute(
        """
        DO $$
        BEGIN
            IF NOT EXISTS (
                SELECT 1
                FROM pg_constraint
                WHERE conname = 'fk_shipments_last_modified_by'
            ) THEN
                ALTER TABLE shipments
                ADD CONSTRAINT fk_shipments_last_modified_by
                FOREIGN KEY (last_modified_by) REFERENCES users(id);
            END IF;
        END $$;
        """
    )
    
    # Actualizar registros existentes para tener last_modified_by
    op.execute("""
        UPDATE shipments 
        SET last_modified_by = created_by, version = 1 
        WHERE last_modified_by IS NULL
    """)
    
    # Crear índices para optimización
    op.execute("CREATE INDEX IF NOT EXISTS ix_shipment_version ON shipments (version)")
    op.execute("CREATE INDEX IF NOT EXISTS ix_shipment_id_version ON shipments (id, version)")
    op.execute("CREATE INDEX IF NOT EXISTS ix_shipment_last_modified ON shipments (last_modified_by)")

def downgrade() -> None:
    # Remover índices
    op.execute("DROP INDEX IF EXISTS ix_shipment_last_modified")
    op.execute("DROP INDEX IF EXISTS ix_shipment_id_version")
    op.execute("DROP INDEX IF EXISTS ix_shipment_version")

    # Remover foreign key constraint
    op.execute("ALTER TABLE shipments DROP CONSTRAINT IF EXISTS fk_shipments_last_modified_by")

    # Remover columnas
    op.execute("ALTER TABLE shipments DROP COLUMN IF EXISTS last_modified_by")
    op.execute("ALTER TABLE shipments DROP COLUMN IF EXISTS version")
