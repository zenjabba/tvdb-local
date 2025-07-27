from sqlalchemy import Column, Integer, String, Text, DateTime, Float, Boolean, ForeignKey, Table
from sqlalchemy.orm import relationship
from sqlalchemy.dialects.postgresql import JSONB, ARRAY
from app.models.base import BaseModel

# Association tables for many-to-many relationships
series_genres = Table(
    'series_genres',
    BaseModel.metadata,
    Column('series_id', Integer, ForeignKey('series.id'), primary_key=True),
    Column('genre_id', Integer, ForeignKey('genres.id'), primary_key=True)
)

series_companies = Table(
    'series_companies', 
    BaseModel.metadata,
    Column('series_id', Integer, ForeignKey('series.id'), primary_key=True),
    Column('company_id', Integer, ForeignKey('companies.id'), primary_key=True)
)


class Series(BaseModel):
    __tablename__ = "series"
    
    # Core identifiers
    tvdb_id = Column(Integer, unique=True, index=True, nullable=False)
    imdb_id = Column(String(20), index=True)
    
    # Basic information
    name = Column(String(500), nullable=False, index=True)
    slug = Column(String(500), index=True)
    overview = Column(Text)
    
    # Metadata
    year = Column(Integer, index=True)
    first_aired = Column(DateTime(timezone=True))
    last_aired = Column(DateTime(timezone=True))
    next_aired = Column(DateTime(timezone=True))
    
    # Status and classification
    status_id = Column(Integer, ForeignKey('series_status.id'))
    original_country = Column(String(10))
    original_language = Column(String(10))
    
    # Ratings and popularity
    average_runtime = Column(Integer)
    rating = Column(Float)
    score = Column(Float)
    popularity = Column(Float, index=True)
    
    # Images and artwork
    image = Column(String(500))
    banner = Column(String(500))
    poster = Column(String(500))
    fanart = Column(String(500))
    
    # Extended metadata (stored as JSON)
    aliases = Column(JSONB)
    tags = Column(ARRAY(String))
    translations = Column(JSONB)
    remote_ids = Column(JSONB)  # Store external IDs (IMDB, etc.)
    
    # Cache control
    last_synced = Column(DateTime(timezone=True))
    needs_full_sync = Column(Boolean, default=False)
    
    # Relationships
    status = relationship("SeriesStatus", back_populates="series")
    seasons = relationship("Season", back_populates="series", cascade="all, delete-orphan")
    episodes = relationship("Episode", back_populates="series", cascade="all, delete-orphan")
    artwork = relationship("Artwork", back_populates="series", cascade="all, delete-orphan")
    characters = relationship("Character", back_populates="series", cascade="all, delete-orphan")
    
    # Many-to-many relationships
    genres = relationship("Genre", secondary=series_genres, back_populates="series")
    companies = relationship("Company", secondary=series_companies, back_populates="series")
    
    def __repr__(self):
        return f"<Series(tvdb_id={self.tvdb_id}, name='{self.name}')>"