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


@router.get("/{person_id}")
@limiter.limit(f"{settings.rate_limit_requests_per_minute}/minute")
async def get_person(
    request: Request,
    person_id: int,
    current_client: dict = Depends(get_current_client)
) -> Dict[str, Any]:
    """
    Get person information by TVDB ID

    - **person_id**: The TVDB person ID
    """
    try:
        logger.info("Person request", person_id=person_id,
                    client=current_client.get("client_name"))

        person_data = await tvdb_client.get_person_extended(person_id)

        if not person_data:
            raise HTTPException(
                status_code=404,
                detail=f"Person with ID {person_id} not found"
            )

        return {
            "data": person_data,
            "meta": {
                "person_id": person_id,
                "cached": True  # Would check if data came from cache
            }
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(
            "Failed to fetch person",
            person_id=person_id,
            error=str(e))
        raise HTTPException(
            status_code=500,
            detail="Failed to fetch person data"
        ) from e


@router.post("/{person_id}/cache/invalidate")
@limiter.limit("10/minute")
async def invalidate_person_cache(
    request: Request,
    person_id: int,
    current_client: dict = Depends(get_current_client)
) -> Dict[str, Any]:
    """
    Invalidate cache for a specific person

    This will force fresh data to be fetched from TVDB on the next request.

    - **person_id**: The TVDB person ID
    """
    try:
        logger.info("Person cache invalidation request",
                    person_id=person_id,
                    client=current_client.get("client_name"))

        await tvdb_client.invalidate_cache("person", person_id)

        return {
            "success": True,
            "message": f"Cache invalidated for person {person_id}",
            "person_id": person_id
        }

    except Exception as e:
        logger.error(
            "Failed to invalidate person cache",
            person_id=person_id,
            error=str(e))
        raise HTTPException(
            status_code=500,
            detail="Failed to invalidate cache"
        ) from e
