import asyncio
import contextlib
import logging
from functools import wraps
from typing import Callable

from celery import Celery

from app.db import get_session_ctx
from app.models import RailWayStation, Locomotive
from app.settings import CELERY_BROKER_URL, CELERY_RESULT_BACKEND
from app.state import incr_app_state, decr_app_state

celery = Celery(
    'tasks',
    broker=CELERY_BROKER_URL,
    backend=CELERY_RESULT_BACKEND
)


@contextlib.asynccontextmanager
async def set_app_busy():
    await incr_app_state()
    yield
    await decr_app_state()


def run_async(async_func: Callable) -> Callable:
    @wraps(async_func)
    def sync_func(*args, **kwargs):
        asyncio.run(async_func(*args, **kwargs))
    return sync_func


@celery.task
@run_async
async def perform_arrival(station_id: int, locomotive_id: int, notify_url: str) -> None:
    async with set_app_busy():
        pass
        async with get_session_ctx() as session:
            station: RailWayStation = await RailWayStation.get(session, _id=station_id)
            locomotive = await Locomotive.get(session, _id=locomotive_id)

        await asyncio.sleep(station.arrival_duration)

        async with get_session_ctx() as session:
            locomotive.railwaystation = station
            session.add(locomotive)
            await session.commit()

    logging.info('Arrival Finished')

