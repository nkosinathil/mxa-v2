from __future__ import annotations

import os
from datetime import timedelta
from pathlib import Path

from minio import Minio
from minio.error import S3Error

from .config import get_settings


class MinioStorage:
    def __init__(self) -> None:
        settings = get_settings()
        self.client = Minio(
            endpoint=settings.minio_endpoint,
            access_key=settings.minio_access_key,
            secret_key=settings.minio_secret_key,
            secure=settings.minio_secure,
        )
        self.input_bucket = settings.minio_bucket_input
        self.output_bucket = settings.minio_bucket_output
        self.presign_expire = settings.minio_presign_expire
        self._ensure_bucket(self.input_bucket)
        self._ensure_bucket(self.output_bucket)

    def _ensure_bucket(self, name: str) -> None:
        found = self.client.bucket_exists(name)
        if not found:
            self.client.make_bucket(name)

    def upload_file(self, bucket: str, object_name: str, file_path: Path) -> None:
        self.client.fput_object(bucket, object_name, str(file_path))

    def download_file(self, bucket: str, object_name: str, file_path: Path) -> None:
        file_path.parent.mkdir(parents=True, exist_ok=True)
        self.client.fget_object(bucket, object_name, str(file_path))

    def presigned_get(self, bucket: str, object_name: str) -> str:
        return self.client.presigned_get_object(bucket, object_name, expires=timedelta(seconds=self.presign_expire))


def zip_directory(source_dir: Path, output_zip: Path) -> None:
    import zipfile

    output_zip.parent.mkdir(parents=True, exist_ok=True)
    with zipfile.ZipFile(output_zip, 'w', compression=zipfile.ZIP_DEFLATED) as zf:
        for root, _, files in os.walk(source_dir):
            for name in files:
                path = Path(root) / name
                arc = path.relative_to(source_dir)
                zf.write(path, arcname=str(arc))
