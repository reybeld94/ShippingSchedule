"""Add shipping notes/tracking/address fields to shipments

Revision ID: 002
Revises: 001
Create Date: 2026-04-03 00:00:00.000000

"""
from alembic import op

# revision identifiers
revision = '002'
down_revision = '001'
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Usar IF NOT EXISTS para mantener compatibilidad con bases ya migradas parcialmente
    op.execute("ALTER TABLE shipments ADD COLUMN IF NOT EXISTS shipping_notes TEXT")
    op.execute("ALTER TABLE shipments ADD COLUMN IF NOT EXISTS tracking_number VARCHAR(100) DEFAULT ''")
    op.execute("ALTER TABLE shipments ADD COLUMN IF NOT EXISTS address BOOLEAN NOT NULL DEFAULT FALSE")

    # Normalizar datos existentes
    op.execute("UPDATE shipments SET shipping_notes = '' WHERE shipping_notes IS NULL")
    op.execute("UPDATE shipments SET tracking_number = '' WHERE tracking_number IS NULL")


def downgrade() -> None:
    op.execute("ALTER TABLE shipments DROP COLUMN IF EXISTS address")
    op.execute("ALTER TABLE shipments DROP COLUMN IF EXISTS tracking_number")
    op.execute("ALTER TABLE shipments DROP COLUMN IF EXISTS shipping_notes")
