"""TVDB v4 API compliant authentication endpoints"""
from datetime import timedelta
from typing import Optional

import structlog
from fastapi import APIRouter, HTTPException, status
from pydantic import BaseModel
from sqlalchemy.orm import Session
from sqlalchemy.sql import func

from app.auth import create_access_token
from app.config import settings
from app.database import SessionLocal
from app.models import ApiKey

logger = structlog.get_logger()

router = APIRouter()


class LoginRequest(BaseModel):
    """TVDB v4 compliant login request"""
    apikey: str
    pin: Optional[str] = None


class LoginResponse(BaseModel):
    """TVDB v4 compliant login response"""
    data: dict
    status: str = "success"


@router.post("/login", response_model=LoginResponse)
async def tvdb_login(credentials: LoginRequest):
    """
    TVDB v4 API compliant login endpoint
    
    Authenticates using apikey and optional pin, returns a bearer token
    that's valid for 1 month as per TVDB specification.
    """
    db = SessionLocal()
    try:
        # Find the API key in database
        api_key = db.query(ApiKey).filter(
            ApiKey.key == credentials.apikey,
            ApiKey.active == True
        ).first()
        
        if not api_key:
            logger.warning("Invalid API key attempted", apikey=credentials.apikey[-4:])
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid credentials"
            )
        
        # Check if PIN is required and validate it
        if api_key.requires_pin:
            if not credentials.pin:
                logger.warning("PIN required but not provided", apikey=credentials.apikey[-4:])
                raise HTTPException(
                    status_code=status.HTTP_401_UNAUTHORIZED,
                    detail="Invalid credentials"
                )
            
            if api_key.pin != credentials.pin:
                logger.warning("Invalid PIN provided", apikey=credentials.apikey[-4:])
                raise HTTPException(
                    status_code=status.HTTP_401_UNAUTHORIZED,
                    detail="Invalid credentials"
                )
        
        # Check if API key is expired
        if api_key.is_expired:
            logger.warning("Expired API key used", apikey=credentials.apikey[-4:])
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid credentials"
            )
        
        # Update usage statistics
        api_key.last_used = func.now()
        api_key.total_requests += 1
        db.commit()
        
        # Create JWT token with 1 month validity (TVDB standard)
        access_token_expires = timedelta(days=30)  # 1 month
        access_token = create_access_token(
            data={
                "sub": api_key.key,
                "client_name": api_key.name,
                "rate_limit": api_key.rate_limit,
                "key_id": api_key.id
            },
            expires_delta=access_token_expires
        )
        
        logger.info(
            "TVDB login successful",
            client_name=api_key.name,
            requires_pin=api_key.requires_pin
        )
        
        # Return TVDB v4 compliant response
        return LoginResponse(
            data={"token": access_token},
            status="success"
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error("TVDB login failed", error=str(e))
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Authentication service error"
        )
    finally:
        db.close()


# Additional TVDB-specific error handlers can be added here
@router.get("/")
async def tvdb_api_info():
    """
    Root endpoint that mimics TVDB API behavior
    """
    return {
        "data": {
            "version": "4.7.0",  # Mimicking TVDB v4 version
            "description": "TVDB API v4 Proxy"
        }
    }