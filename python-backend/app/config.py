from __future__ import annotations

from functools import lru_cache
from pathlib import Path

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file='.env', env_file_encoding='utf-8', case_sensitive=True)

    app_env: str = Field(default='production', alias='APP_ENV')
    api_host: str = Field(default='0.0.0.0', alias='API_HOST')
    api_port: int = Field(default=8000, alias='API_PORT')
    api_key: str = Field(default='change-me', alias='API_KEY')

    redis_url: str = Field(default='redis://127.0.0.1:6379/0', alias='REDIS_URL')
    celery_broker_url: str = Field(default='redis://127.0.0.1:6379/0', alias='CELERY_BROKER_URL')
    celery_result_backend: str = Field(default='redis://127.0.0.1:6379/1', alias='CELERY_RESULT_BACKEND')

    minio_endpoint: str = Field(default='127.0.0.1:9000', alias='MINIO_ENDPOINT')
    minio_access_key: str = Field(default='minioadmin', alias='MINIO_ACCESS_KEY')
    minio_secret_key: str = Field(default='minioadmin', alias='MINIO_SECRET_KEY')
    minio_secure: bool = Field(default=False, alias='MINIO_SECURE')
    minio_bucket_input: str = Field(default='premium-ocr-input', alias='MINIO_BUCKET_INPUT')
    minio_bucket_output: str = Field(default='premium-ocr-output', alias='MINIO_BUCKET_OUTPUT')
    minio_presign_expire: int = Field(default=3600, alias='MINIO_PRESIGN_EXPIRE')

    postgres_dsn: str = Field(alias='POSTGRES_DSN')

    upload_dir: str = Field(default='/workspace/python-backend/uploads', alias='UPLOAD_DIR')
    work_tmp_dir: str = Field(default='/workspace/python-backend/tmp', alias='WORK_TMP_DIR')
    work_output_dir: str = Field(default='/workspace/python-backend/output', alias='WORK_OUTPUT_DIR')

    toolkit_path: str = Field(default='/workspace', alias='TOOLKIT_PATH')

    @property
    def upload_path(self) -> Path:
        return Path(self.upload_dir)

    @property
    def tmp_path(self) -> Path:
        return Path(self.work_tmp_dir)

    @property
    def output_path(self) -> Path:
        return Path(self.work_output_dir)


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    settings = Settings()
    settings.upload_path.mkdir(parents=True, exist_ok=True)
    settings.tmp_path.mkdir(parents=True, exist_ok=True)
    settings.output_path.mkdir(parents=True, exist_ok=True)
    return settings
