from sqlalchemy import (Boolean, Column, DateTime, Float, ForeignKey, Integer,
                        String, Table, Text)
from sqlalchemy.dialects.postgresql import ARRAY, JSONB
from sqlalchemy.orm import relationship

from app.models.base import BaseModel

# Association tables for many-to-many relationships
movie_genres = Table(
    'movie_genres',
    BaseModel.metadata,
    Column('movie_id', Integer, ForeignKey('movies.id'), primary_key=True),
    Column('genre_id', Integer, ForeignKey('genres.id'), primary_key=True)
)

movie_companies = Table(
    'movie_companies',
    BaseModel.metadata,
    Column('movie_id', Integer, ForeignKey('movies.id'), primary_key=True),
    Column('company_id', Integer, ForeignKey('companies.id'), primary_key=True)
)


class Movie(BaseModel):
    __tablename__ = "movies"

    # Core identifiers
    tvdb_id = Column(Integer, unique=True, index=True, nullable=False)
    imdb_id = Column(String(20), index=True)

    # Basic information
    name = Column(String(500), nullable=False, index=True)
    slug = Column(String(500), index=True)
    overview = Column(Text)

    # Metadata
    year = Column(Integer, index=True)
    release_date = Column(DateTime(timezone=True))
    runtime = Column(Integer)

    # Status and classification
    status_id = Column(Integer, ForeignKey('movie_status.id'))
    original_country = Column(String(10))
    original_language = Column(String(10))

    # Ratings and popularity
    rating = Column(Float)
    score = Column(Float)
    popularity = Column(Float, index=True)

    # Budget and revenue
    budget = Column(String(100))  # Store as string to handle currency
    revenue = Column(String(100))

    # Images and artwork
    image = Column(String(500))
    poster = Column(String(500))
    fanart = Column(String(500))
    banner = Column(String(500))
    
    # Local image URLs
    local_image_url = Column(String(500))
    local_poster_url = Column(String(500))
    local_fanart_url = Column(String(500))
    local_banner_url = Column(String(500))

    # Extended metadata
    aliases = Column(JSONB)
    tags = Column(ARRAY(String))
    translations = Column(JSONB)
    remote_ids = Column(JSONB)

    # Cache control
    last_synced = Column(DateTime(timezone=True))
    needs_full_sync = Column(Boolean, default=False)

    # Relationships
    status = relationship("MovieStatus", back_populates="movies")
    artwork = relationship(
        "Artwork",
        back_populates="movie",
        cascade="all, delete-orphan")
    characters = relationship(
        "Character",
        back_populates="movie",
        cascade="all, delete-orphan")

    # Many-to-many relationships
    genres = relationship(
        "Genre",
        secondary=movie_genres,
        back_populates="movies")
    companies = relationship(
        "Company",
        secondary=movie_companies,
        back_populates="movies")

    def __repr__(self):
        return f"<Movie(tvdb_id={self.tvdb_id}, name='{self.name}')>"
