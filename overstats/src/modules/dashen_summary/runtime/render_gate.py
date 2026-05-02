import asyncio
import os


def _read_env_int(name, default):
    raw_value = str(os.getenv(name, "") or "").strip()
    if not raw_value:
        return int(default)
    try:
        return int(raw_value)
    except (TypeError, ValueError):
        return int(default)


GLOBAL_RENDER_CONCURRENCY = max(1, _read_env_int("OVERSHOP_RENDER_CONCURRENCY", 2))
_GLOBAL_RENDER_SEMAPHORE_BY_LOOP = {}


def get_global_render_limit():
    return GLOBAL_RENDER_CONCURRENCY


def get_global_render_semaphore():
    loop = asyncio.get_running_loop()
    semaphore = _GLOBAL_RENDER_SEMAPHORE_BY_LOOP.get(loop)
    if semaphore is None:
        semaphore = asyncio.Semaphore(GLOBAL_RENDER_CONCURRENCY)
        _GLOBAL_RENDER_SEMAPHORE_BY_LOOP[loop] = semaphore
    return semaphore
