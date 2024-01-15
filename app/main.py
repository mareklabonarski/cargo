import asyncio
import logging.config
from uuid import uuid4

import celery.result
import sqlalchemy.exc
from celery.result import AsyncResult
from pydantic import UUID4

from . import tasks
from .settings import *  # noqa
import logging.config
from typing import Optional

import sqlalchemy.exc
from fastapi import FastAPI, Depends, HTTPException, Request, status
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload
from sqlmodel import select

from .db import init_db, get_session
from .exceptions import raise_integrity_error
from .models import RailWayStation, RailWayStationModel, Locomotive, \
    RailWayStationResponse, StationRequest, TaskStatusResponse, StationResponse
from .settings import *  # noqa
from .state import redis_client, incr_app_state, decr_app_state, init_app_state

app = FastAPI()


@app.middleware("http")
async def set_app_state(request: Request, call_next):
    await incr_app_state()
    response = await call_next(request)
    await decr_app_state()
    return response


@app.on_event("startup")
async def on_startup():
    logging.info("Initializing")
    await init_db(True)
    await init_app_state()


@app.on_event("shutdown")
async def on_shutdown():
    logging.info("Shutting down...")
    await redis_client.aclose()


@app.post("/railstations", response_model=RailWayStationModel, status_code=201)
async def create_railstation(
        railwaystation: RailWayStationModel,
        session: AsyncSession = Depends(get_session),
        ) -> RailWayStation:

    railwaystation = RailWayStation(**railwaystation.model_dump())
    session.add(railwaystation)
    try:
        await session.commit()
    except IntegrityError as e:
        await session.rollback()
        raise_integrity_error(e)
    await session.refresh(railwaystation)

    return railwaystation


@app.get("/railstations", response_model=list[RailWayStationResponse], status_code=200)
async def list_railstations(
        session: AsyncSession = Depends(get_session),
        locomotive_name: Optional[str] = None,
) -> list[RailWayStationResponse]:

    stmt = (
        select(RailWayStation).options(selectinload(RailWayStation.locomotives))
        .join(Locomotive, isouter=True).distinct().order_by(RailWayStation.name)
    )
    if locomotive_name:
        stmt = stmt.where(Locomotive.name == locomotive_name)
    railwaystations = await session.exec(stmt)
    railwaystations = railwaystations.all()

    return [
        RailWayStationResponse(**station.model_dump()) for station in railwaystations
    ]


@app.get("/railstations/{_id}", response_model=RailWayStationResponse, status_code=200)
async def create_railstation(
        _id: int,
        session: AsyncSession = Depends(get_session),
) -> RailWayStationResponse:

    stmt = (
        select(RailWayStation).options(selectinload(RailWayStation.locomotives))
        .join(Locomotive, isouter=True).where(RailWayStation.id == _id).distinct()
    )
    result = await session.exec(stmt)
    try:
        railwaystation = result.one()
        return RailWayStationResponse(**railwaystation.model_dump())
    except sqlalchemy.exc.NoResultFound:
        raise HTTPException(status_code=404, detail=f'Station with id {_id} not found.')


@app.post(
    "/railstations/{railwaystation_id}/arrival",
    response_model=StationResponse, status_code=202
)
async def perform_railstation_arrival(
        railwaystation_id: int,
        request: StationRequest,
) -> StationResponse:
    locomotive = Locomotive.get(_id=request.locomotive_id)
    station = RailWayStation.get(_id=railwaystation_id)
    locomotive, station = await asyncio.gather(locomotive, station)

    if locomotive.railwaystation_id:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f'Locomotive {locomotive.name} has been already on a station {station.name}'
        )

    task_id = uuid4()
    result: AsyncResult = tasks.perform_arrival.apply_async(
        args=[railwaystation_id, request.locomotive_id, str(request.notify_url)],
        task_id=str(task_id),
    )

    return StationResponse(
        railwaystation_id=railwaystation_id,
        locomotive_id=request.locomotive_id,
        task_id=task_id,
        estimated_duration=station.arrival_duration,
        notify_url=request.notify_url,
        status=result.status
    )


@app.get(
    "/task-status/{task_id}",
    response_model=TaskStatusResponse, status_code=200
)
async def task_status(
    task_id: UUID4
) -> TaskStatusResponse:
    result = celery.result.AsyncResult(str(task_id))
    return TaskStatusResponse(task_id=task_id, status=result.status)
