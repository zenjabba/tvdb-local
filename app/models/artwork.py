from sqlalchemy import (Boolean, Column, DateTime, Float, ForeignKey, Integer,
                        String)
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import relationship

from app.models.base import BaseModel


class Artwork(BaseModel):
    __tablename__ = "artwork"

    # Core identifiers
    tvdb_id = Column(Integer, unique=True, index=True, nullable=False)

    # Content relationships (one artwork can belong to one content type)
    series_id = Column(Integer, ForeignKey('series.id'), index=True)
    season_id = Column(Integer, ForeignKey('seasons.id'), index=True)
    episode_id = Column(Integer, ForeignKey('episodes.id'), index=True)
    movie_id = Column(Integer, ForeignKey('movies.id'), index=True)
    person_id = Column(Integer, ForeignKey('people.id'), index=True)

    # Artwork classification
    type_id = Column(Integer, ForeignKey('artwork_types.id'), nullable=False)
    language_id = Column(Integer, ForeignKey('languages.id'))

    # Image information
    image_url = Column(String(500), nullable=False)
    thumbnail_url = Column(String(500))

    # Dimensions and quality
    width = Column(Integer)
    height = Column(Integer)
    resolution = Column(String(20))  # 1920x1080, etc.

    # Metadata
    score = Column(Float, default=0.0)
    is_primary = Column(Boolean, default=False)
    include_text = Column(Boolean, default=True)

    # Extended metadata
    tags = Column(JSONB)
    status = Column(String(50))  # active, inactive, etc.

    # Cache control
    last_synced = Column(DateTime(timezone=True))

    # Relationships
    series = relationship("Series", back_populates="artwork")
    season = relationship("Season", back_populates="artwork")
    episode = relationship("Episode", back_populates="artwork")
    movie = relationship("Movie", back_populates="artwork")
    person = relationship("Person", back_populates="artwork")
    type = relationship("ArtworkType", back_populates="artwork")
    language = relationship("Language", back_populates="artwork")

    def __repr__(self):
        return f"<Artwork(tvdb_id={self.tvdb_id}, type_id={self.type_id})>"
