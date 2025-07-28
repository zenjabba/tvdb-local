"""add PIN support to API keys

Revision ID: add_pin_support
Revises: 
Create Date: 2024-01-01 00:00:00.000000

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = 'add_pin_support'
down_revision = None
branch_labels = None
depends_on = None


def upgrade():
    # Add PIN support columns to api_keys table
    op.add_column('api_keys', 
        sa.Column('requires_pin', sa.Boolean(), nullable=False, server_default='false'))
    op.add_column('api_keys', 
        sa.Column('pin', sa.String(20), nullable=True))


def downgrade():
    # Remove PIN support columns
    op.drop_column('api_keys', 'pin')
    op.drop_column('api_keys', 'requires_pin')