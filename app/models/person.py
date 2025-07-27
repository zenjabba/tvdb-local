from sqlalchemy import Column, Integer, String, Text, DateTime, ForeignKey, Boolean
from sqlalchemy.orm import relationship
from sqlalchemy.dialects.postgresql import JSONB, ARRAY
from app.models.base import BaseModel


class Person(BaseModel):
    __tablename__ = "people"
    
    # Core identifiers
    tvdb_id = Column(Integer, unique=True, index=True, nullable=False)
    
    # Basic information
    name = Column(String(500), nullable=False, index=True)
    slug = Column(String(500), index=True)
    overview = Column(Text)
    
    # Personal details
    birth_date = Column(DateTime(timezone=True))
    death_date = Column(DateTime(timezone=True))
    birth_place = Column(String(200))
    
    # Classification
    type_id = Column(Integer, ForeignKey('person_types.id'))
    gender_id = Column(Integer, ForeignKey('genders.id'))
    
    # Images
    image = Column(String(500))
    
    # Extended metadata
    aliases = Column(JSONB)
    tags = Column(ARRAY(String))
    translations = Column(JSONB)
    remote_ids = Column(JSONB)
    
    # Cache control
    last_synced = Column(DateTime(timezone=True))
    needs_full_sync = Column(Boolean, default=False)
    
    # Relationships
    type = relationship("PersonType", back_populates="people")
    gender = relationship("Gender", back_populates="people")
    characters = relationship("Character", back_populates="person", cascade="all, delete-orphan")
    artwork = relationship("Artwork", back_populates="person", cascade="all, delete-orphan")
    
    def __repr__(self):
        return f"<Person(tvdb_id={self.tvdb_id}, name='{self.name}')>"