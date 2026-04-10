"""
MinIO Service

Handles object storage operations.
"""

from minio import Minio
from minio.error import S3Error
from typing import Optional

from app.core.config import settings
from app.core.logging import logger


class MinioService:
    """MinIO object storage service"""
    
    def __init__(self):
        self.client = Minio(
            settings.minio_endpoint,
            access_key=settings.minio_access_key,
            secret_key=settings.minio_secret_key,
            secure=settings.minio_use_ssl
        )
    
    def check_connection(self) -> bool:
        """Check if MinIO is accessible"""
        try:
            # List buckets to verify connection
            list(self.client.list_buckets())
            return True
        except Exception as e:
            logger.error(f"MinIO connection check failed: {e}")
            return False
    
    def upload_file(
        self,
        file_path: str,
        object_name: str,
        bucket_name: Optional[str] = None
    ) -> bool:
        """Upload file to MinIO"""
        if not bucket_name:
            bucket_name = settings.minio_bucket_input
        
        try:
            self.client.fput_object(bucket_name, object_name, file_path)
            logger.info(f"Uploaded {object_name} to {bucket_name}")
            return True
        except S3Error as e:
            logger.error(f"Upload failed: {e}")
            return False
    
    def download_file(
        self,
        object_name: str,
        file_path: str,
        bucket_name: Optional[str] = None
    ) -> bool:
        """Download file from MinIO"""
        if not bucket_name:
            bucket_name = settings.minio_bucket_output
        
        try:
            self.client.fget_object(bucket_name, object_name, file_path)
            logger.info(f"Downloaded {object_name} from {bucket_name}")
            return True
        except S3Error as e:
            logger.error(f"Download failed: {e}")
            return False
    
    def list_objects(
        self,
        prefix: str = "",
        bucket_name: Optional[str] = None
    ) -> list:
        """List objects in bucket"""
        if not bucket_name:
            bucket_name = settings.minio_bucket_output
        
        try:
            objects = self.client.list_objects(bucket_name, prefix=prefix, recursive=True)
            return [obj.object_name for obj in objects]
        except S3Error as e:
            logger.error(f"List objects failed: {e}")
            return []
    
    def get_presigned_url(
        self,
        object_name: str,
        bucket_name: Optional[str] = None,
        expires: int = 3600
    ) -> Optional[str]:
        """Get presigned URL for object"""
        if not bucket_name:
            bucket_name = settings.minio_bucket_output
        
        try:
            url = self.client.presigned_get_object(bucket_name, object_name, expires=expires)
            return url
        except S3Error as e:
            logger.error(f"Presigned URL generation failed: {e}")
            return None
