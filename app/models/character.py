from sqlalchemy import (Boolean, Column, DateTime, ForeignKey, Integer, String,
                        Text)
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import relationship

from app.models.base import BaseModel


class Character(BaseModel):
    __tablename__ = "characters"

    # Core identifiers
    tvdb_id = Column(Integer, unique=True, index=True, nullable=False)

    # Basic information
    name = Column(String(500), nullable=False, index=True)
    overview = Column(Text)

    # Relationships to content
    series_id = Column(Integer, ForeignKey('series.id'), index=True)
    movie_id = Column(Integer, ForeignKey('movies.id'), index=True)
    episode_id = Column(Integer, ForeignKey('episodes.id'), index=True)

    # Person playing the character
    person_id = Column(Integer, ForeignKey('people.id'), index=True)

    # Character details
    is_featured = Column(Boolean, default=False)
    sort_order = Column(Integer)
    character_type = Column(String(50))  # main, guest, recurring, etc.

    # Images
    image = Column(String(500))

    # Extended metadata
    aliases = Column(JSONB)
    translations = Column(JSONB)

    # Cache control
    last_synced = Column(DateTime(timezone=True))
    needs_full_sync = Column(Boolean, default=False)

    # Relationships
    series = relationship("Series", back_populates="characters")
    movie = relationship("Movie", back_populates="characters")
    episode = relationship("Episode", back_populates="characters")
    person = relationship("Person", back_populates="characters")

    def __repr__(self):
        return f"<Character(tvdb_id={self.tvdb_id}, name='{self.name}')>"
