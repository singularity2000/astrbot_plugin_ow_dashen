from __future__ import annotations

import hashlib
import json
import os
from pathlib import Path
import re
import tempfile
from typing import Any, Mapping

try:
    from overstats.paths import ensure_dir, get_overstats_data_dir
except ModuleNotFoundError:
    from paths import ensure_dir, get_overstats_data_dir


PROJECT_ROOT = Path(__file__).resolve().parents[3]
OW_HERO_WIKI_CACHE_DIR = ensure_dir(get_overstats_data_dir() / "ow_hero_wiki")
PAGE_CACHE_DIR = OW_HERO_WIKI_CACHE_DIR / "pages"
STRUCTURED_CACHE_DIR = OW_HERO_WIKI_CACHE_DIR / "structured"
ANSWER_CACHE_DIR = OW_HERO_WIKI_CACHE_DIR / "answers"
IMAGE_CACHE_DIR = OW_HERO_WIKI_CACHE_DIR / "images"


def hash_text(value: Any) -> str:
    return hashlib.sha256(str(value or "").encode("utf-8")).hexdigest()


def build_cache_file_path(directory: Path, key: str, *, extension: str, label: str = "") -> Path:
    digest = hash_text(key)
    prefix = _slug_text(label)[:40].strip("-") or "entry"
    suffix = extension if extension.startswith(".") else f".{extension}"
    return Path(directory) / f"{prefix}-{digest}{suffix}"


def read_json_file(path: Path) -> dict[str, Any] | None:
    try:
        data = json.loads(Path(path).read_text(encoding="utf-8"))
    except Exception:
        return None
    return data if isinstance(data, dict) else None


def write_json_atomic(path: Path, payload: Mapping[str, Any]) -> None:
    _ensure_parent(Path(path))
    fd, temp_path = tempfile.mkstemp(prefix="wiki-cache.", suffix=".tmp", dir=str(Path(path).parent))
    try:
        with os.fdopen(fd, "w", encoding="utf-8", newline="\n") as handle:
            json.dump(dict(payload), handle, ensure_ascii=False, indent=2)
            handle.write("\n")
        Path(temp_path).replace(path)
    except Exception:
        try:
            Path(temp_path).unlink(missing_ok=True)
        except OSError:
            pass
        raise


def read_bytes_file(path: Path) -> bytes | None:
    try:
        data = Path(path).read_bytes()
    except Exception:
        return None
    return data if data else None


def write_bytes_atomic(path: Path, payload: bytes) -> None:
    _ensure_parent(Path(path))
    fd, temp_path = tempfile.mkstemp(prefix="wiki-image.", suffix=".tmp", dir=str(Path(path).parent))
    try:
        with os.fdopen(fd, "wb") as handle:
            handle.write(payload)
        Path(temp_path).replace(path)
    except Exception:
        try:
            Path(temp_path).unlink(missing_ok=True)
        except OSError:
            pass
        raise


def _ensure_parent(path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)


def _slug_text(text: Any) -> str:
    normalized = re.sub(r"[^A-Za-z0-9._-]+", "-", str(text or "").strip().lower())
    normalized = re.sub(r"-{2,}", "-", normalized).strip("-")
    return normalized or "entry"


__all__ = [
    "ANSWER_CACHE_DIR",
    "IMAGE_CACHE_DIR",
    "OW_HERO_WIKI_CACHE_DIR",
    "PAGE_CACHE_DIR",
    "PROJECT_ROOT",
    "STRUCTURED_CACHE_DIR",
    "build_cache_file_path",
    "hash_text",
    "read_bytes_file",
    "read_json_file",
    "write_bytes_atomic",
    "write_json_atomic",
]
