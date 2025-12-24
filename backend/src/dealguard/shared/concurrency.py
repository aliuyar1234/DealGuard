"""Concurrency helpers with backpressure.

This module provides small utilities to avoid unbounded concurrency in places
where we offload work to the default threadpool (e.g., PDF parsing, boto3 calls).
"""

from __future__ import annotations

import asyncio
import os
from collections.abc import Callable
from typing import ParamSpec, TypeVar

_P = ParamSpec("_P")
_T = TypeVar("_T")


def _default_to_thread_limit() -> int:
    cpu = os.cpu_count() or 4
    return max(4, min(32, cpu * 4))


_TO_THREAD_LIMIT = int(os.getenv("DEALGUARD_TO_THREAD_LIMIT", str(_default_to_thread_limit())))
_TO_THREAD_SEMAPHORE = asyncio.Semaphore(_TO_THREAD_LIMIT)


async def to_thread_limited(func: Callable[_P, _T], /, *args: _P.args, **kwargs: _P.kwargs) -> _T:
    """Run a blocking function in a thread with bounded concurrency."""
    await _TO_THREAD_SEMAPHORE.acquire()
    try:
        return await asyncio.to_thread(func, *args, **kwargs)
    finally:
        _TO_THREAD_SEMAPHORE.release()
