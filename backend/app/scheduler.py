import asyncio
import logging

from .alerts import run_checks
from .config import settings
from .database import SessionLocal  # ADJUST if your session factory has another name

log = logging.getLogger("scheduler")


def _tick() -> None:
    db = SessionLocal()
    try:
        run_checks(db)
    except Exception:
        log.exception("Scheduler tick failed")
    finally:
        db.close()


async def scheduler_loop() -> None:
    while True:
        await asyncio.to_thread(_tick)
        await asyncio.sleep(settings.check_interval_seconds)