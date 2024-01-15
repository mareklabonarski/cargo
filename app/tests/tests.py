import asyncio
import json
import logging
from typing import Union
from uuid import uuid4, UUID

import pytest
from starlette import status

from app.models import RailWayStation, Locomotive, ArrivalDepartureStatus
from app.tests.conftest import client


@pytest.mark.parametrize(
    'payload, status_code, error', [
        (
            {
                "name": "Warsaw East", "longitude": 52.237049, "latitude": 21.017532,
                "arrival_duration": 60, "departure_duration": 120
            },
            status.HTTP_201_CREATED,
            None
        ),
        (
            {
                "name": "Warsaw East", "longitude": 52.237049, "latitude": 21.017532,
                "arrival_duration": 60, "departure_duration": 120
            },
            status.HTTP_409_CONFLICT,
            'DETAIL:  Key (name)=(Warsaw East) already exists.'
        ),
        (
                {
                    "name": "Gdynia East", "longitude": "a string", "latitude": 21.017532,
                    "arrival_duration": 60, "departure_duration": 120
                },
                status.HTTP_422_UNPROCESSABLE_ENTITY,
                [{"type": "float_parsing", "loc": ["body", "longitude"],
                  "msg": "Input should be a valid number, unable to parse string as a number",
                  "input": "a string", "url": "https://errors.pydantic.dev/2.5/v/float_parsing"}]

        ),
        (
                {
                    "name": "Warsaw North", "longitude": 52.237049, "latitude": 21.017532,
                    "arrival_duration": 60, "departure_duration": 120, "extra": "extra"
                },
                status.HTTP_422_UNPROCESSABLE_ENTITY,
                [{"type": "extra_forbidden", "loc": ["body", "extra"], "msg": "Extra inputs are not permitted",
                  "input": "extra", "url": "https://errors.pydantic.dev/2.5/v/extra_forbidden"}]
        ),
        (
            {
                "arrival_duration": 60, "departure_duration": 120
            },
            status.HTTP_422_UNPROCESSABLE_ENTITY,
            [{"type": "missing", "loc": ["body", "name"], "msg": "Field required",
              "input": {"arrival_duration": 60, "departure_duration": 120},
              "url": "https://errors.pydantic.dev/2.5/v/missing"},
             {"type": "missing", "loc": ["body", "longitude"], "msg": "Field required",
              "input": {"arrival_duration": 60, "departure_duration": 120},
              "url": "https://errors.pydantic.dev/2.5/v/missing"},
             {"type": "missing", "loc": ["body", "latitude"], "msg": "Field required",
              "input": {"arrival_duration": 60, "departure_duration": 120},
              "url": "https://errors.pydantic.dev/2.5/v/missing"}]

        )
    ]
)
@pytest.mark.asyncio(scope="session")
async def test_create_railstation(client, payload: dict, status_code: int, error: str):
    response = client.post(
        "/railstations", json=payload
    )

    assert response.status_code == status_code
    created = response.json()

    if error is not None:
        logging.info(json.dumps(created['detail']))
        assert created["detail"] == error
    else:
        assert created | payload == created


@pytest.mark.parametrize(
    'locomotive_name, station_names, locomotive_names', [
        (
                'Locomotive 0', ['Station 0'], [['Locomotive 0', 'Locomotive 1']]
        ),
        (
                'Locomotive 2', [], []
        ),
        (
                None, ['Station 0', 'Station 1', 'Station 2'], [['Locomotive 0', 'Locomotive 1'], [], []]
        )
    ]
)
@pytest.mark.asyncio(scope="session")
async def test_list_stations(
        client, db_cleanup, test_data: list[list[Union[RailWayStation, Locomotive]]],
        locomotive_name: str,
        station_names: list[str], locomotive_names: list[list[str]]
):
    response = client.get(
        "/railstations", params={'locomotive_name': locomotive_name}
    )

    assert response.status_code == status.HTTP_200_OK

    stations = response.json()
    assert [station['name'] for station in stations] == station_names
    assert [[locomotive['name'] for locomotive in station['locomotives']] for station in stations] == locomotive_names


@pytest.mark.parametrize(
    '_id, status_code, station_name, locomotive_names, error', [
        (
            1, status.HTTP_200_OK, 'Station 0', ['Locomotive 0', 'Locomotive 1'], None
        ),
        (
                1000, status.HTTP_404_NOT_FOUND, None, None, 'Station with id 1000 not found.'
        )
    ]
)
@pytest.mark.asyncio(scope="session")
async def test_get_station(
        client, db_cleanup, test_data: list[list[Union[RailWayStation, Locomotive]]],
        _id, status_code,
        station_name: str, locomotive_names: list[str], error: str
):
    response = client.get(
        f"/railstations/{_id}"
    )

    assert response.status_code == status_code

    response = response.json()
    if status_code != status.HTTP_200_OK:
        response['detail'] = error
    else:
        station = response
        assert station['name'] == station_name
        assert [locomotive['name'] for locomotive in station['locomotives']] == locomotive_names


@pytest.mark.asyncio(scope="session")
async def test_perform_arrival(
    client, db_cleanup, test_data: list[list[Union[RailWayStation, Locomotive]]],
):
    stations, locomotives = test_data
    station, locomotive = stations[-1], locomotives[-1]
    station: RailWayStation
    notify_url = 'http://localhost/'

    response = client.get(
        f"/railstations/{station.id}"
    )
    assert response.status_code == status.HTTP_200_OK

    _station = response.json()
    assert [_['name'] for _ in _station['locomotives']] == []

    response = client.post(
        f"/railstations/{station.id}/arrival", json={
            'locomotive_id': locomotive.id,
            'notify_url': notify_url
        }
    )

    assert response.status_code == status.HTTP_202_ACCEPTED
    data = response.json()

    assert data['locomotive_id'] == locomotive.id
    assert data['railwaystation_id'] == station.id
    assert data['estimated_duration'] == station.arrival_duration
    assert data['notify_url'] == notify_url
    assert data['status'] in [ArrivalDepartureStatus.STARTED.value, ArrivalDepartureStatus.PENDING.value]

    task_id = data.get('task_id')
    try:
        UUID(task_id)
    except ValueError as e:
        pytest.fail(str(e))

    await asyncio.sleep(2)

    response = client.get(
        f"/task-status/{task_id}"
    )

    assert response.status_code == status.HTTP_200_OK
    data = response.json()

    assert data['status'] in [ArrivalDepartureStatus.STARTED.value, ArrivalDepartureStatus.PENDING.value]
    assert data['task_id'] == task_id

    await asyncio.sleep(station.arrival_duration)

    response = client.get(
        f"/task-status/{task_id}"
    )

    assert response.status_code == status.HTTP_200_OK
    data = response.json()

    assert data['status'] == ArrivalDepartureStatus.SUCCESS.value
    assert data['task_id'] == task_id

    response = client.get(
        f"/railstations/{station.id}"
    )
    assert response.status_code == status.HTTP_200_OK

    _station = response.json()
    assert [_['name'] for _ in _station['locomotives']] == [locomotive.name]

    response = client.post(
        f"/railstations/{station.id}/arrival", json={
            'locomotive_id': locomotive.id,
            'notify_url': notify_url
        }
    )

    assert response.status_code == status.HTTP_409_CONFLICT
    assert response.json()['detail'] == f'Locomotive {locomotive.name} has been already on a station {station.name}'







