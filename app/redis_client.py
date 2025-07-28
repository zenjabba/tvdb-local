import json
from datetime import timedelta
from typing import Any, Optional, Union

import redis
import structlog

from app.config import settings

logger = structlog.get_logger()

# Redis connection
redis_client = redis.from_url(settings.redis_url, decode_responses=True)


class CacheManager:
    """Redis cache manager for TVDB proxy"""

    def __init__(self):
        self.client = redis_client

    def _make_key(self, prefix: str, identifier: Union[str, int]) -> str:
        """Create a standardized cache key"""
        return f"tvdb:{prefix}:{identifier}"

    def get(self, prefix: str, identifier: Union[str, int]) -> Optional[Any]:
        """Get cached data"""
        key = self._make_key(prefix, identifier)
        try:
            data = self.client.get(key)
            if data:
                return json.loads(data)
            return None
        except Exception as e:
            logger.error("Cache get error", key=key, error=str(e))
            return None

    def set(self,
            prefix: str,
            identifier: Union[str,
                              int],
            data: Any,
            ttl_hours: Optional[int] = None) -> bool:
        """Set cached data with optional TTL"""
        key = self._make_key(prefix, identifier)
        try:
            serialized = json.dumps(data, default=str)
            if ttl_hours:
                return self.client.setex(
                    key, timedelta(
                        hours=ttl_hours), serialized)
            else:
                return self.client.set(key, serialized)
        except Exception as e:
            logger.error("Cache set error", key=key, error=str(e))
            return False

    def delete(self, prefix: str, identifier: Union[str, int]) -> bool:
        """Delete cached data"""
        key = self._make_key(prefix, identifier)
        try:
            return self.client.delete(key) > 0
        except Exception as e:
            logger.error("Cache delete error", key=key, error=str(e))
            return False

    def exists(self, prefix: str, identifier: Union[str, int]) -> bool:
        """Check if key exists in cache"""
        key = self._make_key(prefix, identifier)
        try:
            return self.client.exists(key) > 0
        except Exception as e:
            logger.error("Cache exists error", key=key, error=str(e))
            return False

    def get_ttl(self, prefix: str, identifier: Union[str, int]) -> int:
        """Get remaining TTL for a key"""
        key = self._make_key(prefix, identifier)
        try:
            return self.client.ttl(key)
        except Exception as e:
            logger.error("Cache TTL error", key=key, error=str(e))
            return -1

    def flush_pattern(self, pattern: str) -> int:
        """Delete keys matching a pattern"""
        try:
            keys = self.client.keys(f"tvdb:{pattern}")
            if keys:
                return self.client.delete(*keys)
            return 0
        except Exception as e:
            logger.error(
                "Cache flush pattern error",
                pattern=pattern,
                error=str(e))
            return 0

    def get_cache_stats(self) -> dict:
        """Get basic cache statistics"""
        try:
            info = self.client.info()
            return {
                "connected_clients": info.get("connected_clients", 0),
                "used_memory": info.get("used_memory_human", "0B"),
                "total_keys": self.client.dbsize(),
                "hit_rate": self._calculate_hit_rate(info),
            }
        except Exception as e:
            logger.error("Cache stats error", error=str(e))
            return {}

    def _calculate_hit_rate(self, info: dict) -> float:
        """Calculate cache hit rate"""
        hits = info.get("keyspace_hits", 0)
        misses = info.get("keyspace_misses", 0)
        total = hits + misses
        return (hits / total * 100) if total > 0 else 0.0


# Global cache instance
cache = CacheManager()


# Cache helper functions for specific TVDB entities
class TVDBCache:
    """Specific caching functions for TVDB entities"""

    @staticmethod
    def get_series(series_id: int) -> Optional[dict]:
        """Get cached series data"""
        return cache.get("series", series_id)

    @staticmethod
    def set_series(series_id: int, data: dict, extended: bool = False) -> bool:
        """Cache series data with appropriate TTL"""
        ttl = settings.cache_ttl_dynamic_hours if extended else settings.cache_ttl_static_hours
        return cache.set("series", series_id, data, ttl)

    @staticmethod
    def get_episode(episode_id: int) -> Optional[dict]:
        """Get cached episode data"""
        return cache.get("episode", episode_id)

    @staticmethod
    def set_episode(episode_id: int, data: dict) -> bool:
        """Cache episode data"""
        return cache.set(
            "episode",
            episode_id,
            data,
            settings.cache_ttl_dynamic_hours)

    @staticmethod
    def get_movie(movie_id: int) -> Optional[dict]:
        """Get cached movie data"""
        return cache.get("movie", movie_id)

    @staticmethod
    def set_movie(movie_id: int, data: dict) -> bool:
        """Cache movie data"""
        return cache.set(
            "movie",
            movie_id,
            data,
            settings.cache_ttl_dynamic_hours)

    @staticmethod
    def get_person(person_id: int) -> Optional[dict]:
        """Get cached person data"""
        return cache.get("person", person_id)

    @staticmethod
    def set_person(person_id: int, data: dict) -> bool:
        """Cache person data"""
        return cache.set(
            "person",
            person_id,
            data,
            settings.cache_ttl_dynamic_hours)

    @staticmethod
    def get_static_data(data_type: str) -> Optional[dict]:
        """Get cached static data (genres, languages, etc.)"""
        return cache.get("static", data_type)

    @staticmethod
    def set_static_data(data_type: str, data: dict) -> bool:
        """Cache static data with long TTL"""
        return cache.set(
            "static",
            data_type,
            data,
            settings.cache_ttl_static_hours)

    @staticmethod
    def invalidate_series(series_id: int):
        """Invalidate all related series cache"""
        cache.delete("series", series_id)
        cache.flush_pattern(f"series:{series_id}:*")

    @staticmethod
    def get_search_results(
            query: str,
            result_type: str = "series") -> Optional[dict]:
        """Get cached search results"""
        search_key = f"search:{result_type}:{query}"
        return cache.get("search", search_key)

    @staticmethod
    def set_search_results(
            query: str,
            results: dict,
            result_type: str = "series") -> bool:
        """Cache search results with short TTL"""
        search_key = f"search:{result_type}:{query}"
        return cache.set("search", search_key, results, 1)  # 1 hour TTL
