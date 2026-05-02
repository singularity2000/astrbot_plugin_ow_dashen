from __future__ import annotations

from pathlib import Path
from typing import Any, Dict

try:
    from overstats.src.modules.query_tool import get_query_tool_path, load_query_tool
except ModuleNotFoundError:
    from src.modules.query_tool import get_query_tool_path, load_query_tool


def get_ow_config_path() -> str:
    return str(get_query_tool_path())


def refresh_ow_config(force: bool = False) -> Dict[str, Any]:
    return load_query_tool(force_refresh=force)


def load_ow_config(force_refresh: bool = False) -> Dict[str, Any]:
    return load_query_tool(force_refresh=force_refresh)


OW_CONFIG_PATH = str(Path(get_ow_config_path()))
