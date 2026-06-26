from __future__ import annotations

import asyncio
from functools import partial
from typing import Any, Callable, TypeVar


T = TypeVar("T")


async def run_blocking(func: Callable[..., T], /, *args: Any, **kwargs: Any) -> T:
    """Run synchronous CPU or filesystem work without blocking AstrBot's event loop."""
    if kwargs:
        return await asyncio.to_thread(partial(func, *args, **kwargs))
    return await asyncio.to_thread(func, *args)
