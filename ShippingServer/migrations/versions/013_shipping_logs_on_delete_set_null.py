"""Change shipping_logs.shipment_id FK to ON DELETE SET NULL

Without this, deleting a shipment raises IntegrityError in PostgreSQL
because historical log rows (from previous edits) still reference the
shipment id.  Mirrors migration 012 which fixed the same problem for
sills_logs.

Revision ID: 013
Revises: 012
Create Date: 2026-05-19 00:00:00.000000

"""
from alembic import op


revision = '013'
down_revision = '012'
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute(
        "ALTER TABLE shipping_logs "
        "DROP CONSTRAINT IF EXISTS shipping_logs_shipment_id_fkey"
    )
    op.execute(
        "ALTER TABLE shipping_logs "
        "ADD CONSTRAINT shipping_logs_shipment_id_fkey "
        "FOREIGN KEY (shipment_id) REFERENCES shipments(id) ON DELETE SET NULL"
    )


def downgrade() -> None:
    op.execute(
        "ALTER TABLE shipping_logs "
        "DROP CONSTRAINT IF EXISTS shipping_logs_shipment_id_fkey"
    )
    op.execute(
        "ALTER TABLE shipping_logs "
        "ADD CONSTRAINT shipping_logs_shipment_id_fkey "
        "FOREIGN KEY (shipment_id) REFERENCES shipments(id)"
    )
