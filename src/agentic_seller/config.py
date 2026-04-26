from __future__ import annotations

import os
from dataclasses import dataclass

from dotenv import load_dotenv


@dataclass
class Settings:
    openai_api_key: str | None
    openai_model: str
    default_currency: str
    post_mode: str
    headless: bool
    enable_olx: bool
    enable_facebook: bool
    user_data_dir: str


def _as_bool(name: str, default: bool) -> bool:
    value = os.getenv(name)
    if value is None:
        return default
    return value.strip().lower() in {"1", "true", "yes", "on"}


def load_settings() -> Settings:
    load_dotenv()
    return Settings(
        openai_api_key=os.getenv("OPENAI_API_KEY"),
        openai_model=os.getenv("OPENAI_MODEL", "google/gemma-4-e4b"),
        default_currency=os.getenv("DEFAULT_CURRENCY", "PLN"),
        post_mode=os.getenv("POST_MODE", "dry_run"),
        headless=_as_bool("HEADLESS", False),
        enable_olx=_as_bool("ENABLE_OLX", True),
        enable_facebook=_as_bool("ENABLE_FACEBOOK", True),
        user_data_dir=os.getenv("USER_DATA_DIR", "/app/data/browser_profiles"),
    )
