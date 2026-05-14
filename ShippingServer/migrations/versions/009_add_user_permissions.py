"""Add per-user module and column permissions

Revision ID: 009
Revises: 008
Create Date: 2026-05-14 00:00:00.000000

"""
from alembic import op


revision = '009'
down_revision = '008'
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute(
        """
        CREATE TABLE IF NOT EXISTS user_permissions (
            id SERIAL PRIMARY KEY,
            user_id INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
            module VARCHAR(50) NOT NULL,
            column_key VARCHAR(100) NOT NULL DEFAULT '',
            can_view BOOLEAN NOT NULL DEFAULT FALSE,
            can_write BOOLEAN NOT NULL DEFAULT FALSE,
            updated_at TIMESTAMP WITHOUT TIME ZONE NOT NULL DEFAULT NOW(),
            updated_by INTEGER REFERENCES users(id),
            CONSTRAINT uq_user_permissions_user_module_column UNIQUE (user_id, module, column_key)
        )
        """
    )
    op.execute(
        "CREATE UNIQUE INDEX IF NOT EXISTS ix_user_permissions_user_module_column "
        "ON user_permissions (user_id, module, column_key)"
    )
    op.execute(
        "CREATE INDEX IF NOT EXISTS ix_user_permissions_user_module "
        "ON user_permissions (user_id, module)"
    )


def downgrade() -> None:
    op.execute("DROP INDEX IF EXISTS ix_user_permissions_user_module")
    op.execute("DROP INDEX IF EXISTS ix_user_permissions_user_module_column")
    op.execute("DROP TABLE IF EXISTS user_permissions")
