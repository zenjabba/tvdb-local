import secrets
from datetime import datetime

from sqlalchemy import Boolean, Column, DateTime, Integer, String, Text

from app.models.base import BaseModel


class ApiKey(BaseModel):
    __tablename__ = "api_keys"

    # Core fields
    key = Column(String(100), unique=True, index=True, nullable=False)
    name = Column(String(200), nullable=False)
    description = Column(Text)

    # Access control
    active = Column(Boolean, default=True, nullable=False)
    rate_limit = Column(
        Integer,
        default=100,
        nullable=False)  # requests per minute

    # Usage tracking
    last_used = Column(DateTime(timezone=True))
    total_requests = Column(Integer, default=0, nullable=False)

    # Expiration (optional)
    expires_at = Column(DateTime(timezone=True))

    # PIN support (for user-supported keys)
    requires_pin = Column(Boolean, default=False, nullable=False)
    pin = Column(String(20))  # Optional PIN for user-supported keys

    # Admin fields
    created_by = Column(String(100))  # Admin who created the key

    @classmethod
    def generate_key(cls, prefix: str = "api") -> str:
        """Generate a secure API key"""
        return f"{prefix}-{secrets.token_urlsafe(24)}"

    @property
    def is_expired(self) -> bool:
        """Check if the API key has expired"""
        if not self.expires_at:
            return False
        return self.expires_at < datetime.utcnow()

    @property
    def is_valid(self) -> bool:
        """Check if the API key is valid (active and not expired)"""
        return self.active and not self.is_expired

    def to_dict(self, include_key: bool = False) -> dict:
        """Convert to dictionary, optionally including the actual key"""
        data = {
            "id": self.id,
            "name": self.name,
            "description": self.description,
            "active": self.active,
            "rate_limit": self.rate_limit,
            "last_used": self.last_used.isoformat() if self.last_used else None,
            "total_requests": self.total_requests,
            "expires_at": self.expires_at.isoformat() if self.expires_at else None,
            "created_by": self.created_by,
            "created_at": self.created_at.isoformat(),
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
            "requires_pin": self.requires_pin,
            "has_pin": bool(self.pin),  # Don't expose actual PIN
        }

        if include_key:
            data["key"] = self.key

        # Always include key_preview for security/display purposes
        data["key_preview"] = f"...{self.key[-4:]}" if self.key else None

        return data

    def __repr__(self):
        return f"<ApiKey(id={self.id}, name='{self.name}', active={self.active})>"
