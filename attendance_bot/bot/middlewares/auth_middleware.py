# attendance_bot/bot/middlewares/auth_middleware.py
import logging
from typing import Any, Awaitable, Callable, Dict

from aiogram import BaseMiddleware
from aiogram.types import Message, CallbackQuery
from sqlalchemy import select

from core.database import AsyncSessionLocal
from models import User, UserTelegramBinding

logger = logging.getLogger(__name__)


class AuthMiddleware(BaseMiddleware):
    async def __call__(
        self,
        handler: Callable[[Message, Dict[str, Any]], Awaitable[Any]],
        event: Message,
        data: Dict[str, Any]
    ) -> Any:
        # Skip auth for certain commands
        if event.text and event.text.startswith(("/start", "/help", "/bind")):
            return await handler(event, data)

        # Check if user is bound
        telegram_id = event.from_user.id

        async with AsyncSessionLocal() as session:
            result = await session.execute(
                select(User)
                .join(UserTelegramBinding)
                .where(
                    UserTelegramBinding.telegram_id == telegram_id,
                    UserTelegramBinding.is_active == True
                )
            )
            user = result.scalar_one_or_none()

            if user:
                data["user"] = user
            else:
                await event.answer("❌ 请先使用 /start 绑定您的账号。")
                return None

        return await handler(event, data)
