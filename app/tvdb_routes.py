"""TVDB v4 API compliant routes - mounts at root level for full compatibility"""
from fastapi import APIRouter

from app.api.endpoints import (episodes, movies, people, search, series,
                               tvdb_auth)

# Create router without prefix to match TVDB API structure
tvdb_router = APIRouter()

# Mount TVDB-compliant auth endpoints at root
tvdb_router.include_router(tvdb_auth.router, tags=["authentication"])

# Mount content endpoints with v4 prefix to match TVDB structure
v4_router = APIRouter(prefix="/v4")

v4_router.include_router(series.router, prefix="/series", tags=["series"])
v4_router.include_router(movies.router, prefix="/movies", tags=["movies"])
v4_router.include_router(episodes.router, prefix="/episodes", tags=["episodes"])
v4_router.include_router(people.router, prefix="/people", tags=["people"])
v4_router.include_router(search.router, prefix="/search", tags=["search"])

# Add v4 routes to main TVDB router
tvdb_router.include_router(v4_router)
