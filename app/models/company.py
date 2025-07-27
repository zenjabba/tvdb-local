from sqlalchemy import Column, Integer, String, Text
from sqlalchemy.orm import relationship
from app.models.base import BaseModel


class Company(BaseModel):
    __tablename__ = "companies"
    
    # Core identifiers
    tvdb_id = Column(Integer, unique=True, index=True, nullable=False)
    
    # Basic information
    name = Column(String(500), nullable=False, index=True)
    slug = Column(String(500), index=True)
    overview = Column(Text)
    
    # Contact information
    country = Column(String(10))
    primary_company_type = Column(String(100))
    
    # Relationships (back references from association tables)
    series = relationship("Series", secondary="series_companies", back_populates="companies")
    movies = relationship("Movie", secondary="movie_companies", back_populates="companies")
    
    def __repr__(self):
        return f"<Company(tvdb_id={self.tvdb_id}, name='{self.name}')>"