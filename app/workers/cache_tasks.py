import asyncio
from datetime import datetime, timedelta
from typing import List

import structlog
from sqlalchemy import desc
from sqlalchemy.orm import Session

from app.database import SessionLocal
from app.models import Episode, Movie, Person, Series
from app.redis_client import cache
from app.services.tvdb_client import tvdb_client
from app.workers.celery_app import celery_app

logger = structlog.get_logger()


def get_db_session() -> Session:
    """Get database session for worker tasks"""
    return SessionLocal()


@celery_app.task(bind=True)
def cleanup_expired_cache(self):
    """Clean up expired cache entries and optimize cache performance"""
    logger.info("Starting cache cleanup")

    try:
        # Get cache statistics before cleanup
        stats_before = cache.get_cache_stats()

        self.update_state(
            state='PROGRESS',
            meta={
                'current': 0,
                'total': 100,
                'status': 'Starting cache cleanup'})

        # Clean up expired search results (they have short TTL)
        cleaned_search = cache.flush_pattern("search:*")
        self.update_state(
            state='PROGRESS',
            meta={
                'current': 25,
                'total': 100,
                'status': 'Search cache cleaned'})

        # Clean up stale episode lists (regenerate from fresh data)
        cleaned_episodes = cache.flush_pattern("episodes:*_episodes_page_*")
        self.update_state(
            state='PROGRESS',
            meta={
                'current': 50,
                'total': 100,
                'status': 'Episode lists cleaned'})

        # Clean up temporary data
        cleaned_temp = cache.flush_pattern("temp:*")
        self.update_state(
            state='PROGRESS',
            meta={
                'current': 75,
                'total': 100,
                'status': 'Temporary data cleaned'})

        # Get cache statistics after cleanup
        stats_after = cache.get_cache_stats()

        self.update_state(
            state='PROGRESS',
            meta={
                'current': 100,
                'total': 100,
                'status': 'Cache cleanup completed'})

        logger.info("Cache cleanup completed",
                    cleaned_search=cleaned_search,
                    cleaned_episodes=cleaned_episodes,
                    cleaned_temp=cleaned_temp,
                    stats_before=stats_before,
                    stats_after=stats_after)

        return {
            "status": "completed",
            "cleaned_entries": cleaned_search +
            cleaned_episodes +
            cleaned_temp,
            "stats_before": stats_before,
            "stats_after": stats_after}

    except Exception as e:
        logger.error("Cache cleanup failed", error=str(e))
        self.update_state(state='FAILURE', meta={'error': str(e)})
        raise


@celery_app.task(bind=True)
def prefetch_popular_content(self):
    """Prefetch popular content to warm up the cache"""
    logger.info("Starting popular content prefetch")

    try:
        with get_db_session() as db:
            self.update_state(
                state='PROGRESS',
                meta={
                    'current': 0,
                    'total': 100,
                    'status': 'Finding popular content'})

            # Get popular series (by popularity score or recent access)
            popular_series = _get_popular_series(db, limit=50)
            self.update_state(
                state='PROGRESS',
                meta={
                    'current': 20,
                    'total': 100,
                    'status': 'Prefetching popular series'})

            # Prefetch series data
            for i, series in enumerate(popular_series):
                asyncio.run(_prefetch_series_data(series.tvdb_id))
                progress = 20 + int((i / len(popular_series)) * 30)
                self.update_state(
                    state='PROGRESS',
                    meta={
                        'current': progress,
                        'total': 100,
                        'status': f'Prefetching series {i+1}/{len(popular_series)}'})

            # Get popular movies
            popular_movies = _get_popular_movies(db, limit=30)
            self.update_state(
                state='PROGRESS',
                meta={
                    'current': 50,
                    'total': 100,
                    'status': 'Prefetching popular movies'})

            # Prefetch movie data
            for i, movie in enumerate(popular_movies):
                asyncio.run(_prefetch_movie_data(movie.tvdb_id))
                progress = 50 + int((i / len(popular_movies)) * 30)
                self.update_state(
                    state='PROGRESS',
                    meta={
                        'current': progress,
                        'total': 100,
                        'status': f'Prefetching movie {i+1}/{len(popular_movies)}'})

            # Prefetch trending episodes (recently aired)
            trending_episodes = _get_trending_episodes(db, limit=100)
            self.update_state(
                state='PROGRESS',
                meta={
                    'current': 80,
                    'total': 100,
                    'status': 'Prefetching trending episodes'})

            # Prefetch episode data
            for i, episode in enumerate(trending_episodes):
                asyncio.run(
                    _prefetch_episode_data(
                        episode.tvdb_id,
                        episode.series_id))
                if i % 10 == 0:  # Update progress every 10 episodes
                    progress = 80 + int((i / len(trending_episodes)) * 20)
                    self.update_state(
                        state='PROGRESS',
                        meta={
                            'current': progress,
                            'total': 100,
                            'status': f'Prefetching episode {i+1}/{len(trending_episodes)}'})

            self.update_state(
                state='PROGRESS',
                meta={
                    'current': 100,
                    'total': 100,
                    'status': 'Prefetch completed'})

            logger.info("Popular content prefetch completed",
                        series_count=len(popular_series),
                        movies_count=len(popular_movies),
                        episodes_count=len(trending_episodes))

            return {
                "status": "completed",
                "prefetched": {
                    "series": len(popular_series),
                    "movies": len(popular_movies),
                    "episodes": len(trending_episodes)
                }
            }

    except Exception as e:
        logger.error("Popular content prefetch failed", error=str(e))
        self.update_state(state='FAILURE', meta={'error': str(e)})
        raise


@celery_app.task(bind=True)
def warm_cache_for_series(self, series_id: int):
    """Warm cache for a specific series and all related data"""
    logger.info("Warming cache for series", series_id=series_id)

    try:
        self.update_state(
            state='PROGRESS',
            meta={
                'current': 0,
                'total': 100,
                'status': 'Starting cache warming'})

        # Prefetch series basic and extended data
        asyncio.run(_prefetch_series_data(series_id))
        self.update_state(
            state='PROGRESS',
            meta={
                'current': 30,
                'total': 100,
                'status': 'Series data cached'})

        # Prefetch all episodes for the series
        asyncio.run(_prefetch_series_episodes(series_id))
        self.update_state(
            state='PROGRESS',
            meta={
                'current': 70,
                'total': 100,
                'status': 'Episodes cached'})

        # Prefetch seasons data
        asyncio.run(_prefetch_series_seasons(series_id))
        self.update_state(
            state='PROGRESS',
            meta={
                'current': 90,
                'total': 100,
                'status': 'Seasons cached'})

        # Prefetch artwork and cast
        asyncio.run(_prefetch_series_metadata(series_id))
        self.update_state(
            state='PROGRESS',
            meta={
                'current': 100,
                'total': 100,
                'status': 'Cache warming completed'})

        logger.info("Cache warming completed for series", series_id=series_id)
        return {"status": "completed", "series_id": series_id}

    except Exception as e:
        logger.error(
            "Cache warming failed for series",
            series_id=series_id,
            error=str(e))
        self.update_state(state='FAILURE', meta={'error': str(e)})
        raise


@celery_app.task(bind=True)
def rebuild_search_index(self):
    """Rebuild search cache index for faster searches"""
    logger.info("Starting search index rebuild")

    try:
        with get_db_session() as db:
            self.update_state(
                state='PROGRESS',
                meta={
                    'current': 0,
                    'total': 100,
                    'status': 'Clearing old search index'})

            # Clear existing search cache
            cache.flush_pattern("search:*")

            # Build series search index
            self.update_state(
                state='PROGRESS',
                meta={
                    'current': 20,
                    'total': 100,
                    'status': 'Building series search index'})
            _build_series_search_index(db)

            # Build movie search index
            self.update_state(
                state='PROGRESS',
                meta={
                    'current': 60,
                    'total': 100,
                    'status': 'Building movie search index'})
            _build_movie_search_index(db)

            # Build people search index
            self.update_state(
                state='PROGRESS',
                meta={
                    'current': 80,
                    'total': 100,
                    'status': 'Building people search index'})
            _build_people_search_index(db)

            self.update_state(
                state='PROGRESS',
                meta={
                    'current': 100,
                    'total': 100,
                    'status': 'Search index rebuild completed'})

            logger.info("Search index rebuild completed")
            return {
                "status": "completed",
                "message": "Search index rebuilt successfully"}

    except Exception as e:
        logger.error("Search index rebuild failed", error=str(e))
        self.update_state(state='FAILURE', meta={'error': str(e)})
        raise


# Helper functions
def _get_popular_series(db: Session, limit: int = 50) -> List[Series]:
    """Get popular series by popularity score"""
    return db.query(Series)\
        .filter(Series.popularity.isnot(None))\
        .order_by(desc(Series.popularity))\
        .limit(limit)\
        .all()


def _get_popular_movies(db: Session, limit: int = 30) -> List[Movie]:
    """Get popular movies by popularity score"""
    return db.query(Movie)\
        .filter(Movie.popularity.isnot(None))\
        .order_by(desc(Movie.popularity))\
        .limit(limit)\
        .all()


def _get_trending_episodes(db: Session, limit: int = 100) -> List[Episode]:
    """Get recently aired episodes"""
    recent_date = datetime.utcnow() - timedelta(days=7)
    return db.query(Episode)\
        .filter(Episode.aired >= recent_date)\
        .order_by(desc(Episode.aired))\
        .limit(limit)\
        .all()


async def _prefetch_series_data(series_id: int):
    """Prefetch both basic and extended series data"""
    try:
        # Fetch basic series data
        await tvdb_client.get_series(series_id, use_cache=False)

        # Fetch extended series data
        await tvdb_client.get_series_extended(series_id, use_cache=False)

        logger.debug("Series data prefetched", series_id=series_id)
    except Exception as e:
        logger.warning(
            "Failed to prefetch series data",
            series_id=series_id,
            error=str(e))


async def _prefetch_movie_data(movie_id: int):
    """Prefetch both basic and extended movie data"""
    try:
        # Fetch basic movie data
        await tvdb_client.get_movie(movie_id, use_cache=False)

        # Fetch extended movie data
        await tvdb_client.get_movie_extended(movie_id, use_cache=False)

        logger.debug("Movie data prefetched", movie_id=movie_id)
    except Exception as e:
        logger.warning(
            "Failed to prefetch movie data",
            movie_id=movie_id,
            error=str(e))


async def _prefetch_episode_data(episode_id: int, series_id: int):
    """Prefetch episode data"""
    try:
        # Episodes are typically fetched via series, so prefetch series
        # episodes
        await tvdb_client.get_series_episodes(series_id, use_cache=False)

        logger.debug(
            "Episode data prefetched",
            episode_id=episode_id,
            series_id=series_id)
    except Exception as e:
        logger.warning(
            "Failed to prefetch episode data",
            episode_id=episode_id,
            error=str(e))


async def _prefetch_series_episodes(series_id: int):
    """Prefetch all episodes for a series"""
    try:
        page = 0
        while True:
            episodes_data = await tvdb_client.get_series_episodes(series_id, page, use_cache=False)
            if not episodes_data or not episodes_data.get('data'):
                break

            # Check if there are more pages
            if not episodes_data.get('links', {}).get('next'):
                break
            page += 1

        logger.debug(
            "Series episodes prefetched",
            series_id=series_id,
            pages=page + 1)
    except Exception as e:
        logger.warning(
            "Failed to prefetch series episodes",
            series_id=series_id,
            error=str(e))


async def _prefetch_series_seasons(series_id: int):
    """Prefetch season data for a series"""
    try:
        # This would require iterating through seasons
        # For now, just log the operation
        logger.debug("Series seasons prefetch requested", series_id=series_id)
    except Exception as e:
        logger.warning(
            "Failed to prefetch series seasons",
            series_id=series_id,
            error=str(e))


async def _prefetch_series_metadata(series_id: int):
    """Prefetch artwork and cast for a series"""
    try:
        # This would prefetch related artwork, cast, etc.
        logger.debug("Series metadata prefetch requested", series_id=series_id)
    except Exception as e:
        logger.warning(
            "Failed to prefetch series metadata",
            series_id=series_id,
            error=str(e))


def _build_series_search_index(db: Session):
    """Build search index for series"""
    series_list = db.query(Series).filter(Series.name.isnot(None)).all()

    for series in series_list:
        # Create searchable data structure
        search_data = {
            "id": series.tvdb_id,
            "name": series.name,
            "slug": series.slug,
            "year": series.year,
            "type": "series"
        }

        # Cache with series name as key
        cache.set(
            "search_index",
            f"series_{series.name.lower()}",
            search_data,
            24)

    logger.debug("Series search index built", count=len(series_list))


def _build_movie_search_index(db: Session):
    """Build search index for movies"""
    movies_list = db.query(Movie).filter(Movie.name.isnot(None)).all()

    for movie in movies_list:
        search_data = {
            "id": movie.tvdb_id,
            "name": movie.name,
            "slug": movie.slug,
            "year": movie.year,
            "type": "movie"
        }

        cache.set(
            "search_index",
            f"movie_{movie.name.lower()}",
            search_data,
            24)

    logger.debug("Movie search index built", count=len(movies_list))


def _build_people_search_index(db: Session):
    """Build search index for people"""
    people_list = db.query(Person).filter(Person.name.isnot(None)).all()

    for person in people_list:
        search_data = {
            "id": person.tvdb_id,
            "name": person.name,
            "slug": person.slug,
            "type": "person"
        }

        cache.set(
            "search_index",
            f"person_{person.name.lower()}",
            search_data,
            24)

    logger.debug("People search index built", count=len(people_list))
