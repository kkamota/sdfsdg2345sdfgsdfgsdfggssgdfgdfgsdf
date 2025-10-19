from dataclasses import dataclass
from typing import Sequence
import os


@dataclass(slots=True)
class Settings:
    bot_token: str
    channel_username: str
    admin_ids: Sequence[int]
    flyer_api_key: str
    min_withdrawal: int = 15
    start_bonus: int = 3
    referral_bonus: int = 3
    daily_bonus: int = 1


def load_settings() -> Settings:
    token = os.getenv("BOT_TOKEN", "8413197852:AAGnWgpALWsFVuXdAGaa9zi5XC3BRK-Ykuw")
    channel = os.getenv("CHANNEL_USERNAME", "@giftsauctionsru")
    raw_admins = os.getenv("ADMIN_IDS", "5838432507")
    admin_ids = tuple(
        int(admin_id.strip())
        for admin_id in raw_admins.split(",")
        if admin_id.strip().isdigit()
    )
    flyer_api_key = os.getenv(
        "FLYER_API_KEY",
        "FL-nDnAdz-lUODDB-jYqtsJ-neLImC",
    )
    return Settings(
        bot_token=token,
        channel_username=channel,
        admin_ids=admin_ids or (123456789,),
        flyer_api_key=flyer_api_key,
    )
