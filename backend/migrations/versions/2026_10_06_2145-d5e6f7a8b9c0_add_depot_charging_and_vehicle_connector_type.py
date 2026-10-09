"""Add depot charging and vehicle connector_type

Revision ID: d5e6f7a8b9c0
Revises: c4d5e6f7a8b9
Create Date: 2026-10-06 21:45:00.000000+00:00

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'd5e6f7a8b9c0'
down_revision: Union[str, None] = 'c4d5e6f7a8b9'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    with op.batch_alter_table('charging_stations') as batch_op:
        batch_op.add_column(sa.Column('warehouse_id', sa.Integer(), nullable=True))
        batch_op.add_column(sa.Column('is_depot', sa.Boolean(), server_default='0', nullable=False))
        batch_op.create_foreign_key('fk_charging_stations_warehouse_id', 'warehouses', ['warehouse_id'], ['id'], ondelete='SET NULL')
        batch_op.create_index('idx_charging_stations_warehouse_id', ['warehouse_id'])

    with op.batch_alter_table('charging_connectors') as batch_op:
        batch_op.add_column(sa.Column('price_per_kwh', sa.Numeric(precision=6, scale=2), server_default='0.00', nullable=True))

    with op.batch_alter_table('vehicles') as batch_op:
        batch_op.add_column(sa.Column('connector_type', sa.String(length=32), server_default='CCS2', nullable=True))

    with op.batch_alter_table('charging_sessions') as batch_op:
        batch_op.add_column(sa.Column('total_cost', sa.Numeric(precision=8, scale=2), server_default='0.00', nullable=True))


def downgrade() -> None:
    with op.batch_alter_table('charging_sessions') as batch_op:
        batch_op.drop_column('total_cost')

    with op.batch_alter_table('vehicles') as batch_op:
        batch_op.drop_column('connector_type')

    with op.batch_alter_table('charging_connectors') as batch_op:
        batch_op.drop_column('price_per_kwh')

    with op.batch_alter_table('charging_stations') as batch_op:
        batch_op.drop_index('idx_charging_stations_warehouse_id')
        batch_op.drop_constraint('fk_charging_stations_warehouse_id', type_='foreignkey')
        batch_op.drop_column('is_depot')
        batch_op.drop_column('warehouse_id')
