"""add category and display_order to event_types

Revision ID: 5dce47bb5e4a
Revises: d780087b4b53
Create Date: 2026-03-28 09:50:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = '5dce47bb5e4a'
down_revision: Union[str, None] = 'd780087b4b53'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column('event_types', sa.Column('category', sa.String(length=100), nullable=True))
    op.add_column('event_types', sa.Column('display_order', sa.SmallInteger(), nullable=True, server_default='0'))
    op.add_column('event_types', sa.Column('examples', postgresql.JSONB(astext_type=sa.Text()), nullable=True))
    op.add_column('event_types', sa.Column('typical_actions', postgresql.JSONB(astext_type=sa.Text()), nullable=True))


def downgrade() -> None:
    op.drop_column('event_types', 'typical_actions')
    op.drop_column('event_types', 'examples')
    op.drop_column('event_types', 'display_order')
    op.drop_column('event_types', 'category')
