"""Typed environment-driven settings for the API + scripts."""

from __future__ import annotations

from functools import lru_cache

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    database_url: str = Field(..., alias="DATABASE_URL")
    dashscope_api_key: str | None = Field(None, alias="DASHSCOPE_API_KEY")
    anthropic_api_key: str | None = Field(None, alias="ANTHROPIC_API_KEY")
    api_football_key: str | None = Field(None, alias="API_FOOTBALL_KEY")
    the_odds_api_key: str | None = Field(None, alias="THE_ODDS_API_KEY")

    model_version: str = Field("poisson-dc-v3", alias="MODEL_VERSION")
    # v2 was last_n=12, rho=-0.15 (log-loss 0.9937 / 1.0523).
    # v3 adds temperature scaling fit against the reliability curve 2026-04-18:
    # 2024-25 optimum T=1.25, 2025-26 optimum T=1.45 — T=1.35 splits the diff.
    # Reduces overconfidence in the 40-70% bins (biggest leak in calibration).
    default_rho: float = Field(-0.15, alias="DEFAULT_RHO")
    default_last_n: int = Field(12, alias="DEFAULT_LAST_N")
    default_temperature: float = Field(1.35, alias="DEFAULT_TEMPERATURE")


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    return Settings()  # type: ignore[call-arg]
