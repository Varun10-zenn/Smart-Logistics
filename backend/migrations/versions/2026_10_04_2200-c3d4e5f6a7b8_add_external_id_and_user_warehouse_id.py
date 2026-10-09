"""Add external_id to warehouses and warehouse_id to users

Revision ID: c3d4e5f6a7b8
Revises: b2c3d4e5f6a7
Create Date: 2026-10-04 22:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'c3d4e5f6a7b8'
down_revision: Union[str, None] = 'b2c3d4e5f6a7'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Add external_id to warehouses
    with op.batch_alter_table('warehouses', schema=None) as batch_op:
        batch_op.add_column(sa.Column('external_id', sa.String(length=64), nullable=True))
        batch_op.create_index('ix_warehouses_external_id', ['external_id'], unique=False)

    # Add warehouse_id to users
    with op.batch_alter_table('users', schema=None) as batch_op:
        batch_op.add_column(sa.Column('warehouse_id', sa.Integer(), nullable=True))
        batch_op.create_foreign_key('fk_users_warehouse_id_warehouses', 'warehouses', ['warehouse_id'], ['id'], ondelete='SET NULL')

    # Change storage_locations.location_code index from unique=True to unique=False
    with op.batch_alter_table('storage_locations', schema=None) as batch_op:
        batch_op.drop_index('ix_storage_locations_location_code')
        batch_op.create_index('ix_storage_locations_location_code', ['location_code'], unique=False)


def downgrade() -> None:
    with op.batch_alter_table('storage_locations', schema=None) as batch_op:
        batch_op.drop_index('ix_storage_locations_location_code')
        batch_op.create_index('ix_storage_locations_location_code', ['location_code'], unique=True)

    with op.batch_alter_table('users', schema=None) as batch_op:
        batch_op.drop_constraint('fk_users_warehouse_id_warehouses', type_='foreignkey')
        batch_op.drop_column('warehouse_id')

    with op.batch_alter_table('warehouses', schema=None) as batch_op:
        batch_op.drop_index('ix_warehouses_external_id')
        batch_op.drop_column('external_id')
