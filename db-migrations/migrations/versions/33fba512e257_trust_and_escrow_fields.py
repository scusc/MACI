"""trust_and_escrow_fields

Revision ID: 33fba512e257
Revises: 33fba512e256
Create Date: 2026-07-20 16:35:00.000000

"""
from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision = '33fba512e257'
down_revision = '33fba512e256'
branch_labels = None
depends_on = None

def upgrade() -> None:
    # Add new columns to rally_users
    op.add_column('rally_users', sa.Column('kyc_status', sa.String(length=50), server_default='unverified', nullable=True))
    op.add_column('rally_users', sa.Column('karma_score', sa.Integer(), server_default='100', nullable=True))
    op.add_column('rally_users', sa.Column('stripe_connect_id', sa.String(length=255), nullable=True))

def downgrade() -> None:
    # Remove columns from rally_users
    op.drop_column('rally_users', 'stripe_connect_id')
    op.drop_column('rally_users', 'karma_score')
    op.drop_column('rally_users', 'kyc_status')
