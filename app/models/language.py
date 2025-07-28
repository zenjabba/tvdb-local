from sqlalchemy import Column, Integer, String
from sqlalchemy.orm import relationship

from app.models.base import BaseModel


class Language(BaseModel):
    __tablename__ = "languages"

    # Core identifiers
    tvdb_id = Column(Integer, unique=True, index=True, nullable=False)

    # Basic information
    name = Column(String(100), nullable=False, index=True)
    # en, es, fr, etc.
    short_code = Column(String(10), unique=True, index=True)

    # Relationships
    artwork = relationship("Artwork", back_populates="language")

    def __repr__(self):
        return f"<Language(tvdb_id={self.tvdb_id}, name='{self.name}', code='{self.short_code}')>"
