"""Typed settings loaded from the environment (.env).

Fails loudly at startup if a required secret is missing, so a misconfigured
deployment never reaches the first request.
"""
from functools import lru_cache

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    openai_api_key: str = Field(..., min_length=1, description="OpenAI API key")
    openai_model: str = "gpt-4o-mini"
    max_upload_mb: int = 20
    ocr_dpi: int = 200
    ocr_min_chars_per_page: int = 50  # below this, a page is treated as scanned and OCR'd
    max_contract_chars: int = 60_000  # keeps token cost per scan predictable

    @property
    def max_upload_bytes(self) -> int:
        return self.max_upload_mb * 1024 * 1024


@lru_cache
def get_settings() -> Settings:
    return Settings()  # raises ValidationError if OPENAI_API_KEY is missing
