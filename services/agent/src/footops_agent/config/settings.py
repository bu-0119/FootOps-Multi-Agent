"""Environment-backed service configuration."""

from pathlib import Path
from typing import Literal

from pydantic import Field, SecretStr, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

REPOSITORY_ROOT = Path(__file__).resolve().parents[5]


class Settings(BaseSettings):
    """FootOps agent settings loaded from the repository root ``.env``."""

    model_config = SettingsConfigDict(
        env_file=REPOSITORY_ROOT / ".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    llm_mode: Literal["mock", "deepseek"] = "mock"
    deepseek_api_key: SecretStr | None = None
    deepseek_base_url: str = "https://api.deepseek.com"
    deepseek_model: str = "deepseek-v4-flash"
    footops_agent_max_iters: int = Field(default=3, ge=1, le=8)
    footops_input_max_chars: int = Field(default=4000, ge=1, le=100_000)
    footops_request_timeout_seconds: float = Field(default=30, gt=0, le=300)
    statsbomb_open_data_base_url: str = (
        "https://raw.githubusercontent.com/hudl/open-data/master/data"
    )
    footops_data_cache_dir: Path = REPOSITORY_ROOT / "data/cache/statsbomb-open"
    footops_data_timeout_seconds: float = Field(default=20, gt=0, le=120)
    footops_cors_origins: list[str] = Field(
        default_factory=lambda: [
            "http://127.0.0.1:4173",
            "http://localhost:4173",
        ],
    )

    @field_validator("deepseek_api_key", mode="before")
    @classmethod
    def normalize_empty_key(cls, value: object) -> object:
        """Treat an empty environment variable as an absent credential."""
        if isinstance(value, str) and not value.strip():
            return None
        return value

    @property
    def deepseek_key_configured(self) -> bool:
        """Return whether a non-empty DeepSeek API key is configured."""
        return self.deepseek_api_key is not None
