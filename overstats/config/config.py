from __future__ import annotations

_INJECTED_CONFIG: dict | None = None


def _as_bool(value: object, default: bool = False) -> bool:
    if value is None:
        return default
    if isinstance(value, bool):
        return value
    if isinstance(value, (int, float)):
        return bool(value)
    text = str(value).strip().lower()
    if text in {"1", "true", "yes", "on"}:
        return True
    if text in {"0", "false", "no", "off"}:
        return False
    return default


def inject_config(cfg: dict) -> None:
    global _INJECTED_CONFIG
    _INJECTED_CONFIG = cfg
    
    global ANALYSIS_PERSONA_PROMPT, ENABLE_AI_MATCH_REPLIES, ENABLE_PATCH_TRANSLATION
    global ANALYSIS_BASE_URL, ANALYSIS_API_KEY
    global ENABLE_DATABASE_WRITE, DASHEN_CURRENT_SEASON, DASHEN_HISTORY_START_SEASON, OW_HERO_LEADERBOARD_CN_SEASON
    analysis = cfg.get("analysis", {})
    dashen_global = cfg.get("dashen_global", {})
    persona_mode = analysis.get("persona_mode", "custom")
    if persona_mode == "custom":
        ANALYSIS_PERSONA_PROMPT = str(analysis.get("custom_persona_prompt", "")).strip()
    else:
        ANALYSIS_PERSONA_PROMPT = ""
        
    ENABLE_AI_MATCH_REPLIES = bool(analysis.get("enable_ai_match_replies", True))
    ENABLE_PATCH_TRANSLATION = bool(analysis.get("enable_patch_translation", True))
    
    provider_id = analysis.get("analysis_provider", "")
    if provider_id:
        ANALYSIS_BASE_URL = "http://dummy-url"
        ANALYSIS_API_KEY = "dummy-key"
    else:
        ANALYSIS_BASE_URL = ""
        ANALYSIS_API_KEY = ""

    ENABLE_DATABASE_WRITE = _as_bool(dashen_global.get("enable_database_write", ENABLE_DATABASE_WRITE), ENABLE_DATABASE_WRITE)
    DASHEN_CURRENT_SEASON = int(dashen_global.get("dashen_current_season", DASHEN_CURRENT_SEASON))
    DASHEN_HISTORY_START_SEASON = int(dashen_global.get("dashen_history_start_season", DASHEN_HISTORY_START_SEASON))
    OW_HERO_LEADERBOARD_CN_SEASON = int(
        dashen_global.get("ow_hero_leaderboard_cn_season", OW_HERO_LEADERBOARD_CN_SEASON)
    )


def _get(key: str, default: object = None) -> object:
    if _INJECTED_CONFIG is not None:
        return _INJECTED_CONFIG.get(key, default)
    return default


API_HOST = "127.0.0.1"
API_PORT = 18080
USE_STREAM_RESPONSE = True
ENABLE_DATABASE_WRITE = True

DASHEN_ACCOUNTS = _get("dashen_accounts", [])
DASHEN_DTS = _get("dashen_global_dashen_dts", 2026)
DASHEN_SERVER = _get("dashen_global_dashen_server", 1)
DASHEN_ACCOUNT_MAX_REQUESTS_PER_SECOND = _get("dashen_global_account_max_requests_per_second", 5)
DASHEN_ACCOUNT_RATE_LIMIT_WINDOW_SECONDS = _get("dashen_global_account_rate_limit_window_seconds", 1.0)
DASHEN_CLIENT_TYPE = "60"
DASHEN_ORIGIN = "https://act.ds.163.com"
DASHEN_REFERER = "https://act.ds.163.com/"
DASHEN_USER_AGENT = (
    "Mozilla/5.0 (Windows NT 10.0; WOW64) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/108.0.0.0 Safari/537.36 "
    "app/df_client dfVersion/100111"
)
DASHEN_ACCOUNT_FAILURE_COOLDOWN_SECONDS = _get("dashen_global_account_failure_cooldown_seconds", 60)
DASHEN_MAX_CONCURRENT_REQUESTS = _get("dashen_global_max_concurrent_requests", 2)
DASHEN_MAX_ACCEPTED_REQUESTS = 4

DASHEN_INTERNATIONAL_PROXY = _get("network_netease_proxy", "")
DASHEN_NETEASE_PROXIES = [None]

OW_ESPORTS_API_KEY = ""
OW_ESPORTS_URL = ""
OW_ESPORTS_PAYLOAD = {"ids": []}

OW_GUESS_ASSET_ROOT = ""

DASHEN_CURRENT_SEASON = 23
DASHEN_HISTORY_START_SEASON = 15

OW_HERO_LEADERBOARD_CN_SEASON = 3

ANALYSIS_BASE_URL = ""
ANALYSIS_API_KEY = ""
ANALYSIS_DEEPSEEK_MODEL = "deepseek-chat"

PATCH_NOTES_USE_INTERNATIONAL_PROXY = _get("network_patch_notes_use_international_proxy", False)
PATCH_NOTES_INTERNATIONAL_PROXY = _get("network_patch_notes_international_proxy", "")

ANALYSIS_PERSONA_PROMPT = ""
