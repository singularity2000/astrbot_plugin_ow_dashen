from __future__ import annotations

from dataclasses import asdict, is_dataclass
from datetime import datetime, timezone
from pathlib import Path
import sqlite3
from typing import Any, Iterable, Mapping, Optional


OW_HERO_LEADERBOARD_DB_PATH = Path(__file__).resolve().parent / "ow_hero_leaderboard.sqlite3"
HERO_LEADERBOARD_CN_TABLE = "hero_leaderboard_cn"
HERO_LEADERBOARD_GLOBAL_TABLE = "hero_leaderboard_global"
_VALID_TABLES = {HERO_LEADERBOARD_CN_TABLE, HERO_LEADERBOARD_GLOBAL_TABLE}
_ROW_FIELDS = (
    "season",
    "ds",
    "game_mode",
    "mmr",
    "hero_id",
    "hero_type",
    "selection_ratio",
    "ban_ratio",
    "win_ratio",
    "kda",
)


def _safe_float(value: Any) -> float:
    try:
        return float(value)
    except (TypeError, ValueError):
        return 0.0


class OWHeroLeaderboardDB:
    def __init__(self, db_path: Optional[Path] = None) -> None:
        self.db_path = Path(db_path or OW_HERO_LEADERBOARD_DB_PATH)

    def initialize_database(self) -> None:
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        connection = sqlite3.connect(self.db_path)
        try:
            for table_name in _VALID_TABLES:
                connection.execute(
                    f"""
                    CREATE TABLE IF NOT EXISTS {table_name} (
                        season INTEGER NOT NULL,
                        ds TEXT NOT NULL,
                        game_mode TEXT NOT NULL,
                        mmr TEXT NOT NULL,
                        hero_id TEXT NOT NULL,
                        hero_type TEXT NOT NULL DEFAULT '',
                        selection_ratio REAL NOT NULL DEFAULT 0,
                        ban_ratio REAL NOT NULL DEFAULT 0,
                        win_ratio REAL NOT NULL DEFAULT 0,
                        kda REAL NOT NULL DEFAULT 0,
                        created_at TEXT NOT NULL,
                        updated_at TEXT NOT NULL,
                        PRIMARY KEY (season, ds, game_mode, mmr, hero_id)
                    )
                    """
                )
                connection.execute(
                    f"""
                    CREATE INDEX IF NOT EXISTS idx_{table_name}_ds_mode_mmr
                    ON {table_name} (ds, game_mode, mmr)
                    """
                )
            connection.commit()
        finally:
            connection.close()

    def upsert_rows(
        self,
        table_name: str,
        rows: Iterable[Mapping[str, Any] | Any],
        *,
        updated_at: Optional[str] = None,
    ) -> int:
        validated_table = self._validate_table_name(table_name)
        timestamp = str(updated_at or datetime.now(timezone.utc).isoformat())
        normalized_rows = []
        for row in rows:
            payload = self._coerce_row_payload(row)
            normalized_rows.append(
                (
                    int(payload["season"]),
                    str(payload["ds"]),
                    str(payload["game_mode"]),
                    str(payload["mmr"]),
                    str(payload["hero_id"]),
                    str(payload.get("hero_type") or ""),
                    _safe_float(payload.get("selection_ratio")),
                    _safe_float(payload.get("ban_ratio")),
                    _safe_float(payload.get("win_ratio")),
                    _safe_float(payload.get("kda")),
                    timestamp,
                    timestamp,
                )
            )

        if not normalized_rows:
            self.initialize_database()
            return 0

        self.initialize_database()
        connection = sqlite3.connect(self.db_path)
        try:
            connection.executemany(
                f"""
                INSERT INTO {validated_table} (
                    season,
                    ds,
                    game_mode,
                    mmr,
                    hero_id,
                    hero_type,
                    selection_ratio,
                    ban_ratio,
                    win_ratio,
                    kda,
                    created_at,
                    updated_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                ON CONFLICT(season, ds, game_mode, mmr, hero_id) DO UPDATE SET
                    hero_type = excluded.hero_type,
                    selection_ratio = excluded.selection_ratio,
                    ban_ratio = excluded.ban_ratio,
                    win_ratio = excluded.win_ratio,
                    kda = excluded.kda,
                    updated_at = excluded.updated_at
                """,
                normalized_rows,
            )
            connection.commit()
        finally:
            connection.close()
        return len(normalized_rows)

    def fetch_rows(
        self,
        table_name: str,
        *,
        season: Optional[int] = None,
        ds: Optional[str] = None,
        game_mode: Optional[str] = None,
        mmr: Optional[str] = None,
        hero_id: Optional[str] = None,
    ) -> list[dict[str, Any]]:
        validated_table = self._validate_table_name(table_name)
        if not self.db_path.exists():
            return []

        filters = []
        params: list[Any] = []
        for column_name, value in (
            ("season", season),
            ("ds", ds),
            ("game_mode", game_mode),
            ("mmr", mmr),
            ("hero_id", hero_id),
        ):
            if value in (None, ""):
                continue
            filters.append(f"{column_name} = ?")
            params.append(value)

        where_sql = ""
        if filters:
            where_sql = " WHERE " + " AND ".join(filters)

        connection = sqlite3.connect(self.db_path)
        connection.row_factory = sqlite3.Row
        try:
            rows = connection.execute(
                f"""
                SELECT
                    season,
                    ds,
                    game_mode,
                    mmr,
                    hero_id,
                    hero_type,
                    selection_ratio,
                    ban_ratio,
                    win_ratio,
                    kda,
                    created_at,
                    updated_at
                FROM {validated_table}
                {where_sql}
                ORDER BY ds ASC, game_mode ASC, mmr ASC, hero_id ASC
                """,
                params,
            ).fetchall()
        finally:
            connection.close()

        return [dict(row) for row in rows]

    def count_rows(self, table_name: str) -> int:
        validated_table = self._validate_table_name(table_name)
        if not self.db_path.exists():
            return 0
        connection = sqlite3.connect(self.db_path)
        try:
            row = connection.execute(f"SELECT COUNT(*) FROM {validated_table}").fetchone()
        finally:
            connection.close()
        return int(row[0] or 0) if row else 0

    def _validate_table_name(self, table_name: str) -> str:
        normalized = str(table_name or "").strip()
        if normalized not in _VALID_TABLES:
            raise ValueError(f"Unsupported table name: {table_name!r}")
        return normalized

    def _coerce_row_payload(self, row: Mapping[str, Any] | Any) -> dict[str, Any]:
        if isinstance(row, Mapping):
            payload = dict(row)
        elif is_dataclass(row):
            payload = asdict(row)
        else:
            payload = {field_name: getattr(row, field_name) for field_name in _ROW_FIELDS}

        missing = [field_name for field_name in _ROW_FIELDS if field_name not in payload]
        if missing:
            raise ValueError(f"Missing leaderboard row fields: {', '.join(missing)}")
        return payload
