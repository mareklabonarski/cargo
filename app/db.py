import asyncio
import contextlib
import logging
from asyncio import current_task

from sqlalchemy.exc import SQLAlchemyError, InvalidRequestError, DatabaseError
from sqlmodel.ext.asyncio.session import AsyncSession
from sqlalchemy.ext.asyncio import create_async_engine
from sqlalchemy.ext.asyncio import async_sessionmaker, async_scoped_session
from sqlalchemy.pool import NullPool

from . import settings

engine = create_async_engine(settings.DATABASE_URL, echo=True, future=True, poolclass=NullPool)


async def init_db(delete=False):
    from sqlmodel import SQLModel  # noqa
    async with engine.begin() as conn:
        if delete:
            try:
                logging.info("Dropping all models from database")
                await conn.run_sync(SQLModel.metadata.drop_all)
            except SQLAlchemyError:
                pass
        logging.info("Running model migration")
        await conn.run_sync(SQLModel.metadata.create_all)
        logging.info("Model migration finished")


class AsyncMultiSession(AsyncSession):
    async def refresh_all(self, *instances):
        await self.reset()

        async def refresh(instance):
            async with get_session_ctx() as session:
                try:
                    session.add(instance)
                except InvalidRequestError:
                    pass
                else:
                    await session.refresh(instance)

        return await asyncio.gather(*map(refresh, instances))


async_session = async_sessionmaker[AsyncMultiSession](
    engine, expire_on_commit=False, class_=AsyncMultiSession
)

AsyncScopedSession = async_scoped_session[AsyncMultiSession](
    async_session,
    scopefunc=current_task,
)


async def get_session(session=None) -> [AsyncMultiSession]:
    if session:
        yield session
    else:
        async with AsyncScopedSession() as session:
            try:
                yield session
            except DatabaseError:
                await session.rollback()
            finally:
                await AsyncScopedSession.remove()

get_session_ctx = contextlib.asynccontextmanager(get_session)

