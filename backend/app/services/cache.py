from app.core.database import redis_client

class RedisCacheService:
    CACHE_TTL = 3600

    @staticmethod
    async def get_cache(key):
        return await redis_client.get(key)

    @staticmethod
    async def set_cache(key, value):
        await redis_client.set(key, value, ex=RedisCacheService.CACHE_TTL)
