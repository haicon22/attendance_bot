# attendance_bot/bot/middlewares/rate_limit_middleware.py
import logging
from typing import Any, Awaitable, Callable, Dict

from aiogram import BaseMiddleware
from aiogram.types import Message

from core.redis_client import get_redis

logger = logging.getLogger(__name__)


class RateLimitMiddleware(BaseMiddleware):
    def __init__(self, limit: int = 30, window: int = 60):
        self.limit = limit
        self.window = window
        super().__init__()

    async def __call__(
        self,
        handler: Callable[[Message, Dict[str, Any]], Awaitable[Any]],
        event: Message,
        data: Dict[str, Any]
    ) -> Any:
        user_id = event.from_user.id
        key = f"rate_limit:{user_id}"

        redis = await get_redis()
        allowed = await redis.rate_limit(key, self.limit, self.window)

        if not allowed:
            await event.answer(
                "⏳ 请求过于频繁，请稍后再试。"
            )
            return None

        return await handler(event, data)
