from __future__ import annotations

from typing import Any, Dict, Optional

import httpx

try:
    from overstats.config import config as app_config
except ModuleNotFoundError:
    from config import config as app_config


def _normalized_base_url(base_url: str) -> str:
    return str(base_url or "").strip().lower().rstrip("/")


def should_use_analysis_proxy(base_url: str) -> bool:
    normalized = _normalized_base_url(base_url)
    return normalized.startswith("https://api.openai.com/v1") or normalized.startswith(
        "https://generativelanguage.googleapis.com/v1beta/openai"
    )


def get_analysis_proxy(base_url: str) -> str:
    if not should_use_analysis_proxy(base_url):
        return ""
    return str(getattr(app_config, "ANALYSIS_PROXY", "") or "").strip()


def build_async_client(*, timeout: float, proxy_url: str = "", **kwargs: Any) -> httpx.AsyncClient:
    client_kwargs: Dict[str, Any] = dict(kwargs)
    client_kwargs["timeout"] = timeout
    if proxy_url:
        try:
            return httpx.AsyncClient(proxy=proxy_url, **client_kwargs)
        except TypeError:
            return httpx.AsyncClient(proxies=proxy_url, **client_kwargs)
    return httpx.AsyncClient(**client_kwargs)
