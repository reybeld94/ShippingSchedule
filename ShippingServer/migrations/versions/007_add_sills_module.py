"""Add sills and sills_logs tables

Revision ID: 007
Revises: 006
Create Date: 2026-04-07 00:00:00.000000

"""
from alembic import op


revision = '007'
down_revision = '006'
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute(
        """
        CREATE TABLE IF NOT EXISTS sills (
            id SERIAL PRIMARY KEY,
            material VARCHAR(20) NOT NULL,
            dimension VARCHAR(30) NOT NULL DEFAULT '',
            location VARCHAR(40) NOT NULL DEFAULT '',
            die_number VARCHAR(50) NOT NULL DEFAULT '',
            type VARCHAR(20) NOT NULL DEFAULT '',
            speed VARCHAR(10) NOT NULL DEFAULT '',
            width VARCHAR(30) NOT NULL DEFAULT '',
            sales_order VARCHAR(30) NOT NULL DEFAULT '',
            work_order VARCHAR(30) NOT NULL DEFAULT '',
            assembly_number VARCHAR(50) NOT NULL DEFAULT '',
            description TEXT NOT NULL DEFAULT '',
            qty VARCHAR(20) NOT NULL DEFAULT '',
            dimension_needed VARCHAR(30) NOT NULL DEFAULT '',
            notes TEXT NOT NULL DEFAULT '',
            week_to_print VARCHAR(20) NOT NULL DEFAULT '',
            created_by INTEGER NOT NULL REFERENCES users(id),
            created_at TIMESTAMP WITHOUT TIME ZONE NOT NULL DEFAULT NOW(),
            updated_at TIMESTAMP WITHOUT TIME ZONE NOT NULL DEFAULT NOW(),
            last_modified_by INTEGER REFERENCES users(id)
        )
        """
    )

    op.execute("CREATE INDEX IF NOT EXISTS ix_sills_week_to_print ON sills (week_to_print)")
    op.execute("CREATE INDEX IF NOT EXISTS ix_sills_sales_order ON sills (sales_order)")
    op.execute("CREATE INDEX IF NOT EXISTS ix_sills_work_order ON sills (work_order)")

    op.execute(
        """
        CREATE TABLE IF NOT EXISTS sills_logs (
            id SERIAL PRIMARY KEY,
            sill_id INTEGER REFERENCES sills(id),
            changed_by INTEGER NOT NULL REFERENCES users(id),
            action VARCHAR(20) NOT NULL,
            field_name VARCHAR(100) NOT NULL,
            old_value TEXT DEFAULT '',
            new_value TEXT DEFAULT '',
            changed_at TIMESTAMP WITHOUT TIME ZONE NOT NULL DEFAULT NOW(),
            module VARCHAR(30) NOT NULL DEFAULT 'sills'
        )
        """
    )

    op.execute("CREATE INDEX IF NOT EXISTS ix_sills_logs_changed_at ON sills_logs (changed_at)")
    op.execute(
        "CREATE INDEX IF NOT EXISTS ix_sills_logs_sill_changed_at "
        "ON sills_logs (sill_id, changed_at)"
    )
    op.execute("CREATE INDEX IF NOT EXISTS ix_sills_logs_changed_by ON sills_logs (changed_by)")


def downgrade() -> None:
    op.execute("DROP INDEX IF EXISTS ix_sills_logs_changed_by")
    op.execute("DROP INDEX IF EXISTS ix_sills_logs_sill_changed_at")
    op.execute("DROP INDEX IF EXISTS ix_sills_logs_changed_at")
    op.execute("DROP TABLE IF EXISTS sills_logs")

    op.execute("DROP INDEX IF EXISTS ix_sills_work_order")
    op.execute("DROP INDEX IF EXISTS ix_sills_sales_order")
    op.execute("DROP INDEX IF EXISTS ix_sills_week_to_print")
    op.execute("DROP TABLE IF EXISTS sills")
