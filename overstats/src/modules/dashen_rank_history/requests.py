from __future__ import annotations

import asyncio
from dataclasses import dataclass
from typing import Any, Dict, List, Optional

try:
    from overstats.src.client.apiclient import DashenAPIClient, dashen_api_client
except ModuleNotFoundError:
    from src.client.apiclient import DashenAPIClient, dashen_api_client


@dataclass(frozen=True)
class DashenRankHistoryQuery:
    customer_token: str = ""
    bnet_id: str = ""
    start_season: Optional[int] = None
    end_season: Optional[int] = None


@dataclass(frozen=True)
class DashenRankHistorySeasonPayload:
    season: int
    sport: Optional[Dict[str, Any]]
    fight: Optional[Dict[str, Any]]


def payload_data(payload: Any) -> Dict[str, Any]:
    if not isinstance(payload, dict):
        return {}
    data = payload.get("data")
    return data if isinstance(data, dict) else {}


def sport_payload_has_content(payload: Any) -> bool:
    data = payload_data(payload)
    return bool(data.get("guideCountData") or data.get("frequentHeroIds"))


def fight_payload_has_content(payload: Any) -> bool:
    data = payload_data(payload)
    return bool(data.get("roleTypeCountData") or data.get("heroUseSummaryList"))


class DashenRankHistoryRequests:
    def __init__(self, api_client: Optional[DashenAPIClient] = None) -> None:
        self.api_client = api_client or dashen_api_client

    async def get_history_payloads(
        self,
        customer_token: str,
        *,
        start_season: int,
        end_season: int,
    ) -> List[DashenRankHistorySeasonPayload]:
        sport_map, fight_map = await asyncio.gather(
            self.api_client.query_historical_count_info(
                customer_token,
                start_season=start_season,
                end_season=end_season,
                game_mode="sport",
            ),
            self.api_client.query_historical_fight_count(
                customer_token,
                start_season=start_season,
                end_season=end_season,
            ),
        )

        seasons: List[DashenRankHistorySeasonPayload] = []
        for season in range(int(start_season), int(end_season) + 1):
            sport_payload = sport_map.get(season)
            fight_payload = fight_map.get(season)
            seasons.append(
                DashenRankHistorySeasonPayload(
                    season=season,
                    sport=sport_payload if isinstance(sport_payload, dict) and sport_payload.get("code") == 0 else None,
                    fight=fight_payload if isinstance(fight_payload, dict) and fight_payload.get("code") == 0 else None,
                )
            )
        return seasons
