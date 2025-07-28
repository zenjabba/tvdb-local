# Image Storage Documentation

This document describes the scalable image storage solution implemented in the TVDB Proxy application.

## Overview

The image storage system provides:
- Local caching of TVDB images
- Multiple image sizes (original, large, medium, small, thumbnail)
- S3-compatible object storage (AWS S3, MinIO, etc.)
- CDN support for global distribution
- Automatic image optimization (WebP format)
- Background processing with Celery
- Admin controls for syncing and management

## Architecture

### Storage Structure
```
bucket/
├── series/
│   ├── {hash[0:2]}/
│   │   └── {hash[2:4]}/
│   │       └── {series_id}/
│   │           ├── poster/
│   │           │   ├── original.webp
│   │           │   ├── large.webp
│   │           │   ├── medium.webp
│   │           │   ├── small.webp
│   │           │   └── thumbnail.webp
│   │           ├── banner/
│   │           ├── fanart/
│   │           └── image/
├── movies/
├── episodes/
├── seasons/
└── people/
```

### Image Sizes
- **Original**: Unchanged from source
- **Large**: 1920x1080 max
- **Medium**: 1280x720 max
- **Small**: 640x360 max
- **Thumbnail**: 300x169 max

## Configuration

Add the following environment variables:

```env
# S3/Storage Configuration
S3_ENDPOINT_URL=http://localhost:9000  # For MinIO
S3_ACCESS_KEY_ID=your-access-key
S3_SECRET_ACCESS_KEY=your-secret-key
S3_REGION=us-east-1
S3_BUCKET_ORIGINALS=tvdb-images-originals
S3_BUCKET_THUMBNAILS=tvdb-images-thumbnails
CDN_BASE_URL=https://cdn.example.com  # Optional

# Image Processing
IMAGE_FORMAT=webp
IMAGE_QUALITY=85
ENABLE_IMAGE_OPTIMIZATION=true
MAX_IMAGE_FILE_SIZE_MB=10
```

## Local Development with MinIO

1. Start MinIO:
```bash
docker-compose -f docker-compose.storage.yml up -d
```

2. Access MinIO console:
- URL: http://localhost:9001
- Username: minioadmin
- Password: minioadmin

3. Configure your `.env`:
```env
S3_ENDPOINT_URL=http://localhost:9000
S3_ACCESS_KEY_ID=minioadmin
S3_SECRET_ACCESS_KEY=minioadmin
```

## API Endpoints

### Image Serving
```
GET /api/v1/images/{content_type}/{content_id}/{image_type}/{size}
```

Parameters:
- `content_type`: series, movie, episode, season, person
- `content_id`: Database ID of the content
- `image_type`: poster, banner, fanart, image, thumbnail
- `size`: original, large, medium, small, thumbnail

Example:
```
GET /api/v1/images/series/123/poster/medium
```

### Artwork Metadata
```
GET /api/v1/images/artwork/{artwork_id}
```

Returns metadata about artwork including all available sizes.

### Admin Operations

#### Sync Images for Content
```
POST /api/v1/admin/sync/images/{content_type}/{content_id}
```

#### Sync Missing Images
```
POST /api/v1/admin/sync/images/missing?content_type=series&limit=100
```

#### Cleanup Orphaned Images
```
POST /api/v1/admin/sync/images/cleanup
```

#### Get Storage Statistics
```
GET /api/v1/images/storage/stats
```

## Database Schema

New fields added to content models:

### Artwork Table
- `local_image_url`: URL of processed original image
- `local_thumbnail_url`: URL of thumbnail
- `storage_path`: S3 path prefix
- `processed_at`: Timestamp of processing
- `file_size`: Size in bytes

### Content Tables (Series, Movies, Episodes, etc.)
- `local_image_url`: Local URL for main image
- `local_poster_url`: Local URL for poster
- `local_banner_url`: Local URL for banner
- `local_fanart_url`: Local URL for fanart
- `local_thumbnail_url`: Local URL for thumbnail

## Background Tasks

### Celery Tasks

1. **sync_content_images**: Sync images for a specific content item
2. **sync_all_missing_images**: Find and sync content without local images
3. **cleanup_orphaned_images**: Remove images without database references

### Running Workers
```bash
celery -A app.workers.celery_app worker --loglevel=info
```

## Image Processing Pipeline

1. **Download**: Fetch image from TVDB URL
2. **Validate**: Check content type and file size
3. **Process**: Generate multiple sizes
4. **Optimize**: Convert to WebP, apply compression
5. **Upload**: Store in S3 buckets
6. **Update**: Save local URLs in database

## Monitoring

### Storage Usage
```python
from app.services.storage import storage_service

stats = storage_service.get_storage_stats("tvdb-images-originals")
print(f"Total images: {stats['total_objects']}")
print(f"Storage used: {stats['total_size_mb']} MB")
```

### Task Status
```
GET /api/v1/admin/tasks/{task_id}
```

## Production Considerations

1. **CDN Setup**: Configure CloudFront or similar for global distribution
2. **Backup**: Regular S3 backups with lifecycle policies
3. **Monitoring**: Set up CloudWatch or Prometheus metrics
4. **Rate Limiting**: Implement rate limits for image sync operations
5. **Cost Management**: Monitor S3 storage and transfer costs

## Migration

Run the database migration:
```bash
alembic upgrade head
```

This adds local image URL fields to all content models.

## Troubleshooting

### Images Not Loading
1. Check S3 credentials and connectivity
2. Verify bucket permissions (should be public read)
3. Check image processing logs
4. Ensure Celery workers are running

### Storage Full
1. Run cleanup task to remove orphaned images
2. Review image retention policies
3. Consider implementing image expiration

### Performance Issues
1. Enable CDN for image delivery
2. Optimize image sizes and quality settings
3. Implement lazy loading on frontend
4. Use smaller sizes for listings

## Future Enhancements

1. **Smart Cropping**: AI-based image cropping for better thumbnails
2. **AVIF Support**: Next-gen image format support
3. **Image Deduplication**: Content-based deduplication
4. **Responsive Images**: Automatic srcset generation
5. **Image Analytics**: Track most viewed images
6. **Watermarking**: Optional watermark support