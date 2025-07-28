from typing import Any, Dict

import structlog
from fastapi import APIRouter, Depends, HTTPException, Request
from slowapi import Limiter
from slowapi.util import get_remote_address

from app.auth import get_current_client
from app.config import settings
from app.services.tvdb_client import tvdb_client

logger = structlog.get_logger()

router = APIRouter()
limiter = Limiter(key_func=get_remote_address)


@router.get("/{episode_id}")
@limiter.limit(f"{settings.rate_limit_requests_per_minute}/minute")
async def get_episode(
    request: Request,
    episode_id: int,
    current_client: dict = Depends(get_current_client)
) -> Dict[str, Any]:
    """
    Get episode information by TVDB ID

    - **episode_id**: The TVDB episode ID
    """
    try:
        logger.info("Episode request", episode_id=episode_id,
                    client=current_client.get("client_name"))

        episode_data = await tvdb_client.get_episode(episode_id)

        if not episode_data:
            raise HTTPException(
                status_code=404,
                detail=f"Episode with ID {episode_id} not found"
            )

        return {
            "data": episode_data,
            "meta": {
                "episode_id": episode_id,
                "cached": True  # Would check if data came from cache
            }
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(
            "Failed to fetch episode",
            episode_id=episode_id,
            error=str(e))
        raise HTTPException(
            status_code=500,
            detail="Failed to fetch episode data"
        ) from e


@router.post("/{episode_id}/cache/invalidate")
@limiter.limit("10/minute")
async def invalidate_episode_cache(
    request: Request,
    episode_id: int,
    current_client: dict = Depends(get_current_client)
) -> Dict[str, Any]:
    """
    Invalidate cache for a specific episode

    This will force fresh data to be fetched from TVDB on the next request.

    - **episode_id**: The TVDB episode ID
    """
    try:
        logger.info("Episode cache invalidation request",
                    episode_id=episode_id,
                    client=current_client.get("client_name"))

        await tvdb_client.invalidate_cache("episode", episode_id)

        return {
            "success": True,
            "message": f"Cache invalidated for episode {episode_id}",
            "episode_id": episode_id
        }

    except Exception as e:
        logger.error(
            "Failed to invalidate episode cache",
            episode_id=episode_id,
            error=str(e))
        raise HTTPException(
            status_code=500,
            detail="Failed to invalidate cache"
        ) from e
