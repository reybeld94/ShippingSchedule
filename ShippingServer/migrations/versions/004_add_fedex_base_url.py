"""Add base_url field to app connection settings

Revision ID: 004
Revises: 003
Create Date: 2026-04-06 00:00:00.000000

"""
from alembic import op

# revision identifiers
revision = '004'
down_revision = '003'
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute(
        "ALTER TABLE app_connection_settings "
        "ADD COLUMN IF NOT EXISTS base_url VARCHAR(255) DEFAULT ''"
    )


def downgrade() -> None:
    op.execute("ALTER TABLE app_connection_settings DROP COLUMN IF EXISTS base_url")
