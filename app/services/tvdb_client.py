from typing import Any, Dict, List, Optional

import structlog
import tvdb_v4_official
from tenacity import retry, stop_after_attempt, wait_exponential

from app.config import settings
from app.redis_client import TVDBCache, cache

logger = structlog.get_logger()


class TVDBClient:
    """Enhanced TVDB client with caching and error handling"""

    def __init__(self):
        self.client = None
        self.cache = TVDBCache()
        self._authenticated = False

    def _get_client(self) -> tvdb_v4_official.TVDB:
        """Get authenticated TVDB client"""
        if not self.client or not self._authenticated:
            try:
                self.client = tvdb_v4_official.TVDB(
                    settings.tvdb_api_key,
                    pin=settings.tvdb_pin
                )
                self._authenticated = True
                logger.info("TVDB client authenticated successfully")
            except Exception as e:
                logger.error(
                    "Failed to authenticate TVDB client",
                    error=str(e))
                raise
        return self.client

    @retry(stop=stop_after_attempt(3),
           wait=wait_exponential(multiplier=1, min=4, max=10))
    async def get_series(self, series_id: int,
                         use_cache: bool = True) -> Optional[Dict[str, Any]]:
        """Get series by ID with caching"""
        if use_cache:
            cached = self.cache.get_series(series_id)
            if cached:
                logger.debug("Series cache hit", series_id=series_id)
                return cached

        try:
            client = self._get_client()
            series_data = client.get_series(series_id)

            if series_data:
                self.cache.set_series(series_id, series_data)
                logger.debug("Series fetched from API", series_id=series_id)
                return series_data

        except Exception as e:
            logger.error(
                "Failed to fetch series",
                series_id=series_id,
                error=str(e))
            # Return cached data even if stale in case of API error
            cached = self.cache.get_series(series_id)
            if cached:
                logger.warning(
                    "Returning stale cached series data",
                    series_id=series_id)
                return cached

        return None

    @retry(stop=stop_after_attempt(3),
           wait=wait_exponential(multiplier=1, min=4, max=10))
    async def get_series_extended(
            self, series_id: int, use_cache: bool = True) -> Optional[Dict[str, Any]]:
        """Get extended series information"""
        cache_key = f"{series_id}_extended"

        if use_cache:
            cached = self.cache.get_series(cache_key)
            if cached:
                logger.debug("Extended series cache hit", series_id=series_id)
                return cached

        try:
            client = self._get_client()
            series_data = client.get_series_extended(series_id)

            if series_data:
                self.cache.set_series(cache_key, series_data, extended=True)
                logger.debug(
                    "Extended series fetched from API",
                    series_id=series_id)
                return series_data

        except Exception as e:
            logger.error(
                "Failed to fetch extended series",
                series_id=series_id,
                error=str(e))
            cached = self.cache.get_series(cache_key)
            if cached:
                logger.warning(
                    "Returning stale cached extended series data",
                    series_id=series_id)
                return cached

        return None

    @retry(stop=stop_after_attempt(3),
           wait=wait_exponential(multiplier=1, min=4, max=10))
    async def get_series_episodes(self,
                                  series_id: int,
                                  page: int = 0,
                                  use_cache: bool = True) -> Optional[Dict[str,
                                                                           Any]]:
        """Get episodes for a series with pagination"""
        cache_key = f"{series_id}_episodes_page_{page}"

        if use_cache:
            cached = cache.get("episodes", cache_key)
            if cached:
                logger.debug(
                    "Series episodes cache hit",
                    series_id=series_id,
                    page=page)
                return cached

        try:
            client = self._get_client()
            episodes_data = client.get_series_episodes(series_id, season_type='default', page=page)

            if episodes_data:
                cache.set(
                    "episodes",
                    cache_key,
                    episodes_data,
                    settings.cache_ttl_dynamic_hours)
                logger.debug(
                    "Series episodes fetched from API",
                    series_id=series_id,
                    page=page)
                return episodes_data

        except Exception as e:
            logger.error(
                "Failed to fetch series episodes",
                series_id=series_id,
                page=page,
                error=str(e))
            cached = cache.get("episodes", cache_key)
            if cached:
                logger.warning(
                    "Returning stale cached episodes data",
                    series_id=series_id,
                    page=page)
                return cached

        return None

    @retry(stop=stop_after_attempt(3),
           wait=wait_exponential(multiplier=1, min=4, max=10))
    async def get_episode(self, episode_id: int,
                          use_cache: bool = True) -> Optional[Dict[str, Any]]:
        """Get episode by ID"""
        if use_cache:
            cached = self.cache.get_episode(episode_id)
            if cached:
                logger.debug("Episode cache hit", episode_id=episode_id)
                return cached

        try:
            self._get_client()
            # Note: The Python library doesn't have get_episode method in the provided examples
            # This would need to be implemented or episodes fetched via series
            logger.warning(
                "Direct episode fetch not implemented in library",
                episode_id=episode_id)
            return None

        except Exception as e:
            logger.error(
                "Failed to fetch episode",
                episode_id=episode_id,
                error=str(e))
            cached = self.cache.get_episode(episode_id)
            if cached:
                logger.warning(
                    "Returning stale cached episode data",
                    episode_id=episode_id)
                return cached

        return None

    @retry(stop=stop_after_attempt(3),
           wait=wait_exponential(multiplier=1, min=4, max=10))
    async def get_season_extended(
            self, season_id: int, use_cache: bool = True) -> Optional[Dict[str, Any]]:
        """Get extended season information"""
        if use_cache:
            cached = self.cache.get("season", season_id)
            if cached:
                logger.debug("Season cache hit", season_id=season_id)
                return cached

        try:
            client = self._get_client()
            season_data = client.get_season_extended(season_id)

            if season_data:
                self.cache.set("season", season_id, season_data,
                               settings.cache_ttl_dynamic_hours)
                logger.debug("Season fetched from API", season_id=season_id)
                return season_data

        except Exception as e:
            logger.error(
                "Failed to fetch season",
                season_id=season_id,
                error=str(e))
            cached = self.cache.get("season", season_id)
            if cached:
                logger.warning(
                    "Returning stale cached season data",
                    season_id=season_id)
                return cached

        return None

    @retry(stop=stop_after_attempt(3),
           wait=wait_exponential(multiplier=1, min=4, max=10))
    async def get_movie(self, movie_id: int,
                        use_cache: bool = True) -> Optional[Dict[str, Any]]:
        """Get movie by ID"""
        if use_cache:
            cached = self.cache.get_movie(movie_id)
            if cached:
                logger.debug("Movie cache hit", movie_id=movie_id)
                return cached

        try:
            client = self._get_client()
            movie_data = client.get_movie(movie_id)

            if movie_data:
                self.cache.set_movie(movie_id, movie_data)
                logger.debug("Movie fetched from API", movie_id=movie_id)
                return movie_data

        except Exception as e:
            logger.error(
                "Failed to fetch movie",
                movie_id=movie_id,
                error=str(e))
            cached = self.cache.get_movie(movie_id)
            if cached:
                logger.warning(
                    "Returning stale cached movie data",
                    movie_id=movie_id)
                return cached

        return None

    @retry(stop=stop_after_attempt(3),
           wait=wait_exponential(multiplier=1, min=4, max=10))
    async def get_movie_extended(
            self, movie_id: int, use_cache: bool = True) -> Optional[Dict[str, Any]]:
        """Get extended movie information"""
        cache_key = f"{movie_id}_extended"

        if use_cache:
            cached = self.cache.get_movie(cache_key)
            if cached:
                logger.debug("Extended movie cache hit", movie_id=movie_id)
                return cached

        try:
            client = self._get_client()
            movie_data = client.get_movie_extended(movie_id)

            if movie_data:
                self.cache.set_movie(cache_key, movie_data)
                logger.debug(
                    "Extended movie fetched from API",
                    movie_id=movie_id)
                return movie_data

        except Exception as e:
            logger.error(
                "Failed to fetch extended movie",
                movie_id=movie_id,
                error=str(e))
            cached = self.cache.get_movie(cache_key)
            if cached:
                logger.warning(
                    "Returning stale cached extended movie data",
                    movie_id=movie_id)
                return cached

        return None

    @retry(stop=stop_after_attempt(3),
           wait=wait_exponential(multiplier=1, min=4, max=10))
    async def get_person_extended(
            self, person_id: int, use_cache: bool = True) -> Optional[Dict[str, Any]]:
        """Get extended person information"""
        if use_cache:
            cached = self.cache.get_person(person_id)
            if cached:
                logger.debug("Person cache hit", person_id=person_id)
                return cached

        try:
            client = self._get_client()
            person_data = client.get_person_extended(person_id)

            if person_data:
                self.cache.set_person(person_id, person_data)
                logger.debug("Person fetched from API", person_id=person_id)
                return person_data

        except Exception as e:
            logger.error(
                "Failed to fetch person",
                person_id=person_id,
                error=str(e))
            cached = self.cache.get_person(person_id)
            if cached:
                logger.warning(
                    "Returning stale cached person data",
                    person_id=person_id)
                return cached

        return None

    @retry(stop=stop_after_attempt(3),
           wait=wait_exponential(multiplier=1, min=4, max=10))
    async def get_all_series(
            self, page: int = 0, use_cache: bool = True) -> Optional[Dict[str, Any]]:
        """Get all series with pagination"""
        cache_key = f"all_series_page_{page}"

        if use_cache:
            cached = self.cache.get("series_list", cache_key)
            if cached:
                logger.debug("All series cache hit", page=page)
                return cached

        try:
            client = self._get_client()
            series_data = client.get_all_series(page)

            if series_data:
                # Cache for shorter time since this is a list that changes
                # frequently
                self.cache.set(
                    "series_list",
                    cache_key,
                    series_data,
                    1)  # 1 hour
                logger.debug("All series fetched from API", page=page)
                return series_data

        except Exception as e:
            logger.error("Failed to fetch all series", page=page, error=str(e))
            cached = self.cache.get("series_list", cache_key)
            if cached:
                logger.warning("Returning stale cached series list", page=page)
                return cached

        return None

    async def search_series(
            self, query: str, use_cache: bool = True) -> Optional[List[Dict[str, Any]]]:
        """Search for series (to be implemented with search endpoint)"""
        if use_cache:
            cached = self.cache.get_search_results(query, "series")
            if cached:
                logger.debug("Series search cache hit", query=query)
                return cached

        # Note: Search functionality would need to be implemented
        # This is a placeholder for the search endpoint
        logger.warning("Series search not yet implemented", query=query)
        return None

    async def invalidate_cache(self, entity_type: str, entity_id: int):
        """Invalidate cache for specific entity"""
        if entity_type == "series":
            self.cache.invalidate_series(entity_id)
        elif entity_type == "episode":
            self.cache.delete("episode", entity_id)
        elif entity_type == "movie":
            self.cache.delete("movie", entity_id)
        elif entity_type == "person":
            self.cache.delete("person", entity_id)

        logger.info(
            "Cache invalidated",
            entity_type=entity_type,
            entity_id=entity_id)


# Global client instance
tvdb_client = TVDBClient()
