from __future__ import annotations

from pathlib import Path
import random
from typing import Any, Sequence


PROJECT_ROOT = Path(__file__).resolve().parents[2]
RESOURCE_DIR = PROJECT_ROOT / "res"
QUERY_TOOL_MAPS_DIR = RESOURCE_DIR / "query_tool_assets" / "maps"
BACKGROUND_IMAGE_SUFFIXES = frozenset({".png", ".jpg", ".jpeg", ".webp", ".bmp"})


def list_map_background_paths(directory: Path | None = None) -> list[Path]:
    root = Path(directory) if directory is not None else QUERY_TOOL_MAPS_DIR
    if not root.exists() or not root.is_dir():
        return []
    return sorted(
        path
        for path in root.iterdir()
        if path.is_file() and path.suffix.lower() in BACKGROUND_IMAGE_SUFFIXES
    )


def pick_random_map_background_path(*, directory: Path | None = None, rng: Any | None = None) -> Path | None:
    candidates = list_map_background_paths(directory)
    if not candidates:
        return None
    chooser = rng if rng is not None else random
    return Path(chooser.choice(candidates))


def build_random_map_background(
    size: Sequence[int],
    *,
    blur_radius: int = 0,
    overlay: tuple[int, int, int, int] | None = None,
    brightness: float = 0.82,
    color: float = 0.9,
    directory: Path | None = None,
    rng: Any | None = None,
) -> Any | None:
    try:
        from PIL import Image, ImageEnhance, ImageFilter, ImageOps
    except ModuleNotFoundError:
        return None

    try:
        width = int(size[0])
        height = int(size[1])
    except Exception:
        return None
    if width <= 0 or height <= 0:
        return None

    background_path = pick_random_map_background_path(directory=directory, rng=rng)
    if background_path is None:
        return None

    try:
        with Image.open(background_path) as raw_image:
            background = raw_image.convert("RGBA")
    except Exception:
        return None

    try:
        background = ImageOps.fit(
            background,
            (width, height),
            method=_resampling_lanczos(),
            centering=(0.5, 0.5),
        )
    except Exception:
        try:
            background = background.resize((width, height), _resampling_lanczos())
        except Exception:
            return None

    if color != 1.0:
        try:
            background = ImageEnhance.Color(background).enhance(float(color))
        except Exception:
            pass
    if brightness != 1.0:
        try:
            background = ImageEnhance.Brightness(background).enhance(float(brightness))
        except Exception:
            pass
    if int(blur_radius or 0) > 0:
        background = background.filter(ImageFilter.GaussianBlur(radius=int(blur_radius)))
    if overlay is not None:
        background = Image.alpha_composite(background, Image.new("RGBA", (width, height), overlay))
    return background


def _resampling_lanczos() -> Any:
    from PIL import Image

    resampling = getattr(Image, "Resampling", Image)
    return getattr(resampling, "LANCZOS")
