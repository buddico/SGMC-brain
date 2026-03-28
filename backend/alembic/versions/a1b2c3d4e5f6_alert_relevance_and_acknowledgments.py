"""alert relevance and acknowledgments

Revision ID: a1b2c3d4e5f6
Revises: 5dce47bb5e4a
Create Date: 2026-03-28 10:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = 'a1b2c3d4e5f6'
down_revision: Union[str, None] = '5dce47bb5e4a'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Triage fields on alerts
    op.add_column('alerts', sa.Column('is_relevant', sa.Boolean(), nullable=True))
    op.add_column('alerts', sa.Column('triaged_by_email', sa.String(length=255), nullable=True))
    op.add_column('alerts', sa.Column('triaged_by_name', sa.String(length=255), nullable=True))
    op.add_column('alerts', sa.Column('triaged_at', sa.DateTime(), nullable=True))

    # Alert acknowledgments (read receipts for CQC)
    op.create_table('alert_acknowledgments',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column('alert_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('alerts.id'), nullable=False),
        sa.Column('user_email', sa.String(length=255), nullable=False),
        sa.Column('user_name', sa.String(length=255), nullable=False),
        sa.Column('requested_at', sa.DateTime(), server_default=sa.func.now(), nullable=False),
        sa.Column('acknowledged_at', sa.DateTime(), nullable=True),
        sa.Column('method', sa.String(length=50), nullable=True),
    )


def downgrade() -> None:
    op.drop_table('alert_acknowledgments')
    op.drop_column('alerts', 'triaged_at')
    op.drop_column('alerts', 'triaged_by_name')
    op.drop_column('alerts', 'triaged_by_email')
    op.drop_column('alerts', 'is_relevant')
