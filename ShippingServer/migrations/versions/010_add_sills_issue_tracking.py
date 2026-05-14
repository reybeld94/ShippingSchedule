"""Add Sills issue tracking columns

Revision ID: 010
Revises: 009
Create Date: 2026-05-14 00:00:00.000000

"""
from alembic import op


revision = '010'
down_revision = '009'
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute("ALTER TABLE sills ADD COLUMN IF NOT EXISTS issue_quantity VARCHAR(30) NOT NULL DEFAULT '0'")
    op.execute("ALTER TABLE sills ADD COLUMN IF NOT EXISTS issue_quantity_required VARCHAR(30) NOT NULL DEFAULT ''")
    op.execute("ALTER TABLE sills ADD COLUMN IF NOT EXISTS issue_status VARCHAR(20) NOT NULL DEFAULT 'pending'")
    op.execute("ALTER TABLE sills ADD COLUMN IF NOT EXISTS issue_checked_at TIMESTAMP WITHOUT TIME ZONE")
    op.execute("CREATE INDEX IF NOT EXISTS ix_sills_assembly_number ON sills (assembly_number)")
    op.execute("CREATE INDEX IF NOT EXISTS ix_sills_issue_status ON sills (issue_status)")


def downgrade() -> None:
    op.execute("DROP INDEX IF EXISTS ix_sills_issue_status")
    op.execute("DROP INDEX IF EXISTS ix_sills_assembly_number")
    op.execute("ALTER TABLE sills DROP COLUMN IF EXISTS issue_checked_at")
    op.execute("ALTER TABLE sills DROP COLUMN IF EXISTS issue_status")
    op.execute("ALTER TABLE sills DROP COLUMN IF EXISTS issue_quantity_required")
    op.execute("ALTER TABLE sills DROP COLUMN IF EXISTS issue_quantity")
