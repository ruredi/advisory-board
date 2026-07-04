from __future__ import annotations

import asyncio
import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI

from memory_builder.telemetry.run_watchdog import scan_all_stale_runs

log = logging.getLogger(__name__)

WATCHDOG_INTERVAL_SECONDS = 30


async def _watchdog_loop() -> None:
    while True:
        try:
            closed = await asyncio.to_thread(scan_all_stale_runs)
            if closed:
                log.info("Run watchdog closed stale runs: %s", closed)
        except Exception:
            log.exception("Run watchdog scan failed")
        await asyncio.sleep(WATCHDOG_INTERVAL_SECONDS)


@asynccontextmanager
async def run_watchdog_lifespan(_app: FastAPI):
    task = asyncio.create_task(_watchdog_loop())
    try:
        yield
    finally:
        task.cancel()
        try:
            await task
        except asyncio.CancelledError:
            pass
