from __future__ import annotations

from dataclasses import dataclass
from io import BytesIO

from .requests import BnetSearchResult


@dataclass(frozen=True)
class RenderedImage:
    content: bytes
    media_type: str = "image/png"


def render_bnet_search_result(result: BnetSearchResult) -> RenderedImage:
    lines = [
        "BattleTag Search",
        "",
        f"query: {result.query}",
        f"full_id: {result.full_id or '-'}",
        f"bnet_id: {result.bnet_id or '-'}",
        f"has_customer_token: {bool(result.customer_token)}",
        f"code: {result.payload.get('code')}",
    ]
    return _render_text_png(lines)


def _render_text_png(lines: list[str]) -> RenderedImage:
    try:
        from PIL import Image, ImageDraw, ImageFont
    except ModuleNotFoundError as exc:
        raise RuntimeError("render.py requires Pillow to output images") from exc

    width = 960
    line_height = 34
    padding = 36
    height = max(220, padding * 2 + line_height * len(lines))
    image = Image.new("RGB", (width, height), (18, 22, 30))
    draw = ImageDraw.Draw(image)
    font = ImageFont.load_default()
    y = padding
    for idx, line in enumerate(lines):
        fill = (120, 240, 220) if idx == 0 else (230, 235, 245)
        draw.text((padding, y), line, fill=fill, font=font)
        y += line_height

    output = BytesIO()
    image.save(output, format="PNG")
    return RenderedImage(content=output.getvalue())
