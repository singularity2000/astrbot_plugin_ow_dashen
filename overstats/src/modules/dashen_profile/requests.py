from __future__ import annotations

import asyncio
from dataclasses import dataclass
import datetime as dt
from typing import Any, Dict, Iterable, Optional, Sequence

try:
    from overstats.src.client.apiclient import DashenAPIClient, dashen_api_client
    from overstats.src.modules.season_config import get_dashen_current_season, get_dashen_season_rollover_at
except ModuleNotFoundError:
    from src.client.apiclient import DashenAPIClient, dashen_api_client
    from src.modules.season_config import get_dashen_current_season, get_dashen_season_rollover_at


DASHEN_SEASON_ROLLOVER_AT = get_dashen_season_rollover_at()
DASHEN_SEASON_AFTER_ROLLOVER = get_dashen_current_season()
DASHEN_SEASON_BEFORE_ROLLOVER = max(DASHEN_SEASON_AFTER_ROLLOVER - 1, 1)


@dataclass(frozen=True)
class DashenProfileQuery:
    customer_token: str = ""
    bnet_id: str = ""
    season: Optional[int] = None
    include_previous_season: bool = True


@dataclass(frozen=True)
class DashenProfileBundle:
    customer_token: str
    profile_card: Dict[str, Any]
    sport: Dict[str, Any]
    leisure: Dict[str, Any]
    logical_season: Optional[int] = None
    request_season: Optional[int] = None
    include_previous_season: bool = True


def get_live_dashen_season(now: Optional[dt.datetime] = None) -> int:
    return int(get_dashen_current_season())


def get_recent_dashen_seasons(current_season: Optional[int] = None, include_previous: bool = True) -> list[int]:
    current = int(current_season or get_live_dashen_season())
    seasons = [current]
    if include_previous and current > 1:
        seasons.append(current - 1)
    return seasons


def iter_dashen_season_request_values(season: Optional[int]) -> Iterable[Optional[int]]:
    if season is None:
        yield None
        return
    if int(season) == get_live_dashen_season():
        yield None
    yield int(season)


def extract_match_entries(payload: Any, *preferred_keys: str) -> list[Dict[str, Any]]:
    if isinstance(payload, list):
        return [item for item in payload if isinstance(item, dict)]
    if not isinstance(payload, dict):
        return []

    data = payload.get("data", payload)
    if isinstance(data, list):
        return [item for item in data if isinstance(item, dict)]
    if not isinstance(data, dict):
        return []

    keys = preferred_keys or ("matchList", "recentMatchList")
    for key in keys:
        value = data.get(key)
        if isinstance(value, list):
            return [item for item in value if isinstance(item, dict)]
    return []


def count_unique_match_entries(entries: Sequence[Dict[str, Any]]) -> int:
    seen_ids = set()
    count = 0
    for match in entries or []:
        match_id = str(match.get("matchId") or "").strip()
        if match_id:
            if match_id in seen_ids:
                continue
            seen_ids.add(match_id)
        count += 1
    return count


def merge_unique_match_entries(
    existing_entries: Sequence[Dict[str, Any]],
    new_entries: Sequence[Dict[str, Any]],
) -> list[Dict[str, Any]]:
    def _begin_ts(match: Dict[str, Any]) -> int:
        try:
            return int(match.get("beginTs") or 0)
        except (TypeError, ValueError):
            return 0

    merged_entries: list[Dict[str, Any]] = []
    seen_ids = set()
    for source in (existing_entries or [], new_entries or []):
        for match in source:
            if not isinstance(match, dict):
                continue
            item = dict(match)
            match_id = str(item.get("matchId") or "").strip()
            if match_id:
                if match_id in seen_ids:
                    continue
                seen_ids.add(match_id)
            merged_entries.append(item)
    merged_entries.sort(key=_begin_ts, reverse=True)
    return merged_entries


def _profile_value_has_meaningful_content(value: Any) -> bool:
    if isinstance(value, dict):
        return any(_profile_value_has_meaningful_content(item) for item in value.values())
    if isinstance(value, list):
        return bool(value)
    if isinstance(value, (int, float)):
        return value != 0
    return bool(value)


def payload_has_match_entries(payload: Any, *preferred_keys: str) -> bool:
    return bool(extract_match_entries(payload, *preferred_keys))


def payload_has_profile_content(payload: Any) -> bool:
    if not isinstance(payload, dict):
        return False

    data = payload.get("data", payload)
    if not isinstance(data, dict):
        return False

    list_fields = (
        "guideCountData",
        "matchList",
        "recentMatchList",
        "presetsHeroUseSummaryList",
        "v6HeroUseSummaryList",
        "openHeroUseSummaryList",
        "presetsHeroList",
        "openHeroList",
        "userProvinceRankList",
    )
    dict_fields = (
        "presetsSummaryData",
        "openSummaryData",
        "recentMatchCount",
        "gameAction",
    )

    for key in list_fields:
        value = data.get(key)
        if isinstance(value, list) and value:
            return True

    for key in dict_fields:
        if _profile_value_has_meaningful_content(data.get(key)):
            return True

    return False


def build_empty_count_payload(game_mode: Optional[str] = None, season: Optional[int] = None) -> Dict[str, Any]:
    server_map_defaults = {
        "kill": 0,
        "maxKill": 0,
        "damage": 0,
        "maxDamage": 0,
        "cure": 0,
        "maxCure": 0,
        "resistDamage": 0,
        "maxResistDamage": 0,
        "death": 0,
        "maxDeath": 0,
    }

    def _summary_defaults() -> Dict[str, Any]:
        return {
            "aveKill": 0,
            "aveHeroDamage": 0,
            "aveCure": 0,
            "aveResistDamage": 0,
            "aveDeath": 0,
            "serverMapCountData": dict(server_map_defaults),
        }

    recent_defaults = {
        "aveKill": 0,
        "aveDamage": 0,
        "aveCure": 0,
        "aveResistDamage": 0,
        "aveDeath": 0,
    }

    data: Dict[str, Any] = {
        "guideCountData": [],
        "matchList": [],
        "recentMatchList": [],
        "recentMatchCount": recent_defaults,
        "presetsSummaryData": _summary_defaults(),
        "openSummaryData": _summary_defaults(),
        "presetsHeroUseSummaryList": [],
        "v6HeroUseSummaryList": [],
        "openHeroUseSummaryList": [],
        "presetsHeroList": [],
        "openHeroList": [],
        "userProvinceRankList": [],
    }
    if game_mode:
        data["gameMode"] = game_mode
    if season is not None:
        data["season"] = season
    return {
        "code": 0,
        "success": True,
        "msg": "ok",
        "data": data,
    }


def normalize_count_payload(
    payload: Any,
    *,
    game_mode: Optional[str] = None,
    season: Optional[int] = None,
) -> Dict[str, Any]:
    normalized = build_empty_count_payload(game_mode=game_mode, season=season)
    if not isinstance(payload, dict):
        return normalized

    normalized["code"] = payload.get("code", normalized["code"])
    normalized["success"] = payload.get("success", normalized["success"])
    normalized["msg"] = payload.get("msg", normalized["msg"])

    raw_data = payload.get("data")
    if not isinstance(raw_data, dict):
        return normalized

    merged_data = normalized["data"]
    for key, value in raw_data.items():
        if key in {"presetsSummaryData", "openSummaryData"} and isinstance(value, dict):
            merged_summary = dict(merged_data.get(key, {}))
            raw_server_map = value.get("serverMapCountData")
            for sub_key, sub_value in value.items():
                if sub_key == "serverMapCountData":
                    continue
                merged_summary[sub_key] = sub_value
            if isinstance(raw_server_map, dict):
                merged_server_map = dict(merged_summary.get("serverMapCountData", {}))
                merged_server_map.update(raw_server_map)
                merged_summary["serverMapCountData"] = merged_server_map
            merged_data[key] = merged_summary
            continue

        if key == "recentMatchCount" and isinstance(value, dict):
            merged_recent = dict(merged_data.get(key, {}))
            merged_recent.update(value)
            merged_data[key] = merged_recent
            continue

        merged_data[key] = value

    return normalized


class DashenProfileRequests:
    def __init__(self, api_client: Optional[DashenAPIClient] = None) -> None:
        self.api_client = api_client or dashen_api_client

    async def get_profile_bundle(self, query: DashenProfileQuery) -> DashenProfileBundle:
        card = await self.api_client.query_card(query.customer_token)

        if query.season is None:
            logical_seasons = get_recent_dashen_seasons(include_previous=query.include_previous_season)
        else:
            logical_seasons = [int(query.season)]

        last_sport = build_empty_count_payload("sport")
        last_leisure = build_empty_count_payload("leisure")
        last_logical_season: Optional[int] = logical_seasons[0] if logical_seasons else None
        last_request_season: Optional[int] = None

        for logical_season in logical_seasons:
            sport_payload, leisure_payload, request_season = await self.get_count_payload_pair(
                query.customer_token,
                logical_season=logical_season,
            )
            last_sport = sport_payload
            last_leisure = leisure_payload
            last_logical_season = logical_season
            last_request_season = request_season

            if payload_has_profile_content(sport_payload) or payload_has_profile_content(leisure_payload):
                return DashenProfileBundle(
                    customer_token=query.customer_token,
                    profile_card=card,
                    sport=sport_payload,
                    leisure=leisure_payload,
                    logical_season=logical_season,
                    request_season=request_season,
                    include_previous_season=query.include_previous_season,
                )

        return DashenProfileBundle(
            customer_token=query.customer_token,
            profile_card=card,
            sport=last_sport,
            leisure=last_leisure,
            logical_season=last_logical_season,
            request_season=last_request_season,
            include_previous_season=query.include_previous_season,
        )

    async def get_count_payload_pair(
        self,
        customer_token: str,
        *,
        logical_season: Optional[int],
    ) -> tuple[Dict[str, Any], Dict[str, Any], Optional[int]]:
        last_sport = build_empty_count_payload("sport", logical_season)
        last_leisure = build_empty_count_payload("leisure", logical_season)
        last_request_season: Optional[int] = None

        for request_season in iter_dashen_season_request_values(logical_season):
            sport_payload, leisure_payload = await self._fetch_count_pair(
                customer_token,
                logical_season=logical_season,
                request_season=request_season,
            )
            last_sport = sport_payload
            last_leisure = leisure_payload
            last_request_season = request_season

            if payload_has_profile_content(sport_payload) or payload_has_profile_content(leisure_payload):
                return sport_payload, leisure_payload, request_season

        return last_sport, last_leisure, last_request_season

    async def get_extra_match_page(
        self,
        customer_token: str,
        game_mode: str,
        *,
        page: int = 2,
        logical_season: Optional[int],
    ) -> Optional[Dict[str, Any]]:
        for request_season in iter_dashen_season_request_values(logical_season):
            try:
                payload = await self.api_client.query_match_list(
                    customer_token,
                    game_mode,
                    page=page,
                    season=request_season,
                )
            except Exception:
                continue
            if isinstance(payload, dict) and payload.get("code") == 0 and payload_has_match_entries(payload, "matchList", "recentMatchList"):
                return payload
        return None

    async def get_stadium_leisure_role_card(
        self,
        customer_token: str,
        *,
        logical_season: Optional[int],
    ) -> Optional[Dict[str, Any]]:
        for request_season in iter_dashen_season_request_values(logical_season):
            try:
                payload = await self.api_client.fight_leisure_role_card(customer_token, season=request_season)
            except Exception:
                continue
            if isinstance(payload, dict) and payload.get("code") == 0 and payload_has_match_entries(payload, "recentMatchList", "matchList"):
                return payload
        return None

    async def get_stadium_count(
        self,
        customer_token: str,
        *,
        logical_season: Optional[int],
    ) -> Optional[Dict[str, Any]]:
        for request_season in iter_dashen_season_request_values(logical_season):
            try:
                payload = await self.api_client.fight_query_count(customer_token, season=request_season)
            except Exception:
                continue
            if isinstance(payload, dict) and payload.get("code") == 0 and payload_has_match_entries(payload, "matchList", "recentMatchList"):
                return payload
        return None

    async def get_billboard_user(self, customer_token: str) -> Optional[Dict[str, Any]]:
        try:
            payload = await self.api_client.get_billboard_user(customer_token)
        except Exception:
            return None
        if isinstance(payload, dict) and payload.get("code") == 0:
            return payload
        return None

    async def get_match_detail(self, customer_token: str, match_id: str) -> Dict[str, Any]:
        return await self.api_client.query_match_info(customer_token, str(match_id))

    async def get_fight_match_detail(self, customer_token: str, match_id: str) -> Dict[str, Any]:
        return await self.api_client.fight_query_match_info(customer_token, str(match_id))

    async def list_stadium_match_page(
        self,
        customer_token: str,
        *,
        game_mode: str,
        page: int,
        logical_season: Optional[int],
    ) -> Optional[Dict[str, Any]]:
        for request_season in iter_dashen_season_request_values(logical_season):
            try:
                payload = await self.api_client.fight_query_match_list(
                    customer_token,
                    game_mode=game_mode,
                    page=page,
                    season=request_season,
                )
            except Exception:
                continue
            if isinstance(payload, dict) and payload.get("code") == 0 and payload_has_match_entries(payload, "matchList", "recentMatchList"):
                return payload
        return None

    async def _fetch_count_pair(
        self,
        customer_token: str,
        *,
        logical_season: Optional[int],
        request_season: Optional[int],
    ) -> tuple[Dict[str, Any], Dict[str, Any]]:
        tasks = (
            self.api_client.query_count_info(customer_token, "sport", season=request_season),
            self.api_client.query_count_info(customer_token, "leisure", season=request_season),
        )
        sport_raw, leisure_raw = await asyncio.gather(*tasks, return_exceptions=True)

        sport_payload = (
            normalize_count_payload(sport_raw, game_mode="sport", season=logical_season)
            if isinstance(sport_raw, dict) and sport_raw.get("code") == 0
            else build_empty_count_payload("sport", logical_season)
        )
        leisure_payload = (
            normalize_count_payload(leisure_raw, game_mode="leisure", season=logical_season)
            if isinstance(leisure_raw, dict) and leisure_raw.get("code") == 0
            else build_empty_count_payload("leisure", logical_season)
        )
        return sport_payload, leisure_payload
