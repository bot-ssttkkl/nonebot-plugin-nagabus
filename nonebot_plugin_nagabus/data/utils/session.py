import contextvars
from contextlib import AbstractAsyncContextManager, asynccontextmanager

from nonebot import logger
from sqlalchemy.ext.asyncio import AsyncSession
from nonebot_plugin_datastore.db import get_engine

_nagabus_current_session = contextvars.ContextVar("_nagabus_current_session")


@asynccontextmanager
async def _use_session() -> AbstractAsyncContextManager[AsyncSession]:
    try:
        yield _nagabus_current_session.get()
    except LookupError:
        session = AsyncSession(get_engine())
        logger.trace("sqlalchemy session was created")
        token = _nagabus_current_session.set(session)

        try:
            yield session
        finally:
            await session.close()
            logger.trace("sqlalchemy session was closed")
            _nagabus_current_session.reset(token)
