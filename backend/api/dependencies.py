from __future__ import annotations

from collections.abc import AsyncIterator
from pathlib import Path

from sqlalchemy.ext.asyncio import AsyncSession

from .config import Settings, get_settings
from .database import get_session
from .services.ai_pipeline import AIPipelineService
from .services.apify import ApifyClient
from .services.gemini import GeminiService
from .services.groq import GroqClient
from .services.queue import QueueService


_settings = get_settings()
_queue_service = QueueService(_settings.redis_url, namespace=_settings.queue_namespace)
_groq_client = GroqClient(
    _settings.groq_base_url,
    _settings.groq_api_key,
    _settings.groq_model,
    timeout=_settings.http_timeout_seconds,
)
_apify_client = ApifyClient(
    _settings.apify_base_url,
    _settings.apify_token,
    timeout=_settings.http_timeout_seconds,
)
_ai_config_path = Path(_settings.ai_core_config_dir).expanduser()
if not _ai_config_path.is_absolute():
    repo_root = Path(__file__).resolve().parents[2]
    _ai_config_path = (repo_root / _ai_config_path).resolve()
_ai_pipeline = AIPipelineService(_ai_config_path, groq_client=_groq_client if _settings.groq_api_key else None)
_gemini_service = GeminiService(Path(__file__).resolve().parents[2])


def get_settings_dependency() -> Settings:
    return _settings


def get_queue_service() -> QueueService:
    return _queue_service


def get_groq_client() -> GroqClient:
    return _groq_client


def get_apify_client() -> ApifyClient:
    return _apify_client



def get_ai_pipeline() -> AIPipelineService:
    return _ai_pipeline


def get_gemini_service() -> GeminiService:
    return _gemini_service


async def get_db_session() -> AsyncIterator[AsyncSession]:
    async for session in get_session():
        yield session


async def connect_queue() -> None:
    await _queue_service.connect()


async def close_queue() -> None:
    await _queue_service.close()
