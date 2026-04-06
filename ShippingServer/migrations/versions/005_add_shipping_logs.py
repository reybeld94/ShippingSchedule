"""Add shipping_logs table for shipping module data changes

Revision ID: 005
Revises: 004
Create Date: 2026-04-06 00:00:00.000000

"""
from alembic import op


# revision identifiers
revision = '005'
down_revision = '004'
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute(
        """
        CREATE TABLE IF NOT EXISTS shipping_logs (
            id SERIAL PRIMARY KEY,
            shipment_id INTEGER REFERENCES shipments(id),
            changed_by INTEGER NOT NULL REFERENCES users(id),
            action VARCHAR(20) NOT NULL,
            field_name VARCHAR(100) NOT NULL,
            old_value TEXT DEFAULT '',
            new_value TEXT DEFAULT '',
            changed_at TIMESTAMP WITHOUT TIME ZONE NOT NULL DEFAULT NOW(),
            module VARCHAR(30) NOT NULL DEFAULT 'shipping'
        )
        """
    )

    op.execute("CREATE INDEX IF NOT EXISTS ix_shipping_logs_changed_at ON shipping_logs (changed_at)")
    op.execute(
        "CREATE INDEX IF NOT EXISTS ix_shipping_logs_shipment_changed_at "
        "ON shipping_logs (shipment_id, changed_at)"
    )
    op.execute("CREATE INDEX IF NOT EXISTS ix_shipping_logs_changed_by ON shipping_logs (changed_by)")


def downgrade() -> None:
    op.execute("DROP INDEX IF EXISTS ix_shipping_logs_changed_by")
    op.execute("DROP INDEX IF EXISTS ix_shipping_logs_shipment_changed_at")
    op.execute("DROP INDEX IF EXISTS ix_shipping_logs_changed_at")
    op.execute("DROP TABLE IF EXISTS shipping_logs")
