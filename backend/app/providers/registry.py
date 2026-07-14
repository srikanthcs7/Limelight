"""Maps an engine key -> provider instance. Adding an engine = one entry here."""
from __future__ import annotations

from app.providers.base import EngineProvider
from app.providers.openai_provider import OpenAIProvider
from app.providers.serpapi_provider import SerpApiAIOProvider

_PROVIDERS: dict[str, EngineProvider] = {
    OpenAIProvider.key: OpenAIProvider(),
    SerpApiAIOProvider.key: SerpApiAIOProvider(),
}


def get_provider(key: str) -> EngineProvider:
    try:
        return _PROVIDERS[key]
    except KeyError:
        raise ValueError(f"No engine provider registered for key {key!r}") from None


def provider_keys() -> list[str]:
    return list(_PROVIDERS)
