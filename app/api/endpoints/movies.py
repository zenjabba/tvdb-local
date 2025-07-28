from typing import Any, Dict

import structlog
from fastapi import APIRouter, Depends, HTTPException, Query, Request
from slowapi import Limiter
from slowapi.util import get_remote_address

from app.auth import get_current_client
from app.config import settings
from app.services.tvdb_client import tvdb_client

logger = structlog.get_logger()

router = APIRouter()
limiter = Limiter(key_func=get_remote_address)


@router.get("/{movie_id}")
@limiter.limit(f"{settings.rate_limit_requests_per_minute}/minute")
async def get_movie(
    request: Request,
    movie_id: int,
    extended: bool = Query(False, description="Return extended movie information"),
    current_client: dict = Depends(get_current_client)
) -> Dict[str, Any]:
    """
    Get movie information by TVDB ID

    - **movie_id**: The TVDB movie ID
    - **extended**: If true, returns extended information including cast, crew, etc.
    """
    try:
        logger.info(
            "Movie request",
            movie_id=movie_id,
            extended=extended,
            client=current_client.get("client_name"))

        if extended:
            movie_data = await tvdb_client.get_movie_extended(movie_id)
        else:
            movie_data = await tvdb_client.get_movie(movie_id)

        if not movie_data:
            raise HTTPException(
                status_code=404,
                detail=f"Movie with ID {movie_id} not found"
            )

        return {
            "data": movie_data,
            "meta": {
                "movie_id": movie_id,
                "extended": extended,
                "cached": True  # Would check if data came from cache
            }
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error("Failed to fetch movie", movie_id=movie_id, error=str(e))
        raise HTTPException(
            status_code=500,
            detail="Failed to fetch movie data"
        ) from e


@router.post("/{movie_id}/cache/invalidate")
@limiter.limit("10/minute")
async def invalidate_movie_cache(
    request: Request,
    movie_id: int,
    current_client: dict = Depends(get_current_client)
) -> Dict[str, Any]:
    """
    Invalidate cache for a specific movie

    This will force fresh data to be fetched from TVDB on the next request.

    - **movie_id**: The TVDB movie ID
    """
    try:
        logger.info("Movie cache invalidation request",
                    movie_id=movie_id,
                    client=current_client.get("client_name"))

        await tvdb_client.invalidate_cache("movie", movie_id)

        return {
            "success": True,
            "message": f"Cache invalidated for movie {movie_id}",
            "movie_id": movie_id
        }

    except Exception as e:
        logger.error(
            "Failed to invalidate movie cache",
            movie_id=movie_id,
            error=str(e))
        raise HTTPException(
            status_code=500,
            detail="Failed to invalidate cache"
        ) from e
