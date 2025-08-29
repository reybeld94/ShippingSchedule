"""
Migration: Add versioning and integrity fields
Date: 2024-12-20
Description: Adds version control and last_modified_by fields to shipments table
"""

from alembic import op
import sqlalchemy as sa
from datetime import datetime


def upgrade():
    # Agregar nuevas columnas
    op.add_column('shipments', sa.Column('version', sa.Integer(), nullable=False, server_default='1'))
    op.add_column('shipments', sa.Column('last_modified_by', sa.Integer(), nullable=True))

    # Agregar foreign key constraint
    op.create_foreign_key(
        'fk_shipments_last_modified_by',
        'shipments', 'users',
        ['last_modified_by'], ['id']
    )

    # Actualizar registros existentes
    op.execute("""
        UPDATE shipments 
        SET last_modified_by = created_by, version = 1 
        WHERE version IS NULL OR last_modified_by IS NULL
    """)


def downgrade():
    op.drop_constraint('fk_shipments_last_modified_by', 'shipments', type_='foreignkey')
    op.drop_column('shipments', 'last_modified_by')
    op.drop_column('shipments', 'version')
