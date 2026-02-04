"""
Configuration settings for the Honeypot API.
"""

from pydantic_settings import BaseSettings, SettingsConfigDict
from functools import lru_cache
from typing import Optional
from pathlib import Path

# Get the directory where .env is located (ScamNest root)
BASE_DIR = Path(__file__).resolve().parent.parent


class Settings(BaseSettings):
    """Application settings loaded from environment variables."""
    
    api_key: str = "ABC-123"
    openai_api_key: Optional[str] = None
    hf_token: Optional[str] = None
    openai_model: str = "gpt-4o-mini"
    guvi_callback_url: str = "https://hackathon.guvi.in/api/updateHoneyPotFinalResult"
    callback_timeout: int = 10
    min_messages_for_callback: int = 3
    scam_confidence_threshold: float = 0.7
    
    model_config = SettingsConfigDict(
        env_file=BASE_DIR / ".env",
        env_file_encoding="utf-8",
        extra="ignore"
    )


@lru_cache()
def get_settings() -> Settings:
    return Settings()
