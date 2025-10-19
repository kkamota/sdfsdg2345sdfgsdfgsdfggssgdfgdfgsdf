import asyncio
import logging
from collections import defaultdict
from contextlib import suppress
from typing import Any, Callable, Dict, Optional

from aiogram import BaseMiddleware
from aiogram.types import CallbackQuery, Message, TelegramObject
from flyerapi import APIError, Flyer

from .database import db


class ThrottlingMiddleware(BaseMiddleware):
    def __init__(self, rate_limit: float = 1.0) -> None:
        super().__init__()
        self.rate_limit = rate_limit
        self._user_timestamps: Dict[int, float] = defaultdict(float)
        self._lock = asyncio.Lock()

    async def __call__(
        self,
        handler: Callable[[TelegramObject, Dict[str, Any]], Any],
        event: TelegramObject,
        data: Dict[str, Any],
    ) -> Any:
        user = data.get("event_from_user")
        if user is None:
            return await handler(event, data)

        async with self._lock:
            now = asyncio.get_running_loop().time()
            last_time = self._user_timestamps[user.id]
            if now - last_time < self.rate_limit:
                return
            self._user_timestamps[user.id] = now
        return await handler(event, data)


class FlyerCheckMiddleware(BaseMiddleware):
    def __init__(self, flyer: Flyer, *, message_template: Optional[Dict[str, str]] = None) -> None:
        super().__init__()
        self.flyer = flyer
        self._message_template = message_template or {
            "text": "Чтобы продолжить работу с ботом, выполните задания ниже.",
        }

    async def __call__(
        self,
        handler: Callable[[TelegramObject, Dict[str, Any]], Any],
        event: TelegramObject,
        data: Dict[str, Any],
    ) -> Any:
        user = data.get("event_from_user")
        if user is None:
            return await handler(event, data)

        language_code = getattr(user, "language_code", None)
        message_payload = dict(self._message_template)

        user_record = await db.get_user(user.id)
        if user_record and user_record.flyer_verified:
            return await handler(event, data)

        was_verified = bool(user_record.flyer_verified) if user_record else False

        try:
            is_allowed = await self.flyer.check(
                user.id,
                language_code=language_code,
                message=message_payload,
            )
        except APIError:
            logging.exception("Flyer API returned an error during check")
            return await handler(event, data)
        except Exception:
            logging.exception("Unexpected error during Flyer verification")
            return await handler(event, data)

        if not is_allowed:
            await self._notify_verification_required(event)
            return None

        if user_record is None:
            await db.create_user(
                user.id,
                0,
                None,
                getattr(user, "username", None),
            )
        await db.set_flyer_verified(user.id, True)

        if not was_verified:
            await self._trigger_start(event, data)

        return await handler(event, data)

    async def _notify_verification_required(self, event: TelegramObject) -> None:
        if isinstance(event, CallbackQuery):
            with suppress(Exception):
                await event.answer()

    async def _trigger_start(
        self, event: TelegramObject, data: Dict[str, Any]
    ) -> None:
        bot = data.get("bot")
        if bot is None:
            return

        chat_id: Optional[int] = None
        if isinstance(event, Message):
            if (event.text or "").startswith("/start"):
                return
            chat_id = event.chat.id
        elif isinstance(event, CallbackQuery) and event.message:
            chat_id = event.message.chat.id

        if chat_id is None:
            return

        with suppress(Exception):
            await bot.send_message(chat_id, "/start")


def mask_sensitive(text: str) -> str:
    if len(text) <= 6:
        return "*" * len(text)
    return text[:3] + "*" * (len(text) - 6) + text[-3:]
