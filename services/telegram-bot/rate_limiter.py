import logging
from typing import Optional
from datetime import datetime

import redis.asyncio as redis

from config import config

logger = logging.getLogger(__name__)


class RateLimiter:
    def __init__(self):
        self.redis: Optional[redis.Redis] = None
        self.prefix = "d1337:telegram:"

    async def connect(self):
        try:
            self.redis = redis.from_url(
                config.REDIS_URL,
                encoding="utf-8",
                decode_responses=True
            )
            await self.redis.ping()
            logger.info("Redis connection established")
        except Exception as e:
            logger.error(f"Failed to connect to Redis: {e}")
            raise

    async def close(self):
        if self.redis:
            await self.redis.close()
            logger.info("Redis connection closed")

    def _get_daily_key(self, user_id: int) -> str:
        today = datetime.utcnow().strftime("%Y-%m-%d")
        return f"{self.prefix}daily:{user_id}:{today}"

    async def get_query_count(self, user_id: int) -> int:
        key = self._get_daily_key(user_id)
        count = await self.redis.get(key)
        return int(count) if count else 0

    async def increment_query_count(self, user_id: int) -> int:
        key = self._get_daily_key(user_id)
        count = await self.redis.incr(key)
        if count == 1:
            await self.redis.expire(key, config.RATE_LIMIT_WINDOW)
        return count

    async def can_query(self, user_id: int, is_premium: bool) -> tuple[bool, int]:
        if is_premium:
            return True, -1
        
        current_count = await self.get_query_count(user_id)
        remaining = config.FREE_QUERY_LIMIT - current_count
        
        if remaining <= 0:
            return False, 0
        
        return True, remaining

    async def get_remaining_queries(self, user_id: int, is_premium: bool) -> int:
        if is_premium:
            return -1
        
        current_count = await self.get_query_count(user_id)
        return max(0, config.FREE_QUERY_LIMIT - current_count)

    async def reset_user_limit(self, user_id: int) -> bool:
        key = self._get_daily_key(user_id)
        await self.redis.delete(key)
        return True

    async def get_ttl(self, user_id: int) -> int:
        key = self._get_daily_key(user_id)
        ttl = await self.redis.ttl(key)
        return max(0, ttl)


rate_limiter = RateLimiter()
