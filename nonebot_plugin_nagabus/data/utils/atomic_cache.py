from typing import Callable
from collections.abc import Coroutine
from asyncio import Future, create_task

_cache: dict[str, Future] = {}
_cache_consumers: dict[str, int] = {}


async def get_atomic_cache(key: str, get_cache: Callable[[], Coroutine]):
    if key not in _cache:
        _cache_consumers[key] = 0
        _cache[key] = create_task(get_cache())

    _cache_consumers[key] += 1
    try:
        return await _cache[key]
    finally:
        _cache_consumers[key] -= 1
        if _cache_consumers[key] == 0:
            del _cache[key]
            del _cache_consumers[key]
