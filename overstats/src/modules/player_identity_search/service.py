from __future__ import annotations

from dataclasses import dataclass
from typing import Optional

try:
    from overstats.src.db.match_stats import IDPoolDB
    from overstats.src.db.player_identity import search_identity_by_bnet_id
    from overstats.src.modules.errors import ModuleError
except ModuleNotFoundError:
    from src.db.match_stats import IDPoolDB
    from src.db.player_identity import search_identity_by_bnet_id
    from src.modules.errors import ModuleError


@dataclass(frozen=True)
class PlayerIdentitySearchQuery:
    bnet_id: str
    limit: int = 10
    exact_only: bool = False


@dataclass(frozen=True)
class PlayerIdentityMatch:
    bnet_id: str
    battletag: str
    battlename: str
    battlenum: str
    update_time: int
    match_type: str

    def to_dict(self) -> dict[str, object]:
        return {
            "bnet_id": self.bnet_id,
            "battletag": self.battletag,
            "battlename": self.battlename,
            "battlenum": self.battlenum,
            "update_time": self.update_time,
            "match_type": self.match_type,
        }


@dataclass(frozen=True)
class PlayerIdentitySearchOutput:
    query: PlayerIdentitySearchQuery
    matches: tuple[PlayerIdentityMatch, ...]


class PlayerIdentitySearchModule:
    def __init__(self, db: Optional[IDPoolDB] = None) -> None:
        self.db = db or IDPoolDB()

    async def search(self, query: PlayerIdentitySearchQuery) -> PlayerIdentitySearchOutput:
        normalized_bnet_id = str(query.bnet_id or "").strip()
        if not normalized_bnet_id:
            raise ModuleError(
                error="missing_target",
                message="Missing query target: bnet_id is required.",
                status_code=400,
                hint='Example: {"bnet_id":"123456789"}',
            )

        try:
            normalized_limit = int(query.limit or 10)
        except (TypeError, ValueError) as exc:
            raise ModuleError(
                error="invalid_limit",
                message="limit must be an integer when provided.",
                status_code=400,
                hint='Example: {"bnet_id":"123456789","limit":10}',
                details={"limit": query.limit},
            ) from exc

        if normalized_limit <= 0:
            raise ModuleError(
                error="invalid_limit",
                message="limit must be greater than 0.",
                status_code=400,
                hint='Example: {"bnet_id":"123456789","limit":10}',
                details={"limit": normalized_limit},
            )

        normalized_limit = min(normalized_limit, 50)
        rows = await search_identity_by_bnet_id(
            normalized_bnet_id,
            db=self.db,
            limit=normalized_limit,
            exact_only=bool(query.exact_only),
        )
        matches = tuple(
            PlayerIdentityMatch(
                bnet_id=str(row.get("bnetid") or "").strip(),
                battletag=str(row.get("battletag") or "").strip(),
                battlename=str(row.get("battlename") or "").strip(),
                battlenum=str(row.get("battlenum") or "").strip(),
                update_time=int(row.get("update_time") or 0),
                match_type=str(row.get("match_type") or "").strip() or "exact",
            )
            for row in rows
        )
        return PlayerIdentitySearchOutput(
            query=PlayerIdentitySearchQuery(
                bnet_id=normalized_bnet_id,
                limit=normalized_limit,
                exact_only=bool(query.exact_only),
            ),
            matches=matches,
        )


player_identity_search_module = PlayerIdentitySearchModule()
