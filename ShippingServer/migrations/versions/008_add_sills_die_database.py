"""Add sills die database table

Revision ID: 008
Revises: 007
Create Date: 2026-04-23 00:00:00.000000

"""
from alembic import op


revision = '008'
down_revision = '007'
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute(
        """
        CREATE TABLE IF NOT EXISTS sills_die_database (
            id SERIAL PRIMARY KEY,
            die_number VARCHAR(50) NOT NULL UNIQUE,
            type VARCHAR(20) NOT NULL DEFAULT '',
            speed VARCHAR(10) NOT NULL DEFAULT '',
            width VARCHAR(30) NOT NULL DEFAULT '',
            supplier VARCHAR(120) NOT NULL DEFAULT '',
            notes TEXT NOT NULL DEFAULT '',
            vendor_drawing TEXT NOT NULL DEFAULT '',
            created_by INTEGER NOT NULL REFERENCES users(id),
            created_at TIMESTAMP WITHOUT TIME ZONE NOT NULL DEFAULT NOW(),
            updated_at TIMESTAMP WITHOUT TIME ZONE NOT NULL DEFAULT NOW(),
            last_modified_by INTEGER REFERENCES users(id)
        )
        """
    )

    op.execute("CREATE INDEX IF NOT EXISTS ix_sills_die_database_die_number ON sills_die_database (die_number)")


def downgrade() -> None:
    op.execute("DROP INDEX IF EXISTS ix_sills_die_database_die_number")
    op.execute("DROP TABLE IF EXISTS sills_die_database")
