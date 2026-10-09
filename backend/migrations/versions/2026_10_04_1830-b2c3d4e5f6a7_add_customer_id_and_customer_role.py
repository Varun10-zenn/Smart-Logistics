"""Add customer_id to orders and insert customer role

Revision ID: b2c3d4e5f6a7
Revises: a1b2c3d4e5f6
Create Date: 2026-10-04 18:30:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'b2c3d4e5f6a7'
down_revision: Union[str, None] = 'a1b2c3d4e5f6'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Add customer_id column to orders
    with op.batch_alter_table('orders', schema=None) as batch_op:
        batch_op.add_column(sa.Column('customer_id', sa.BigInteger().with_variant(sa.Integer(), 'sqlite'), nullable=True))
        batch_op.create_foreign_key('fk_orders_customer_id_users', 'users', ['customer_id'], ['id'], ondelete='SET NULL')

    # Seed 'customer' role if not present
    op.execute(
        "INSERT INTO roles (code, description, created_at) "
        "SELECT 'customer', 'Customer e-commerce ordering role', CURRENT_TIMESTAMP "
        "WHERE NOT EXISTS (SELECT 1 FROM roles WHERE code = 'customer')"
    )


def downgrade() -> None:
    with op.batch_alter_table('orders', schema=None) as batch_op:
        batch_op.drop_constraint('fk_orders_customer_id_users', type_='foreignkey')
        batch_op.drop_column('customer_id')
