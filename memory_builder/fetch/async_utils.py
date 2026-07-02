from __future__ import annotations

import asyncio
from collections.abc import Coroutine
from typing import TypeVar


T = TypeVar("T")


def run_async(coro: Coroutine[object, object, T]) -> T:
    return asyncio.run(coro)
