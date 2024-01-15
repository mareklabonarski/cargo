import enum

from pydantic import BaseModel, HttpUrl, UUID4
from sqlmodel._compat import SQLModelConfig
from typing import Optional, List, Any
from sqlalchemy.dialects.postgresql import ENUM
from sqlmodel import SQLModel, Field, Relationship, select

from app.db import get_session_ctx


# --------------------------------- SQL MODELS ---------------------------------
class BaseSQLModel(SQLModel, table=False):
    model_config = SQLModelConfig(table=False, extra='forbid', arbitrary_types_allowed=True, from_attributes=True)

    @classmethod
    async def get(cls, session=None, _id=None, **kw) -> "RailWayStation":
        async with get_session_ctx(session) as session:
            stmt = select(cls).where(cls.id == _id)
            instance = (await session.exec(stmt)).one()
            return instance


class RailWayStationModel(BaseSQLModel):
    id: Optional[int] = Field(default=None, primary_key=True)
    name: str = Field(unique=True)
    longitude: float
    latitude: float
    arrival_duration: float
    departure_duration: float


class EngineType(enum.Enum):
    fuel = "fuel"
    electric = "electric"
    steam = "steam"


class LocomotiveModel(BaseSQLModel):
    id: Optional[int] = Field(default=None, primary_key=True)
    name: str
    number: str
    engine_type: str = ENUM(EngineType)
    railwaystation_id: Optional[int] = Field(default=None, foreign_key="railwaystation.id")


class RailWayStation(RailWayStationModel):
    model_config = SQLModelConfig(table=True, extra='forbid', arbitrary_types_allowed=True, from_attributes=True)

    locomotives: Optional[List["Locomotive"]] = Relationship(back_populates="railwaystation")

    def model_dump(self, related=True, **kwargs):  # could not dump with related :(
        instance = super().model_dump(**kwargs)
        if related:
            instance.update({
                "locomotives": [locomotive.model_dump(related=False) for locomotive in self.locomotives]
            })
        return instance


class Locomotive(LocomotiveModel):
    model_config = SQLModelConfig(table=True, extra='forbid', arbitrary_types_allowed=True, from_attributes=True)

    railwaystation: Optional["RailWayStation"] = Relationship(back_populates="locomotives")

    def model_dump(self, related=True, **kwargs):  # could not dump with related :(
        instance = super().model_dump(**kwargs)
        if related:
            instance.update({
                "railwaystation": self.railwaystation.model_dump(related=False)
            })
        return instance


# --------------------------------- Response MODELS ---------------------------------
class RailWayStationResponse(RailWayStationModel):
    locomotives: List["LocomotiveModel"] = []


class ArrivalDepartureStatus(enum.Enum):
    #: Task state is unknown (assumed pending since you know the id).
    PENDING = 'PENDING'
    #: Task was received by a worker (only used in events).
    RECEIVED = 'RECEIVED'
    #: Task was started by a worker (:setting:`task_track_started`).
    STARTED = 'STARTED'
    #: Task succeeded
    SUCCESS = 'SUCCESS'
    #: Task failed
    FAILURE = 'FAILURE'
    #: Task was revoked.
    REVOKED = 'REVOKED'
    #: Task was rejected (only used in events).
    REJECTED = 'REJECTED'
    #: Task is waiting for retry.
    RETRY = 'RETRY'
    IGNORED = 'IGNORED'


class StationRequest(BaseModel):
    locomotive_id: int
    notify_url: HttpUrl | None


class TaskStatusResponse(BaseModel):
    task_id: UUID4
    status: str = ArrivalDepartureStatus


class StationResponse(BaseModel):
    locomotive_id: int
    railwaystation_id: int
    notify_url: HttpUrl | None
    task_id: UUID4
    estimated_duration: float
    status: ArrivalDepartureStatus


class AppStatusResponse(BaseModel):
    request_counter: int
