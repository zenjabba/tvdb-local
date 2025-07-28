from datetime import datetime
from typing import Optional

from pydantic import BaseModel, Field, validator


class ApiKeyCreate(BaseModel):
    name: str = Field(..., min_length=1, max_length=200,
                      description="Human-readable name for the API key")
    description: Optional[str] = Field(
        None,
        max_length=1000,
        description="Optional description of the key's purpose")
    rate_limit: int = Field(
        100,
        ge=1,
        le=10000,
        description="Requests per minute (1-10000)")
    active: bool = Field(True, description="Whether the key is active")
    expires_at: Optional[datetime] = Field(
        None, description="Optional expiration date")
    created_by: Optional[str] = Field(
        None, max_length=100, description="Admin who created the key")
    requires_pin: bool = Field(
        False, description="Whether this key requires a PIN (user-supported key)")
    pin: Optional[str] = Field(
        None, max_length=20, description="PIN for user-supported keys")

    @validator('name')
    def validate_name(cls, v):
        if not v.strip():
            raise ValueError('Name cannot be empty or whitespace only')
        return v.strip()


class ApiKeyUpdate(BaseModel):
    name: Optional[str] = Field(None, min_length=1, max_length=200)
    description: Optional[str] = Field(None, max_length=1000)
    rate_limit: Optional[int] = Field(None, ge=1, le=10000)
    active: Optional[bool] = None
    expires_at: Optional[datetime] = None
    requires_pin: Optional[bool] = None
    pin: Optional[str] = Field(None, max_length=20)

    @validator('name')
    def validate_name(cls, v):
        if v is not None and not v.strip():
            raise ValueError('Name cannot be empty or whitespace only')
        return v.strip() if v else v


class ApiKeyResponse(BaseModel):
    id: int
    name: str
    description: Optional[str]
    active: bool
    rate_limit: int
    key_preview: Optional[str]
    last_used: Optional[datetime]
    total_requests: int
    expires_at: Optional[datetime]
    created_by: Optional[str]
    created_at: datetime
    updated_at: Optional[datetime]
    requires_pin: bool
    has_pin: bool  # Whether a PIN is set (don't expose actual PIN)

    class Config:
        from_attributes = True


class ApiKeyWithKey(ApiKeyResponse):
    """Response that includes the full API key - only for creation"""
    key: str

    class Config:
        from_attributes = True


class ApiKeyList(BaseModel):
    keys: list[ApiKeyResponse]
    total: int
    page: int
    per_page: int
    has_next: bool
    has_prev: bool


class ApiKeyUsageStats(BaseModel):
    total_keys: int
    active_keys: int
    inactive_keys: int
    expired_keys: int
    total_requests: int
    avg_requests_per_key: float
    top_keys: list[dict]  # Top 5 most used keys


class ApiKeyRotateResponse(BaseModel):
    id: int
    name: str
    old_key_preview: str
    new_key: str
    message: str
