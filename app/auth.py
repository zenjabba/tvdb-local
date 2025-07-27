from datetime import datetime, timedelta
from typing import Optional
from jose import JWTError, jwt
from passlib.context import CryptContext
from fastapi import HTTPException, status, Depends
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from sqlalchemy.orm import Session
from app.config import settings
from app.database import SessionLocal
from app.models import ApiKey

# Password hashing
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

# JWT token handling
security = HTTPBearer()

# Default API keys for demo (in production, store in database)
VALID_API_KEYS = {
    "demo-key-1": {
        "name": "Demo Client 1",
        "rate_limit": 100,
        "active": True
    },
    "demo-key-2": {
        "name": "Demo Client 2", 
        "rate_limit": 200,
        "active": True
    }
}


def verify_password(plain_password: str, hashed_password: str) -> bool:
    """Verify a password against its hash"""
    return pwd_context.verify(plain_password, hashed_password)


def get_password_hash(password: str) -> str:
    """Hash a password"""
    return pwd_context.hash(password)


def create_access_token(data: dict, expires_delta: Optional[timedelta] = None) -> str:
    """Create a JWT access token"""
    to_encode = data.copy()
    if expires_delta:
        expire = datetime.utcnow() + expires_delta
    else:
        expire = datetime.utcnow() + timedelta(minutes=settings.access_token_expire_minutes)
    
    to_encode.update({"exp": expire})
    encoded_jwt = jwt.encode(to_encode, settings.secret_key, algorithm="HS256")
    return encoded_jwt


def verify_token(token: str) -> dict:
    """Verify and decode a JWT token"""
    try:
        payload = jwt.decode(token, settings.secret_key, algorithms=["HS256"])
        return payload
    except JWTError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Could not validate credentials",
            headers={"WWW-Authenticate": "Bearer"},
        )


def get_db_session() -> Session:
    """Get database session for auth operations"""
    return SessionLocal()


def verify_api_key(api_key: str) -> dict:
    """Verify an API key against the database and return client information"""
    # First check hardcoded keys for backward compatibility
    if api_key in VALID_API_KEYS:
        client_info = VALID_API_KEYS[api_key]
        if client_info["active"]:
            return {
                "api_key": api_key,
                "client_name": client_info["name"],
                "rate_limit": client_info["rate_limit"]
            }
    
    # Check database for API key
    db = get_db_session()
    try:
        db_key = db.query(ApiKey).filter(ApiKey.key == api_key).first()
        
        if not db_key:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid API key"
            )
        
        if not db_key.is_valid:
            detail = "API key is disabled"
            if db_key.is_expired:
                detail = "API key has expired"
            
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail=detail
            )
        
        # Update usage statistics
        db_key.last_used = datetime.utcnow()
        db_key.total_requests += 1
        db.commit()
        
        return {
            "api_key": api_key,
            "client_name": db_key.name,
            "rate_limit": db_key.rate_limit,
            "key_id": db_key.id
        }
        
    except HTTPException:
        raise
    except Exception as e:
        import structlog
        logger = structlog.get_logger()
        logger.error("Database error during API key verification", error=str(e))
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Authentication service temporarily unavailable"
        )
    finally:
        db.close()


def get_current_client(credentials: HTTPAuthorizationCredentials = Depends(security)) -> dict:
    """Dependency to get current authenticated client"""
    token = credentials.credentials
    
    # Try to verify as JWT token first
    try:
        payload = verify_token(token)
        return payload
    except HTTPException:
        pass
    
    # If JWT fails, try as API key
    try:
        return verify_api_key(token)
    except HTTPException:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid authentication credentials",
            headers={"WWW-Authenticate": "Bearer"},
        )