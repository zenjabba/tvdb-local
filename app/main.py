import time

import structlog
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from slowapi import Limiter, _rate_limit_exceeded_handler
from slowapi.errors import RateLimitExceeded
from slowapi.util import get_remote_address

from app.api.endpoints.images import router as images_router
from app.api.routes import api_router
from app.config import settings
from app.database import create_tables
from app.redis_client import cache
from app.tvdb_routes import tvdb_router

# Configure structured logging
structlog.configure(
    processors=[
        structlog.stdlib.filter_by_level,
        structlog.stdlib.add_logger_name,
        structlog.stdlib.add_log_level,
        structlog.stdlib.PositionalArgumentsFormatter(),
        structlog.processors.TimeStamper(fmt="iso"),
        structlog.processors.StackInfoRenderer(),
        structlog.processors.format_exc_info,
        structlog.processors.UnicodeDecoder(),
        structlog.processors.JSONRenderer()
        if settings.structured_logging
        else structlog.dev.ConsoleRenderer(),
    ],
    context_class=dict,
    logger_factory=structlog.stdlib.LoggerFactory(),
    cache_logger_on_first_use=True,
)

logger = structlog.get_logger()

# Rate limiter
limiter = Limiter(key_func=get_remote_address)

# Create FastAPI app
app = FastAPI(
    title=settings.app_name,
    version=settings.version,
    description="A high-performance caching proxy for TVDB API v4",
    openapi_url=f"{settings.api_v1_prefix}/openapi.json" if settings.debug else None,
)

# Add rate limiting
app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"] if settings.debug else ["http://localhost:3000"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# Request logging middleware
@app.middleware("http")
async def log_requests(request: Request, call_next):
    start_time = time.time()

    response = await call_next(request)

    process_time = time.time() - start_time

    logger.info(
        "Request processed",
        method=request.method,
        url=str(request.url),
        status_code=response.status_code,
        process_time=round(process_time, 4),
        client_host=request.client.host if request.client else None,
    )

    response.headers["X-Process-Time"] = str(process_time)
    return response


# Startup event
@app.on_event("startup")
async def startup_event():
    logger.info("Starting TVDB Proxy API", version=settings.version)

    # Create database tables
    try:
        create_tables()
        logger.info("Database tables created/verified")
    except Exception as e:
        logger.error("Failed to create database tables", error=str(e))
        raise

    # Test Redis connection
    try:
        cache.client.ping()
        logger.info("Redis connection established")
    except Exception as e:
        logger.error("Failed to connect to Redis", error=str(e))
        raise


# Shutdown event
@app.on_event("shutdown")
async def shutdown_event():
    logger.info("Shutting down TVDB Proxy API")


# Health check endpoint
@app.get("/health")
async def health_check():
    """Health check endpoint"""
    try:
        # Check Redis
        cache.client.ping()
        redis_status = "healthy"
    except Exception:
        redis_status = "unhealthy"

    # Check database would go here
    db_status = "healthy"  # Simplified for now

    overall_status = (
        "healthy" if redis_status == "healthy" and db_status == "healthy"
        else "unhealthy"
    )

    return {
        "status": overall_status,
        "version": settings.version,
        "services": {
            "redis": redis_status,
            "database": db_status,
        },
        "cache_stats": cache.get_cache_stats()
    }


# Root endpoint
@app.get("/")
async def root():
    """Root endpoint with API information"""
    return {
        "name": settings.app_name,
        "version": settings.version,
        "description": "TVDB API v4 Caching Proxy",
        "docs_url": f"{settings.api_v1_prefix}/docs" if settings.debug else None,
        "health_url": "/health",
        "api_prefix": settings.api_v1_prefix,
    }


# Include API routes
app.include_router(api_router, prefix=settings.api_v1_prefix)

# Include TVDB v4 compliant routes at root level
# This allows the proxy to be a drop-in replacement for TVDB API
app.include_router(tvdb_router)

# Include image serving endpoints at /images (TVDB-compliant)
app.include_router(images_router, prefix="/images", tags=["images"])


# Global exception handler
@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    logger.error(
        "Unhandled exception",
        error=str(exc),
        path=request.url.path,
        method=request.method,
        exc_info=exc,
    )

    return JSONResponse(
        status_code=500,
        content={
            "error": "Internal server error",
            "message": "An unexpected error occurred",
            "request_id": getattr(request.state, "request_id", None),
        }
    )


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "app.main:app",
        host="0.0.0.0",
        port=8000,
        reload=settings.debug,
        log_level=settings.log_level.lower(),
    )
