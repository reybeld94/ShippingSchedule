"""Add Sills issue completion timestamp

Revision ID: 011
Revises: 010
Create Date: 2026-05-14 00:00:00.000000

"""
from alembic import op


revision = '011'
down_revision = '010'
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute("ALTER TABLE sills ADD COLUMN IF NOT EXISTS issue_completed_at TIMESTAMP WITHOUT TIME ZONE")


def downgrade() -> None:
    op.execute("ALTER TABLE sills DROP COLUMN IF EXISTS issue_completed_at")
