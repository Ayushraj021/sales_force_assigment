"""S3/MinIO storage client."""

import io
from functools import lru_cache
from typing import BinaryIO

import boto3
import structlog
from botocore.config import Config
from botocore.exceptions import ClientError

from app.config import settings

logger = structlog.get_logger()


class S3Client:
    """S3/MinIO storage client for managing file uploads and downloads."""

    def __init__(
        self,
        endpoint_url: str | None = None,
        access_key: str | None = None,
        secret_key: str | None = None,
        region: str = "us-east-1",
        bucket_name: str | None = None,
    ):
        """Initialize S3 client.

        Args:
            endpoint_url: S3 endpoint URL (for MinIO, use http://localhost:9000)
            access_key: AWS access key or MinIO access key
            secret_key: AWS secret key or MinIO secret key
            region: AWS region (default: us-east-1)
            bucket_name: Default bucket name for operations
        """
        self.endpoint_url = endpoint_url or settings.S3_ENDPOINT_URL
        self.access_key = access_key or settings.S3_ACCESS_KEY
        self.secret_key = secret_key or settings.S3_SECRET_KEY
        self.region = region or settings.S3_REGION
        self.bucket_name = bucket_name or settings.S3_BUCKET_NAME

        # Configure boto3 client
        config = Config(
            signature_version="s3v4",
            retries={"max_attempts": 3, "mode": "standard"},
        )

        self._client = boto3.client(
            "s3",
            endpoint_url=self.endpoint_url,
            aws_access_key_id=self.access_key,
            aws_secret_access_key=self.secret_key,
            region_name=self.region,
            config=config,
        )

        self._resource = boto3.resource(
            "s3",
            endpoint_url=self.endpoint_url,
            aws_access_key_id=self.access_key,
            aws_secret_access_key=self.secret_key,
            region_name=self.region,
            config=config,
        )

    def ensure_bucket_exists(self, bucket_name: str | None = None) -> bool:
        """Ensure the bucket exists, create if it doesn't.

        Args:
            bucket_name: Bucket name (uses default if not provided)

        Returns:
            True if bucket exists or was created successfully
        """
        bucket = bucket_name or self.bucket_name
        if not bucket:
            raise ValueError("Bucket name is required")

        try:
            self._client.head_bucket(Bucket=bucket)
            logger.debug("Bucket exists", bucket=bucket)
            return True
        except ClientError as e:
            error_code = e.response.get("Error", {}).get("Code")
            if error_code == "404":
                # Bucket doesn't exist, create it
                try:
                    if self.region == "us-east-1":
                        self._client.create_bucket(Bucket=bucket)
                    else:
                        self._client.create_bucket(
                            Bucket=bucket,
                            CreateBucketConfiguration={"LocationConstraint": self.region},
                        )
                    logger.info("Bucket created", bucket=bucket)
                    return True
                except ClientError as create_error:
                    logger.error("Failed to create bucket", bucket=bucket, error=str(create_error))
                    raise
            else:
                logger.error("Error checking bucket", bucket=bucket, error=str(e))
                raise

    def upload_file(
        self,
        file_obj: BinaryIO,
        key: str,
        bucket_name: str | None = None,
        content_type: str | None = None,
        metadata: dict | None = None,
    ) -> str:
        """Upload a file to S3/MinIO.

        Args:
            file_obj: File-like object to upload
            key: Object key (path in bucket)
            bucket_name: Bucket name (uses default if not provided)
            content_type: MIME content type
            metadata: Additional metadata to store with the object

        Returns:
            The S3 URI of the uploaded object (s3://bucket/key)
        """
        bucket = bucket_name or self.bucket_name
        if not bucket:
            raise ValueError("Bucket name is required")

        # Ensure bucket exists
        self.ensure_bucket_exists(bucket)

        extra_args = {}
        if content_type:
            extra_args["ContentType"] = content_type
        if metadata:
            extra_args["Metadata"] = metadata

        try:
            self._client.upload_fileobj(file_obj, bucket, key, ExtraArgs=extra_args or None)
            s3_uri = f"s3://{bucket}/{key}"
            logger.info("File uploaded to S3", bucket=bucket, key=key, uri=s3_uri)
            return s3_uri
        except ClientError as e:
            logger.error("Failed to upload file", bucket=bucket, key=key, error=str(e))
            raise

    def upload_bytes(
        self,
        data: bytes,
        key: str,
        bucket_name: str | None = None,
        content_type: str | None = None,
        metadata: dict | None = None,
    ) -> str:
        """Upload bytes data to S3/MinIO.

        Args:
            data: Bytes to upload
            key: Object key (path in bucket)
            bucket_name: Bucket name (uses default if not provided)
            content_type: MIME content type
            metadata: Additional metadata to store with the object

        Returns:
            The S3 URI of the uploaded object (s3://bucket/key)
        """
        return self.upload_file(
            io.BytesIO(data),
            key,
            bucket_name=bucket_name,
            content_type=content_type,
            metadata=metadata,
        )

    def download_file(
        self,
        key: str,
        bucket_name: str | None = None,
    ) -> bytes:
        """Download a file from S3/MinIO.

        Args:
            key: Object key (path in bucket)
            bucket_name: Bucket name (uses default if not provided)

        Returns:
            File contents as bytes
        """
        bucket = bucket_name or self.bucket_name
        if not bucket:
            raise ValueError("Bucket name is required")

        try:
            response = self._client.get_object(Bucket=bucket, Key=key)
            data = response["Body"].read()
            logger.debug("File downloaded from S3", bucket=bucket, key=key, size=len(data))
            return data
        except ClientError as e:
            logger.error("Failed to download file", bucket=bucket, key=key, error=str(e))
            raise

    def download_fileobj(
        self,
        key: str,
        file_obj: BinaryIO,
        bucket_name: str | None = None,
    ) -> None:
        """Download a file from S3/MinIO to a file object.

        Args:
            key: Object key (path in bucket)
            file_obj: File-like object to write to
            bucket_name: Bucket name (uses default if not provided)
        """
        bucket = bucket_name or self.bucket_name
        if not bucket:
            raise ValueError("Bucket name is required")

        try:
            self._client.download_fileobj(bucket, key, file_obj)
            logger.debug("File downloaded from S3", bucket=bucket, key=key)
        except ClientError as e:
            logger.error("Failed to download file", bucket=bucket, key=key, error=str(e))
            raise

    def delete_file(
        self,
        key: str,
        bucket_name: str | None = None,
    ) -> bool:
        """Delete a file from S3/MinIO.

        Args:
            key: Object key (path in bucket)
            bucket_name: Bucket name (uses default if not provided)

        Returns:
            True if deleted successfully
        """
        bucket = bucket_name or self.bucket_name
        if not bucket:
            raise ValueError("Bucket name is required")

        try:
            self._client.delete_object(Bucket=bucket, Key=key)
            logger.info("File deleted from S3", bucket=bucket, key=key)
            return True
        except ClientError as e:
            logger.error("Failed to delete file", bucket=bucket, key=key, error=str(e))
            raise

    def file_exists(
        self,
        key: str,
        bucket_name: str | None = None,
    ) -> bool:
        """Check if a file exists in S3/MinIO.

        Args:
            key: Object key (path in bucket)
            bucket_name: Bucket name (uses default if not provided)

        Returns:
            True if file exists
        """
        bucket = bucket_name or self.bucket_name
        if not bucket:
            raise ValueError("Bucket name is required")

        try:
            self._client.head_object(Bucket=bucket, Key=key)
            return True
        except ClientError as e:
            if e.response.get("Error", {}).get("Code") == "404":
                return False
            raise

    def get_presigned_url(
        self,
        key: str,
        bucket_name: str | None = None,
        expires_in: int = 3600,
        operation: str = "get_object",
    ) -> str:
        """Generate a presigned URL for temporary access.

        Args:
            key: Object key (path in bucket)
            bucket_name: Bucket name (uses default if not provided)
            expires_in: URL expiration time in seconds (default: 1 hour)
            operation: S3 operation (get_object or put_object)

        Returns:
            Presigned URL string
        """
        bucket = bucket_name or self.bucket_name
        if not bucket:
            raise ValueError("Bucket name is required")

        try:
            url = self._client.generate_presigned_url(
                operation,
                Params={"Bucket": bucket, "Key": key},
                ExpiresIn=expires_in,
            )
            return url
        except ClientError as e:
            logger.error("Failed to generate presigned URL", bucket=bucket, key=key, error=str(e))
            raise

    def list_objects(
        self,
        prefix: str = "",
        bucket_name: str | None = None,
        max_keys: int = 1000,
    ) -> list[dict]:
        """List objects in a bucket with optional prefix filter.

        Args:
            prefix: Object key prefix to filter by
            bucket_name: Bucket name (uses default if not provided)
            max_keys: Maximum number of keys to return

        Returns:
            List of object metadata dictionaries
        """
        bucket = bucket_name or self.bucket_name
        if not bucket:
            raise ValueError("Bucket name is required")

        try:
            response = self._client.list_objects_v2(
                Bucket=bucket,
                Prefix=prefix,
                MaxKeys=max_keys,
            )
            objects = response.get("Contents", [])
            return [
                {
                    "key": obj["Key"],
                    "size": obj["Size"],
                    "last_modified": obj["LastModified"],
                    "etag": obj["ETag"],
                }
                for obj in objects
            ]
        except ClientError as e:
            logger.error("Failed to list objects", bucket=bucket, prefix=prefix, error=str(e))
            raise


@lru_cache()
def get_s3_client() -> S3Client:
    """Get a cached S3 client instance."""
    return S3Client()
