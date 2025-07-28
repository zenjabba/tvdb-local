from typing import Optional

from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    # TVDB API Configuration
    tvdb_api_key: str
    tvdb_pin: Optional[str] = None

    # Database Configuration
    database_url: str
    test_database_url: Optional[str] = None

    # Redis Configuration
    redis_url: str = "redis://localhost:6379/0"

    # API Configuration
    secret_key: str
    api_v1_prefix: str = "/api/v1"
    access_token_expire_minutes: int = 10080  # 1 week

    # Rate Limiting
    rate_limit_requests_per_minute: int = 100
    rate_limit_burst: int = 200

    # Sync Configuration
    sync_interval_minutes: int = 15
    initial_sync_batch_size: int = 100
    max_concurrent_requests: int = 10

    # Cache Configuration
    cache_ttl_static_hours: int = 24
    cache_ttl_dynamic_hours: int = 1
    cache_ttl_popular_minutes: int = 30

    # Logging
    log_level: str = "INFO"
    structured_logging: bool = True

    # Application
    app_name: str = "TVDB Proxy"
    version: str = "1.0.0"
    debug: bool = False

    # S3/Storage Configuration (Ceph S3 Compatible)
    s3_endpoint_url: Optional[str] = None  # For Ceph/MinIO/S3-compatible storage
    s3_access_key_id: Optional[str] = None
    s3_secret_access_key: Optional[str] = None
    s3_region: str = "us-east-1"
    s3_bucket_name: str = "tvdb-images"  # Single bucket with prefixes
    s3_use_ssl: bool = True
    s3_verify_ssl: bool = True
    cdn_base_url: Optional[str] = None  # Optional CDN URL for serving images
    
    # Storage Backend Selection
    storage_backend: str = "s3"  # Options: "s3", "local", "none"
    local_storage_path: str = "/app/storage/images"
    
    # Image Storage Configuration - No size limits for 1:1 raw storage
    
    # Image Sync Configuration
    image_sync_batch_size: int = 50
    image_sync_concurrent_downloads: int = 5
    image_sync_retry_failed: bool = True
    image_sync_retry_after_hours: int = 24

    class Config:
        env_file = ".env"
        case_sensitive = False
        extra = "ignore"


settings = Settings()
