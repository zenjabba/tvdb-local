from pydantic_settings import BaseSettings
from typing import Optional


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
    
    class Config:
        env_file = ".env"
        case_sensitive = False


settings = Settings()