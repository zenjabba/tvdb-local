from sqlalchemy import Column, Integer, String
from sqlalchemy.orm import relationship
from app.models.base import BaseModel


class Genre(BaseModel):
    __tablename__ = "genres"
    
    # Core identifiers
    tvdb_id = Column(Integer, unique=True, index=True, nullable=False)
    
    # Basic information
    name = Column(String(100), nullable=False, unique=True, index=True)
    slug = Column(String(100), unique=True, index=True)
    
    # Relationships (back references from association tables)
    series = relationship("Series", secondary="series_genres", back_populates="genres")
    movies = relationship("Movie", secondary="movie_genres", back_populates="genres")
    
    def __repr__(self):
        return f"<Genre(tvdb_id={self.tvdb_id}, name='{self.name}')>"