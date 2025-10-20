from __future__ import annotations

import asyncio
import logging

from aiogram import Bot

from .config import Settings
from .database import db
from .handlers import _verify_and_activate_subscription

logger = logging.getLogger(__name__)


async def run_referral_audit(
    bot: Bot,
    settings: Settings,
    *,
    interval_seconds: int = 3600,
) -> None:
    """Periodically re-check referral subscriptions to keep the leaderboard fresh."""

    try:
        while True:
            try:
                users = await db.list_all_users()
                for user in users:
                    if not user.referred_by or not user.is_subscribed:
                        continue
                    try:
                        await _verify_and_activate_subscription(bot, settings, user)
                    except asyncio.CancelledError:
                        raise
                    except Exception:
                        logger.exception(
                            "Failed to audit subscription state for user %s", user.telegram_id
                        )
                    await asyncio.sleep(0)
            except asyncio.CancelledError:
                raise
            except Exception:
                logger.exception("Unexpected error during referral audit iteration")

            try:
                await asyncio.sleep(interval_seconds)
            except asyncio.CancelledError:
                raise
    except asyncio.CancelledError:
        logger.info("Referral audit task cancelled")
        raise
