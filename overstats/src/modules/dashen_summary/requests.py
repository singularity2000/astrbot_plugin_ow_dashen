from __future__ import annotations

import base64
from dataclasses import dataclass
from typing import Any, Dict

try:
    from overstats.src.modules.errors import ModuleError
except ModuleNotFoundError:
    from src.modules.errors import ModuleError

from .engine import render_summary_payload, title_for_scope


def decode_summary_image_base64(image_base64: str) -> tuple[bytes, str]:
    payload = str(image_base64 or "").strip()
    if payload.startswith("base64://"):
        payload = payload[len("base64://") :]
    if not payload:
        raise ModuleError(
            error="summary_image_missing",
            message="Summary module did not return image data.",
            status_code=502,
        )
    try:
        image_bytes = base64.b64decode(payload)
    except Exception as exc:
        raise ModuleError(
            error="summary_image_invalid",
            message="Summary module returned malformed base64 image data.",
            status_code=502,
        ) from exc

    media_type = "application/octet-stream"
    if image_bytes.startswith(b"\xff\xd8\xff"):
        media_type = "image/jpeg"
    elif image_bytes.startswith(b"\x89PNG\r\n\x1a\n"):
        media_type = "image/png"
    return image_bytes, media_type


@dataclass(frozen=True)
class DashenSummaryQuery:
    customer_token: str = ""
    bnet_id: str = ""
    full_id: str = ""
    icon_url: str = ""
    scope: str = "today"


@dataclass(frozen=True)
class DashenSummaryWorkerResult:
    scope: str
    title: str
    worker_url: str
    payload: Dict[str, Any]

    @property
    def image_base64(self) -> str:
        return str(self.payload.get("image_base64") or "")


class DashenSummaryRequests:
    async def render_summary(self, query: DashenSummaryQuery) -> DashenSummaryWorkerResult:
        scope = str(query.scope or "today").strip().lower()
        payload = await render_summary_payload(query)
        return DashenSummaryWorkerResult(
            scope=scope,
            title=title_for_scope(scope),
            worker_url=str(payload.get("worker_url") or "local-module"),
            payload=payload,
        )
