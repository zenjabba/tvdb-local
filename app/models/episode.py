from sqlalchemy import (Boolean, Column, DateTime, Float, ForeignKey, Integer,
                        String, Text)
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import relationship

from app.models.base import BaseModel


class Episode(BaseModel):
    __tablename__ = "episodes"

    # Core identifiers
    tvdb_id = Column(Integer, unique=True, index=True, nullable=False)
    series_id = Column(
        Integer,
        ForeignKey('series.id'),
        nullable=False,
        index=True)
    season_id = Column(Integer, ForeignKey('seasons.id'), index=True)

    # Basic information
    name = Column(String(500), index=True)
    overview = Column(Text)

    # Episode numbering
    number = Column(Integer, index=True)
    absolute_number = Column(Integer, index=True)
    dvd_episode_number = Column(Float)
    dvd_season_number = Column(Integer)
    season_number = Column(Integer, index=True)

    # Metadata
    year = Column(Integer)
    aired = Column(DateTime(timezone=True), index=True)
    runtime = Column(Integer)

    # Ratings
    rating = Column(Float)

    # Images
    image = Column(String(500))
    thumbnail = Column(String(500))

    # Local image URLs
    local_image_url = Column(String(500))
    local_thumbnail_url = Column(String(500))

    # Extended metadata
    translations = Column(JSONB)
    production_code = Column(String(50))
    last_updated = Column(DateTime(timezone=True))
    finale_type = Column(String(50))  # series, season, mid-season, etc.

    # Cache control
    last_synced = Column(DateTime(timezone=True))
    needs_full_sync = Column(Boolean, default=False)

    # Relationships
    series = relationship("Series", back_populates="episodes")
    season = relationship("Season", back_populates="episodes")
    artwork = relationship(
        "Artwork",
        back_populates="episode",
        cascade="all, delete-orphan")
    characters = relationship(
        "Character",
        back_populates="episode",
        cascade="all, delete-orphan")

    def __repr__(self):
        return (
            f"<Episode(tvdb_id={self.tvdb_id}, "
            f"series_id={self.series_id}, number={self.number})>"
        )
