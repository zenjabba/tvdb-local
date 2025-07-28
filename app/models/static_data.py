from sqlalchemy import Column, Integer, String, Text
from sqlalchemy.orm import relationship

from app.models.base import BaseModel


class ArtworkType(BaseModel):
    __tablename__ = "artwork_types"

    tvdb_id = Column(Integer, unique=True, index=True, nullable=False)
    name = Column(String(100), nullable=False, unique=True)
    slug = Column(String(100), unique=True)
    width = Column(Integer)
    height = Column(Integer)

    # Relationships
    artwork = relationship("Artwork", back_populates="type")

    def __repr__(self):
        return f"<ArtworkType(name='{self.name}')>"


class AwardCategory(BaseModel):
    __tablename__ = "award_categories"

    tvdb_id = Column(Integer, unique=True, index=True, nullable=False)
    name = Column(String(200), nullable=False)
    allow_cowinners = Column(String(10))

    def __repr__(self):
        return f"<AwardCategory(name='{self.name}')>"


class ContentRating(BaseModel):
    __tablename__ = "content_ratings"

    tvdb_id = Column(Integer, unique=True, index=True, nullable=False)
    name = Column(String(50), nullable=False)
    country = Column(String(10))
    content_type = Column(String(50))
    order = Column(Integer)
    full_name = Column(String(200))
    description = Column(Text)

    def __repr__(self):
        return f"<ContentRating(name='{self.name}', country='{self.country}')>"


class EntityType(BaseModel):
    __tablename__ = "entity_types"

    tvdb_id = Column(Integer, unique=True, index=True, nullable=False)
    name = Column(String(100), nullable=False, unique=True)

    def __repr__(self):
        return f"<EntityType(name='{self.name}')>"


class Gender(BaseModel):
    __tablename__ = "genders"

    tvdb_id = Column(Integer, unique=True, index=True, nullable=False)
    name = Column(String(50), nullable=False, unique=True)

    # Relationships
    people = relationship("Person", back_populates="gender")

    def __repr__(self):
        return f"<Gender(name='{self.name}')>"


class InspiationType(BaseModel):
    __tablename__ = "inspiration_types"

    tvdb_id = Column(Integer, unique=True, index=True, nullable=False)
    name = Column(String(100), nullable=False)
    description = Column(Text)
    reference_name = Column(String(100))
    url = Column(String(500))

    def __repr__(self):
        return f"<InspiationType(name='{self.name}')>"


class MovieStatus(BaseModel):
    __tablename__ = "movie_status"

    tvdb_id = Column(Integer, unique=True, index=True, nullable=False)
    name = Column(String(100), nullable=False, unique=True)
    keep_updated = Column(String(10))
    record_type = Column(String(50))

    # Relationships
    movies = relationship("Movie", back_populates="status")

    def __repr__(self):
        return f"<MovieStatus(name='{self.name}')>"


class SeriesStatus(BaseModel):
    __tablename__ = "series_status"

    tvdb_id = Column(Integer, unique=True, index=True, nullable=False)
    name = Column(String(100), nullable=False, unique=True)
    keep_updated = Column(String(10))
    record_type = Column(String(50))

    # Relationships
    series = relationship("Series", back_populates="status")

    def __repr__(self):
        return f"<SeriesStatus(name='{self.name}')>"


class PersonType(BaseModel):
    __tablename__ = "person_types"

    tvdb_id = Column(Integer, unique=True, index=True, nullable=False)
    name = Column(String(100), nullable=False, unique=True)

    # Relationships
    people = relationship("Person", back_populates="type")

    def __repr__(self):
        return f"<PersonType(name='{self.name}')>"


class SourceType(BaseModel):
    __tablename__ = "source_types"

    tvdb_id = Column(Integer, unique=True, index=True, nullable=False)
    name = Column(String(100), nullable=False)
    slug = Column(String(100))
    sort = Column(Integer)
    prefix = Column(String(20))
    postfix = Column(String(20))

    def __repr__(self):
        return f"<SourceType(name='{self.name}')>"
