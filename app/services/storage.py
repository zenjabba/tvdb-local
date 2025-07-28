"""Storage service for managing images in S3/Ceph-compatible storage."""
from typing import Any, Dict, Optional

import boto3
import structlog
from botocore.exceptions import ClientError

from app.config import settings

logger = structlog.get_logger()


class StorageService:
    """Service for managing S3/Ceph storage operations."""

    def __init__(self):
        self.client = None
        self.bucket_name = settings.s3_bucket_name
        self._initialized = False

    def _get_client(self):
        """Get or create S3 client."""
        if not self.client and settings.storage_backend == "s3":
            try:
                # Configure for Ceph S3 or AWS S3

                # Log configuration for debugging
                logger.info("Initializing S3 client",
                            endpoint=settings.s3_endpoint_url,
                            access_key_exists=bool(settings.s3_access_key_id),
                            secret_key_exists=bool(settings.s3_secret_access_key))

                self.client = boto3.client(
                    's3',
                    endpoint_url=settings.s3_endpoint_url,
                    aws_access_key_id=settings.s3_access_key_id,
                    aws_secret_access_key=settings.s3_secret_access_key,
                    region_name=settings.s3_region,
                    config=boto3.session.Config(
                        signature_version='s3v4',
                        s3={'addressing_style': 'path'}  # Ceph compatibility
                    )
                )

                # Initialize bucket if needed
                self._ensure_bucket_exists()
                self._initialized = True

                logger.info("S3 client initialized",
                            endpoint=settings.s3_endpoint_url,
                            bucket=self.bucket_name)

            except Exception as e:
                logger.error("Failed to initialize S3 client", error=str(e))
                raise

        return self.client

    def _ensure_bucket_exists(self):
        """Ensure the bucket exists, create if not."""
        try:
            self.client.head_bucket(Bucket=self.bucket_name)
            logger.debug("Bucket exists", bucket=self.bucket_name)
        except ClientError as e:
            error_code = e.response['Error']['Code']
            if error_code == '404':
                try:
                    self.client.create_bucket(Bucket=self.bucket_name)
                    logger.info("Created bucket", bucket=self.bucket_name)
                except Exception as create_error:
                    logger.error("Failed to create bucket",
                                 bucket=self.bucket_name,
                                 error=str(create_error))
                    raise
            else:
                logger.error("Bucket check failed",
                             bucket=self.bucket_name,
                             error=str(e))
                raise

    def upload_image(self, key: str, image_data: bytes,
                     content_type: str = "image/webp",
                     metadata: Optional[Dict[str, str]] = None) -> bool:
        """Upload image to S3/Ceph storage.

        Args:
            key: S3 object key (e.g., "series/123/poster/medium.webp")
            image_data: Image bytes
            content_type: MIME type of the image
            metadata: Optional metadata for the object

        Returns:
            bool: True if successful
        """
        if settings.storage_backend != "s3":
            return False

        try:
            client = self._get_client()
            if not client:
                return False

            # Prepare upload parameters
            extra_args = {
                'ContentType': content_type,
                'CacheControl': 'public, max-age=86400'  # 24 hours
            }

            if metadata:
                extra_args['Metadata'] = metadata

            # Upload to S3
            client.put_object(
                Bucket=self.bucket_name,
                Key=key,
                Body=image_data,
                **extra_args
            )

            logger.debug("Image uploaded", key=key, size=len(image_data))
            return True

        except Exception as e:
            logger.error("Failed to upload image",
                         key=key,
                         error=str(e))
            return False

    def download_image(self, key: str) -> Optional[bytes]:
        """Download image from S3/Ceph storage.

        Args:
            key: S3 object key

        Returns:
            Image bytes or None if not found
        """
        if settings.storage_backend != "s3":
            return None

        try:
            client = self._get_client()
            if not client:
                return None

            response = client.get_object(
                Bucket=self.bucket_name,
                Key=key
            )

            return response['Body'].read()

        except ClientError as e:
            if e.response['Error']['Code'] == 'NoSuchKey':
                logger.debug("Image not found", key=key)
            else:
                logger.error("Failed to download image",
                             key=key,
                             error=str(e))
            return None

    def delete_image(self, key: str) -> bool:
        """Delete image from S3/Ceph storage.

        Args:
            key: S3 object key

        Returns:
            bool: True if successful
        """
        if settings.storage_backend != "s3":
            return False

        try:
            client = self._get_client()
            if not client:
                return False

            client.delete_object(
                Bucket=self.bucket_name,
                Key=key
            )

            logger.debug("Image deleted", key=key)
            return True

        except Exception as e:
            logger.error("Failed to delete image",
                         key=key,
                         error=str(e))
            return False

    def image_exists(self, key: str) -> bool:
        """Check if image exists in storage.

        Args:
            key: S3 object key

        Returns:
            bool: True if exists
        """
        if settings.storage_backend != "s3":
            return False

        try:
            client = self._get_client()
            if not client:
                return False

            client.head_object(
                Bucket=self.bucket_name,
                Key=key
            )
            return True

        except ClientError as e:
            if e.response['Error']['Code'] == '404':
                return False
            logger.error("Failed to check image existence",
                         key=key,
                         error=str(e))
            return False

    def list_images(self, prefix: str, max_keys: int = 1000) -> list:
        """List images with given prefix.

        Args:
            prefix: S3 key prefix (e.g., "series/123/")
            max_keys: Maximum number of keys to return

        Returns:
            List of object keys
        """
        if settings.storage_backend != "s3":
            return []

        try:
            client = self._get_client()
            if not client:
                return []

            response = client.list_objects_v2(
                Bucket=self.bucket_name,
                Prefix=prefix,
                MaxKeys=max_keys
            )

            if 'Contents' not in response:
                return []

            return [obj['Key'] for obj in response['Contents']]

        except Exception as e:
            logger.error("Failed to list images",
                         prefix=prefix,
                         error=str(e))
            return []

    def get_storage_stats(self) -> Dict[str, Any]:
        """Get storage statistics.

        Returns:
            Dict with storage statistics
        """
        if settings.storage_backend != "s3":
            return {"backend": "none", "enabled": False}

        try:
            client = self._get_client()
            if not client:
                return {"backend": "s3", "enabled": False, "error": "Not initialized"}

            # Get bucket size and object count
            paginator = client.get_paginator('list_objects_v2')
            total_size = 0
            total_objects = 0

            for page in paginator.paginate(Bucket=self.bucket_name):
                if 'Contents' in page:
                    for obj in page['Contents']:
                        total_size += obj['Size']
                        total_objects += 1

            return {
                "backend": "s3",
                "enabled": True,
                "bucket": self.bucket_name,
                "endpoint": settings.s3_endpoint_url or "AWS S3",
                "total_objects": total_objects,
                "total_size_bytes": total_size,
                "total_size_mb": round(total_size / (1024 * 1024), 2),
                "total_size_gb": round(total_size / (1024 * 1024 * 1024), 2)
            }

        except Exception as e:
            logger.error("Failed to get storage stats", error=str(e))
            return {
                "backend": "s3",
                "enabled": True,
                "error": str(e)
            }

    def generate_presigned_url(self, key: str, expiration: int = 3600) -> Optional[str]:
        """Generate presigned URL for direct access.

        Note: This is for internal use only. Public access should go through
        the application proxy endpoints.

        Args:
            key: S3 object key
            expiration: URL expiration in seconds

        Returns:
            Presigned URL or None
        """
        if settings.storage_backend != "s3":
            return None

        try:
            client = self._get_client()
            if not client:
                return None

            url = client.generate_presigned_url(
                'get_object',
                Params={
                    'Bucket': self.bucket_name,
                    'Key': key
                },
                ExpiresIn=expiration
            )

            return url

        except Exception as e:
            logger.error("Failed to generate presigned URL",
                         key=key,
                         error=str(e))
            return None


# Global storage instance
storage = StorageService()
