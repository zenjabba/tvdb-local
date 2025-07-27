from fastapi import APIRouter
from app.api.endpoints import series, episodes, movies, people, search, auth, admin

api_router = APIRouter()

# Include all endpoint routers
api_router.include_router(auth.router, prefix="/auth", tags=["authentication"])
api_router.include_router(admin.router, prefix="/admin", tags=["admin"])
api_router.include_router(series.router, prefix="/series", tags=["series"])
api_router.include_router(episodes.router, prefix="/episodes", tags=["episodes"])
api_router.include_router(movies.router, prefix="/movies", tags=["movies"])
api_router.include_router(people.router, prefix="/people", tags=["people"])
api_router.include_router(search.router, prefix="/search", tags=["search"])