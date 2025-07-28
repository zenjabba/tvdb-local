from datetime import timedelta

import structlog
from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import HTTPBearer
from pydantic import BaseModel

from app.auth import create_access_token, verify_api_key, get_current_client
from app.config import settings

logger = structlog.get_logger()

router = APIRouter()
security = HTTPBearer()


class TokenRequest(BaseModel):
    api_key: str


class TokenResponse(BaseModel):
    access_token: str
    token_type: str
    expires_in: int


@router.post("/token", response_model=TokenResponse)
async def create_token(token_request: TokenRequest):
    """
    Exchange API key for JWT token

    This endpoint allows clients to exchange their API key for a JWT token
    that can be used for subsequent API calls.
    """
    try:
        # Verify the API key
        client_info = verify_api_key(token_request.api_key)

        # Create JWT token
        access_token_expires = timedelta(
            minutes=settings.access_token_expire_minutes)
        access_token = create_access_token(
            data={
                "sub": client_info["api_key"],
                "client_name": client_info["client_name"],
                "rate_limit": client_info["rate_limit"]
            },
            expires_delta=access_token_expires
        )

        logger.info(
            "JWT token created",
            client_name=client_info["client_name"])

        return TokenResponse(
            access_token=access_token,
            token_type="bearer",
            expires_in=settings.access_token_expire_minutes * 60
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error("Token creation failed", error=str(e))
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to create token"
        ) from e


@router.get("/verify")
async def verify_token(current_client: dict = Depends(lambda: None)):
    """
    Verify current authentication token

    This endpoint can be used to verify if the current token is valid
    and retrieve client information.
    """

    try:
        # This will verify the token and return client info
        client_info = get_current_client()

        return {
            "valid": True,
            "client_name": client_info.get("client_name"),
            "rate_limit": client_info.get("rate_limit"),
            "token_type": "bearer" if "exp" in client_info else "api_key"
        }

    except HTTPException:
        return {
            "valid": False,
            "error": "Invalid or expired token"
        }
    except Exception as e:
        logger.error("Token verification failed", error=str(e))
        return {
            "valid": False,
            "error": "Token verification failed"
        }
