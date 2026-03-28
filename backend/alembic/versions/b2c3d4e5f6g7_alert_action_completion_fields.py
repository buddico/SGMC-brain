"""alert action completion fields

Revision ID: b2c3d4e5f6g7
Revises: a1b2c3d4e5f6
Create Date: 2026-03-28 11:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

revision: str = 'b2c3d4e5f6g7'
down_revision: Union[str, None] = 'a1b2c3d4e5f6'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column('alert_actions', sa.Column('description', sa.Text(), nullable=True))
    op.add_column('alert_actions', sa.Column('assigned_to_name', sa.String(length=255), nullable=True))
    op.add_column('alert_actions', sa.Column('assigned_to_email', sa.String(length=255), nullable=True))
    op.add_column('alert_actions', sa.Column('deadline', sa.Date(), nullable=True))
    op.add_column('alert_actions', sa.Column('completed_at', sa.DateTime(), nullable=True))
    op.add_column('alert_actions', sa.Column('completed_by', sa.String(length=255), nullable=True))


def downgrade() -> None:
    op.drop_column('alert_actions', 'completed_by')
    op.drop_column('alert_actions', 'completed_at')
    op.drop_column('alert_actions', 'deadline')
    op.drop_column('alert_actions', 'assigned_to_email')
    op.drop_column('alert_actions', 'assigned_to_name')
    op.drop_column('alert_actions', 'description')
