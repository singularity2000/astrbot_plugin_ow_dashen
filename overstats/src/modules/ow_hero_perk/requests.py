from __future__ import annotations

from dataclasses import dataclass
from typing import Any


MINOR_PERK_LEVEL = 1
MAJOR_PERK_LEVEL = 2
SUPPORTED_PERK_LEVELS = (MINOR_PERK_LEVEL, MAJOR_PERK_LEVEL)


@dataclass(frozen=True)
class OWHeroPerkQuery:
    hero: str = ""


def normalize_hero_query(value: Any) -> str:
    normalized = str(value or "").strip()
    if normalized:
        return normalized
    raise ValueError("hero is required.")


__all__ = [
    "MAJOR_PERK_LEVEL",
    "MINOR_PERK_LEVEL",
    "OWHeroPerkQuery",
    "SUPPORTED_PERK_LEVELS",
    "normalize_hero_query",
]
