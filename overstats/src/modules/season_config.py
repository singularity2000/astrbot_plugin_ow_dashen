from __future__ import annotations

import datetime as dt
import json
from pathlib import Path
from typing import Any, Dict, Mapping, Optional

try:
    from overstats.config import config as app_config
    from overstats.paths import get_overstats_data_dir
except ModuleNotFoundError:
    from config import config as app_config
    from paths import get_overstats_data_dir


DEFAULT_DASHEN_CURRENT_SEASON = 23
DEFAULT_DASHEN_HISTORY_START_SEASON = 15


def _safe_positive_int(value: Any) -> Optional[int]:
    try:
        resolved = int(str(value).strip())
    except (TypeError, ValueError):
        return None
    return resolved if resolved > 0 else None


def _safe_text(value: Any) -> str:
    return str(value or "").strip()


def _extract_auto_dashen_season(config: Mapping[str, Any]) -> int:
    latest = 0
    items = config.get("AIEvaluateConfig")
    if not isinstance(items, list):
        return latest
    for item in items:
        if not isinstance(item, Mapping):
            continue
        season_ids = item.get("seasonIdList")
        if not isinstance(season_ids, list):
            continue
        for raw_season in season_ids:
            season = _safe_positive_int(raw_season)
            if season is not None:
                latest = max(latest, season)
    return latest


def get_query_tool_path() -> Path:
    return get_overstats_data_dir() / "query_tool.json"


def get_dashen_manual_season() -> int:
    configured = getattr(app_config, "DASHEN_CURRENT_SEASON", DEFAULT_DASHEN_CURRENT_SEASON)
    return _safe_positive_int(configured) or DEFAULT_DASHEN_CURRENT_SEASON


def get_dashen_history_start_season() -> int:
    configured = getattr(app_config, "DASHEN_HISTORY_START_SEASON", DEFAULT_DASHEN_HISTORY_START_SEASON)
    return _safe_positive_int(configured) or DEFAULT_DASHEN_HISTORY_START_SEASON


def read_local_query_tool(default: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
    fallback = dict(default or {})
    query_tool_path = get_query_tool_path()
    if not query_tool_path.exists():
        return normalize_query_tool_config(fallback)
    try:
        payload = json.loads(query_tool_path.read_text(encoding="utf-8"))
    except Exception as exc:
        print(f"[overstats] failed to read query_tool season config {query_tool_path}: {exc}")
        return normalize_query_tool_config(fallback)
    if not isinstance(payload, dict):
        return normalize_query_tool_config(fallback)
    return normalize_query_tool_config(payload)


def get_dashen_auto_season(query_tool_config: Optional[Mapping[str, Any]] = None) -> int:
    config = query_tool_config if isinstance(query_tool_config, Mapping) else read_local_query_tool(default={})
    return _extract_auto_dashen_season(config)


def get_dashen_current_season(query_tool_config: Optional[Mapping[str, Any]] = None) -> int:
    manual = get_dashen_manual_season()
    config = query_tool_config if isinstance(query_tool_config, Mapping) else read_local_query_tool(default={})
    auto = _extract_auto_dashen_season(config)
    return max(manual, auto)


def normalize_query_tool_config(config: Optional[Mapping[str, Any]]) -> Dict[str, Any]:
    normalized = dict(config or {})
    current_season = get_dashen_current_season(normalized)
    start_season = min(get_dashen_history_start_season(), current_season)

    raw_season_list = normalized.get("seasonList")
    season_list: Dict[str, Any] = dict(raw_season_list) if isinstance(raw_season_list, Mapping) else {}
    for season in range(start_season, current_season + 1):
        key = str(season)
        if isinstance(season_list.get(key), Mapping):
            continue

        prev_info = season_list.get(str(season - 1))
        prev_mapping = prev_info if isinstance(prev_info, Mapping) else {}
        season_list[key] = {
            "startTime": _safe_text(prev_mapping.get("endTime")) or _safe_text(prev_mapping.get("startTime")),
            "endTime": "",
            "desc": f"S{season}",
        }

    normalized["seasonList"] = season_list
    return normalized


def parse_dashen_season_time(value: Any) -> Optional[dt.datetime]:
    raw_value = _safe_text(value).replace("/", ".")
    if not raw_value:
        return None
    parts = [part for part in raw_value.split(".") if part]
    try:
        if len(parts) >= 3:
            year, month, day = (int(parts[0]), int(parts[1]), int(parts[2]))
        elif len(parts) == 2:
            year, month, day = (int(parts[0]), int(parts[1]), 1)
        else:
            return None
        return dt.datetime(year, month, day)
    except ValueError:
        return None


def get_dashen_season_rollover_at(query_tool_config: Optional[Mapping[str, Any]] = None) -> Optional[dt.datetime]:
    if query_tool_config is None:
        config = read_local_query_tool(default={})
    else:
        config = normalize_query_tool_config(query_tool_config)
    current_season = get_dashen_current_season(config)
    season_list = config.get("seasonList")
    if not isinstance(season_list, Mapping):
        return None

    current_info = season_list.get(str(current_season))
    if isinstance(current_info, Mapping):
        start_time = parse_dashen_season_time(current_info.get("startTime"))
        if start_time is not None:
            return start_time

    prev_info = season_list.get(str(current_season - 1))
    if isinstance(prev_info, Mapping):
        return parse_dashen_season_time(prev_info.get("endTime"))
    return None
