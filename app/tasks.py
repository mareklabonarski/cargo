import asyncio
import contextlib
import logging
from functools import wraps
from typing import Callable, Optional

import httpx
from celery import Celery

from app.db import get_session_ctx
from app.models import RailWayStation, Locomotive, ArrivalDepartureStatus
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


async def _perform_arrival(station_id: int, locomotive_id: int) -> None:
    async with get_session_ctx() as session:
        station: RailWayStation = await RailWayStation.get(session, _id=station_id)
        locomotive = await Locomotive.get(session, _id=locomotive_id)

    await asyncio.sleep(station.arrival_duration)

    async with get_session_ctx() as session:
        locomotive.railwaystation = station
        session.add(locomotive)
        await session.commit()


@celery.task
@run_async
async def perform_arrival(station_id: int, locomotive_id: int, notify_url: Optional[str] = None) -> None:
    status = ArrivalDepartureStatus.SUCCESS.value

    async with set_app_busy():
        try:
            await _perform_arrival(station_id, locomotive_id)
        except Exception as e:  # noqa
            logging.error('Error occurred while performing arrival', exc_info=e)
            status = ArrivalDepartureStatus.FAILURE.value

    if notify_url:
        async with httpx.AsyncClient() as client:
            try:
                response = await client.get(notify_url, params={
                    'railwaystation_id': station_id,
                    'locomotive_id': locomotive_id,
                    'notify_url': notify_url,
                    'status': status,
                })
            except Exception as e:
                logging.error(f'Could not send notify request to {notify_url} with status {status}. {str(e)}')

    logging.info('Arrival Finished')

