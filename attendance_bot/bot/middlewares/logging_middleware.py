# attendance_bot/bot/middlewares/logging_middleware.py
import logging
import time
from typing import Any, Awaitable, Callable, Dict

from aiogram import BaseMiddleware
from aiogram.types import Message, CallbackQuery

logger = logging.getLogger(__name__)


class LoggingMiddleware(BaseMiddleware):
    async def __call__(
        self,
        handler: Callable[[Message, Dict[str, Any]], Awaitable[Any]],
        event: Message,
        data: Dict[str, Any]
    ) -> Any:
        start_time = time.time()

        user_id = event.from_user.id if event.from_user else "unknown"
        username = event.from_user.username if event.from_user else "unknown"

        logger.info(
            f"User {user_id} (@{username}) sent: {event.text[:50] if event.text else 'non-text'}"
        )

        try:
            result = await handler(event, data)
            duration = time.time() - start_time
            logger.info(f"Handler completed in {duration:.3f}s")
            return result
        except Exception as e:
            duration = time.time() - start_time
            logger.error(f"Handler failed after {duration:.3f}s: {str(e)}")
            raise
