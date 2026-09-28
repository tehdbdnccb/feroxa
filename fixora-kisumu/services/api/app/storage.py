from __future__ import annotations

import hashlib
import io
from pathlib import Path
from uuid import uuid4

from .config import settings

try:
    import boto3
except ImportError:  # pragma: no cover
    boto3 = None


class StorageError(RuntimeError):
    pass


class ObjectStorage:
    def __init__(self) -> None:
        self.s3 = None
        if settings.storage_bucket:
            if boto3 is None:
                raise StorageError("boto3 is required when STORAGE_BUCKET is configured")
            self.s3 = boto3.client(
                "s3",
                region_name=settings.storage_region,
                endpoint_url=settings.storage_endpoint_url,
                aws_access_key_id=settings.storage_access_key_id,
                aws_secret_access_key=settings.storage_secret_access_key,
            )
        Path(settings.media_root).mkdir(parents=True, exist_ok=True)

    @property
    def is_s3(self) -> bool:
        return self.s3 is not None

    def put(self, data: bytes, content_type: str, original_name: str) -> tuple[str, str]:
        suffix = Path(original_name).suffix.lower()[:10]
        key = f"repairs/{uuid4()}{suffix}"
        sha256 = hashlib.sha256(data).hexdigest()
        if self.s3:
            self.s3.put_object(Bucket=settings.storage_bucket, Key=key, Body=io.BytesIO(data), ContentType=content_type)
        else:
            path = Path(settings.media_root) / key
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_bytes(data)
        return key, sha256

    def download_url(self, key: str) -> str | None:
        if self.s3:
            return self.s3.generate_presigned_url(
                "get_object",
                Params={"Bucket": settings.storage_bucket, "Key": key},
                ExpiresIn=600,
            )
        return None

    def local_path(self, key: str) -> Path:
        root = Path(settings.media_root).resolve()
        target = (root / key).resolve()
        if root not in target.parents:
            raise StorageError("Invalid object key")
        return target


storage = ObjectStorage()
