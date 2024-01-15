import pytest_asyncio
from starlette.testclient import TestClient

from app.db import init_db, get_session_ctx
from app.main import app
from .. import settings
from ..models import RailWayStation, Locomotive, EngineType
from ..settings import *

settings.DATABASE_URL = (
    f"postgresql+asyncpg://{env('POSTGRES_USER')}:{env('POSTGRES_PASSWORD')}"
    f"@db:{env('POSTGRES_PORT')}/test_db_{env('POSTGRES_DB')}"
)


@pytest_asyncio.fixture(scope="session")
async def client():
    with TestClient(app) as client:
        yield client


@pytest_asyncio.fixture
async def db_cleanup(session):
    await init_db(True)
    yield


@pytest_asyncio.fixture(scope="session")
async def session():
    async with get_session_ctx() as session:
        yield session


@pytest_asyncio.fixture
async def test_data(client, session):
    stations, locomotives = [], []

    for i in range(3):
        stations.append(
            RailWayStation(
                name=f'Station {i}',
                longitude=52.237049,
                latitude=52.237049,
                arrival_duration=30,
                departure_duration=5,
            )
        )
        locomotives.append(
            Locomotive(
                name=f'Locomotive {i}',
                number=f'Number {i}',
                engine_type=EngineType.fuel.value,
            )
        )

    locomotives[0].railwaystation = stations[0]
    locomotives[1].railwaystation = stations[0]
    session.add_all(stations + locomotives)
    await session.commit()
    await session.refresh_all(*stations, *locomotives)

    return stations, locomotives
