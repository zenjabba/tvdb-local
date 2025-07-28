"""Utilities for handling image URLs in API responses."""
from typing import Any, Dict

from fastapi import Request
from sqlalchemy.orm import Session

from app.config import settings
from app.models import Episode, Movie, Person, Season, Series
from app.services.image_service import image_service
from app.services.storage import storage


def get_base_url(request: Request) -> str:
    """Get the base URL for the current request.

    Args:
        request: FastAPI request object

    Returns:
        Base URL string (e.g., https://api.example.com)
    """
    # Use CDN URL if configured
    if settings.cdn_base_url:
        return settings.cdn_base_url.rstrip('/')

    # Otherwise construct from request
    scheme = request.url.scheme
    host = request.headers.get('x-forwarded-host', request.url.hostname)
    port = request.url.port

    if (scheme == 'https' and port == 443) or (scheme == 'http' and port == 80):
        return f"{scheme}://{host}"
    if port:
        return f"{scheme}://{host}:{port}"
    return f"{scheme}://{host}"


def enrich_with_local_images(data: Dict[str, Any], entity_type: str,
                             db: Session, base_url: str) -> Dict[str, Any]:
    """Enrich entity data with local image URLs.

    This function checks if we have local images stored and replaces TVDB URLs
    with our local URLs when available, maintaining TVDB API compatibility.

    Args:
        data: Entity data dictionary
        entity_type: Type of entity (series, movie, episode, person)
        db: Database session
        base_url: Base URL for constructing image URLs

    Returns:
        Modified data dictionary with local image URLs
    """
    if not data or not isinstance(data, dict):
        return data

    entity_id = data.get('id')
    if not entity_id:
        return data

    # Get entity from database to check for local images
    entity = None
    if entity_type == 'series':
        entity = db.query(Series).filter(Series.tvdb_id == entity_id).first()
    elif entity_type == 'movie':
        entity = db.query(Movie).filter(Movie.tvdb_id == entity_id).first()
    elif entity_type == 'episode':
        entity = db.query(Episode).filter(Episode.tvdb_id == entity_id).first()
    elif entity_type == 'person':
        entity = db.query(Person).filter(Person.tvdb_id == entity_id).first()
    elif entity_type == 'season':
        entity = db.query(Season).filter(Season.tvdb_id == entity_id).first()

    if not entity:
        return data

    # Map of TVDB fields to local fields
    image_field_map = {
        'image': 'local_image_url',
        'poster': 'local_poster_url',
        'banner': 'local_banner_url',
        'fanart': 'local_fanart_url',
        'thumbnail': 'local_thumbnail_url'
    }

    # Replace image URLs with local ones if available
    for tvdb_field, local_field in image_field_map.items():
        if tvdb_field in data and hasattr(entity, local_field):
            local_url = getattr(entity, local_field, None)

            # Check if we have a local image stored
            if local_url or _check_local_image_exists(entity_type, entity_id, tvdb_field):
                # Generate the local URL
                data[tvdb_field] = image_service.get_local_image_url(
                    entity_type, entity_id, tvdb_field, base_url
                )

    return data


def _check_local_image_exists(entity_type: str, entity_id: int, image_type: str) -> bool:
    """Check if a local image exists in storage.

    Args:
        entity_type: Type of entity
        entity_id: Entity ID
        image_type: Type of image

    Returns:
        True if image exists locally
    """

    # Check for common image extensions
    for ext in ['jpg', 'jpeg', 'png', 'gif', 'webp']:
        key = f"{entity_type}/{entity_id}/{image_type}.{ext}"
        if storage.image_exists(key):
            return True
    return False


def enrich_list_with_local_images(data_list: list, entity_type: str,
                                  db: Session, base_url: str) -> list:
    """Enrich a list of entities with local image URLs.

    Args:
        data_list: List of entity dictionaries
        entity_type: Type of entity
        db: Database session
        base_url: Base URL for constructing image URLs

    Returns:
        Modified list with local image URLs
    """
    if not data_list or not isinstance(data_list, list):
        return data_list

    return [enrich_with_local_images(item, entity_type, db, base_url)
            for item in data_list]
