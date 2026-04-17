"""
Configuration Management

Loads settings from environment variables.
"""

from pydantic_settings import BaseSettings
from typing import Optional


class Settings(BaseSettings):
    """Application settings loaded from environment variables"""
    
    # Application
    app_name: str = "MxA Mobile Backend"
    app_env: str = "production"
    debug: bool = False
    
    # API Server
    api_host: str = "0.0.0.0"
    api_port: int = 8104
    api_workers: int = 4
    
    # Database
    db_host: str = "192.168.1.66"
    db_port: int = 5432
    db_name: str = "mxa_mobile"
    db_user: str = "mxa_mobile_user"
    db_password: str
    db_pool_size: int = 10
    db_max_overflow: int = 20
    
    # Redis
    redis_host: str = "192.168.1.90"
    redis_port: int = 6379
    redis_db: int = 0
    redis_password: Optional[str] = None
    
    # Celery
    celery_broker_url: str = "redis://192.168.1.90:6379/0"
    celery_result_backend: str = "redis://192.168.1.90:6379/0"
    celery_queue_name: str = "mxa_mobile"
    celery_worker_concurrency: int = 4
    celery_task_time_limit: int = 3600
    celery_task_soft_time_limit: int = 3300
    
    # MinIO
    minio_endpoint: str = "192.168.1.90:9000"
    minio_access_key: str
    minio_secret_key: str
    minio_use_ssl: bool = False
    minio_region: str = "us-east-1"
    minio_bucket_input: str = "mxa-mobile-input"
    minio_bucket_output: str = "mxa-mobile-output"
    minio_bucket_temp: str = "mxa-mobile-temp"
    
    # Keycloak
    keycloak_server_url: str = "http://192.168.1.59:8080"
    keycloak_realm: str = "forensics"
    keycloak_client_id: str = "mxa-mobile-web"
    keycloak_client_secret: str
    
    # Processing Settings
    enable_audio_transcription: bool = True
    audio_max_transcription_seconds: int = 600
    enable_ocr: bool = True
    ocr_min_image_width: int = 720
    ocr_min_image_height: int = 1280
    default_category_models: str = "generic"
    
    # Logging
    log_level: str = "INFO"
    log_file: Optional[str] = None
    
    # Paths
    app_dir: str = "/opt/apps/mxa-mobile"
    temp_dir: str = "/tmp/mxa-mobile"
    
    @property
    def database_url(self) -> str:
        """Get database connection URL"""
        return f"postgresql://{self.db_user}:{self.db_password}@{self.db_host}:{self.db_port}/{self.db_name}"
    
    @property
    def redis_url(self) -> str:
        """Get Redis connection URL"""
        if self.redis_password:
            return f"redis://:{self.redis_password}@{self.redis_host}:{self.redis_port}/{self.redis_db}"
        return f"redis://{self.redis_host}:{self.redis_port}/{self.redis_db}"
    
    class Config:
        env_file = ".env"
        case_sensitive = False


# Global settings instance
settings = Settings()
