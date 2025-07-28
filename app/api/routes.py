from fastapi import APIRouter

from app.api.endpoints import (admin, admin_sync, auth, episodes, images,
                               movies, people, search, series)

api_router = APIRouter()

# Include all endpoint routers
api_router.include_router(auth.router, prefix="/auth", tags=["authentication"])
api_router.include_router(admin.router, prefix="/admin", tags=["admin"])
api_router.include_router(admin_sync.router, prefix="/admin", tags=["admin-sync"])
api_router.include_router(series.router, prefix="/series", tags=["series"])
api_router.include_router(
    episodes.router,
    prefix="/episodes",
    tags=["episodes"])
api_router.include_router(movies.router, prefix="/movies", tags=["movies"])
api_router.include_router(people.router, prefix="/people", tags=["people"])
api_router.include_router(search.router, prefix="/search", tags=["search"])
api_router.include_router(images.router, prefix="/images", tags=["images"])
