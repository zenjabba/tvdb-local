"""Admin endpoints for managing synchronization and images."""
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
import structlog

from app.auth import require_admin
from app.database import get_db
from app.workers.sync_tasks import (
    sync_content_images,
    sync_all_missing_images,
    cleanup_orphaned_images,
    full_sync,
    incremental_sync,
    sync_series_detailed
)

logger = structlog.get_logger()

router = APIRouter()


@router.post("/sync/images/{entity_type}/{entity_id}")
async def sync_entity_images(
    entity_type: str,
    entity_id: int,
    admin: dict = Depends(require_admin),
    db: Session = Depends(get_db)
):
    """Sync images for a specific entity.
    
    Args:
        entity_type: Type of entity (series, movie, episode, person)
        entity_id: Database ID of the entity
        
    Returns:
        Task information
    """
    valid_types = ["series", "movie", "episode", "person", "season"]
    if entity_type not in valid_types:
        raise HTTPException(status_code=400, detail=f"Invalid entity type. Must be one of: {valid_types}")
    
    try:
        task = sync_content_images.delay(entity_type, entity_id)
        
        logger.info(
            "Image sync task queued",
            entity_type=entity_type,
            entity_id=entity_id,
            task_id=task.id,
            admin=admin.get("name")
        )
        
        return {
            "status": "success",
            "message": f"Image sync task queued for {entity_type} {entity_id}",
            "task_id": task.id
        }
        
    except Exception as e:
        logger.error("Failed to queue image sync", error=str(e))
        raise HTTPException(status_code=500, detail="Failed to queue image sync task")


@router.post("/sync/images/missing")
async def sync_missing_images(
    entity_type: Optional[str] = None,
    limit: int = 100,
    admin: dict = Depends(require_admin)
):
    """Find and sync images for entities without local images.
    
    Args:
        entity_type: Optional filter by entity type
        limit: Maximum number of items to process (default: 100, max: 1000)
        
    Returns:
        Task information
    """
    if limit > 1000:
        raise HTTPException(status_code=400, detail="Limit cannot exceed 1000")
    
    if entity_type:
        valid_types = ["series", "movie", "episode", "person", "season"]
        if entity_type not in valid_types:
            raise HTTPException(status_code=400, detail=f"Invalid entity type. Must be one of: {valid_types}")
    
    try:
        task = sync_all_missing_images.delay(entity_type, limit)
        
        logger.info(
            "Missing images sync task queued",
            entity_type=entity_type,
            limit=limit,
            task_id=task.id,
            admin=admin.get("name")
        )
        
        return {
            "status": "success",
            "message": f"Missing images sync task queued",
            "task_id": task.id,
            "entity_type": entity_type,
            "limit": limit
        }
        
    except Exception as e:
        logger.error("Failed to queue missing images sync", error=str(e))
        raise HTTPException(status_code=500, detail="Failed to queue missing images sync task")


@router.post("/sync/images/cleanup")
async def cleanup_images(
    admin: dict = Depends(require_admin)
):
    """Clean up orphaned images in storage.
    
    This removes images from storage that no longer have database references.
    
    Returns:
        Task information
    """
    try:
        task = cleanup_orphaned_images.delay()
        
        logger.info(
            "Image cleanup task queued",
            task_id=task.id,
            admin=admin.get("name")
        )
        
        return {
            "status": "success",
            "message": "Image cleanup task queued",
            "task_id": task.id
        }
        
    except Exception as e:
        logger.error("Failed to queue image cleanup", error=str(e))
        raise HTTPException(status_code=500, detail="Failed to queue image cleanup task")


@router.post("/sync/full")
async def trigger_full_sync(
    admin: dict = Depends(require_admin)
):
    """Trigger a full synchronization with TVDB.
    
    This syncs all data from TVDB including series, movies, and people.
    
    Returns:
        Task information
    """
    try:
        task = full_sync.delay()
        
        logger.info(
            "Full sync task queued",
            task_id=task.id,
            admin=admin.get("name")
        )
        
        return {
            "status": "success",
            "message": "Full sync task queued",
            "task_id": task.id
        }
        
    except Exception as e:
        logger.error("Failed to queue full sync", error=str(e))
        raise HTTPException(status_code=500, detail="Failed to queue full sync task")


@router.post("/sync/incremental")
async def trigger_incremental_sync(
    admin: dict = Depends(require_admin)
):
    """Trigger an incremental synchronization with TVDB.
    
    This syncs only recent updates from TVDB.
    
    Returns:
        Task information
    """
    try:
        task = incremental_sync.delay()
        
        logger.info(
            "Incremental sync task queued",
            task_id=task.id,
            admin=admin.get("name")
        )
        
        return {
            "status": "success",
            "message": "Incremental sync task queued",
            "task_id": task.id
        }
        
    except Exception as e:
        logger.error("Failed to queue incremental sync", error=str(e))
        raise HTTPException(status_code=500, detail="Failed to queue incremental sync task")


@router.post("/sync/series/{series_id}")
async def sync_series(
    series_id: int,
    admin: dict = Depends(require_admin)
):
    """Sync detailed information for a specific series.
    
    Args:
        series_id: TVDB series ID
        
    Returns:
        Task information
    """
    try:
        task = sync_series_detailed.delay(series_id)
        
        logger.info(
            "Series sync task queued",
            series_id=series_id,
            task_id=task.id,
            admin=admin.get("name")
        )
        
        return {
            "status": "success",
            "message": f"Series sync task queued for series {series_id}",
            "task_id": task.id,
            "series_id": series_id
        }
        
    except Exception as e:
        logger.error("Failed to queue series sync", error=str(e))
        raise HTTPException(status_code=500, detail="Failed to queue series sync task")


@router.get("/tasks/{task_id}")
async def get_task_status(
    task_id: str,
    admin: dict = Depends(require_admin)
):
    """Get the status of a background task.
    
    Args:
        task_id: Celery task ID
        
    Returns:
        Task status information
    """
    from app.workers.celery_app import celery_app
    
    try:
        task = celery_app.AsyncResult(task_id)
        
        return {
            "task_id": task_id,
            "state": task.state,
            "current": task.info.get("current", 0) if task.info else 0,
            "total": task.info.get("total", 100) if task.info else 100,
            "status": task.info.get("status", "") if task.info else "",
            "result": task.result if task.state == "SUCCESS" else None,
            "error": str(task.info) if task.state == "FAILURE" else None
        }
        
    except Exception as e:
        logger.error("Failed to get task status", task_id=task_id, error=str(e))
        raise HTTPException(status_code=500, detail="Failed to get task status")