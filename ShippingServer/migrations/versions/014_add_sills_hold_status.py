"""Add Sills manual hold status

Revision ID: 014
Revises: 013
Create Date: 2026-05-28 00:00:00.000000

"""
from alembic import op


revision = '014'
down_revision = '013'
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute("ALTER TABLE sills ADD COLUMN IF NOT EXISTS hold_status VARCHAR(10) NOT NULL DEFAULT ''")


def downgrade() -> None:
    op.execute("ALTER TABLE sills DROP COLUMN IF EXISTS hold_status")
