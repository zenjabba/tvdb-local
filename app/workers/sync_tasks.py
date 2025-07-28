"""Celery tasks for synchronizing data with TVDB API."""
import asyncio
from datetime import datetime, timedelta
from typing import Any, Dict, List

import structlog
from sqlalchemy import or_ as db_or
from sqlalchemy.orm import Session

from app.database import SessionLocal
from app.models import Episode, Series
from app.models.artwork import Artwork
from app.models.movie import Movie
from app.models.person import Person
from app.models.season import Season
from app.services.image_service import image_service
from app.services.tvdb_client import tvdb_client
from app.workers.celery_app import celery_app

logger = structlog.get_logger()


def get_db_session() -> Session:
    """Get database session for worker tasks"""
    return SessionLocal()


@celery_app.task(bind=True)
def full_sync(self):
    """Perform full database synchronization with TVDB"""
    logger.info("Starting full database sync")

    try:
        with get_db_session() as db:
            # Update task progress
            self.update_state(
                state='PROGRESS',
                meta={
                    'current': 0,
                    'total': 100,
                    'status': 'Starting full sync'})

            # Sync static data first
            _sync_static_data_sync(db)
            self.update_state(
                state='PROGRESS',
                meta={
                    'current': 20,
                    'total': 100,
                    'status': 'Static data synced'})

            # Sync all series
            _sync_all_series_sync(db)
            self.update_state(
                state='PROGRESS',
                meta={
                    'current': 60,
                    'total': 100,
                    'status': 'Series synced'})

            # Sync movies
            _sync_movies_sync(db)
            self.update_state(
                state='PROGRESS',
                meta={
                    'current': 80,
                    'total': 100,
                    'status': 'Movies synced'})

            # Sync people
            _sync_people_sync(db)
            self.update_state(
                state='PROGRESS',
                meta={
                    'current': 100,
                    'total': 100,
                    'status': 'Full sync completed'})

            logger.info("Full database sync completed successfully")
            return {
                "status": "completed",
                "message": "Full sync completed successfully"}

    except Exception as e:
        logger.error("Full sync failed", error=str(e))
        self.update_state(state='FAILURE', meta={'error': str(e)})
        raise


@celery_app.task(bind=True)
def incremental_sync(self):
    """Perform incremental sync using TVDB updates endpoint"""
    logger.info("Starting incremental sync")

    try:
        with get_db_session() as db:
            self.update_state(
                state='PROGRESS',
                meta={
                    'current': 0,
                    'total': 100,
                    'status': 'Fetching updates'})

            # Get last sync time
            last_sync = _get_last_sync_time(db)

            # Fetch updates from TVDB (this would use the /updates endpoint)
            # Note: The Python library doesn't show this endpoint, would need
            # to implement
            updated_items = _fetch_tvdb_updates(last_sync)

            if not updated_items:
                logger.info("No updates found")
                return {"status": "completed", "message": "No updates found"}

            total_items = len(updated_items)
            processed = 0

            for item in updated_items:
                _process_update_item(db, item)
                processed += 1
                progress = int((processed / total_items) * 100)
                self.update_state(
                    state='PROGRESS',
                    meta={
                        'current': progress,
                        'total': 100,
                        'status': f'Processing updates: {processed}/{total_items}'})

            # Update last sync time
            _update_last_sync_time(db)

            logger.info(
                "Incremental sync completed",
                items_processed=processed)
            return {
                "status": "completed",
                "message": f"Processed {processed} updates"}

    except Exception as e:
        logger.error("Incremental sync failed", error=str(e))
        self.update_state(state='FAILURE', meta={'error': str(e)})
        raise


@celery_app.task(bind=True)
def sync_static_data(self):
    """Sync static/reference data from TVDB"""
    logger.info("Starting static data sync")

    try:
        with get_db_session() as db:
            _sync_static_data_sync(db)
            logger.info("Static data sync completed")
            return {
                "status": "completed",
                "message": "Static data synced successfully"}

    except Exception as e:
        logger.error("Static data sync failed", error=str(e))
        self.update_state(state='FAILURE', meta={'error': str(e)})
        raise


@celery_app.task(bind=True)
def sync_series_detailed(self, series_id: int):
    """Sync detailed information for a specific series"""
    logger.info("Starting detailed series sync", series_id=series_id)

    try:
        with get_db_session() as db:
            # Fetch extended series data
            series_data = asyncio.run(
                tvdb_client.get_series_extended(
                    series_id, use_cache=False))
            if series_data:
                _update_or_create_series(db, series_data)

            # Fetch all episodes for the series
            page = 0
            while True:
                episodes_data = asyncio.run(
                    tvdb_client.get_series_episodes(
                        series_id, page, use_cache=False))
                if not episodes_data or not episodes_data.get('data'):
                    break

                for episode_data in episodes_data['data']:
                    _update_or_create_episode(db, episode_data, series_id)

                # Check if there are more pages
                if not episodes_data.get('links', {}).get('next'):
                    break
                page += 1

            db.commit()
            logger.info("Detailed series sync completed", series_id=series_id)
            return {"status": "completed", "series_id": series_id}

    except Exception as e:
        logger.error(
            "Detailed series sync failed",
            series_id=series_id,
            error=str(e))
        db.rollback()
        raise


def _sync_static_data_sync(db: Session):
    """Synchronize static data (helper function)"""
    logger.info("Syncing static data")

    # This would sync genres, languages, artwork types, etc.
    # For now, we'll create some basic entries
    static_data_types = [
        "genres", "languages", "artwork_types", "series_status",
        "movie_status", "person_types", "genders", "content_ratings"
    ]

    for data_type in static_data_types:
        logger.debug("Syncing static data type", type=data_type)
        # Implementation would fetch from TVDB API and update database
        # For now, just log the operation


def _sync_all_series_sync(db: Session):
    """Synchronize all series from TVDB"""
    logger.info("Syncing all series")

    page = 0
    total_series = 0

    while True:
        series_data = asyncio.run(
            tvdb_client.get_all_series(
                page, use_cache=False))
        if not series_data or not series_data.get('data'):
            break

        for series in series_data['data']:
            _update_or_create_series(db, series)
            total_series += 1

        # Check if there are more pages
        if not series_data.get('links', {}).get('next'):
            break
        page += 1

        # Commit periodically to avoid large transactions
        if page % 10 == 0:
            db.commit()
            logger.debug(
                "Committed series batch",
                page=page,
                total=total_series)

    db.commit()
    logger.info("All series sync completed", total_series=total_series)


def _sync_movies_sync(db: Session):
    """Synchronize movies from TVDB"""
    logger.info("Syncing movies")
    # Similar implementation to series sync
    # Would iterate through movies and update database


def _sync_people_sync(db: Session):
    """Synchronize people from TVDB"""
    logger.info("Syncing people")
    # Similar implementation for people/cast


def _update_or_create_series(db: Session, series_data: Dict[str, Any]):
    """Update or create series record"""
    tvdb_id = series_data.get('id')
    if not tvdb_id:
        return

    series = db.query(Series).filter(Series.tvdb_id == tvdb_id).first()

    # Extract relevant fields from TVDB response
    series_fields = {
        'name': series_data.get('name', ''),
        'slug': series_data.get('slug', ''),
        'overview': series_data.get('overview', ''),
        'year': series_data.get('year'),
        'first_aired': series_data.get('firstAired'),
        'original_country': series_data.get('originalCountry'),
        'original_language': series_data.get('originalLanguage'),
        'average_runtime': series_data.get('averageRuntime'),
        'score': series_data.get('score'),
        'image': series_data.get('image'),
        'imdb_id': next((r.get('id') for r in series_data.get('remoteIds', []) if r.get('type') == 2), None),
        'aliases': [a.get('name') for a in series_data.get('aliases', [])],
        'last_synced': datetime.utcnow()
    }

    if series:
        # Update existing series
        for key, value in series_fields.items():
            if hasattr(series, key):
                setattr(series, key, value)
    else:
        # Create new series
        series = Series(tvdb_id=tvdb_id, **series_fields)
        db.add(series)

    logger.debug("Series updated/created", tvdb_id=tvdb_id)


def _update_or_create_episode(
        db: Session, episode_data: Dict[str, Any], series_id: int):
    """Update or create episode record"""
    tvdb_id = episode_data.get('id')
    if not tvdb_id:
        return

    # Get the series record to link the episode
    series = db.query(Series).filter(Series.tvdb_id == series_id).first()
    if not series:
        logger.error("Series not found for episode", series_id=series_id)
        return

    episode = db.query(Episode).filter(Episode.tvdb_id == tvdb_id).first()

    # Extract relevant fields from TVDB response
    episode_fields = {
        'name': episode_data.get('name', ''),
        'overview': episode_data.get('overview', ''),
        'number': episode_data.get('number'),
        'season_number': episode_data.get('seasonNumber'),
        'air_date': episode_data.get('aired'),
        'runtime': episode_data.get('runtime'),
        'image': episode_data.get('image'),
        'last_synced': datetime.utcnow()
    }

    if episode:
        # Update existing episode
        for key, value in episode_fields.items():
            if hasattr(episode, key):
                setattr(episode, key, value)
    else:
        # Create new episode
        episode = Episode(
            tvdb_id=tvdb_id,
            series_id=series.id,  # Use the database ID, not TVDB ID
            **episode_fields
        )
        db.add(episode)

    logger.debug(
        "Episode updated/created",
        tvdb_id=tvdb_id,
        series_tvdb_id=series_id)


def _get_last_sync_time(db: Session) -> datetime:
    """Get the last successful sync time"""
    # This would query a sync_status table or similar
    # For now, return 24 hours ago
    return datetime.utcnow() - timedelta(hours=24)


def _update_last_sync_time(db: Session):
    """Update the last sync time"""
    # This would update a sync_status table
    logger.debug("Last sync time updated")


def _fetch_tvdb_updates(since: datetime) -> List[Dict[str, Any]]:
    """Fetch updates from TVDB since given time"""
    # This would use the /updates endpoint
    # For now, return empty list
    logger.debug("Fetching TVDB updates", since=since.isoformat())
    return []


def _process_update_item(db: Session, item: Dict[str, Any]):
    """Process a single update item"""
    entity_type = item.get('entityType')
    entity_id = item.get('recordId')

    if entity_type == 'series':
        series_data = asyncio.run(
            tvdb_client.get_series_extended(
                entity_id, use_cache=False))
        if series_data:
            _update_or_create_series(db, series_data)

    elif entity_type == 'episode':
        # Would fetch and update episode
        pass

    elif entity_type == 'movie':
        movie_data = asyncio.run(
            tvdb_client.get_movie_extended(
                entity_id, use_cache=False))
        if movie_data:
            # _update_or_create_movie(db, movie_data)
            pass

    db.commit()
    logger.debug("Update item processed", type=entity_type, id=entity_id)


@celery_app.task(bind=True, max_retries=3, default_retry_delay=60)
def sync_content_images(self, content_type: str, content_id: int):
    """
    Sync images for a specific content item

    Args:
        content_type: Type of content (series, movie, episode, season, person)
        content_id: Database ID of the content
    """
    logger.info(
        "Starting image sync",
        content_type=content_type,
        content_id=content_id
    )

    try:
        with get_db_session() as db:
            # Get content from database
            content = _get_content_by_id(db, content_type, content_id)
            if not content:
                logger.error(
                    "Content not found",
                    content_type=content_type,
                    content_id=content_id
                )
                return {"status": "failed", "message": "Content not found"}

            # Sync direct image fields
            synced_images = {}
            image_fields = _get_content_image_fields(content_type)

            # Collect all image URLs to download
            image_downloads = []
            for field_name in image_fields:
                image_url = getattr(content, field_name, None)
                if image_url:
                    image_downloads.append((field_name, image_url))

            # Download all images in a single event loop
            if image_downloads:
                synced_images = asyncio.run(_sync_content_images_async(
                    image_downloads, content_type, content_id, content
                ))

            # Commit content image updates
            if synced_images:
                db.commit()

            # Sync artwork if available
            if hasattr(content, "artwork"):
                # Collect all artwork URLs to download
                artwork_downloads = []
                for artwork in content.artwork:
                    if artwork.image_url:
                        artwork_downloads.append(("image", artwork.image_url, artwork))
                    if artwork.thumbnail_url:
                        artwork_downloads.append(("thumbnail", artwork.thumbnail_url, artwork))

                # Download all artwork images in a single event loop
                artwork_count = 0
                if artwork_downloads:
                    artwork_count = asyncio.run(_sync_artwork_images_async(artwork_downloads))

                # Commit artwork updates
                if artwork_count > 0:
                    db.commit()

                logger.info(
                    "Artwork sync completed",
                    count=artwork_count
                )

            return {
                "status": "completed",
                "content_type": content_type,
                "content_id": content_id,
                "synced_images": synced_images
            }

    except Exception as e:
        logger.error(
            "Image sync task failed",
            content_type=content_type,
            content_id=content_id,
            error=str(e)
        )

        # Retry the task
        raise self.retry(exc=e)


@celery_app.task(bind=True)
def sync_all_missing_images(self, content_type: str = None, limit: int = 100):
    """
    Find and sync images for content that doesn't have local images

    Args:
        content_type: Optional filter by content type
        limit: Maximum number of items to process
    """
    logger.info(
        "Starting missing images sync",
        content_type=content_type,
        limit=limit
    )

    try:
        with get_db_session() as db:
            processed = 0

            # Process each content type
            content_types = [content_type] if content_type else [
                "series", "movie", "episode", "season", "person"
            ]

            for ct in content_types:
                items = _get_content_without_local_images(db, ct, limit)

                for item in items:
                    # Queue individual sync task
                    sync_content_images.delay(ct, item.id)
                    processed += 1

                    if processed >= limit:
                        break

                if processed >= limit:
                    break

            logger.info(
                "Missing images sync queued",
                processed=processed
            )

            return {
                "status": "completed",
                "queued": processed
            }

    except Exception as e:
        logger.error(
            "Missing images sync failed",
            error=str(e)
        )
        raise


@celery_app.task(bind=True)
def cleanup_orphaned_images(self):
    """Clean up images in storage that no longer have database references"""
    logger.info("Starting orphaned images cleanup")

    try:
        with get_db_session() as db:
            # Get all active entity IDs
            active_entity_ids = {
                "series": [s.id for s in db.query(Series.id).all()],
                "movie": [m.id for m in db.query(Movie.id).all()],
                "episode": [e.id for e in db.query(Episode.id).all()],
                "season": [s.id for s in db.query(Season.id).all()],
                "person": [p.id for p in db.query(Person.id).all()],
                "artwork": [a.id for a in db.query(Artwork.id).all()]
            }

            deleted_count = asyncio.run(
                image_service.cleanup_orphaned_images(active_entity_ids)
            )

            logger.info(
                "Orphaned images cleanup completed",
                deleted_count=deleted_count
            )

            return {
                "status": "completed",
                "deleted_count": deleted_count
            }

    except Exception as e:
        logger.error(
            "Orphaned images cleanup failed",
            error=str(e)
        )
        raise


def _get_content_by_id(db: Session, content_type: str, content_id: int):
    """Get content from database by type and ID"""
    model_map = {
        "series": Series,
        "movie": Movie,
        "episode": Episode,
        "season": Season,
        "person": Person
    }

    model = model_map.get(content_type)
    if model:
        return db.query(model).filter(model.id == content_id).first()
    return None


def _get_content_image_fields(content_type: str) -> List[str]:
    """Get image field names for content type"""
    field_map = {
        "series": ["image", "banner", "poster", "fanart"],
        "movie": ["image", "poster", "fanart", "banner"],
        "episode": ["image", "thumbnail"],
        "season": ["image", "poster"],
        "person": ["image"]
    }
    return field_map.get(content_type, [])


def _get_content_without_local_images(
    db: Session,
    content_type: str,
    limit: int
):
    """Get content items that don't have local images"""
    model_map = {
        "series": Series,
        "movie": Movie,
        "episode": Episode,
        "season": Season,
        "person": Person
    }

    model = model_map.get(content_type)
    if not model:
        return []

    # Query for items with image URLs but no local processing
    # This is a simplified query - in practice you'd check for local_image_url field
    query = db.query(model)

    # Filter by items that have source images
    if content_type in ["series", "movie", "person"]:
        query = query.filter(model.image.isnot(None))
    elif content_type == "episode":
        query = query.filter(
            db_or(
                model.image.isnot(None),
                model.thumbnail.isnot(None)
            )
        )
    elif content_type == "season":
        query = query.filter(
            db_or(
                model.image.isnot(None),
                model.poster.isnot(None)
            )
        )

    return query.limit(limit).all()


async def _sync_content_images_async(image_downloads, content_type, content_id, content):
    """Download and store content images in a single async context."""
    from app.services.image_service import ImageService

    synced_images = {}

    # Create a fresh ImageService instance for this task
    async with ImageService() as image_service:
        for field_name, image_url in image_downloads:
            try:
                # Download and store the image
                stored_key = await image_service.download_and_store_image(
                    image_url,
                    content_type,
                    content_id,
                    field_name
                )
                if stored_key:
                    synced_images[field_name] = stored_key
                    # Update the local image URL in the database
                    setattr(content, f"local_{field_name}_url",
                            image_service.get_local_image_url(
                                content_type, content_id, field_name
                            ))
                logger.info(
                    "Image synced",
                    field=field_name,
                    key=stored_key
                )
            except Exception as e:
                logger.error(
                    "Failed to sync image",
                    field=field_name,
                    error=str(e)
                )

    return synced_images


async def _sync_artwork_images_async(artwork_downloads):
    """Download and store artwork images in a single async context."""
    from app.services.image_service import ImageService

    artwork_count = 0

    # Create a fresh ImageService instance for this task
    async with ImageService() as image_service:
        for image_type, image_url, artwork in artwork_downloads:
            try:
                stored_key = await image_service.download_and_store_image(
                    image_url,
                    "artwork",
                    artwork.id,
                    image_type
                )
                if stored_key:
                    if image_type == "image":
                        artwork.local_image_url = image_service.get_local_image_url(
                            "artwork", artwork.id, "image"
                        )
                        artwork.storage_path = stored_key
                        from datetime import datetime
                        artwork.processed_at = datetime.utcnow()
                        artwork_count += 1
                    elif image_type == "thumbnail":
                        artwork.local_thumbnail_url = image_service.get_local_image_url(
                            "artwork", artwork.id, "thumbnail"
                        )
            except Exception as e:
                logger.error(
                    "Failed to sync artwork",
                    artwork_id=artwork.id,
                    image_type=image_type,
                    error=str(e)
                )

    return artwork_count
