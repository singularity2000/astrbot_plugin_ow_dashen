from __future__ import annotations

try:
    from overstats.src.db.match_stats import IDPoolDB, MATCH_STATS_DB_PATH
except ModuleNotFoundError:
    from src.db.match_stats import IDPoolDB, MATCH_STATS_DB_PATH


__all__ = ["IDPoolDB", "MATCH_STATS_DB_PATH"]
