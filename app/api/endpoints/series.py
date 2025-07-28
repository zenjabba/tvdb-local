from typing import Any, Dict, Optional

import structlog
from fastapi import APIRouter, Depends, HTTPException, Query, Request
from slowapi import Limiter
from slowapi.util import get_remote_address
from sqlalchemy.orm import Session

from app.auth import get_current_client
from app.config import settings
from app.database import get_db
from app.services.tvdb_client import tvdb_client
from app.api.utils.image_urls import enrich_with_local_images, get_base_url

logger = structlog.get_logger()

router = APIRouter()
limiter = Limiter(key_func=get_remote_address)


@router.get("/{series_id}")
@limiter.limit(f"{settings.rate_limit_requests_per_minute}/minute")
async def get_series(
    request: Request,
    series_id: int,
    extended: bool = Query(False, description="Return extended series information"),
    current_client: dict = Depends(get_current_client),
    db: Session = Depends(get_db)
) -> Dict[str, Any]:
    """
    Get series information by TVDB ID

    - **series_id**: The TVDB series ID
    - **extended**: If true, returns extended information including cast, crew, etc.
    """
    try:
        logger.info(
            "Series request",
            series_id=series_id,
            extended=extended,
            client=current_client.get("client_name"))

        if extended:
            series_data = await tvdb_client.get_series_extended(series_id)
        else:
            series_data = await tvdb_client.get_series(series_id)

        if not series_data:
            raise HTTPException(
                status_code=404,
                detail=f"Series with ID {series_id} not found"
            )

        # Enrich with local image URLs
        base_url = get_base_url(request)
        series_data = enrich_with_local_images(series_data, 'series', db, base_url)

        return {
            "data": series_data,
            "meta": {
                "series_id": series_id,
                "extended": extended,
                "cached": True  # Would check if data came from cache
            }
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(
            "Failed to fetch series",
            series_id=series_id,
            error=str(e))
        raise HTTPException(
            status_code=500,
            detail="Failed to fetch series data"
        )


@router.get("/{series_id}/episodes")
@limiter.limit(f"{settings.rate_limit_requests_per_minute}/minute")
async def get_series_episodes(
    request: Request,
    series_id: int,
    page: int = Query(0, ge=0, description="Page number for pagination"),
    season: Optional[int] = Query(None, description="Filter by season number"),
    current_client: dict = Depends(get_current_client)
) -> Dict[str, Any]:
    """
    Get episodes for a series

    - **series_id**: The TVDB series ID
    - **page**: Page number for pagination (starts at 0)
    - **season**: Optional season number filter
    """
    try:
        logger.info("Series episodes request",
                    series_id=series_id,
                    page=page,
                    season=season,
                    client=current_client.get("client_name"))

        episodes_data = await tvdb_client.get_series_episodes(series_id, page)

        if not episodes_data:
            raise HTTPException(
                status_code=404,
                detail=f"No episodes found for series {series_id}"
            )

        # Filter by season if requested
        if season is not None and episodes_data.get('data'):
            filtered_episodes = [
                ep for ep in episodes_data['data']
                if ep.get('seasonNumber') == season
            ]
            episodes_data['data'] = filtered_episodes

        return {
            "data": episodes_data.get(
                'data',
                []),
            "meta": {
                "series_id": series_id,
                "page": page,
                "season_filter": season,
                "total_pages": episodes_data.get(
                    'links',
                    {}).get('totalPages'),
                "has_next": bool(
                    episodes_data.get(
                        'links',
                        {}).get('next')),
                "has_prev": bool(
                    episodes_data.get(
                        'links',
                        {}).get('prev'))}}

    except HTTPException:
        raise
    except Exception as e:
        logger.error(
            "Failed to fetch series episodes",
            series_id=series_id,
            error=str(e))
        raise HTTPException(
            status_code=500,
            detail="Failed to fetch series episodes"
        )


@router.get("/{series_id}/seasons/{season_id}")
@limiter.limit(f"{settings.rate_limit_requests_per_minute}/minute")
async def get_season(
    request: Request,
    series_id: int,
    season_id: int,
    current_client: dict = Depends(get_current_client)
) -> Dict[str, Any]:
    """
    Get season information

    - **series_id**: The TVDB series ID
    - **season_id**: The TVDB season ID
    """
    try:
        logger.info("Season request",
                    series_id=series_id,
                    season_id=season_id,
                    client=current_client.get("client_name"))

        season_data = await tvdb_client.get_season_extended(season_id)

        if not season_data:
            raise HTTPException(
                status_code=404,
                detail=f"Season with ID {season_id} not found"
            )

        return {
            "data": season_data,
            "meta": {
                "series_id": series_id,
                "season_id": season_id
            }
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(
            "Failed to fetch season",
            season_id=season_id,
            error=str(e))
        raise HTTPException(
            status_code=500,
            detail="Failed to fetch season data"
        )


@router.get("/")
@limiter.limit(f"{settings.rate_limit_requests_per_minute}/minute")
async def get_all_series(
    request: Request,
    page: int = Query(0, ge=0, description="Page number for pagination"),
    current_client: dict = Depends(get_current_client)
) -> Dict[str, Any]:
    """
    Get all series with pagination

    - **page**: Page number for pagination (starts at 0)
    """
    try:
        logger.info(
            "All series request",
            page=page,
            client=current_client.get("client_name"))

        series_data = await tvdb_client.get_all_series(page)

        if not series_data:
            return {
                "data": [],
                "meta": {
                    "page": page,
                    "total_pages": 0,
                    "has_next": False,
                    "has_prev": False
                }
            }

        return {
            "data": series_data.get('data', []),
            "meta": {
                "page": page,
                "total_pages": series_data.get('links', {}).get('totalPages'),
                "has_next": bool(series_data.get('links', {}).get('next')),
                "has_prev": bool(series_data.get('links', {}).get('prev'))
            }
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error("Failed to fetch all series", page=page, error=str(e))
        raise HTTPException(
            status_code=500,
            detail="Failed to fetch series list"
        )


@router.post("/{series_id}/cache/invalidate")
@limiter.limit("10/minute")
async def invalidate_series_cache(
    request: Request,
    series_id: int,
    current_client: dict = Depends(get_current_client)
) -> Dict[str, Any]:
    """
    Invalidate cache for a specific series

    This will force fresh data to be fetched from TVDB on the next request.

    - **series_id**: The TVDB series ID
    """
    try:
        logger.info("Cache invalidation request",
                    series_id=series_id,
                    client=current_client.get("client_name"))

        await tvdb_client.invalidate_cache("series", series_id)

        return {
            "success": True,
            "message": f"Cache invalidated for series {series_id}",
            "series_id": series_id
        }

    except Exception as e:
        logger.error(
            "Failed to invalidate cache",
            series_id=series_id,
            error=str(e))
        raise HTTPException(
            status_code=500,
            detail="Failed to invalidate cache"
        )
