from __future__ import annotations

from functools import lru_cache
from typing import Literal

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict

AuthProviderType = Literal["dev", "clerk"]
BillingProviderType = Literal["mock", "stripe"]


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    anthropic_api_key: str = Field(default="")
    openai_api_key: str = Field(default="")
    anthropic_model: str = Field(default="claude-sonnet-4-6")
    openai_embedding_model: str = Field(default="text-embedding-3-small")
    embedding_dim: int = Field(default=1536)

    auth_provider: AuthProviderType = Field(default="dev")
    jwt_secret: str = Field(default="dev-secret-change-me")
    jwt_ttl_minutes: int = Field(default=1440, ge=5, le=60 * 24 * 30)
    clerk_secret_key: str = Field(default="")
    clerk_public_key: str = Field(default="")

    billing_provider: BillingProviderType = Field(default="mock")
    stripe_secret_key: str = Field(default="")
    stripe_webhook_secret: str = Field(default="")
    stripe_price_pro: str = Field(default="")
    stripe_price_enterprise: str = Field(default="")

    database_url: str = Field(default="postgresql+asyncpg://saas:saas@postgres:5432/saas")

    api_host: str = Field(default="0.0.0.0")
    api_port: int = Field(default=8000)
    cors_origins: str = Field(default="http://localhost:3002")
    log_level: str = Field(default="INFO")

    chunk_size_tokens: int = Field(default=512)
    chunk_overlap_tokens: int = Field(default=64)
    retrieve_top_k: int = Field(default=5)

    plan_free_docs: int = 20
    plan_free_messages: int = 200
    plan_free_cost_budget: float = 5.0
    plan_pro_docs: int = 500
    plan_pro_messages: int = 10000
    plan_pro_cost_budget: float = 50.0
    plan_enterprise_docs: int = 10000
    plan_enterprise_messages: int = 200000
    plan_enterprise_cost_budget: float = 500.0

    @property
    def cors_origin_list(self) -> list[str]:
        return [o.strip() for o in self.cors_origins.split(",") if o.strip()]


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    return Settings()


settings = get_settings()
