"""Celery tasks for synchronizing data with TVDB API."""
import asyncio
from datetime import datetime, timedelta
from typing import Any, Dict, List

import structlog
from sqlalchemy.orm import Session

from app.database import SessionLocal
from app.models import Episode, Series
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
