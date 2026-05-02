from __future__ import annotations

import json
from typing import Any, Dict

import httpx


REMOTE_QUERY_TOOL_URL = "https://s.166.net/config/ds_ow/ow_record_query_tool.json"
REMOTE_HERO_URL = "https://s.166.net/config/ds_ow/ow_hero_config.json"
REMOTE_MAP_URL = "https://s.166.net/config/ds_ow/ow_map_config.json"
REMOTE_MOD_TRAIT_URL = "https://s.166.net/config/ds_ow/ow_record_query_tool_mod_trait.json"
REMOTE_HERO_ATTR_URL = "https://s.166.net/config/ds_ow/ow_hero_attr.json"
REMOTE_PERK_LIST_URL = "https://s.166.net/config/ds_ow/ow_perk_list.json"

REMOTE_TIMEOUT = 30
REMOTE_HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/123.0.0.0 Safari/537.36"
    )
}

MANUAL_KEYS = ("seasonList", "heroConfig")
REMOTE_SECTION_SOURCES = {
    "heroList": REMOTE_HERO_URL,
    "mapList": REMOTE_MAP_URL,
    "modTrait": REMOTE_MOD_TRAIT_URL,
    "heroAttrList": REMOTE_HERO_ATTR_URL,
    "heroPerkList": REMOTE_PERK_LIST_URL,
}
REMOTE_TOOL_EXCLUDED_KEYS = set(MANUAL_KEYS) | set(REMOTE_SECTION_SOURCES)


class QueryToolRequests:
    async def fetch_remote_query_tool(self) -> Dict[str, Any]:
        async with httpx.AsyncClient(headers=REMOTE_HEADERS, timeout=REMOTE_TIMEOUT) as client:
            merged: Dict[str, Any] = {}
            failures = []
            try:
                base_config = await self._fetch_json(client, REMOTE_QUERY_TOOL_URL, "query_tool")
                if isinstance(base_config, dict):
                    for key, value in base_config.items():
                        if key not in REMOTE_TOOL_EXCLUDED_KEYS:
                            merged[key] = value
            except Exception as exc:
                failures.append(f"query_tool: {type(exc).__name__}: {exc}")
                print(f"[overstats] failed to fetch remote query_tool base fields: {exc}")

            for key, url in REMOTE_SECTION_SOURCES.items():
                try:
                    merged[key] = await self._fetch_json(client, url, key)
                except Exception as exc:
                    failures.append(f"{key}: {type(exc).__name__}: {exc}")
                    print(f"[overstats] failed to fetch remote {key}: {exc}")
            if not merged:
                raise RuntimeError(
                    "failed to fetch query_tool from NetEase remote sources: "
                    + "; ".join(failures)
                )
            print(f"[overstats] fetched query_tool from NetEase remote sources: sections={len(merged)}")
            return merged

    async def _fetch_json(self, client: httpx.AsyncClient, url: str, label: str) -> Any:
        response = await client.get(url)
        response.raise_for_status()
        try:
            return response.json()
        except json.JSONDecodeError as exc:
            raise ValueError(f"{label} did not return valid JSON") from exc
