"""Change shipments.address from boolean to text

Revision ID: 006
Revises: 005
Create Date: 2026-04-07 00:00:00.000000

"""
from alembic import op


# revision identifiers
revision = '006'
down_revision = '005'
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute(
        """
        ALTER TABLE shipments
        ALTER COLUMN address TYPE TEXT
        USING CASE WHEN address THEN 'Address available' ELSE '' END
        """
    )
    op.execute("ALTER TABLE shipments ALTER COLUMN address DROP NOT NULL")
    op.execute("ALTER TABLE shipments ALTER COLUMN address SET DEFAULT ''")
    op.execute("UPDATE shipments SET address = '' WHERE address IS NULL")
    op.execute("ALTER TABLE shipments ALTER COLUMN address SET NOT NULL")


def downgrade() -> None:
    op.execute(
        """
        ALTER TABLE shipments
        ALTER COLUMN address TYPE BOOLEAN
        USING CASE
            WHEN lower(trim(coalesce(address, ''))) IN ('', '0', 'false', 'no', 'n') THEN FALSE
            ELSE TRUE
        END
        """
    )
    op.execute("ALTER TABLE shipments ALTER COLUMN address SET DEFAULT FALSE")
    op.execute("UPDATE shipments SET address = FALSE WHERE address IS NULL")
    op.execute("ALTER TABLE shipments ALTER COLUMN address SET NOT NULL")
