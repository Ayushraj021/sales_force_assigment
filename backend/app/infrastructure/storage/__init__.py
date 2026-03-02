"""Storage infrastructure for S3/MinIO."""

from app.infrastructure.storage.s3 import S3Client, get_s3_client

__all__ = ["S3Client", "get_s3_client"]
