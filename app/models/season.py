from sqlalchemy import (Boolean, Column, DateTime, ForeignKey, Integer, String,
                        Text)
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import relationship

from app.models.base import BaseModel


class Season(BaseModel):
    __tablename__ = "seasons"

    # Core identifiers
    tvdb_id = Column(Integer, unique=True, index=True, nullable=False)
    series_id = Column(
        Integer,
        ForeignKey('series.id'),
        nullable=False,
        index=True)

    # Basic information
    name = Column(String(500))
    overview = Column(Text)
    number = Column(Integer, nullable=False, index=True)
    season_type = Column(String(50))  # official, dvd, absolute, etc.

    # Metadata
    year = Column(Integer)
    air_date = Column(DateTime(timezone=True))

    # Images
    image = Column(String(500))
    poster = Column(String(500))
    
    # Local image URLs
    local_image_url = Column(String(500))
    local_poster_url = Column(String(500))

    # Extended metadata
    translations = Column(JSONB)
    tags = Column(JSONB)

    # Cache control
    last_synced = Column(DateTime(timezone=True))
    needs_full_sync = Column(Boolean, default=False)

    # Relationships
    series = relationship("Series", back_populates="seasons")
    episodes = relationship(
        "Episode",
        back_populates="season",
        cascade="all, delete-orphan")
    artwork = relationship(
        "Artwork",
        back_populates="season",
        cascade="all, delete-orphan")

    def __repr__(self):
        return f"<Season(tvdb_id={self.tvdb_id}, series_id={self.series_id}, number={self.number})>"
