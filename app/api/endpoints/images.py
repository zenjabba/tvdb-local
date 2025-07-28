"""Image serving endpoints - TVDB API compliant."""
from typing import Optional

from fastapi import APIRouter, HTTPException, Response
from fastapi.responses import StreamingResponse
import structlog

from app.config import settings
from app.services.image_service import image_service
from app.services.storage import storage
from app.database import get_db
from app.models import Series, Movie, Episode, Person
from sqlalchemy.orm import Session
from fastapi import Depends

logger = structlog.get_logger()

router = APIRouter()


@router.get("/{entity_type}/{entity_id}/{image_type}")
async def get_image(
    entity_type: str,
    entity_id: int,
    image_type: str,
    db: Session = Depends(get_db)
):
    """Serve raw image from storage with fallback to TVDB.
    
    This endpoint serves raw images stored in our S3/Ceph storage.
    If the image is not found locally, it falls back to the TVDB URL.
    
    Args:
        entity_type: Type of entity (series, movie, episode, person)
        entity_id: TVDB ID of the entity
        image_type: Type of image (poster, banner, fanart, image)
    
    Returns:
        Raw image data with appropriate content type
    """
    # Validate entity type
    valid_entity_types = ["series", "movie", "episode", "person"]
    if entity_type not in valid_entity_types:
        raise HTTPException(status_code=404, detail="Invalid entity type")
    
    # Validate image type
    valid_image_types = ["poster", "banner", "fanart", "image", "thumbnail"]
    if image_type not in valid_image_types:
        raise HTTPException(status_code=404, detail="Invalid image type")
    
    # Try to get image from storage
    result = await image_service.get_image(entity_type, entity_id, image_type)
    
    if result:
        image_data, content_type = result
        
        # Return image with caching headers
        return Response(
            content=image_data,
            media_type=content_type,
            headers={
                "Cache-Control": "public, max-age=86400",  # 24 hours
                "X-Content-Type-Options": "nosniff"
            }
        )
    
    # If not found locally, check if we have a TVDB URL to fallback to
    fallback_url = await _get_tvdb_fallback_url(db, entity_type, entity_id, image_type)
    
    if fallback_url:
        # Optionally, we could redirect to TVDB
        # return RedirectResponse(url=fallback_url, status_code=302)
        
        # Or return 404 and let client use the URL from API response
        raise HTTPException(
            status_code=404, 
            detail="Image not found locally, use TVDB URL from API response"
        )
    
    raise HTTPException(status_code=404, detail="Image not found")


async def _get_tvdb_fallback_url(
    db: Session, 
    entity_type: str, 
    entity_id: int, 
    image_type: str
) -> Optional[str]:
    """Get TVDB fallback URL for an image.
    
    Args:
        db: Database session
        entity_type: Type of entity
        entity_id: TVDB ID
        image_type: Type of image
        
    Returns:
        TVDB URL or None
    """
    try:
        if entity_type == "series":
            series = db.query(Series).filter(Series.tvdb_id == entity_id).first()
            if series:
                return getattr(series, image_type, None)
        elif entity_type == "movie":
            movie = db.query(Movie).filter(Movie.tvdb_id == entity_id).first()
            if movie:
                return getattr(movie, image_type, None)
        elif entity_type == "episode":
            episode = db.query(Episode).filter(Episode.tvdb_id == entity_id).first()
            if episode:
                return getattr(episode, "image" if image_type == "image" else None, None)
        elif entity_type == "person":
            person = db.query(Person).filter(Person.tvdb_id == entity_id).first()
            if person:
                return getattr(person, "image", None)
    except Exception as e:
        logger.error("Failed to get fallback URL", 
                    entity_type=entity_type,
                    entity_id=entity_id,
                    error=str(e))
    
    return None


@router.get("/storage/stats")
async def get_storage_stats():
    """Get storage statistics (admin endpoint).
    
    Returns:
        Storage statistics including total size and object count
    """
    try:
        stats = storage.get_storage_stats()
        return {"status": "success", "data": stats}
    except Exception as e:
        logger.error("Failed to get storage stats", error=str(e))
        raise HTTPException(status_code=500, detail="Failed to get storage statistics")