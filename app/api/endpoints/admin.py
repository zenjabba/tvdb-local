from datetime import datetime
from typing import Optional

import structlog
from fastapi import APIRouter, Depends, HTTPException, Query, Request
from slowapi import Limiter
from slowapi.util import get_remote_address
from sqlalchemy import desc, func
from sqlalchemy.orm import Session

from app.auth import get_current_client
from app.database import get_db
from app.models import ApiKey
from app.schemas.api_key import (ApiKeyCreate, ApiKeyList, ApiKeyResponse,
                                 ApiKeyRotateResponse, ApiKeyUpdate,
                                 ApiKeyUsageStats, ApiKeyWithKey)

logger = structlog.get_logger()

router = APIRouter()
limiter = Limiter(key_func=get_remote_address)

# Admin authentication - for now, use a special admin key
ADMIN_API_KEYS = {
    "admin-super-key-change-in-production": {
        "name": "Super Admin",
        "permissions": ["api_key_management"]
    }
}


def verify_admin_access(
        current_client: dict = Depends(get_current_client)) -> dict:
    """Verify that the current client has admin access"""
    api_key = current_client.get("api_key") or current_client.get("sub")

    if api_key not in ADMIN_API_KEYS:
        raise HTTPException(
            status_code=403,
            detail="Admin access required"
        )

    return current_client


@router.post("/api-keys", response_model=ApiKeyWithKey)
@limiter.limit("10/minute")
async def create_api_key(
    request: Request,
    key_data: ApiKeyCreate,
    admin: dict = Depends(verify_admin_access),
    db: Session = Depends(get_db)
):
    """
    Create a new API key

    Admin access required. Returns the full API key only once upon creation.
    """
    try:
        logger.info(
            "Creating new API key",
            name=key_data.name,
            admin=admin.get("client_name"))

        # Generate a secure API key
        api_key = ApiKey.generate_key()

        # Create the database record
        db_key = ApiKey(
            key=api_key,
            name=key_data.name,
            description=key_data.description,
            rate_limit=key_data.rate_limit,
            active=key_data.active,
            expires_at=key_data.expires_at,
            created_by=key_data.created_by or admin.get("client_name", "admin"),
            requires_pin=key_data.requires_pin,
            pin=key_data.pin
        )

        db.add(db_key)
        db.commit()
        db.refresh(db_key)

        logger.info("API key created successfully",
                    key_id=db_key.id,
                    name=db_key.name,
                    rate_limit=db_key.rate_limit)

        # Return the full key only once
        result = db_key.to_dict(include_key=True)
        return ApiKeyWithKey(**result)

    except Exception as e:
        logger.error("Failed to create API key", error=str(e))
        db.rollback()
        raise HTTPException(
            status_code=500,
            detail="Failed to create API key"
        ) from e


@router.get("/api-keys", response_model=ApiKeyList)
@limiter.limit("30/minute")
async def list_api_keys(
    request: Request,
    page: int = Query(1, ge=1, description="Page number"),
    per_page: int = Query(20, ge=1, le=100, description="Items per page"),
    active_only: bool = Query(False, description="Show only active keys"),
    search: Optional[str] = Query(None, description="Search by name"),
    admin: dict = Depends(verify_admin_access),
    db: Session = Depends(get_db)
):
    """
    List all API keys with pagination

    Admin access required. Never returns the actual API keys.
    """
    try:
        logger.info(
            "Listing API keys",
            page=page,
            per_page=per_page,
            admin=admin.get("client_name"))

        # Build query
        query = db.query(ApiKey)

        if active_only:
            query = query.filter(ApiKey.active)

        if search:
            query = query.filter(ApiKey.name.ilike(f"%{search}%"))

        # Get total count
        total = query.count()

        # Apply pagination
        offset = (page - 1) * per_page
        keys = query.order_by(desc(ApiKey.created_at)).offset(
            offset).limit(per_page).all()

        # Convert to response format
        key_responses = [ApiKeyResponse(**key.to_dict()) for key in keys]

        return ApiKeyList(
            keys=key_responses,
            total=total,
            page=page,
            per_page=per_page,
            has_next=(offset + per_page) < total,
            has_prev=page > 1
        )

    except Exception as e:
        logger.error("Failed to list API keys", error=str(e))
        raise HTTPException(
            status_code=500,
            detail="Failed to retrieve API keys"
        )


@router.get("/api-keys/{key_id}", response_model=ApiKeyResponse)
@limiter.limit("60/minute")
async def get_api_key(
    request: Request,
    key_id: int,
    admin: dict = Depends(verify_admin_access),
    db: Session = Depends(get_db)
):
    """
    Get details of a specific API key

    Admin access required. Does not return the actual API key.
    """
    try:
        db_key = db.query(ApiKey).filter(ApiKey.id == key_id).first()

        if not db_key:
            raise HTTPException(
                status_code=404,
                detail="API key not found"
            )

        logger.info(
            "Retrieved API key details",
            key_id=key_id,
            admin=admin.get("client_name"))

        return ApiKeyResponse(**db_key.to_dict())

    except HTTPException:
        raise
    except Exception as e:
        logger.error("Failed to get API key", key_id=key_id, error=str(e))
        raise HTTPException(
            status_code=500,
            detail="Failed to retrieve API key"
        )


@router.put("/api-keys/{key_id}", response_model=ApiKeyResponse)
@limiter.limit("10/minute")
async def update_api_key(
    request: Request,
    key_id: int,
    key_data: ApiKeyUpdate,
    admin: dict = Depends(verify_admin_access),
    db: Session = Depends(get_db)
):
    """
    Update an existing API key

    Admin access required. Cannot update the actual key value.
    """
    try:
        db_key = db.query(ApiKey).filter(ApiKey.id == key_id).first()

        if not db_key:
            raise HTTPException(
                status_code=404,
                detail="API key not found"
            )

        # Update only provided fields
        update_data = key_data.dict(exclude_unset=True)
        for field, value in update_data.items():
            setattr(db_key, field, value)

        db.commit()
        db.refresh(db_key)

        logger.info("API key updated successfully",
                    key_id=key_id,
                    updates=list(update_data.keys()),
                    admin=admin.get("client_name"))

        return ApiKeyResponse(**db_key.to_dict())

    except HTTPException:
        raise
    except Exception as e:
        logger.error("Failed to update API key", key_id=key_id, error=str(e))
        db.rollback()
        raise HTTPException(
            status_code=500,
            detail="Failed to update API key"
        )


@router.delete("/api-keys/{key_id}")
@limiter.limit("5/minute")
async def delete_api_key(
    request: Request,
    key_id: int,
    admin: dict = Depends(verify_admin_access),
    db: Session = Depends(get_db)
):
    """
    Delete an API key

    Admin access required. This action is irreversible.
    """
    try:
        db_key = db.query(ApiKey).filter(ApiKey.id == key_id).first()

        if not db_key:
            raise HTTPException(
                status_code=404,
                detail="API key not found"
            )

        key_name = db_key.name
        db.delete(db_key)
        db.commit()

        logger.info("API key deleted successfully",
                    key_id=key_id,
                    key_name=key_name,
                    admin=admin.get("client_name"))

        return {"message": f"API key '{key_name}' deleted successfully"}

    except HTTPException:
        raise
    except Exception as e:
        logger.error("Failed to delete API key", key_id=key_id, error=str(e))
        db.rollback()
        raise HTTPException(
            status_code=500,
            detail="Failed to delete API key"
        ) from e


@router.post("/api-keys/{key_id}/rotate", response_model=ApiKeyRotateResponse)
@limiter.limit("5/minute")
async def rotate_api_key(
    request: Request,
    key_id: int,
    admin: dict = Depends(verify_admin_access),
    db: Session = Depends(get_db)
):
    """
    Rotate an API key (generate new key value)

    Admin access required. Returns the new key value only once.
    """
    try:
        db_key = db.query(ApiKey).filter(ApiKey.id == key_id).first()

        if not db_key:
            raise HTTPException(
                status_code=404,
                detail="API key not found"
            )

        old_key_preview = f"...{db_key.key[-4:]}"
        new_key = ApiKey.generate_key()

        db_key.key = new_key
        db_key.total_requests = 0  # Reset request count
        db_key.last_used = None    # Reset last used

        db.commit()

        logger.info("API key rotated successfully",
                    key_id=key_id,
                    key_name=db_key.name,
                    admin=admin.get("client_name"))

        return ApiKeyRotateResponse(
            id=db_key.id,
            name=db_key.name,
            old_key_preview=old_key_preview,
            new_key=new_key,
            message="API key rotated successfully. Update your applications with the new key."
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error("Failed to rotate API key", key_id=key_id, error=str(e))
        db.rollback()
        raise HTTPException(
            status_code=500,
            detail="Failed to rotate API key"
        ) from e


@router.get("/api-keys/stats/usage", response_model=ApiKeyUsageStats)
@limiter.limit("10/minute")
async def get_api_key_stats(
    request: Request,
    admin: dict = Depends(verify_admin_access),
    db: Session = Depends(get_db)
):
    """
    Get API key usage statistics

    Admin access required.
    """
    try:
        total_keys = db.query(ApiKey).count()
        active_keys = db.query(ApiKey).filter(ApiKey.active).count()
        inactive_keys = total_keys - active_keys

        # Count expired keys
        expired_keys = db.query(ApiKey).filter(
            ApiKey.expires_at < datetime.utcnow()
        ).count()

        # Total requests across all keys
        total_requests_result = db.query(
            func.sum(ApiKey.total_requests)).scalar()
        total_requests = total_requests_result or 0

        # Average requests per key
        avg_requests = total_requests / total_keys if total_keys > 0 else 0

        # Top 5 most used keys
        top_keys_query = db.query(ApiKey).order_by(
            desc(ApiKey.total_requests)).limit(5)
        top_keys = [
            {
                "id": key.id,
                "name": key.name,
                "total_requests": key.total_requests,
                "last_used": key.last_used.isoformat() if key.last_used else None
            }
            for key in top_keys_query.all()
        ]

        logger.info("API key stats retrieved", admin=admin.get("client_name"))

        return ApiKeyUsageStats(
            total_keys=total_keys,
            active_keys=active_keys,
            inactive_keys=inactive_keys,
            expired_keys=expired_keys,
            total_requests=total_requests,
            avg_requests_per_key=round(avg_requests, 2),
            top_keys=top_keys
        )

    except Exception as e:
        logger.error("Failed to get API key stats", error=str(e))
        raise HTTPException(
            status_code=500,
            detail="Failed to retrieve API key statistics"
        ) from e
