"""Add app connection settings table for FedEx credentials

Revision ID: 003
Revises: 002
Create Date: 2026-04-06 00:00:00.000000

"""
from alembic import op

# revision identifiers
revision = '003'
down_revision = '002'
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute(
        """
        CREATE TABLE IF NOT EXISTS app_connection_settings (
            id SERIAL PRIMARY KEY,
            provider VARCHAR(50) NOT NULL UNIQUE,
            enabled BOOLEAN NOT NULL DEFAULT FALSE,
            api_key VARCHAR(255) DEFAULT '',
            secret_key VARCHAR(255) DEFAULT '',
            updated_at TIMESTAMP WITHOUT TIME ZONE DEFAULT NOW()
        )
        """
    )
    op.execute(
        "CREATE INDEX IF NOT EXISTS ix_app_connection_settings_id ON app_connection_settings (id)"
    )
    op.execute(
        "CREATE INDEX IF NOT EXISTS ix_app_connection_settings_provider ON app_connection_settings (provider)"
    )


def downgrade() -> None:
    op.execute("DROP INDEX IF EXISTS ix_app_connection_settings_provider")
    op.execute("DROP INDEX IF EXISTS ix_app_connection_settings_id")
    op.execute("DROP TABLE IF EXISTS app_connection_settings")
