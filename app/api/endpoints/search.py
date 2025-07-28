from typing import Any, Dict, List

import structlog
from fastapi import APIRouter, Depends, HTTPException, Query, Request
from slowapi import Limiter
from slowapi.util import get_remote_address

from app.auth import get_current_client
from app.config import settings
from app.redis_client import cache
from app.services.tvdb_client import tvdb_client

logger = structlog.get_logger()

router = APIRouter()
limiter = Limiter(key_func=get_remote_address)


@router.get("/series")
@limiter.limit(f"{settings.rate_limit_requests_per_minute}/minute")
async def search_series(
    request: Request,
    q: str = Query(..., min_length=2, description="Search query (minimum 2 characters)"),
    limit: int = Query(20, ge=1, le=100, description="Maximum number of results"),
    current_client: dict = Depends(get_current_client)
) -> Dict[str, Any]:
    """
    Search for series

    - **q**: Search query string
    - **limit**: Maximum number of results to return (1-100)
    """
    try:
        logger.info("Series search request", query=q, limit=limit,
                    client=current_client.get("client_name"))

        # Check cache first
        cached_results = cache.get("search", f"series:{q.lower()}:{limit}")
        if cached_results:
            logger.debug("Search cache hit", query=q)
            return {
                "data": cached_results,
                "meta": {
                    "query": q,
                    "type": "series",
                    "limit": limit,
                    "cached": True
                }
            }

        # Perform search (this would integrate with TVDB search endpoint)
        search_results = await tvdb_client.search_series(q)

        if search_results is None:
            # Fallback to basic text matching in cached data
            search_results = await _fallback_series_search(q, limit)

        # Limit results
        if search_results and len(search_results) > limit:
            search_results = search_results[:limit]

        # Cache results
        if search_results:
            cache.set(
                "search",
                f"series:{q.lower()}:{limit}",
                search_results,
                1)  # 1 hour cache

        return {
            "data": search_results or [],
            "meta": {
                "query": q,
                "type": "series",
                "limit": limit,
                "count": len(search_results) if search_results else 0,
                "cached": False
            }
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error("Series search failed", query=q, error=str(e))
        raise HTTPException(
            status_code=500,
            detail="Search request failed"
        ) from e


@router.get("/movies")
@limiter.limit(f"{settings.rate_limit_requests_per_minute}/minute")
async def search_movies(
    request: Request,
    q: str = Query(..., min_length=2, description="Search query (minimum 2 characters)"),
    limit: int = Query(20, ge=1, le=100, description="Maximum number of results"),
    current_client: dict = Depends(get_current_client)
) -> Dict[str, Any]:
    """
    Search for movies

    - **q**: Search query string
    - **limit**: Maximum number of results to return (1-100)
    """
    try:
        logger.info("Movie search request", query=q, limit=limit,
                    client=current_client.get("client_name"))

        # Check cache first
        cached_results = cache.get("search", f"movies:{q.lower()}:{limit}")
        if cached_results:
            logger.debug("Movie search cache hit", query=q)
            return {
                "data": cached_results,
                "meta": {
                    "query": q,
                    "type": "movies",
                    "limit": limit,
                    "cached": True
                }
            }

        # Perform search (placeholder - would integrate with TVDB search)
        search_results = await _fallback_movie_search(q, limit)

        # Cache results
        if search_results:
            cache.set(
                "search",
                f"movies:{q.lower()}:{limit}",
                search_results,
                1)  # 1 hour cache

        return {
            "data": search_results or [],
            "meta": {
                "query": q,
                "type": "movies",
                "limit": limit,
                "count": len(search_results) if search_results else 0,
                "cached": False
            }
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error("Movie search failed", query=q, error=str(e))
        raise HTTPException(
            status_code=500,
            detail="Search request failed"
        ) from e


@router.get("/people")
@limiter.limit(f"{settings.rate_limit_requests_per_minute}/minute")
async def search_people(
    request: Request,
    q: str = Query(..., min_length=2, description="Search query (minimum 2 characters)"),
    limit: int = Query(20, ge=1, le=100, description="Maximum number of results"),
    current_client: dict = Depends(get_current_client)
) -> Dict[str, Any]:
    """
    Search for people (actors, directors, etc.)

    - **q**: Search query string
    - **limit**: Maximum number of results to return (1-100)
    """
    try:
        logger.info("People search request", query=q, limit=limit,
                    client=current_client.get("client_name"))

        # Check cache first
        cached_results = cache.get("search", f"people:{q.lower()}:{limit}")
        if cached_results:
            logger.debug("People search cache hit", query=q)
            return {
                "data": cached_results,
                "meta": {
                    "query": q,
                    "type": "people",
                    "limit": limit,
                    "cached": True
                }
            }

        # Perform search (placeholder - would integrate with TVDB search)
        search_results = await _fallback_people_search(q, limit)

        # Cache results
        if search_results:
            cache.set(
                "search",
                f"people:{q.lower()}:{limit}",
                search_results,
                1)  # 1 hour cache

        return {
            "data": search_results or [],
            "meta": {
                "query": q,
                "type": "people",
                "limit": limit,
                "count": len(search_results) if search_results else 0,
                "cached": False
            }
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error("People search failed", query=q, error=str(e))
        raise HTTPException(
            status_code=500,
            detail="Search request failed"
        ) from e


@router.get("/all")
@limiter.limit(f"{settings.rate_limit_requests_per_minute}/minute")
async def search_all(
    request: Request,
    q: str = Query(..., min_length=2, description="Search query (minimum 2 characters)"),
    limit: int = Query(20, ge=1, le=100, description="Maximum number of results per type"),
    current_client: dict = Depends(get_current_client)
) -> Dict[str, Any]:
    """
    Search across all content types (series, movies, people)

    - **q**: Search query string
    - **limit**: Maximum number of results per content type (1-100)
    """
    try:
        logger.info(
            "Universal search request",
            query=q,
            limit=limit,
            client=current_client.get("client_name"))

        # Check cache first
        cached_results = cache.get("search", f"all:{q.lower()}:{limit}")
        if cached_results:
            logger.debug("Universal search cache hit", query=q)
            return {
                "data": cached_results,
                "meta": {
                    "query": q,
                    "type": "all",
                    "limit": limit,
                    "cached": True
                }
            }

        # Perform searches across all types
        series_results = await _fallback_series_search(q, limit)
        movie_results = await _fallback_movie_search(q, limit)
        people_results = await _fallback_people_search(q, limit)

        combined_results = {
            "series": series_results or [],
            "movies": movie_results or [],
            "people": people_results or []
        }

        # Cache results
        cache.set(
            "search",
            f"all:{q.lower()}:{limit}",
            combined_results,
            1)  # 1 hour cache

        total_count = len(combined_results["series"]) + len(
            combined_results["movies"]) + len(combined_results["people"])

        return {
            "data": combined_results,
            "meta": {
                "query": q,
                "type": "all",
                "limit": limit,
                "total_count": total_count,
                "counts": {
                    "series": len(combined_results["series"]),
                    "movies": len(combined_results["movies"]),
                    "people": len(combined_results["people"])
                },
                "cached": False
            }
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error("Universal search failed", query=q, error=str(e))
        raise HTTPException(
            status_code=500,
            detail="Search request failed"
        ) from e


# Fallback search functions (using cached index data)
async def _fallback_series_search(
        query: str, limit: int) -> List[Dict[str, Any]]:
    """Fallback series search using cached index"""
    try:
        # This would search through cached series data
        # For now, return empty list
        logger.debug("Performing fallback series search", query=query)
        return []
    except Exception as e:
        logger.error("Fallback series search failed", error=str(e))
        return []


async def _fallback_movie_search(
        query: str, limit: int) -> List[Dict[str, Any]]:
    """Fallback movie search using cached index"""
    try:
        # This would search through cached movie data
        logger.debug("Performing fallback movie search", query=query)
        return []
    except Exception as e:
        logger.error("Fallback movie search failed", error=str(e))
        return []


async def _fallback_people_search(
        query: str, limit: int) -> List[Dict[str, Any]]:
    """Fallback people search using cached index"""
    try:
        # This would search through cached people data
        logger.debug("Performing fallback people search", query=query)
        return []
    except Exception as e:
        logger.error("Fallback people search failed", error=str(e))
        return []
