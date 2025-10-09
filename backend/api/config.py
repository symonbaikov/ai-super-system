import functools
from typing import Optional
from pydantic import Field
from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    api_title: str = "Super Parser API"
    api_version: str = "0.1.0"
    api_debug: bool = False
    api_docs_url: Optional[str] = "/docs"

    redis_url: str = Field(..., alias="REDIS_URL")
    database_url: str = Field(..., alias="DATABASE_URL")

    queue_namespace: str = "sp"
    parser_queue_name: str = "parser:run"
    helius_queue_name: str = "helius:events"
    alert_queue_name: str = "alerts:dispatch"
    apify_queue_name: str = "apify:dataset"

    apify_base_url: str = "https://api.apify.com"
    apify_token: Optional[str] = Field(default=None, alias="APIFY_TOKEN")
    apify_actor_id: Optional[str] = Field(default=None, alias="APIFY_ACTOR_ID")
    apify_twitter_actor_id: Optional[str] = Field(default=None, alias="APIFY_ACTOR_TWITTER")
    apify_telegram_actor_id: Optional[str] = Field(default=None, alias="APIFY_ACTOR_TELEGRAM")

    groq_base_url: str = "https://api.groq.com/openai/v1"
    groq_api_key: Optional[str] = Field(default=None, alias="GROQ_API_KEY")
    groq_model: str = Field(default="mixtral-8x7b", alias="GROQ_MODEL", validation_alias="GROQ_MODEL")

    gemini_base_url: str = Field(default="https://api.flowith.io/v1/gemini", alias="GEMINI_BASE_URL")
    gemini_api_key: Optional[str] = Field(default=None, alias="GEMINI_API_KEY")

    helius_webhook_secret: Optional[str] = Field(default=None, alias="HELIUS_WEBHOOK_SECRET")
    alerts_signature_secret: Optional[str] = Field(default=None, alias="ALERTS_SIGNATURE_SECRET")

    parser_default_sources: list[str] = Field(default_factory=lambda: ["twitter", "telegram"])
    parser_default_filters: list[str] = Field(default_factory=lambda: ["hot", "safe"])

    ai_core_config_dir: str = Field(default='ai_core/configs', alias='AI_CORE_CONFIG_DIR')
    fastapi_url: Optional[str] = Field(default=None, alias='FASTAPI_URL')

    http_timeout_seconds: int = 15

    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"
        case_sensitive = False
        extra = "ignore"


@functools.lru_cache(maxsize=1)
def get_settings() -> Settings:
    return Settings()  # type: ignore[arg-type]
