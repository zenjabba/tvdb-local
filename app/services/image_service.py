"""Image service for downloading and storing raw images without processing."""
from typing import Dict, List, Optional
from urllib.parse import urlparse

import httpx
import structlog

from app.services.storage import storage

logger = structlog.get_logger()


class ImageService:
    """Service for downloading and managing TVDB images."""

    def __init__(self):
        self.http_client = httpx.AsyncClient(
            timeout=30.0,
            follow_redirects=True,
            headers={'User-Agent': 'TVDB-Proxy/1.0'}
        )

    async def __aenter__(self):
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        await self.http_client.aclose()

    def _get_image_key(self, entity_type: str, entity_id: int,
                       image_type: str) -> str:
        """Generate S3 key for an image.

        Args:
            entity_type: Type of entity (series, movie, episode, person)
            entity_id: Entity ID
            image_type: Type of image (poster, banner, fanart, image)

        Returns:
            S3 key string
        """
        # Extract file extension from URL or default to jpg
        return f"{entity_type}/{entity_id}/{image_type}"

    def _get_file_extension(self, url: str, content_type: str = None) -> str:
        """Get file extension from URL or content type.

        Args:
            url: Image URL
            content_type: HTTP Content-Type header

        Returns:
            File extension (e.g., 'jpg', 'png')
        """
        # Try to get from URL first
        parsed = urlparse(url)
        path = parsed.path
        if '.' in path:
            ext = path.split('.')[-1].lower()
            if ext in ['jpg', 'jpeg', 'png', 'gif', 'webp']:
                return ext

        # Try content type
        if content_type:
            if 'jpeg' in content_type or 'jpg' in content_type:
                return 'jpg'
            elif 'png' in content_type:
                return 'png'
            elif 'gif' in content_type:
                return 'gif'
            elif 'webp' in content_type:
                return 'webp'

        # Default to jpg
        return 'jpg'

    async def download_image(self, url: str) -> Optional[tuple[bytes, str]]:
        """Download image from URL.

        Args:
            url: Image URL

        Returns:
            Tuple of (image bytes, file extension) or None if failed
        """
        if not url:
            return None

        try:
            response = await self.http_client.get(url)
            response.raise_for_status()

            # Check content type
            content_type = response.headers.get('content-type', '')
            if not content_type.startswith('image/'):
                logger.warning("Invalid content type for image",
                               url=url,
                               content_type=content_type)
                return None

            # No size limits - store 1:1 raw images regardless of size
            # Get file extension
            ext = self._get_file_extension(url, content_type)

            return response.content, ext

        except Exception as e:
            logger.error("Failed to download image", url=url, error=str(e))
            return None

    async def download_and_store_image(self, url: str, entity_type: str,
                                       entity_id: int, image_type: str) -> Optional[str]:
        """Download and store raw image.

        Args:
            url: Source image URL
            entity_type: Type of entity
            entity_id: Entity ID
            image_type: Type of image

        Returns:
            S3 key of stored image or None if failed
        """
        # Download image
        result = await self.download_image(url)
        if not result:
            logger.warning("Failed to download image", url=url)
            return None

        image_bytes, ext = result

        # Generate S3 key with extension
        base_key = self._get_image_key(entity_type, entity_id, image_type)
        key = f"{base_key}.{ext}"

        # Determine content type
        content_type_map = {
            'jpg': 'image/jpeg',
            'jpeg': 'image/jpeg',
            'png': 'image/png',
            'gif': 'image/gif',
            'webp': 'image/webp'
        }
        content_type = content_type_map.get(ext, 'image/jpeg')

        # Upload to storage
        success = storage.upload_image(
            key=key,
            image_data=image_bytes,
            content_type=content_type,
            metadata={
                'source_url': url,
                'entity_type': entity_type,
                'entity_id': str(entity_id),
                'image_type': image_type
            }
        )

        if success:
            logger.debug("Image stored",
                         entity_type=entity_type,
                         entity_id=entity_id,
                         image_type=image_type,
                         key=key)
            return key

        return None

    async def get_image(self, entity_type: str, entity_id: int,
                        image_type: str) -> Optional[tuple[bytes, str]]:
        """Get image from storage.

        Args:
            entity_type: Type of entity
            entity_id: Entity ID
            image_type: Type of image

        Returns:
            Tuple of (image bytes, content type) or None if not found
        """
        # Try different extensions
        for ext in ['jpg', 'jpeg', 'png', 'gif', 'webp']:
            key = f"{entity_type}/{entity_id}/{image_type}.{ext}"
            image_data = storage.download_image(key)
            if image_data:
                content_type_map = {
                    'jpg': 'image/jpeg',
                    'jpeg': 'image/jpeg',
                    'png': 'image/png',
                    'gif': 'image/gif',
                    'webp': 'image/webp'
                }
                return image_data, content_type_map.get(ext, 'image/jpeg')

        return None

    async def sync_entity_images(self, entity_type: str, entity_id: int,
                                 image_urls: Dict[str, str]) -> Dict[str, str]:
        """Sync all images for an entity.

        Args:
            entity_type: Type of entity
            entity_id: Entity ID
            image_urls: Dict mapping image types to URLs

        Returns:
            Dict mapping image types to stored S3 keys
        """
        results = {}

        # Process each image type
        tasks = []
        for image_type, url in image_urls.items():
            if url:
                task = self.download_and_store_image(url, entity_type, entity_id, image_type)
                tasks.append((image_type, task))

        # Wait for all downloads to complete
        for image_type, task in tasks:
            try:
                key = await task
                if key:
                    results[image_type] = key
            except Exception as e:
                logger.error("Failed to sync image",
                             entity_type=entity_type,
                             entity_id=entity_id,
                             image_type=image_type,
                             error=str(e))

        return results

    def get_local_image_url(self, entity_type: str, entity_id: int,
                            image_type: str, base_url: str = "") -> str:
        """Get local image URL for API responses.

        Args:
            entity_type: Type of entity
            entity_id: Entity ID
            image_type: Type of image
            base_url: Base URL for the image (e.g., https://api.example.com)

        Returns:
            Full URL for the image
        """
        if base_url:
            return f"{base_url}/images/{entity_type}/{entity_id}/{image_type}"
        return f"/images/{entity_type}/{entity_id}/{image_type}"

    async def cleanup_orphaned_images(self, active_entity_ids: Dict[str, List[int]]) -> int:
        """Remove images for entities that no longer exist.

        Args:
            active_entity_ids: Dict mapping entity types to lists of active IDs

        Returns:
            Number of images deleted
        """
        deleted_count = 0

        for entity_type, active_ids in active_entity_ids.items():
            # List all images for this entity type
            all_keys = storage.list_images(f"{entity_type}/")

            # Extract entity IDs from keys
            entity_id_set = set(active_ids)

            for key in all_keys:
                try:
                    # Parse entity ID from key
                    parts = key.split('/')
                    if len(parts) >= 2:
                        entity_id = int(parts[1])

                        # Delete if entity no longer exists
                        if entity_id not in entity_id_set:
                            if storage.delete_image(key):
                                deleted_count += 1

                except (ValueError, IndexError):
                    logger.warning("Invalid image key format", key=key)

        logger.info("Cleaned up orphaned images", deleted_count=deleted_count)
        return deleted_count


# Global image service instance
image_service = ImageService()
