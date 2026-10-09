"""Add route_source to delivery_routes

Revision ID: c4d5e6f7a8b9
Revises: b2e7499a8d08
Create Date: 2026-10-06 11:30:00.000000+00:00

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'c4d5e6f7a8b9'
down_revision: Union[str, None] = 'b2e7499a8d08'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    with op.batch_alter_table('delivery_routes') as batch_op:
        batch_op.add_column(
            sa.Column('route_source', sa.String(length=32), nullable=True, server_default='osrm')
        )


def downgrade() -> None:
    with op.batch_alter_table('delivery_routes') as batch_op:
        batch_op.drop_column('route_source')
