"""Add versioning and integrity fields

Revision ID: 001
Revises: 
Create Date: 2024-12-20 10:00:00.000000

"""
from alembic import op
import sqlalchemy as sa
from datetime import datetime

# revision identifiers
revision = '001'
down_revision = None
branch_labels = None
depends_on = None

def upgrade() -> None:
    # Agregar columna de versión con valor por defecto
    op.add_column('shipments', sa.Column('version', sa.Integer(), nullable=False, server_default='1'))
    
    # Agregar columna last_modified_by
    op.add_column('shipments', sa.Column('last_modified_by', sa.Integer(), nullable=True))
    
    # Crear foreign key constraint
    op.create_foreign_key(
        'fk_shipments_last_modified_by',
        'shipments', 'users',
        ['last_modified_by'], ['id']
    )
    
    # Actualizar registros existentes para tener last_modified_by
    op.execute("""
        UPDATE shipments 
        SET last_modified_by = created_by, version = 1 
        WHERE last_modified_by IS NULL
    """)
    
    # Crear índices para optimización
    op.create_index('ix_shipment_version', 'shipments', ['version'])
    op.create_index('ix_shipment_id_version', 'shipments', ['id', 'version'])
    op.create_index('ix_shipment_last_modified', 'shipments', ['last_modified_by'])

def downgrade() -> None:
    # Remover índices
    op.drop_index('ix_shipment_last_modified', table_name='shipments')
    op.drop_index('ix_shipment_id_version', table_name='shipments')
    op.drop_index('ix_shipment_version', table_name='shipments')
    
    # Remover foreign key constraint
    op.drop_constraint('fk_shipments_last_modified_by', 'shipments', type_='foreignkey')
    
    # Remover columnas
    op.drop_column('shipments', 'last_modified_by')
    op.drop_column('shipments', 'version')
