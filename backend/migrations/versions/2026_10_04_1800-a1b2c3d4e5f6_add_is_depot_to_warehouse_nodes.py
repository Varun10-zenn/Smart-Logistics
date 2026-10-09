"""add_is_depot_to_warehouse_nodes

Revision ID: a1b2c3d4e5f6
Revises: 56199acc6fa4
Create Date: 2026-10-04 18:00:00.000000+00:00

"""
from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'a1b2c3d4e5f6'
down_revision: Union[str, None] = '56199acc6fa4'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # 1. Add is_depot column
    op.add_column(
        'warehouse_nodes',
        sa.Column('is_depot', sa.Boolean(), nullable=False, server_default=sa.text('0'))
    )

    # 2. Backfill is_depot = True for the node with the lowest ID for each existing warehouse
    bind = op.get_bind()
    # Find lowest node id per warehouse_id
    result = bind.execute(sa.text(
        "SELECT warehouse_id, MIN(id) AS min_node_id FROM warehouse_nodes GROUP BY warehouse_id"
    ))
    min_nodes = result.fetchall()
    for row in min_nodes:
        if row.min_node_id is not None:
            bind.execute(
                sa.text("UPDATE warehouse_nodes SET is_depot = 1 WHERE id = :node_id"),
                {"node_id": row.min_node_id}
            )


def downgrade() -> None:
    op.drop_column('warehouse_nodes', 'is_depot')
