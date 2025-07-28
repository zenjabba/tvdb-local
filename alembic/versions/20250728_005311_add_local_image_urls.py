"""Add local image URL fields to content models

Revision ID: add_local_image_urls
Revises: add_pin_support
Create Date: 2025-07-28 00:53:11

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = 'add_local_image_urls'
down_revision = 'add_pin_support'
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Add local image URL fields to artwork table
    op.add_column('artwork', sa.Column('local_image_url', sa.String(500), nullable=True))
    op.add_column('artwork', sa.Column('local_thumbnail_url', sa.String(500), nullable=True))
    op.add_column('artwork', sa.Column('storage_path', sa.String(500), nullable=True))
    op.add_column('artwork', sa.Column('processed_at', sa.DateTime(timezone=True), nullable=True))
    op.add_column('artwork', sa.Column('file_size', sa.Integer(), nullable=True))
    
    # Add local image URL fields to series table
    op.add_column('series', sa.Column('local_image_url', sa.String(500), nullable=True))
    op.add_column('series', sa.Column('local_banner_url', sa.String(500), nullable=True))
    op.add_column('series', sa.Column('local_poster_url', sa.String(500), nullable=True))
    op.add_column('series', sa.Column('local_fanart_url', sa.String(500), nullable=True))
    
    # Add local image URL fields to movies table
    op.add_column('movies', sa.Column('local_image_url', sa.String(500), nullable=True))
    op.add_column('movies', sa.Column('local_poster_url', sa.String(500), nullable=True))
    op.add_column('movies', sa.Column('local_fanart_url', sa.String(500), nullable=True))
    op.add_column('movies', sa.Column('local_banner_url', sa.String(500), nullable=True))
    
    # Add local image URL fields to episodes table
    op.add_column('episodes', sa.Column('local_image_url', sa.String(500), nullable=True))
    op.add_column('episodes', sa.Column('local_thumbnail_url', sa.String(500), nullable=True))
    
    # Add local image URL fields to seasons table
    op.add_column('seasons', sa.Column('local_image_url', sa.String(500), nullable=True))
    op.add_column('seasons', sa.Column('local_poster_url', sa.String(500), nullable=True))
    
    # Add local image URL field to people table
    op.add_column('people', sa.Column('local_image_url', sa.String(500), nullable=True))
    
    # Create indexes for faster lookups
    op.create_index('idx_artwork_local_image_url', 'artwork', ['local_image_url'])
    op.create_index('idx_artwork_processed_at', 'artwork', ['processed_at'])


def downgrade() -> None:
    # Drop indexes
    op.drop_index('idx_artwork_processed_at', 'artwork')
    op.drop_index('idx_artwork_local_image_url', 'artwork')
    
    # Remove columns from people table
    op.drop_column('people', 'local_image_url')
    
    # Remove columns from seasons table
    op.drop_column('seasons', 'local_poster_url')
    op.drop_column('seasons', 'local_image_url')
    
    # Remove columns from episodes table
    op.drop_column('episodes', 'local_thumbnail_url')
    op.drop_column('episodes', 'local_image_url')
    
    # Remove columns from movies table
    op.drop_column('movies', 'local_banner_url')
    op.drop_column('movies', 'local_fanart_url')
    op.drop_column('movies', 'local_poster_url')
    op.drop_column('movies', 'local_image_url')
    
    # Remove columns from series table
    op.drop_column('series', 'local_fanart_url')
    op.drop_column('series', 'local_poster_url')
    op.drop_column('series', 'local_banner_url')
    op.drop_column('series', 'local_image_url')
    
    # Remove columns from artwork table
    op.drop_column('artwork', 'file_size')
    op.drop_column('artwork', 'processed_at')
    op.drop_column('artwork', 'storage_path')
    op.drop_column('artwork', 'local_thumbnail_url')
    op.drop_column('artwork', 'local_image_url')