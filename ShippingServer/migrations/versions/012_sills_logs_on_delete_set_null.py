"""Change sills_logs.sill_id FK to ON DELETE SET NULL

Without this, deleting a sill raises IntegrityError in PostgreSQL because
historical log rows (from previous edits) still reference the sill id.

Revision ID: 012
Revises: 011
Create Date: 2026-05-19 00:00:00.000000

"""
from alembic import op


revision = '012'
down_revision = '011'
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Drop the existing FK constraint and re-add it with ON DELETE SET NULL.
    # The constraint name is the default PostgreSQL-generated name.
    op.execute(
        "ALTER TABLE sills_logs "
        "DROP CONSTRAINT IF EXISTS sills_logs_sill_id_fkey"
    )
    op.execute(
        "ALTER TABLE sills_logs "
        "ADD CONSTRAINT sills_logs_sill_id_fkey "
        "FOREIGN KEY (sill_id) REFERENCES sills(id) ON DELETE SET NULL"
    )


def downgrade() -> None:
    # Restore the original strict FK (rows with NULL sill_id are kept as-is).
    op.execute(
        "ALTER TABLE sills_logs "
        "DROP CONSTRAINT IF EXISTS sills_logs_sill_id_fkey"
    )
    op.execute(
        "ALTER TABLE sills_logs "
        "ADD CONSTRAINT sills_logs_sill_id_fkey "
        "FOREIGN KEY (sill_id) REFERENCES sills(id)"
    )
