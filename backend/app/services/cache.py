import logging
from app.core.database import redis_client

logger = logging.getLogger(__name__)

class RedisCacheService:
    CACHE_TTL = 3600

    @staticmethod
    async def get_cache(key):
        try:
            return await redis_client.get(key)
        except Exception as e:
            logger.warning(f"Redis get_cache error for key {key}: {e}")
            return None

    @staticmethod
    async def set_cache(key, value):
        try:
            await redis_client.set(key, value, ex=RedisCacheService.CACHE_TTL)
        except Exception as e:
            logger.warning(f"Redis set_cache error for key {key}: {e}")
